"""POC01-007C3-B: construct explicit closure bridges and audit their full motion.

Exit 0: complete continuous collision certification. Exit 2: completed but
not certified (also closure-only mode). Exit 3: construction/input unavailable.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "certification"))
from certify_motion import write_json
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.ccd_adapter import get_backend, BackendUnavailable
from generative_origami.simulation.closure_path import ClosurePathConfig, HybridClosurePath
from generative_origami.simulation.continuous_ccd import CertificationConfig, ContinuousPathCertifier
from generative_origami.simulation.spherical_bridge import BridgeUnavailable
import numpy as np

DEFAULT_INPUT = REPO_ROOT / "experiments/current/baseline_inputs/dog_layer_order_keyframes.json"
DEFAULT_OUTPUT = REPO_ROOT / "work/repair_motion"


def aggregate_cells(index, plan, certificates, collision_checked=True):
    closure_pass = bool(certificates) and all(c["hinge_closure"]["status"] == "PASS" for c in certificates)
    joined = plan["continuous_join_passed"]
    descriptions = plan.get("cells",[])
    covered = len(descriptions) == len(certificates) and bool(certificates)
    previous = 0.
    for description in descriptions:
        a,b = description["source_parameter_interval"]
        covered &= (a == previous and 0 <= a < b <= 1 and description["construction_status"] == "PASS")
        previous = b
    covered &= previous == 1.
    expected_pairs=set(itertools.combinations(range(8),2))
    complete_pairs = not collision_checked or all(len(c["pairs"]) == 28
        and {tuple(p["panels"]) for p in c["pairs"]} == expected_pairs for c in certificates)
    statuses = [c["status"] for c in certificates]
    underlying_pass = collision_checked and all(c.get("sector_passed",False)
        and all(p["status"] == "PASS" for p in c["pairs"]) for c in certificates)
    all_pass = bool(statuses) and all(s == "PASS" for s in statuses) and joined and covered and complete_pairs and closure_pass and underlying_pass
    status = "COLLISION" if "COLLISION" in statuses else "PASS" if all_pass else "UNCERTAIN"
    reasons = sorted({r for c in certificates if c["status"] != "PASS" for r in c["reasons"]})
    if not joined:
        reasons.append("CELL_ANGLE_JOIN_NOT_PROVEN")
    if not covered or not complete_pairs:
        reasons.append("CELL_OR_PAIR_COVERAGE_NOT_PROVEN")
    if collision_checked and not underlying_pass and all(s == "PASS" for s in statuses):
        reasons.append("UNDERLYING_SECTOR_OR_PAIR_NOT_PASS")
    if not collision_checked:
        reasons.append("COLLISION_NOT_CHECKED")
    return {"interval": index, "keyframes": [index,index+1], "status": status,
            "reasons": reasons or ["ALL_CONTINUOUS_GATES_PASS"],
            "closure_status": "PASS" if closure_pass and joined and covered else "UNCERTAIN",
            "coverage_passed":bool(covered and complete_pairs),
            "collision_checked": collision_checked, "cell_count": len(certificates),
            "plan": plan, "cell_certificates": certificates}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backend", choices=["reference","native"], default="reference")
    parser.add_argument("--closure-only", action="store_true")
    parser.add_argument("--analytic-depth", type=int, default=3)
    parser.add_argument("--curve-depth", type=int, default=3)
    parser.add_argument("--feature-budget", type=int, default=64)
    args = parser.parse_args(argv)
    start = time.perf_counter()
    try:
        source = json.loads(args.input.read_text(encoding="utf-8"))
        m = SingleVertexMechanism(generate_fold(parse_target("狗")))
        if len(source) != 163:
            raise ValueError("Expected original 163 Dog keyframes")
        for i, frame in enumerate(source):
            q, xyz = np.asarray(frame["angles_rad"],float), np.asarray(frame["panels_xyz"],float)
            if (frame.get("index",i) != i or q.shape != (m.n,) or xyz.shape != (m.n,3,3)
                    or not np.isfinite(q).all() or not np.isfinite(xyz).all()
                    or np.max(np.abs(np.asarray(m.panel_triangles(q))-xyz)) > 1e-9):
                raise ValueError(f"Invalid rigid source keyframe {i}")
        config = ClosurePathConfig(analytic_depth=args.analytic_depth)
        builder = HybridClosurePath(m,config)
        nodes, changes = builder.repair_nodes([frame["angles_rad"] for frame in source])
        write_json(args.out / "repaired_source_knots.json", changes)
        backend = get_backend(args.backend)
        certifier = ContinuousPathCertifier(m,layer_order=[7,6,5,0,4,1,3,2],backend=backend,
            config=CertificationConfig(max_curve_depth=args.curve_depth,max_feature_subdivisions=args.feature_budget))
        intervals, counts, kinds = [], Counter(), Counter()
        cell_count = 0
        max_closure_bound = 0.
        for i, (left,right) in enumerate(zip(nodes,nodes[1:])):
            motions, plan = builder.build_interval(left,right,i)
            if not motions or len(motions) != len(plan["cells"]):
                raise ValueError(f"Empty or mismatched constructed cells for source interval {i}")
            certificates = []
            for j, (motion,description) in enumerate(zip(motions,plan["cells"])):
                kinds[description["kind"]] += 1
                if args.closure_only:
                    closure = motion.continuous_closure(tolerance=config.closure_tolerance)
                    certificate = {"interval":j,"status":"UNCERTAIN","reasons":["COLLISION_NOT_CHECKED"],
                                   "hinge_closure":closure,"pairs":[]}
                else:
                    certificate = certifier.certify_defined_motion(motion,j)
                certificate["source_parameter_interval"] = description["source_parameter_interval"]
                certificates.append(certificate)
                max_closure_bound = max(max_closure_bound,certificate["hinge_closure"]["continuous_upper_bound"])
            result = aggregate_cells(i,plan,certificates,not args.closure_only)
            intervals.append(result)
            counts[result["status"]] += 1
            cell_count += len(certificates)
            write_json(args.out / "certificates" / f"interval_{i:03d}.json",result)
            if i % 10 == 0 or i == 161:
                print(f"interval {i:03d}/161: {result['status']}, closure={result['closure_status']}, cells={len(certificates)}; counts={dict(counts)}",flush=True)
        all_pass = len(intervals) == 162 and all(c["status"] == "PASS" for c in intervals)
        closure_counts = dict(Counter(c["closure_status"] for c in intervals))
        report = {"schema_version":1,"experiment_id":"C3C_BASELINE_REPAIR_WORK",
            "status":"CONTINUOUS_RIGID_PATH_COLLISION_CERTIFIED" if all_pass else "CONTINUOUS_RIGID_PATH_NOT_CERTIFIED",
            "continuous_collision_detection_certified":all_pass,
            "historical_baseline_status":"RIGID_PATH_LAYER_ORDER_VALIDATED",
            "continuous_closure_within_tolerance":closure_counts.get("PASS",0) == 162,
            "whole_path_exact_manifold_claimed":False,"collision_checked":not args.closure_only,
            "source_keyframe_count":163,"source_interval_count":162,"generated_cell_count":cell_count,
            "counts":{s:counts[s] for s in ("PASS","COLLISION","UNCERTAIN")},
            "closure_counts":closure_counts,"cell_motion_kinds":dict(kinds),
            "max_continuous_closure_bound":max_closure_bound,
            "source_sha256":hashlib.sha256(args.input.read_bytes()).hexdigest(),
            "max_source_knot_correction":max(c["correction_norm"] for c in changes),
            "source_knots_changed":sum(c["correction_norm"]>0 for c in changes),
            "config":asdict(config),"ccd_config":asdict(certifier.config),
            "backend":backend.backend_info(),"native_tight_inclusion_used":bool(backend.backend_info().get("native",False)),
            "elapsed_seconds":time.perf_counter()-start,
            "motion_definition":"Joined regular spherical 3R cells plus explicitly recorded finite-tolerance q-linear rigid FK fallback cells",
            "numeric_scope":"Analytic bounds with conditional float64 reference guards; not formal interval arithmetic or a native Tight-Inclusion run",
            "upgrade_gate":"All cells, pairs, closure, nonlinear sectors and joins in all 162 source intervals must PASS; no unknown may inherit certification",
            "intervals":intervals}
        write_json(args.out / "interval_certificates.json",report)
        summary = {k:v for k,v in report.items() if k != "intervals"}
        write_json(args.out / "report.json",summary)
        table=["# C3-B source-interval certificates","",
               "| Source interval | Result | Closure | Cells | Reasons |","| --- | --- | --- | --- | --- |"]
        for c in intervals:
            i=c["interval"]
            table.append(f"| [{i:03d}](certificates/interval_{i:03d}.json) | {c['status']} | {c['closure_status']} | {c['cell_count']} | {'; '.join(c['reasons'])} |")
        (args.out / "INTERVAL_SUMMARY.md").write_text("\n".join(table)+"\n",encoding="utf-8")
        print(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False))
        return 0 if all_pass else 2
    except (BackendUnavailable,BridgeUnavailable,ValueError,OSError,TypeError,KeyError) as exc:
        print(json.dumps({"status":"UNCERTAIN","reason":"BRIDGE_OR_INPUT_UNAVAILABLE",
                          "error":str(exc),"continuous_collision_detection_certified":False},ensure_ascii=False),file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())