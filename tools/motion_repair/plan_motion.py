from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))

from generative_origami.semantic import parse_target
from generative_origami.foldgen import generate_fold
from generative_origami.simulation import SingleVertexMechanism, LayerContactModel
from generative_origami.planner import BidirectionalManifoldPlanner


def main():
    parser = argparse.ArgumentParser(description="Rigid single-vertex manifold motion planner")
    parser.add_argument("query", help="例如：狗 / 狐狸 / 千纸鹤")
    parser.add_argument("--mode", choices=["strict", "contact-aware", "layer-order", "off"], default="layer-order")
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--out", default="runtime_outputs")
    args = parser.parse_args()

    fold = generate_fold(parse_target(args.query))
    mechanism = SingleVertexMechanism(fold)
    layer_model = LayerContactModel(mechanism) if args.mode == "layer-order" else None
    planner = BidirectionalManifoldPlanner(
        mechanism,
        seed=42,
        collision_check=args.mode != "off",
        contact_aware=args.mode == "contact-aware",
        layer_model=layer_model,
    )
    result = planner.plan(max_iterations=args.iterations)
    out = Path(args.out) / (args.query.strip() or "query") / "motion"
    out.mkdir(parents=True, exist_ok=True)
    (out / "motion_plan.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "collision_mode": result.get("collision_mode"),
        "iterations": result.get("iterations"),
        "path_length_nodes": result.get("path_length_nodes"),
        "keyframe_count": result.get("keyframe_count"),
        "max_closure_error": result.get("densify_audit",{}).get("max_closure_error"),
        "layer_order": None if layer_model is None else layer_model.report.order,
        "output": str(out / "motion_plan.json"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()