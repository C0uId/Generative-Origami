import math
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))

from generative_origami.semantic import parse_target
from generative_origami.foldgen import generate_fold
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.ccd_motion import RigidMechanismInterval, RigidTriangleMotion


class ContinuousRigidMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SingleVertexMechanism(generate_fold(parse_target("狗")))

    def test_fk_preserves_rigid_lengths_and_tree_hinges(self):
        motion = RigidMechanismInterval(self.m, self.m.flat, self.m.goal)
        initial = [motion.triangle(i, 0) for i in range(self.m.n)]
        for t in (0.0, 0.137, 0.5, 0.881, 1.0):
            triangles = [motion.triangle(i, t) for i in range(self.m.n)]
            for i, tri in enumerate(triangles):
                for u, v in ((0, 1), (1, 2), (2, 0)):
                    self.assertAlmostEqual(np.linalg.norm(tri[u] - tri[v]),
                                           np.linalg.norm(initial[i][u] - initial[i][v]), places=12)
                if i:
                    np.testing.assert_allclose(tri[1], triangles[i - 1][2], atol=2e-13)

    def test_real_rigid_arc_is_not_vertex_interpolation(self):
        local = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
        motion = RigidTriangleMotion(local, np.eye(3), Rotation.from_rotvec([0., 0., math.pi / 2]).as_matrix())
        midpoint = motion.triangle(0, .5)
        chord_midpoint = (motion.triangle(0, 0) + motion.triangle(0, 1)) / 2
        self.assertGreater(np.linalg.norm(midpoint[1] - chord_midpoint[1]), .25)
        self.assertAlmostEqual(np.linalg.norm(midpoint[1]), 1., places=14)

    def test_swept_bounds_enclose_curved_fk_and_shrink(self):
        motion = RigidMechanismInterval(self.m, self.m.flat, self.m.goal)
        rng = np.random.default_rng(703)
        for panel in range(self.m.n):
            for a, b in ((0., 1.), (.13, .37), (.77, .91)):
                lo, hi = motion.triangle_bounds(panel, a, b)
                vlo, vhi = motion.vertex_bounds(panel, a, b)
                rlo, rhi = motion.rotation_bounds(panel, a, b)
                for t in rng.uniform(a, b, 17):
                    tri, r = motion.triangle(panel, t), motion.rotation(panel, t)
                    self.assertTrue(np.all(tri >= lo) and np.all(tri <= hi))
                    self.assertTrue(np.all(tri >= vlo) and np.all(tri <= vhi))
                    self.assertTrue(np.all(r >= rlo) and np.all(r <= rhi))
            self.assertLessEqual(motion.chord_error_bound(panel, 0, .5),
                                 motion.chord_error_bound(panel, 0, 1) / 4 + 1e-16)

    def test_chord_error_bound_contains_actual_material_trajectory(self):
        local = np.array([[.2, .1, 0], [1., 0, 0], [.1, .8, .4]])
        motion = RigidTriangleMotion(local, np.eye(3), Rotation.from_rotvec([.9, -.4, 1.2]).as_matrix(),
                                     np.array([1., 2., 3.]), np.array([-1., 3., 2.]))
        for a, b in ((0, 1), (.1, .2), (.56, .93)):
            bound = motion.chord_error_bound(0, a, b)
            start, end = motion.triangle(0, a), motion.triangle(0, b)
            lo, hi = motion.triangle_bounds(0, a, b)
            for t in np.linspace(a, b, 31):
                alpha = (t - a) / (b - a)
                actual = motion.triangle(0, t)
                chord = (1 - alpha) * start + alpha * end
                self.assertLessEqual(float(np.linalg.norm(actual - chord, axis=1).max()), bound + 2e-14)
                self.assertTrue(np.all(actual >= lo) and np.all(actual <= hi))

    def test_closed_endpoints_do_not_certify_nonclosed_interior(self):
        # Both endpoints are independently closed.  Their linear q bridge is
        # not on the manifold and must fail even if the original frames pass.
        self.assertLess(np.linalg.norm(self.m.closure_residual(self.m.flat)), 1e-6)
        self.assertLess(np.linalg.norm(self.m.closure_residual(self.m.goal)), 1e-6)
        motion = RigidMechanismInterval(self.m, self.m.flat, self.m.goal)
        result = motion.continuous_closure()
        self.assertEqual(result["status"], "UNCERTAIN")
        self.assertEqual(result["reason"], "CLOSURE_TOLERANCE_VIOLATION_WITNESS")
        self.assertGreater(result["observed_lower_bound"], 1e-2)
        self.assertIsNotNone(result["witness"])
        self.assertGreater(result["continuous_upper_bound"], result["tolerance"])

    def test_nontrivial_closed_motion_passes_analytic_subdivision(self):
        # Creases 0 and 4 have opposite local axes. Equal rotations cancel at
        # every t; the closing radial edge is also invariant throughout.
        target = np.zeros(self.m.n)
        target[0] = target[4] = .3
        motion = RigidMechanismInterval(self.m, self.m.flat, target)
        result = motion.continuous_closure(tolerance=4e-6, max_depth=8)
        self.assertEqual(result["status"], "PASS", result)
        self.assertLessEqual(result["continuous_upper_bound"], result["tolerance"])
        self.assertGreater(result["subdivisions"], 0)
        self.assertLess(result["observed_lower_bound"], 1e-11)
        # A zero depth budget cannot certify using the same endpoints alone.
        result = motion.continuous_closure(tolerance=4e-6, max_depth=0)
        self.assertEqual(result["status"], "UNCERTAIN")

    def test_static_interval_has_continuous_certificate(self):
        motion = RigidMechanismInterval(self.m, self.m.flat, self.m.flat)
        result = motion.continuous_closure()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["subdivisions"], 0)
        self.assertLess(result["continuous_upper_bound"], 1e-10)


if __name__ == "__main__":
    unittest.main()