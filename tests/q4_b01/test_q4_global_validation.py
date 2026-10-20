import copy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from base_intake import inspect
from q4_cp_candidate import build_medium_medium_cp, FACE_IDS
from q4_global_validation import local_vertex_checks, fan_adapter, motion_probe, validation_report

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'experiments/q4_b01/Q4-B01-GLOBAL-VALIDATION'


class Q4GlobalValidationTests(unittest.TestCase):
    def test_all_interior_vertices_measured_including_subdivisions(self):
        rows = local_vertex_checks(build_medium_medium_cp())
        self.assertEqual([r['vertex_index'] for r in rows], [8,9,10])
        self.assertEqual([r['degree'] for r in rows], [8,2,2])
        for row in rows:
            self.assertEqual((row['kawasaki'], row['maekawa']), ('PASS','PASS'))
            np.testing.assert_allclose(row['alternating_sums_deg'], [180,180], atol=1e-10)

    def test_coordinate_perturbation_is_not_a_hardcoded_local_pass(self):
        cp = build_medium_medium_cp()
        cp['vertices_coords'][3][1] += 0.03
        row = next(r for r in local_vertex_checks(cp) if r['vertex_index'] == 8)
        self.assertEqual(row['kawasaki'], 'FAIL')
        self.assertNotEqual(row['sector_angles_deg'], [45]*8)

    def test_mv_mutation_exposes_maekawa_and_adapter_limit(self):
        cp = build_medium_medium_cp()
        cp['edges_assignment'][14] = 'M'
        row = next(r for r in local_vertex_checks(cp) if r['vertex_index'] == 9)
        self.assertEqual(row['maekawa'], 'FAIL')
        self.assertEqual(motion_probe(cp)['status'], 'UNKNOWN')
        self.assertIn('SUBDIVISION_MV_MISMATCH', motion_probe(cp)['reason'])

    def test_unassigned_local_crease_remains_unknown(self):
        cp = build_medium_medium_cp()
        cp['edges_assignment'][8] = 'F'
        row = next(r for r in local_vertex_checks(cp) if r['vertex_index'] == 8)
        self.assertEqual(row['kawasaki'], 'UNKNOWN')
        self.assertEqual(row['maekawa'], 'UNKNOWN')

    def test_adapter_handles_center_not_at_zero_and_preserves_face_ids(self):
        cp = build_medium_medium_cp()
        mechanism, center, sectors = fan_adapter(cp)
        self.assertEqual(center, 8)
        self.assertEqual(mechanism.n, 8)
        self.assertEqual(set(sectors), set(range(8)))
        order = list(reversed(range(len(cp['vertices_coords']))))
        inverse = {old:new for new,old in enumerate(order)}
        changed = copy.deepcopy(cp)
        changed['vertices_coords'] = [cp['vertices_coords'][i] for i in order]
        changed['edges_vertices'] = [[inverse[i] for i in e] for e in cp['edges_vertices']]
        changed['faces_vertices'] = [[inverse[i] for i in f] for f in cp['faces_vertices']]
        other, reindexed_center, other_sectors = fan_adapter(changed)
        self.assertEqual(reindexed_center, inverse[8])
        self.assertEqual(sectors, other_sectors)
        np.testing.assert_allclose(mechanism.signs, other.signs)

    def test_single_path_failure_is_not_global_infeasibility(self):
        probe = motion_probe(build_medium_medium_cp())
        self.assertEqual(probe['status'], 'FAIL')
        self.assertEqual(probe['global_foldability'], 'UNKNOWN')
        self.assertEqual([r['status'] for r in probe['samples']], ['PASS']+['FAIL']*7+['PASS'])
        half = probe['samples'][4]
        self.assertAlmostEqual(half['closure_residual_rad'], 2.680409687897, places=9)
        self.assertGreater(half['max_shared_vertex_gap_unit'], 0.8)
        self.assertFalse(probe['continuous_motion_certified'])
        for gate in ('collision','contact','layer_order'):
            self.assertEqual(probe[gate], 'UNKNOWN')

    def test_failed_probe_still_uses_full_rigid_material_polygons(self):
        cp = build_medium_medium_cp()
        probe = motion_probe(cp)
        for sample in probe['samples']:
            self.assertEqual([f['face_id'] for f in sample['full_faces']], list(FACE_IDS))
            for f, raw in zip(sample['full_faces'], cp['faces_vertices']):
                self.assertEqual(f['vertex_indices'], raw)
                for i in range(len(raw)):
                    for j in range(i):
                        self.assertAlmostEqual(math.dist(f['vertices_coords'][i], f['vertices_coords'][j]),
                            math.dist(cp['vertices_coords'][raw[i]], cp['vertices_coords'][raw[j]]), places=10)
        # Short solver rays must not truncate the original full material faces.
        self.assertEqual(probe['samples'][0]['full_faces'][0]['vertex_indices'], [0,1,9,8])

    def test_material_areas_and_claim_boundaries(self):
        report = validation_report(build_medium_medium_cp())
        trace = report['material_traceability']
        self.assertEqual(trace['planar_ownership'], 'PASS')
        self.assertEqual(trace['assembled_folded_material_flow'], 'UNKNOWN')
        areas = trace['total_area_mm2_exact']
        self.assertEqual(sum(map(Fraction, areas.values())), 40000)
        self.assertEqual(areas['MAT_BODY'], '20000')
        self.assertEqual(areas['MAT_HEAD'], '5000')
        self.assertEqual(areas['MAT_TAIL'], '5000')
        for leg in ('MAT_FL','MAT_FR','MAT_HL','MAT_HR'):
            self.assertEqual(areas[leg], '2500')
        self.assertFalse(report['physical_verified'])
        self.assertFalse(report['continuous_motion_verified'])
        self.assertTrue(report['unresolved'])

    def test_invalid_planar_input_is_rejected_without_certificate(self):
        cp = build_medium_medium_cp()
        cp['vertices_coords'][0] = [-0.01,0]
        self.assertEqual(motion_probe(cp)['status'], 'UNKNOWN')
        with self.assertRaisesRegex(ValueError, 'PLANAR_GATE_FAILED'):
            validation_report(cp)


