import json
import sys
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))

from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.adaptive_bridge import AdaptiveBridgeConfig, AdaptiveClosureBridge
from generative_origami.simulation.ccd_motion import RigidMechanismInterval


class AdaptiveClosureBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SingleVertexMechanism(generate_fold(parse_target("狗")))
        path = REPO_ROOT / "experiments" / "current" / "baseline_inputs" / "dog_layer_order_keyframes.json"
        cls.frames = json.loads(path.read_text(encoding="utf-8"))

    def test_static_closed_bridge_is_finite_tolerance_only(self):
        report = AdaptiveClosureBridge(self.m).build([self.m.flat, self.m.flat])
        self.assertTrue(report["continuous_closure_within_tolerance"])
        self.assertFalse(report["exact_manifold_claimed"])
        self.assertFalse(report["continuous_collision_detection_certified"])
        self.assertEqual(report["segment_count"], 1)

    def test_projection_repairs_real_internal_violation_and_all_segments_recertify(self):
        a, b = [np.asarray(self.frames[i]["angles_rad"]) for i in (15, 16)]
        self.assertEqual(RigidMechanismInterval(self.m, a, b).continuous_closure()["status"], "UNCERTAIN")
        bridge = AdaptiveClosureBridge(self.m)
        report = bridge.build([a, b])
        self.assertTrue(report["continuous_closure_within_tolerance"], report["interval_counts"])
        segments = report["intervals"][0]["segments"]
        self.assertGreater(len(segments), 1)
        self.assertEqual(segments[0]["source_parameter_interval"][0], 0.)
        self.assertEqual(segments[-1]["source_parameter_interval"][1], 1.)
        for left, right in zip(segments, segments[1:]):
            self.assertEqual(left["source_parameter_interval"][1], right["source_parameter_interval"][0])
            np.testing.assert_array_equal(left["q1"], right["q0"])
        for segment in segments:
            result = RigidMechanismInterval(self.m, segment["q0"], segment["q1"]).continuous_closure(
                tolerance=bridge.config.closure_tolerance)
            self.assertEqual(result["status"], "PASS")
            self.assertLessEqual(result["continuous_upper_bound"], bridge.config.closure_tolerance)

    def test_sector_clipping_is_explicit_and_large_changes_are_rejected(self):
        bridge = AdaptiveClosureBridge(self.m)
        outside = self.m.flat.copy()
        outside[0] = -self.m.signs[0] * 1e-9
        node, record = bridge.repair_node(outside, source_index=7)
        self.assertEqual(record["status"], "PASS")
        self.assertTrue(record["changed"])
        self.assertNotEqual(record["clip_delta"][0], 0.)
        np.testing.assert_array_equal(node, self.m.flat)
        outside[0] = -self.m.signs[0] * .01
        node, record = bridge.repair_node(outside)
        self.assertEqual(record["status"], "UNCERTAIN")
        self.assertEqual(record["reason"], "NODE_CORRECTION_EXCEEDS_BUDGET")
        np.testing.assert_array_equal(node, outside)

    def test_budget_exhaustion_never_passes(self):
        a, b = [self.frames[i]["angles_rad"] for i in (15, 16)]
        bridge = AdaptiveClosureBridge(self.m, AdaptiveBridgeConfig(max_closure_checks_per_interval=1))
        result = bridge.build([a, b])
        self.assertFalse(result["continuous_closure_within_tolerance"])
        self.assertEqual(result["closure_checks"], 1)
        segments = result["intervals"][0]["segments"]
        self.assertTrue(all(s["status"] == "UNCERTAIN" for s in segments))
        self.assertTrue(all(s["reason"] == "CLOSURE_CHECK_BUDGET_EXHAUSTED" for s in segments))

    def test_small_rotation_log_does_not_select_near_pi_fallback(self):
        bridge = AdaptiveClosureBridge(self.m)
        q = self.m.flat.copy()
        q[0] = self.m.signs[0] * 7e-8
        expected = np.r_[self.m.rays[0]["unit2"], 0.] * q[0]
        np.testing.assert_allclose(bridge.closure_residual(q), expected, atol=1e-15, rtol=0.)
        _, record = bridge.repair_node(q)
        self.assertEqual(record["status"], "PASS")
        self.assertLessEqual(record["projected_closure_error"], bridge.config.projection_tolerance)

    def test_invalid_inputs_and_depth_limit_fail_closed(self):
        with self.assertRaises(ValueError):
            AdaptiveBridgeConfig(max_bridge_depth=-1)
        with self.assertRaises(ValueError):
            AdaptiveBridgeConfig(projection_tolerance=4e-6)
        with self.assertRaises(ValueError):
            AdaptiveClosureBridge(self.m).build([self.m.flat])
        with self.assertRaises(ValueError):
            AdaptiveClosureBridge(self.m).build([self.m.flat, [float("nan")] * self.m.n])
        a, b = [self.frames[i]["angles_rad"] for i in (15, 16)]
        result = AdaptiveClosureBridge(self.m, AdaptiveBridgeConfig(max_bridge_depth=0)).build([a, b])
        self.assertFalse(result["continuous_closure_within_tolerance"])
        self.assertEqual(result["intervals"][0]["segments"][0]["reason"], "BRIDGE_SUBDIVISION_DEPTH_EXHAUSTED")


if __name__ == "__main__":
    unittest.main()