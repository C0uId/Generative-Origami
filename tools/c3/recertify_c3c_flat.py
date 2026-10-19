"""Recheck all nine cells affected by the audited Flat evaluator bound repair.

The complete 162-interval run must finish first. The middle and Goal code,
inputs and geometry are unchanged by this repair. No old Flat PASS is reused.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
ROOT = REPO_ROOT
sys.path.insert(0, str(ROOT))
from singular_contact_motion import (B, DEFAULT_OUTPUT as OUT, ORDER, SOURCE, digest,
    final_gate, joined, replay_plan, unresolved_record, whole_interval_bounds)
from tools.motion_repair.repair_motion import aggregate_cells
sys.path.insert(0, str(REPO_ROOT / "tools" / "certification"))
from certify_motion import write_json
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.continuous_ccd import ContinuousPathCertifier, CertificationConfig
from generative_origami.simulation.singular_bridge import FlatSingularBridgeBuilder


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = time.perf_counter()
    data = json.loads((OUT / "interval_certificates.json").read_text(encoding="utf-8"))
    if len(data["intervals"]) != 162 or file_hash(SOURCE) != data["source_sha256"]:
        raise ValueError("Complete run or unchanged source is missing")
    m = SingleVertexMechanism(generate_fold(parse_target("狗")))
    baseline = json.loads((B / "interval_certificates.json").read_text(encoding="utf-8"))
    nodes = [np.asarray(c["repaired"], float) for c in json.loads((B / "repaired_source_knots.json").read_text(encoding="utf-8"))]
    builder = FlatSingularBridgeBuilder(m)
    certifier = ContinuousPathCertifier(m, layer_order=ORDER, config=CertificationConfig(**data["ccd_config"]))
    untouched = digest(data["intervals"][9:])
    before_counts = data["counts"].copy()
    prepared_path = OUT / "flat_recheck"
    prepared = None
    if (prepared_path / "metadata.json").exists():
        meta = json.loads((prepared_path / "metadata.json").read_text(encoding="utf-8"))
        checks = [meta["source_sha256"] == file_hash(SOURCE),
                  meta["singular_module_sha256"] == file_hash(REPO_ROOT / "src/generative_origami/simulation/singular_bridge.py"),
                  meta["source_knot_records_sha256"] == file_hash(B / "repaired_source_knots.json"),
                  meta["ccd_config"] == data["ccd_config"], meta["interval_indices"] == list(range(9)),
                  meta.get("completed") is True, meta.get("interval_count") == 9,
                  meta.get("layer_order") == ORDER]
        if not all(checks):
            raise ValueError("Prepared Flat recheck provenance does not match current source/config")
        if any(file_hash(prepared_path / name) != expected
               for name, expected in meta["interval_files_sha256"].items()):
            raise ValueError("Prepared Flat recheck certificate hash mismatch")
        prepared = [json.loads((prepared_path / f"interval_{i:03d}.json").read_text(encoding="utf-8")) for i in range(9)]
    for i in range(9):
        if prepared is not None:
            result = prepared[i]
            if result["interval"] != i:
                raise ValueError("Wrong prepared Flat source interval")
            fresh = aggregate_cells(i, result["plan"], result["cell_certificates"], True)
            if fresh["status"] != result["ccd_status"] or fresh["closure_status"] != result["closure_status"]:
                raise ValueError("Prepared Flat certificate disagrees with independent aggregation")
            data["intervals"][i] = result
            write_json(OUT / "certificates" / f"interval_{i:03d}.json", result)
            print(f"Flat fresh worker recheck {i}/8: {result['status']}, closure={result['closure_status']}", flush=True)
            continue
        motions, plan = builder.build_interval(nodes[i], nodes[i+1], i)
        attempt = deepcopy(plan)
        valid, error = joined(motions, nodes[i], nodes[i+1])
        exact = bool(motions and valid and plan.get("continuous_join_passed")
                     and all(c.get("construction_status") == "PASS" and c.get("exact_seam_claimed") for c in plan["cells"]))
        if not exact:
            plan = deepcopy(baseline["intervals"][i]["plan"])
            motions = replay_plan(m, nodes, i, plan)
        certs = []
        for j, (motion, description) in enumerate(zip(motions, plan["cells"])):
            cert = certifier.certify_defined_motion(motion, j)
            cert["source_parameter_interval"] = description["source_parameter_interval"]
            cert["whole_interval_bounds"] = whole_interval_bounds(motion, certifier)
            certs.append(cert)
        result = aggregate_cells(i, plan, certs, True)
        result.update(ccd_status=result["status"], exact_bridge_passed=exact,
            bridge_attempt=attempt, baseline_plan_preserved=plan == baseline["intervals"][i]["plan"],
            endpoint_join_error=error,
            audit_recertification="Ideal analytic chart; evaluator error included in joint refinement and feature chord enclosure")
        if not exact:
            if result["status"] == "PASS":
                result["status"] = "UNCERTAIN"
            result["reasons"] = sorted(set(result["reasons"] + ["EXACT_ENDPOINT_BRIDGE_NOT_PROVEN"]))
        data["intervals"][i] = result
        write_json(OUT / "certificates" / f"interval_{i:03d}.json", result)
        print(f"Flat recheck {i}/8: {result['status']}, closure={result['closure_status']}, exact={exact}", flush=True)
    if untouched != digest(data["intervals"][9:]):
        raise ValueError("Unaffected intervals changed during Flat recheck")
    intervals = data["intervals"]
    joins = []
    for left, right in zip(intervals[:9], intervals[1:10]):
        qa = np.asarray(left["plan"]["cells"][-1]["q1"])
        qb = np.asarray(right["plan"]["cells"][0]["q0"])
        error = float(np.max(np.abs(qa-qb)))
        joins.append({"interval_boundary": right["interval"], "max_angle_evaluation_difference": error,
                      "passed": error <= 2e-11})
    data["global_join_passed"] = data["global_join_passed"] and all(j["passed"] for j in joins)
    data["counts"] = {s:sum(c["status"] == s for c in intervals) for s in ("PASS", "COLLISION", "UNCERTAIN")}
    data["raw_ccd_counts"] = dict(Counter(c["ccd_status"] for c in intervals))
    data["closure_counts"] = dict(Counter(c["closure_status"] for c in intervals))
    data["max_continuous_closure_bound"] = max(cell["hinge_closure"]["continuous_upper_bound"] for c in intervals for cell in c["cell_certificates"])
    data["generated_cell_count"] = sum(c["cell_count"] for c in intervals)
    data["cell_motion_kinds"] = dict(Counter(p["kind"] for c in intervals for p in c["plan"]["cells"]))
    data["exact_endpoint_interval_count"] = sum(c["exact_bridge_passed"] for c in intervals if c["interval"] not in range(9,70))
    data["whole_path_exact_manifold_claimed"] = all(c["exact_bridge_passed"] for c in intervals)
    data["remaining_intervals"] = [c["interval"] for c in intervals if c["status"] != "PASS"]
    certified = final_gate(intervals, data["middle_intervals_preserved"], data["global_join_passed"])
    data["continuous_collision_detection_certified"] = certified
    data["status"] = "CONTINUOUS_RIGID_PATH_COLLISION_CERTIFIED" if certified else "CONTINUOUS_RIGID_PATH_NOT_CERTIFIED"
    data["flat_recheck_seconds"] = time.perf_counter()-start
    if prepared is not None:
        data["flat_recheck_worker_seconds"] = meta["elapsed_seconds"]
    data["elapsed_seconds"] += data["flat_recheck_seconds"]
    data["flat_bound_audit_repair"] = {"affected_source_intervals": list(range(9)),
        "all_affected_intervals_recertified": True, "unaffected_certificates_sha256": untouched,
        "singular_module_sha256": file_hash(REPO_ROOT / "src/generative_origami/simulation/singular_bridge.py"),
        "counts_before_recheck": before_counts, "counts_after_recheck": data["counts"],
        "rechecked_global_joins_including_protected_boundary": joins,
        "motion_definition": "Ideal analytic implicit deflated h; finite Taylor is a bounded evaluator, never a replacement curve",
        "repairs": ["joint refinements include total evaluation error", "feature chord enclosure includes endpoint evaluation error", "ideal/evaluator contract made explicit"],
        "rerun_scope": "Every one of 162 intervals ran in the complete audit, then all nine intervals affected by this bound repair ran again"}
    write_json(OUT / "interval_certificates.json", data)
    write_json(OUT / "report.json", {k:v for k,v in data.items() if k != "intervals"})
    write_json(OUT / "remaining_failures.json", [unresolved_record(c) for c in intervals if c["status"] != "PASS"])
    write_json(OUT / "flat_bound_audit_repair.json", data["flat_bound_audit_repair"])
    lines = ["# C3-C 连续认证区间表", "", "| 区间 | Result | Closure | Exact bridge | 原因 |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| [{c['interval']:03d}](certificates/interval_{c['interval']:03d}.json) | {c['status']} | {c['closure_status']} | {c['exact_bridge_passed']} | {'; '.join(c['reasons'])} |" for c in intervals]
    (OUT / "INTERVAL_SUMMARY.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"counts": data["counts"], "status": data["status"], "affected_intervals_rechecked": 9}))
    return 0 if certified else 2


if __name__ == "__main__":
    raise SystemExit(main())