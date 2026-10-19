"""Independent exact-arithmetic audit of the fixed-axis all-pi endpoint.

The intended folded endpoint consists of halfturns, so its planar rotation
product can be evaluated with rational arithmetic without sin/acos calls.
This audit does not certify a motion, modify axes, or change the saved goal.
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "motion_repair"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "certification"))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation.single_vertex import SingleVertexMechanism


def main():
    mechanism = SingleVertexMechanism(generate_fold(parse_target("狗")))
    product = [[Fraction(1), Fraction(0)], [Fraction(0), Fraction(1)]]
    order = list(range(1, mechanism.n)) + [0]
    for k in order:
        x, y = map(Fraction, mechanism.rays[k]["unit2"])
        norm_squared = x*x + y*y
        halfturn = [[2*x*x/norm_squared - 1, 2*x*y/norm_squared],
                    [2*x*y/norm_squared, 2*y*y/norm_squared - 1]]
        product = [[sum(product[i][j]*halfturn[j][column] for j in range(2))
                    for column in range(2)] for i in range(2)]
    identity = all(product[i][j] == Fraction(i == j)
                   for i in range(2) for j in range(2))
    source = REPO_ROOT / "src/generative_origami/foldgen.py"
    result = {
        "method": "Exact Fraction product of H(v)=2*v*v.T/(v.T*v)-I",
        "axis_representation": "Each stored binary64 unit2 component treated as its exact rational value",
        "ideal_goal_angles": "Every joint is a mathematical +pi or -pi halfturn; both have the same rotation",
        "cyclic_product_order": order,
        "exact_planar_halfturn_product_is_identity": identity,
        "product_fraction_strings": [[str(x) for x in row] for row in product],
        "product_approximation": [[float(x) for x in row] for row in product],
        "exact_nonzero_entry": [0, 1] if product[0][1] else None,
        "geometry_modified": False,
        "goal_modified": False,
        "motion_certified": False,
        "foldgen_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "interpretation": (
            "The intended all-pi goal on these fixed axes is not an exact closed endpoint. "
            "This does not exclude another nearby endpoint, another geometry, or a finite-tolerance bridge; "
            "none is silently substituted by this audit."
            if not identity else "The ideal all-pi endpoint passes this exact identity check only; no motion is certified."
        ),
        "scope": "An independent static algebraic endpoint identity audit, not a continuous collision certificate or a general origami impossibility claim",
    }
    output = REPO_ROOT / "experiments/current/POC01-007C3-C_SINGULAR_CONTACT_EXACT_BRIDGE/independent_goal_halfturn_audit.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"exact_halfturn_identity": identity,
                      "P01_approximation": float(product[0][1]),
                      "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())