class Q4GlobalEvidenceTests(unittest.TestCase):
    def test_exact_evidence_manifest_and_candidate_hashes(self):
        manifest = json.loads((EVIDENCE / 'evidence_manifest.json').read_text())
        self.assertGreater(len(manifest['files']), 10)
        for name, sha in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), sha, name)
        cp = json.loads((EVIDENCE / 'candidate.fold').read_text())
        report = json.loads((EVIDENCE / 'global_validation.json').read_text())
        self.assertEqual(cp, build_medium_medium_cp())
        self.assertEqual(manifest['cp_geometry_sha256'], inspect(cp)['geometry_sha256'])
        runtime = validation_report(cp)
        self.assertEqual(report['cp_geometry_sha256'], runtime['cp_geometry_sha256'])
        self.assertEqual(report['local_vertices'], runtime['local_vertices'])
        self.assertEqual(report['motion_probe']['failed_sample_times'], runtime['motion_probe']['failed_sample_times'])
        for stored, actual in zip(report['motion_probe']['samples'], runtime['motion_probe']['samples']):
            self.assertEqual(stored['status'], actual['status'])
            self.assertAlmostEqual(stored['closure_residual_rad'], actual['closure_residual_rad'], places=9)
            self.assertAlmostEqual(stored['max_shared_vertex_gap_unit'], actual['max_shared_vertex_gap_unit'], places=9)

    def test_printable_kit_and_blank_physical_records(self):
        svg = ET.parse(EVIDENCE/'printable_cp.svg').getroot()
        self.assertEqual(svg.attrib['width'], '210mm')
        self.assertEqual(svg.attrib['height'], '297mm')
        text = ''.join(svg.itertext())
        self.assertIn('200 x 200 mm', text)
        self.assertIn('Uniform-angle trial FAILED', text)
        for face_id in FACE_IDS:
            self.assertIn(face_id, text)
        ids = json.loads((EVIDENCE/'stable_ids.json').read_text())
        self.assertEqual(len(ids['vertices']), 11)
        self.assertEqual(len(ids['edges']), 18)
        self.assertEqual(set(ids['faces']), set(FACE_IDS))
        record = json.loads((EVIDENCE/'physical_evidence_template.json').read_text())
        self.assertFalse(record['physical_base_certified'])
        self.assertFalse(record['validated_folding_sequence_available'])
        for key in ('design_specimen','independent_refold_1','independent_refold_2'):
            self.assertEqual(record[key]['status'], 'NOT_RUN')
            self.assertEqual(record[key]['result'], 'UNKNOWN')
            self.assertEqual(record[key]['macro_actions'], [])


if __name__ == '__main__':
    unittest.main()
