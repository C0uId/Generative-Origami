import hashlib
import json
import math
from pathlib import Path
import unittest

import numpy as np

from q4_cp_candidate import build_medium_medium_cp
from q4_global_validation import fan_adapter
from q4_rigid_path_search import check_configuration, evaluate_interpolation, search

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'experiments/q4_b01/Q4-B01-ALTERNATIVE-RIGID-PATH'


class RigidPathSearchTests(unittest.TestCase):
    def setUp(self):
        self.cp = build_medium_medium_cp()
        self.m, _, _ = fan_adapter(self.cp)

    def test_independent_check_recovers_known_counterexample(self):
        row = check_configuration(self.cp, self.m.signs*math.pi/2, .5)
        self.assertEqual(row['status'], 'FAIL')
        self.assertAlmostEqual(row['closure_rad'], 2.6804096878968, places=10)
        self.assertAlmostEqual(row['shared_vertex_gap_unit'], .898408786493275, places=10)
        self.assertLess(row['independent_agreement_rad'], 1e-10)
        self.assertLess(row['rigid_distance_error_unit'], 1e-12)

    def test_closure_alone_cannot_accept_wrong_progress(self):
        self.assertEqual(check_configuration(self.cp, np.zeros(8), 0)['status'], 'PASS')
        wrong = check_configuration(self.cp, np.zeros(8), .5)
        self.assertEqual(wrong['closure_rad'], 0)
        self.assertEqual(wrong['status'], 'FAIL')

    def test_nontrivial_compatible_hinge_configuration_passes(self):
        # Opposite collinear valley half-rays: a known single straight hinge.
        # It uses only two creases, so this is a checker control, not the target
        # all-crease fold or a new search experiment.
        q = np.zeros(8)
        q[0] = q[4] = math.pi/2
        row = check_configuration(self.cp, q, .125)
        self.assertEqual(row['status'], 'PASS')
        self.assertEqual(row['strictly_active_creases'], 2)
        self.assertLess(row['shared_vertex_gap_unit'], 1e-12)

    def test_full_turn_cannot_evade_angle_domain(self):
        row = check_configuration(self.cp, self.m.signs*2*math.pi, 1)
        self.assertFalse(row['angle_domain_valid'])
        self.assertEqual(row['status'], 'FAIL')

    def test_invalid_numeric_inputs_rejected(self):
        for q in ([0]*7, [float('nan')]*8, [float('inf')]*8):
            with self.assertRaises(ValueError):
                check_configuration(self.cp, q, .5)
        for t in (-.1, 1.1, float('nan')):
            with self.assertRaises(ValueError):
                check_configuration(self.cp, [0]*8, t)

    def test_endpoint_pass_does_not_certify_interpolation(self):
        knots = [{'target': 0., 'q_rad': [0.]*8}, {'target': 1., 'q_rad': (self.m.signs*math.pi).tolist()}]
        result = evaluate_interpolation(self.cp, knots)
        self.assertEqual(result['failed_knot_targets'], [])
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['continuous_certificate'])

    def test_sampling_never_promotes_to_continuous_pass(self):
        # An extremely short interval stays under the numeric tolerance, but
        # finite samples still do not establish an interval certificate.
        knots = [{'target': 0., 'q_rad': [0.]*8}, {'target': 1e-10, 'q_rad': (self.m.signs*math.pi*1e-10).tolist()}]
        result = evaluate_interpolation(self.cp, knots)
        self.assertTrue(all(r['status'] == 'PASS' for r in result['samples']))
        self.assertEqual(result['status'], 'UNKNOWN')

    def test_low_budget_retains_failed_trials_and_uncertainty(self):
        result = search(self.cp, targets=3, max_calls=1)
        for sweep in result['sweeps']:
            trial = next(r for r in sweep['attempts'] if r['target'] == .5)
            self.assertEqual(trial['solver']['status'], 'BUDGET_EXHAUSTED')
            self.assertEqual(trial['residual_calls'], 1)
            self.assertEqual(trial['status'], 'FAIL')
            self.assertEqual(sweep['rejected_targets'], [.5])
        self.assertEqual(result['global_foldability'], 'UNKNOWN')
        self.assertEqual(result['continuous_rigid_path'], 'UNKNOWN')
        self.assertFalse(result['physical_verified'])

    def test_search_budget_and_interpolation_order_guards(self):
        for kwargs in ({'targets':34}, {'targets':True}, {'max_calls':301}, {'max_calls':0}):
            with self.assertRaises(ValueError):
                search(self.cp, **kwargs)
        with self.assertRaises(ValueError):
            evaluate_interpolation(self.cp, [{'target':1., 'q_rad': [0]*8}, {'target':0., 'q_rad':[0]*8}])

    def test_committed_trials_replay_and_manifest_matches(self):
        report = json.loads((EVIDENCE/'search_report.json').read_text())
        manifest = json.loads((EVIDENCE/'evidence_manifest.json').read_text())
        for path, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(), digest, path)
        self.assertEqual(report['settings']['targets_per_sweep'], 33)
        self.assertEqual(report['settings']['max_residual_calls_per_solve'], 300)
        for sweep in report['sweeps']:
            self.assertEqual(len(sweep['attempts']), 33)
            for trial in sweep['attempts']:
                actual = check_configuration(self.cp, trial['q_rad'], trial['target'])
                self.assertEqual(trial['status'], actual['status'])
                self.assertAlmostEqual(trial['closure_rad'], actual['closure_rad'], places=10)
                self.assertLessEqual(trial['residual_calls'], 300)
            knots = sorted([r for r in sweep['attempts'] if r['status']=='PASS'], key=lambda r:r['target'])
            actual = evaluate_interpolation(self.cp, knots)
            self.assertEqual(actual['status'], sweep['interpolation']['status'])
        for key in ('global_foldability','continuous_rigid_path','collision','contact','signed_gap','layer_order','final_semantic_material_flow'):
            self.assertEqual(report[key], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
