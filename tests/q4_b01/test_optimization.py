import json
import tempfile
import unittest
from pathlib import Path
from parameter_projector import project, grid
from failure_signatures import summarize

class OptimizationTests(unittest.TestCase):
    def test_grid(self):
        rows = grid()
        self.assertEqual(len({tuple(r['implemented'].values()) for r in rows}), 9)
        self.assertTrue(all(r['domain_status'] == 'EXPERIMENTAL_NOT_CERTIFIED' for r in rows))

    def test_boundaries_and_nonfinite(self):
        for value in [-1, 2, float('nan'), float('inf'), True]:
            with self.assertRaises(ValueError):
                project({'body_to_leg_ratio': value, 'tail_ratio': 'medium'})
        result = project({'body_to_leg_ratio': 2, 'tail_ratio': 'medium'}, policy='snap')
        self.assertEqual(result['implemented']['body_to_leg_ratio'], 'long')
        self.assertEqual(len(result['approximation_notes']), 1)

    def test_no_duplicate_parent_or_diagnostic_count(self):
        doc = {'interval': 71, 'status': 'UNCERTAIN', 'cell_certificates': [
            {'pairs': [{'panels': [0, 4], 'status': 'UNCERTAIN', 'reason': 'SUBDIVISION', 'children': [
                {'status': 'PASS', 'reason': 'OK'}, {'status': 'UNCERTAIN', 'reason': 'CONTACT'}]}],
             'diagnostic': {'status': 'UNCERTAIN', 'reason': 'OLD_WORLD_Z'}}]}
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'interval_071.json').write_text(json.dumps(doc))
            result = summarize(directory)
        self.assertFalse(result['complete_interval_coverage'])
        self.assertFalse(result['certification_changed'])
        self.assertEqual(len(result['clusters']), 1)
        self.assertEqual(result['clusters'][0]['leaf_count'], 1)
        self.assertEqual(result['clusters'][0]['reason'], 'CONTACT')

if __name__ == '__main__':
    unittest.main()