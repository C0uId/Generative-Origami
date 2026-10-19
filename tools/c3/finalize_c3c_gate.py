"""Recheck completed numeric evidence with the strengthened final proof gate.

This does not recompute, replace, or alter the trajectory or cell certificates.
The execution's original driver snapshot and hashes remain in provenance.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT=Path(__file__).resolve().parents[2]
ROOT=REPO_ROOT
sys.path.insert(0,str(ROOT))
from singular_contact_motion import final_gate, DEFAULT_OUTPUT as OUT
sys.path.insert(0, str(REPO_ROOT / "tools" / "certification"))
from certify_motion import write_json
from generative_origami.simulation.certification_evidence import validate_goal_contact_evidence


def sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    provenance=json.loads((OUT/"run_provenance.json").read_text(encoding="utf-8"))
    if not provenance["completed"] or provenance["interval_count"]!=162:
        raise ValueError("The complete numeric audit must finish first")
    snapshot=OUT/"run_driver_snapshot.py.txt"
    original_driver=provenance["modules_sha256"]["singular_contact_motion.py"]
    if sha(snapshot)!=original_driver:
        raise ValueError("Original execution driver snapshot mismatch")
    for path,digest in provenance["modules_sha256"].items():
        if path!="singular_contact_motion.py" and sha(ROOT/path)!=digest:
            raise ValueError(f"Numerical module changed after execution: {path}")
    data=json.loads((OUT/"interval_certificates.json").read_text(encoding="utf-8"))
    checked_goal_cells=0
    for interval in data["intervals"][70:]:
        for cell in interval["cell_certificates"]:
            active=cell["whole_interval_bounds"].get("active_set_contact_bounds")
            if active and active.get("status")=="PASS":
                if not validate_goal_contact_evidence(cell,[7,6,5,0,4,1,3,2]):
                    raise ValueError("A claimed complete contact mode proof failed independent reconstruction")
                checked_goal_cells+=1
    old=data["continuous_collision_detection_certified"]
    fresh=final_gate(data["intervals"],data["middle_intervals_preserved"],data["global_join_passed"])
    if fresh!=old:
        raise ValueError("Strengthened proof gate changes the recorded result; investigate before release")
    audit={"original_driver_sha256":original_driver,
        "current_driver_sha256":sha(ROOT/"singular_contact_motion.py"),
        "evidence_validator_sha256":sha(REPO_ROOT/"src/generative_origami/simulation/certification_evidence.py"),
        "numerical_trajectory_recomputed":False,"cell_certificates_replaced":False,
        "all_claimed_complete_goal_mode_cells_reconstructed":checked_goal_cells,
        "continuous_certification_before":old,"continuous_certification_after":fresh,
        "interval_files_sha256":{f"interval_{i:03d}.json":sha(OUT/"certificates"/f"interval_{i:03d}.json") for i in range(162)},
        "scope":"Proof-schema gate strengthened after full execution; original execution source retained. All stored numeric certificates unchanged."}
    write_json(OUT/"post_run_gate_audit.json",audit)
    data["post_run_gate_audit"]="post_run_gate_audit.json"
    write_json(OUT/"interval_certificates.json",data)
    write_json(OUT/"report.json",{k:v for k,v in data.items() if k!="intervals"})
    provenance["post_run_gate_audit"]="post_run_gate_audit.json"
    write_json(OUT/"run_provenance.json",provenance)
    print(json.dumps({"validated":True,"goal_mode_cells":checked_goal_cells,
                      "continuous_collision_detection_certified":fresh}))


if __name__=="__main__":
    main()