"""Goal contact chart regression and fail-closed proof tests."""
import json
import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT/'src'))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.contact_bridge import (
    ContactState, GoalContactBridgeBuilder, GoalContactBridgeConfig, GoalMaterialContact)


class GoalContactBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SingleVertexMechanism(generate_fold(parse_target('狗')))
        records = json.loads((REPO_ROOT/'experiments/current/baseline_inputs/repaired_source_knots.json').read_text(encoding='utf8'))
        cls.source = [np.asarray(r['repaired']) for r in records]
        cls.builder = GoalContactBridgeBuilder(cls.m)
        cls.nodes, cls.repairs = cls.builder.repair_nodes(cls.source)
        cls.motions, cls.plan = cls.builder.build_interval(cls.nodes[80], cls.nodes[81], 80)

    def test_shared_repair_keeps_certified_path_and_goal_exactly_unchanged(self):
        for index in list(range(71))+[162]:
            np.testing.assert_array_equal(self.nodes[index], self.source[index])
        self.assertEqual(len(self.repairs), 163)
        for repaired, original, record in zip(self.nodes, self.source, self.repairs):
            np.testing.assert_allclose(repaired-original, record['delta'], atol=0., rtol=0.)
            self.assertLessEqual(record['correction_norm'], 1e-3)
            self.assertTrue(self.m.sector_valid(repaired, tol=0.))
        self.assertEqual(self.nodes[80][3], -math.pi)
        self.assertEqual(self.nodes[80][7], -math.pi)
        self.assertTrue(self.repairs[80]['chart_after_active_set_update']['recomputed'])
        self.assertIn(3, self.repairs[80]['chart_after_active_set_update']['active_boundary_joints'])

    def test_regular_chart_supplies_whole_interval_geometric_bounds_and_joins(self):
        self.assertTrue(self.motions)
        self.assertTrue(self.plan['continuous_join_passed'])
        previous = self.nodes[80]
        for motion, cell in zip(self.motions, self.plan['cells']):
            np.testing.assert_allclose(previous, motion.q0, atol=2e-11, rtol=0.)
            previous = motion.q1
            self.assertEqual(motion.continuous_closure()['status'], 'PASS')
            self.assertEqual(cell['regularity']['status'], 'PASS')
            self.assertEqual(cell['construction_status'], 'PASS')
            self.assertTrue(np.isfinite(motion.speed_bound(3)))
            self.assertTrue(np.isfinite(motion.acceleration_bound(3)))
            self.assertGreater(motion.acceleration_bound(3), 0.)
            lo, hi = motion.vertex_bounds(3)
            # This only tests enclosure consistency; it never sets proof status.
            for t in [0., .137, .5, .823, 1.]:
                point = motion.triangle(3, t)
                self.assertTrue(np.all(point >= lo))
                self.assertTrue(np.all(point <= hi))
            self.assertTrue(cell['chart_after_active_set_update']['recomputed'])
        np.testing.assert_allclose(previous, self.nodes[81], atol=2e-11, rtol=0.)

    def test_fixed_contact_has_finite_material_map_and_layer_order(self):
        self.assertEqual(len(self.builder.contact.patches), 28)
        proof = self.motions[0].contact_pair_certificate((2, 3))
        self.assertIsNotNone(proof)
        self.assertEqual(proof['status'], 'PASS')
        self.assertEqual(proof['state'], ContactState.CONTACT.value)
        self.assertEqual(proof['signed_gap_lower_bound'], 0.)
        self.assertFalse(proof['whole_panel_exemption'])
        self.assertGreaterEqual(len(proof['material_coordinates']), 3)
        self.assertEqual(proof['layer_order'], [7, 6])
        self.assertIn('fixed goal Rodrigues product', proof['relative_pose_identity'])

    def test_equal_contact_endpoints_never_establish_persistent_material_pose(self):
        curve = SimpleNamespace(q0=self.m.goal.copy(), q1=self.m.goal.copy(),
                                fixed_joint_values=np.full(self.m.n, np.nan))
        self.assertIsNone(self.builder.contact.fixed_goal_patch(curve, (2, 3)))
        curve.fixed_joint_values[3] = np.nextafter(-math.pi, 0.)
        self.assertIsNone(self.builder.contact.fixed_goal_patch(curve, (2, 3)))

    def test_unknown_signed_gap_stays_unknown_after_successful_closure(self):
        audit = self.motions[0].contact_audit()
        self.assertEqual(audit['status'], 'UNCERTAIN')
        self.assertFalse(audit['sampled_gap_used_as_proof'])
        unproved = [p for p in audit['pairs'] if p['status'] == 'UNCERTAIN']
        self.assertTrue(unproved)
        self.assertTrue(all(p['signed_gap_lower_bound'] < 0. for p in unproved))
        self.assertTrue(all(not p['endpoint_contact_exemption'] for p in unproved))
        self.assertEqual(self.motions[0].continuous_closure()['status'], 'PASS')

    def test_event_roots_are_isolated_in_declared_free_coordinates(self):
        parent = SimpleNamespace(free=[3], reference_q0=self.nodes[80].copy(), reference_q1=self.nodes[81].copy(), dq=np.zeros(self.m.n))
        parent.reference_q0[3] = -math.pi
        parent.dq[3] = .1
        events = self.builder.contact.events(parent)
        release = [e for e in events if e['joint'] == 3][0]
        self.assertEqual(release['event'], 'RELEASE')
        self.assertEqual(release['time_interval'], [-0., -0.])
        self.assertTrue(release['requires_tangent_and_chart_recomputation'])
        parent.reference_q0[3] = -math.pi+.1
        parent.dq[3] = -.2
        event = [e for e in self.builder.contact.events(parent) if e['joint'] == 3][0]
        self.assertEqual(event['event'], 'CONTACT')
        self.assertAlmostEqual(event['time_interval'][0], .5)
        parent.free = []
        parent.reference_q0[3] = -math.pi
        events = self.builder.contact.events(parent)
        nonlinear = [e for e in events if e['joint'] == 3][0]
        self.assertEqual(nonlinear['status'], 'UNCERTAIN')

    def test_singular_goal_is_rejected_without_fallback_or_endpoint_exemption(self):
        motions, plan = self.builder.build_interval(self.nodes[161], self.nodes[162], 161)
        self.assertFalse(motions)
        self.assertEqual(plan['construction_status'], 'UNCERTAIN')
        self.assertFalse(plan['continuous_join_passed'])
        self.assertFalse(plan['finite_tolerance_fallback_created'])
        self.assertEqual(len(plan['atlas_attempts']), 8)
        self.assertTrue(any('SINGULAR' in a['reason'] for a in plan['atlas_attempts']))

    def test_builder_cannot_modify_certified_source_intervals(self):
        with self.assertRaises(ValueError):
            self.builder.build_interval(self.nodes[40], self.nodes[41], 40)
        with self.assertRaises(ValueError):
            GoalContactBridgeConfig(max_depth=-1)
        with self.assertRaises(ValueError):
            GoalMaterialContact(self.m, list(range(8)))


if __name__ == '__main__':
    unittest.main()
