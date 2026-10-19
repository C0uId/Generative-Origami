import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))

from generative_origami.semantic import parse_target
from generative_origami.foldgen import generate_fold
from generative_origami.validate import validate_fold
from generative_origami.simulation import SingleVertexMechanism, LayerContactModel
from generative_origami.planner import BidirectionalManifoldPlanner


class ManifoldPlannerTests(unittest.TestCase):
    def setUp(self):
        self.fold = generate_fold(parse_target("狗"))
        self.m = SingleVertexMechanism(self.fold)

    def test_new_8ray_assignment_keeps_local_flatfold_rules(self):
        report = validate_fold(self.fold)
        self.assertTrue(report.passed, report.to_dict())
        radial = [a for a in self.fold["edges_assignment"] if a in {"M", "V"}]
        self.assertEqual(radial, ["M","V","M","M","V","M","V","M"])

    def test_endpoint_cones_are_seedable(self):
        flat = self.m.endpoint_cone(self.m.flat, outward=True)
        goal = self.m.endpoint_cone(self.m.goal, outward=False)
        self.assertTrue(flat.feasible, flat)
        self.assertTrue(goal.feasible, goal)
        self.assertGreater(flat.margin, 0.1)
        self.assertGreater(goal.margin, 0.1)
        self.assertLess(np.linalg.norm(self.m.closure_residual(self.m.goal)), 1e-6)

    def test_strict_collision_detects_goal_layer_contact(self):
        seeds, _ = self.m.endpoint_seeds(goal_side=True, count=1, epsilon=0.10, seed=47)
        self.assertEqual(len(seeds), 1)
        strict = self.m.collision_report(seeds[0], contact_aware=False)
        aware = self.m.collision_report(seeds[0], contact_aware=True, contact_progress_threshold=0.55)
        self.assertTrue(strict["collision"], strict)
        self.assertFalse(aware["collision"], aware)

    def test_layer_order_birrt_finds_dense_rigid_path(self):
        layer = LayerContactModel(self.m)
        self.assertTrue(layer.report.feasible, layer.report)
        self.assertGreater(layer.report.inward_progress, 0.1)
        planner = BidirectionalManifoldPlanner(
            self.m,
            seed=42,
            collision_check=True,
            layer_model=layer,
            step_size=0.22,
        )
        result = planner.plan(max_iterations=40)
        self.assertEqual(result["status"], "RIGID_PATH_LAYER_ORDER_VALIDATED")
        self.assertTrue(result["densify_audit"]["passed"])
        self.assertGreater(result["keyframe_count"], result["path_length_nodes"])
        self.assertLess(result["densify_audit"]["max_closure_error"], 2e-6)
        self.assertTrue(np.allclose(result["keyframes"][0], self.m.flat, atol=1e-8))
        self.assertTrue(np.allclose(result["keyframes"][-1], self.m.goal, atol=1e-8))



if __name__ == "__main__":
    unittest.main()