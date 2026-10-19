"""Reaudit only flat endpoint intervals using the frozen ideal/evaluator contract.

Writes independent flat_recheck artifacts. It never mutates the full-run
certificates or aggregate report; the main process verifies and merges them.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

REPO_ROOT=Path(__file__).resolve().parents[2]
ROOT=REPO_ROOT
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(REPO_ROOT/"src"))
sys.path.insert(0,str(REPO_ROOT/"tools"/"motion_repair"))
sys.path.insert(0,str(REPO_ROOT/"tools"/"certification"))
from singular_contact_motion import (
    B,DEFAULT_OUTPUT,SOURCE,ORDER,JOIN_TOL,digest,joined,
    whole_interval_bounds,aggregate_cells,replay_plan,write_json)
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.singular_bridge import FlatSingularBridgeBuilder
from generative_origami.simulation.contact_bridge import GoalContactBridgeBuilder
from generative_origami.simulation.continuous_ccd import CertificationConfig,ContinuousPathCertifier
from generative_origami.simulation.ccd_adapter import get_backend
import numpy as np


class Tee:
    def __init__(self,stream,file): self.stream,self.file=stream,file
    def write(self,text):
        self.stream.write(text);self.file.write(text)
        self.stream.flush();self.file.flush()
    def flush(self): self.stream.flush();self.file.flush()


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    start=time.perf_counter()
    out=DEFAULT_OUTPUT/"flat_recheck"
    out.mkdir(parents=True,exist_ok=True)
    module=REPO_ROOT/"src/generative_origami/simulation/singular_bridge.py"
    original_stdout=sys.stdout;original_stderr=sys.stderr
    with (out/"console_output.txt").open("w",encoding="utf8") as log:
        sys.stdout=Tee(original_stdout,log);sys.stderr=Tee(original_stderr,log)
        try:
            baseline=json.loads((B/"interval_certificates.json").read_text(encoding="utf8"))
            changes=json.loads((B/"repaired_source_knots.json").read_text(encoding="utf8"))
            baseline_nodes=[np.asarray(x["repaired"],float) for x in changes]
            if len(baseline_nodes)!=163 or sha(SOURCE)!=baseline["source_sha256"]:
                raise ValueError("Source coverage/hash differs from B")
            m=SingleVertexMechanism(generate_fold(parse_target("狗")))
            nodes,repairs=GoalContactBridgeBuilder(m).repair_nodes(baseline_nodes)
            nodes=[np.asarray(q,float) for q in nodes]
            if any(not np.array_equal(nodes[i],baseline_nodes[i]) for i in range(10)):
                raise ValueError("Protected flat nodes changed during shared knot preparation")
            config=CertificationConfig(max_curve_depth=3,max_feature_subdivisions=64)
            backend=get_backend("reference")
            certifier=ContinuousPathCertifier(m,layer_order=ORDER,backend=backend,config=config)
            builder=FlatSingularBridgeBuilder(m)
            module_hash=sha(module)
            metadata={"source_sha256":sha(SOURCE),"singular_module_sha256":module_hash,
                "source_knot_records_sha256":sha(B/"repaired_source_knots.json"),
                "ccd_config":asdict(config),"interval_indices":list(range(9)),
                "fixed_nodes_sha256":digest([q.tolist() for q in nodes]),
                "baseline_nodes_sha256":digest([q.tolist() for q in baseline_nodes]),
                "flat_nodes_sha256":digest([q.tolist() for q in nodes[:10]]),
                "fixed_nodes_definition":"all 163 shared repaired nodes after frozen contact repair; flat nodes unchanged from B",
                "layer_order":ORDER,"backend":backend.backend_info(),
                "audit_reason":"Reaudit flat intervals after ideal analytic/evaluator contract, joint evaluator guard and CCD chord endpoint inflation fix",
                "interval_files_sha256":{},"completed":False}
            write_json(out/"metadata.json",metadata)
            print("Frozen singular module:",module_hash,flush=True)
            counts=Counter();results=[];previous=None;global_join=True
            for i in range(9):
                old_plan=baseline["intervals"][i]["plan"]
                motions,plan=builder.build_interval(nodes[i],nodes[i+1],i)
                attempt=deepcopy(plan)
                ok,error=joined(motions,nodes[i],nodes[i+1])
                exact=bool(motions and ok and plan.get("continuous_join_passed",False)
                    and all(c.get("construction_status")=="PASS" and c.get("exact_seam_claimed",False)
                            for c in plan["cells"])
                    and not any(c["kind"]=="FINITE_TOLERANCE_POLYLINE" for c in plan["cells"]))
                if not exact:
                    attempt["root_rejection"]="EXACT_CONSTRUCTION_OR_ENDPOINT_JOIN_NOT_PROVEN"
                    attempt["root_max_join_error"]=error
                    plan=deepcopy(old_plan)
                    motions=replay_plan(m,baseline_nodes,i,plan)
                local_join,local_error=joined(motions,nodes[i],nodes[i+1])
                if not local_join:raise ValueError(f"Endpoint join failed: {i}: {local_error}")
                if previous is not None:
                    global_join&=bool(np.max(abs(previous-motions[0].q0))<=JOIN_TOL)
                previous=motions[-1].q1
                certificates=[]
                for j,(motion,description) in enumerate(zip(motions,plan["cells"])):
                    certificate=certifier.certify_defined_motion(motion,j)
                    certificate["source_parameter_interval"]=description["source_parameter_interval"]
                    certificate["whole_interval_bounds"]=whole_interval_bounds(motion,certifier)
                    certificates.append(certificate)
                result=aggregate_cells(i,plan,certificates,True)
                result.update(ccd_status=result["status"],exact_bridge_passed=exact,
                    bridge_attempt=attempt,baseline_plan_preserved=plan==old_plan,
                    endpoint_join_error=local_error,
                    audit_recertification={"reason":metadata["audit_reason"],
                        "singular_module_sha256":module_hash,"source_sha256":metadata["source_sha256"],
                        "fixed_nodes_sha256":metadata["fixed_nodes_sha256"],"ccd_config":asdict(config)})
                if not exact:
                    if result["status"]=="PASS":result["status"]="UNCERTAIN"
                    result["reasons"]=sorted(set(result["reasons"]+["EXACT_ENDPOINT_BRIDGE_NOT_PROVEN"]))
                path=out/f"interval_{i:03d}.json"
                write_json(path,result)
                metadata["interval_files_sha256"][path.name]=sha(path)
                counts[result["status"]]+=1;results.append(result)
                print(f"interval {i:03d}/008: {result['status']}; closure={result['closure_status']}; exact={exact}; cells={len(certificates)}; elapsed={time.perf_counter()-start:.2f}s",flush=True)
            if sha(module)!=module_hash:raise ValueError("Singular module changed during flat recheck")
            metadata.update(completed=True,elapsed_seconds=time.perf_counter()-start,
                interval_count=len(results),counts={k:counts[k] for k in ("PASS","COLLISION","UNCERTAIN")},
                closure_counts=dict(Counter(x["closure_status"] for x in results)),
                cell_count=sum(x["cell_count"] for x in results),
                global_join_passed=bool(global_join),
                max_continuous_closure_bound=max(c["hinge_closure"]["continuous_upper_bound"] for r in results for c in r["cell_certificates"]))
            write_json(out/"metadata.json",metadata)
            print(json.dumps(metadata,ensure_ascii=False,indent=2,allow_nan=False),flush=True)
            return 0
        finally:
            sys.stdout=original_stdout;sys.stderr=original_stderr


if __name__=="__main__":
    raise SystemExit(run())