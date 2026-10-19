import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.continuous_ccd import CertificationConfig, ContinuousPathCertifier
from generative_origami.simulation.ccd_motion import RigidMechanismInterval


class ContinuousCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SingleVertexMechanism(generate_fold(parse_target("狗")))
        cls.frames = json.loads((REPO_ROOT / "experiments/current/baseline_inputs/dog_layer_order_keyframes.json").read_text(encoding="utf-8"))

    def certifier(self):
        return ContinuousPathCertifier(self.m, layer_order=[7, 6, 5, 0, 4, 1, 3, 2],
                                       config=CertificationConfig(max_curve_depth=0, max_feature_subdivisions=16))

    def test_all_163_keyframes_are_rigid_reconstructions_not_a_continuous_proof(self):
        self.assertEqual(len(self.frames), 163)
        for frame in self.frames:
            np.testing.assert_allclose(self.m.panel_triangles(np.asarray(frame["angles_rad"])), frame["panels_xyz"], atol=1e-12, rtol=0)
        r = self.certifier().certify_interval(self.frames[15]["angles_rad"], self.frames[16]["angles_rad"], 15)
        self.assertNotEqual(r["status"], "PASS")
        self.assertEqual(r["hinge_closure"]["status"], "UNCERTAIN")
        self.assertGreater(r["hinge_closure"]["observed_lower_bound"], 1e-4)

    def test_shared_center_is_not_a_finite_radius_exemption(self):
        m = self.m
        class StaticMotion:
            q0 = q1 = np.ones(m.n) * .3
            A = np.array([[0., 0., 0.], [2., -1., 0.], [2., 1., 0.]])
            B = np.array([[0., 0., 0.], [1., -1., -1e-8], [1., 1., 1e-8]])
            def triangle(self, panel, t):
                return self.B if panel == 2 else self.A
            def vertex_bounds(self, panel, a, b):
                tri = self.triangle(panel, a)
                return tri.copy(), tri.copy()
            def chord_error_bound(self, panel, a, b):
                return 0.
        result = self.certifier().certify_pair(StaticMotion(), (0, 2))
        # The intersection is a short segment from the common center. No
        # primitive boundary event need occur in this already intersecting state.
        self.assertEqual(result["status"], "UNCERTAIN")
        self.assertFalse(result["features"]["initial_disjointness_proven"])

    def test_goal_contact_requires_full_material_pose_not_only_pair_membership(self):
        c = self.certifier()
        motion = RigidMechanismInterval(self.m, self.m.goal, self.m.goal)
        result = c.contact.persistent_goal_patch(motion, (0, 2))
        self.assertEqual(result["status"], "PASS")
        q = self.m.goal.copy(); q[1] += 1e-5
        altered = RigidMechanismInterval(self.m, self.m.goal, q)
        self.assertIsNone(c.contact.persistent_goal_patch(altered, (0, 2)))

    def test_invalid_layer_permutation_rejected(self):
        with self.assertRaises(ValueError):
            ContinuousPathCertifier(self.m, layer_order=[0] * 8)
        with self.assertRaises(ValueError):
            ContinuousPathCertifier(self.m, layer_order=list(range(8)))

    def test_one_unknown_interval_prevents_status_upgrade(self):
        c = self.certifier()
        frames = copy.deepcopy(self.frames[:3])
        results = [{"interval": 0, "status": "PASS"}, {"interval": 1, "status": "UNCERTAIN"}]
        with patch.object(c, "certify_interval", side_effect=results):
            report = c.certify_frames(frames)
        self.assertFalse(report["continuous_collision_detection_certified"])
        self.assertEqual(report["effective_motion_status"], "RIGID_PATH_LAYER_ORDER_VALIDATED")
        with patch.object(c, "certify_interval", side_effect=results):
            stale = c.certify_frames(frames, source_status="CONTINUOUS_RIGID_PATH_COLLISION_CERTIFIED")
        self.assertNotEqual(stale["effective_motion_status"], "CONTINUOUS_RIGID_PATH_COLLISION_CERTIFIED")

    def test_mismatched_and_nonfinite_saved_geometry_rejected(self):
        c = self.certifier()
        bad = copy.deepcopy(self.frames[:2])
        bad[0]["panels_xyz"][0][1][0] += .01
        with self.assertRaises(ValueError):
            c.certify_frames(bad)
        bad = copy.deepcopy(self.frames[:2]); bad[0]["angles_rad"][0] = float("nan")
        with self.assertRaises(ValueError):
            c.certify_frames(bad)

    def test_positive_thickness_is_not_silently_assumed_by_zero_thickness_contact(self):
        with self.assertRaises(ValueError):
            CertificationConfig(minimum_separation=.01)


if __name__ == "__main__":
    unittest.main()