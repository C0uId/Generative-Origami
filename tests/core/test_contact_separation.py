"""Relative-frame whole-time and induced finite-contact proof regressions."""
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT/'src'))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.ccd_motion import RigidMechanismInterval
from generative_origami.simulation.contact_bridge import GoalContactBridgeBuilder
from generative_origami.simulation.contact_separation import RelativeContactSeparation, certify_material_pair


class RelativeContactSeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SingleVertexMechanism(generate_fold(parse_target('狗')))
        cls.prover = RelativeContactSeparation(cls.m)
        source = json.loads((REPO_ROOT/'experiments/current/baseline_inputs/repaired_source_knots.json').read_text(encoding='utf8'))
        builder = GoalContactBridgeBuilder(cls.m)
        nodes, _ = builder.repair_nodes([np.asarray(r['repaired']) for r in source])
        cls.motion = builder.build_interval(nodes[80], nodes[81], 80)[0][0]

    def test_three_forward_induced_hinges_have_finite_material_and_layer_proofs(self):
        for pair, containing, zero_vertex in [((1, 3), 'anchor', 2), ((2, 4), 'target', 1), ((5, 7), 'anchor', 2)]:
            with self.subTest(pair=pair):
                proof = certify_material_pair(self.m, self.motion, pair)
                self.assertEqual(proof['status'], 'PASS')
                self.assertEqual(proof['reason'], 'ANALYTIC_INDUCED_MATERIAL_HINGE')
                self.assertFalse(proof['uses_exact_cyclic_closure'])
                self.assertFalse(proof['whole_panel_exemption'])
                self.assertTrue(proof['distinct_original_axes_retained'])
                self.assertTrue(proof['layer_order_gate_proven'])
                self.assertEqual(proof['layer_proof']['status'], 'PASS')
                self.assertEqual(proof['material_proof']['status'], 'PASS')
                self.assertEqual(proof['layer_proof']['containing_triangle'], containing)
                self.assertEqual(proof['layer_proof']['symbolic_zero_vertices'], [0, zero_vertex])
                self.assertTrue(all(x >= 0. for x in proof['layer_proof']['coefficient_lower_bounds']))
                self.assertGreater(max(proof['layer_proof']['coefficient_lower_bounds']), .35)
                self.assertGreaterEqual(proof['patch_vertex_count'], 3)
                self.assertEqual(len(proof['material_coordinates']), proof['patch_vertex_count'])
                self.assertEqual(proof['time_interval'], [0., 1.])

    def test_reversing_layer_order_cannot_reuse_the_approach_certificate(self):
        reverse = RelativeContactSeparation(self.m, layer_order=list(reversed(self.prover.order)))
        for pair in [(1, 3), (2, 4), (5, 7)]:
            proof = reverse.induced_hinge_certificate(self.motion, pair)
            self.assertEqual(proof['status'], 'UNCERTAIN')
            self.assertIn('INDUCED_HINGE_LAYER_APPROACH_NOT_PROVEN', proof['rejections'])

    def test_only_whole_time_fixed_coordinates_establish_the_hinge_identity(self):
        q0, q1 = self.motion.q(0.), self.motion.q(1.)
        fake = SimpleNamespace(q0=q0, q1=q1, fixed_joint_values=np.full(self.m.n, np.nan),
            joint_bounds=self.motion.joint_bounds, q=self.motion.q)
        self.assertEqual(self.prover.induced_hinge_certificate(fake, (1, 3))['status'], 'UNCERTAIN')
        fake.fixed_joint_values[3] = np.nextafter(-math.pi, 0.)
        self.assertEqual(self.prover.induced_hinge_certificate(fake, (1, 3))['status'], 'UNCERTAIN')

    def test_unfolded_coplanar_endpoint_is_not_granted_a_goal_patch_exemption(self):
        q0, q1 = self.motion.q(0.), self.motion.q(1.)
        q0[2] = 0.
        motion = RigidMechanismInterval(self.m, q0, q1)
        proof = self.prover.induced_hinge_certificate(motion, (1, 3))
        self.assertEqual(proof['status'], 'UNCERTAIN')
        self.assertIn('ANGLE_RANGE_CONTAINS_UNFOLDED_COPLANAR_STATE_OR_LEAVES_SECTOR', proof['rejections'])

    def test_near_coincident_virtual_axes_do_not_create_a_multi_joint_identity(self):
        # These actual Dog pairs have nearly coincident folded rays and small
        # sampled gaps. Their multiple varying joint products are not fixed.
        for pair in [(0, 4), (0, 5), (1, 4), (1, 5)]:
            proof = self.prover.certify_pair(self.motion, pair)
            self.assertEqual(proof['status'], 'UNCERTAIN')
        # The complement would need an exact goal identity, absent in this
        # finite input. The rule deliberately does not certify (0,6) that way.
        self.assertEqual(self.prover.induced_hinge_certificate(self.motion, (0, 6))['status'], 'UNCERTAIN')

    def test_relative_interval_bounds_enclose_curved_fk_without_vertex_lerp(self):
        pair = (1, 5)
        proof = self.prover.relative_vertex_bounds(self.motion, pair)
        self.assertIsNotNone(proof)
        # Diagnostic samples verify the enclosure implementation only. They
        # never determine a certificate status or supply its extrema.
        for t in [0., .173, .51, .827, 1.]:
            rots = self.m.panel_rotations(self.motion.q(t))
            actual = self.motion.triangle(pair[1], t)@rots[pair[0]]
            self.assertTrue(np.all(actual >= proof['lower']))
            self.assertTrue(np.all(actual <= proof['upper']))
        np.testing.assert_array_equal(proof['lower'][0], np.zeros(3))
        np.testing.assert_array_equal(proof['upper'][0], np.zeros(3))

    def test_relative_plane_requires_analytic_positive_margin(self):
        flat = RigidMechanismInterval(self.m, self.m.flat, self.m.flat)
        proof = self.prover.cone_certificate(flat, (0, 2))
        self.assertEqual(proof['status'], 'PASS')
        self.assertEqual(proof['reason'], 'RELATIVE_FRAME_CONTINUOUS_SEPARATION')
        self.assertGreater(proof['margin_lower_bound'], 1e-6)
        self.assertFalse(proof['sampled_plane_used_as_proof'])
        self.assertFalse(proof['whole_panel_exemption'])
        self.assertEqual(proof['material_proof']['status'], 'PASS')
        self.assertEqual(proof['layer_proof']['status'], 'PASS')

    def test_invalid_layer_order_and_nonfinite_bounds_fail_closed(self):
        with self.assertRaises(ValueError):
            RelativeContactSeparation(self.m, layer_order=list(range(8)))
        fake = SimpleNamespace(fixed_joint_values=np.full(8, np.nan),
            joint_bounds=lambda a, b: (np.zeros(8), np.full(8, np.nan)))
        self.assertEqual(self.prover.induced_hinge_certificate(fake, (1, 3))['status'], 'UNCERTAIN')
        self.assertIsNone(self.prover.relative_vertex_bounds(fake, (1, 3)))
        with self.assertRaises(ValueError):
            self.prover.certify_pair(self.motion, (3, 1))


if __name__ == '__main__':
    unittest.main()