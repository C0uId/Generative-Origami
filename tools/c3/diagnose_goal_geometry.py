"""Record the existing Goal geometry; never snap it to an ideal new model."""
import json
from pathlib import Path
import sys

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "motion_repair"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "certification"))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism


def main():
    m = SingleVertexMechanism(generate_fold(parse_target("狗")))
    product = np.eye(3)
    axes = {}
    for k in list(range(1, m.n)) + [0]:
        axis = np.r_[m.rays[k]["unit2"], 0.]
        axes[k] = product @ axis
        product = product @ m._axis_rotation(axis, m.goal[k])
    result = {"diagnostic_only_not_an_impossibility_proof": True,
              "existing_geometry_changed": False, "existing_goal_changed": False,
              "goal_product_rotation_matrix": product.tolist(),
              "goal_product_identity_frobenius_residual": float(np.linalg.norm(product-np.eye(3), ord="fro")),
              "goal_closure_residual_norm": float(np.linalg.norm(m.closure_residual(m.goal))),
              "folded_virtual_crease_axes": {str(k): v.tolist() for k,v in sorted(axes.items())},
              "opposite_original_axis_sum_norms": [float(np.linalg.norm(
                  np.asarray(m.rays[k]["unit2"])+np.asarray(m.rays[k+4]["unit2"]))) for k in range(4)],
              "interpretation": "The finite input geometry must not be silently replaced by exactly coincident virtual A/B axes to assert pair cancellation. A small observed residual is a tolerance diagnostic, not an exact identity.",
              "terminal_bridge_evidence": "See interval 161 atlas_attempts and contact_root_causes.json; no reliable regular/deflated Goal endpoint chart was established."}
    out = REPO_ROOT / "experiments/current/POC01-007C3-C_SINGULAR_CONTACT_EXACT_BRIDGE/goal_geometry_diagnostic.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"goal_product_identity_frobenius_residual":result["goal_product_identity_frobenius_residual"],
                      "geometry_changed": False}))


if __name__ == "__main__":
    main()