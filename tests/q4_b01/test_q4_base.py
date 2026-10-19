import copy
from fractions import Fraction
import unittest
from q4_base import manifest, validate_manifest, material_at, compile_layout, import_cp, project_q4, LEVELS
from test_base_intake import square

class Q4Tests(unittest.TestCase):
    def test_coverage(self):
        m=manifest(); self.assertTrue(validate_manifest(m))
        regions={r['id']:0 for r in m['material_regions']}
        for x in range(16):
            for y in range(16): regions[material_at((x+.5)*12.5,(y+.5)*12.5)]+=1
        self.assertEqual(regions,dict(MAT_FL=16,MAT_FR=16,MAT_HL=16,MAT_HR=16,MAT_HEAD=32,MAT_BODY=128,MAT_TAIL=32))
    def test_boundaries(self):
        self.assertEqual(material_at(50,150),'MAT_HEAD')
        self.assertEqual(material_at(150,150),'MAT_FR')
        self.assertEqual(material_at(200,200),'MAT_FR')
        for x in [-1,201,float('nan'),True]:
            with self.assertRaises(ValueError):material_at(x,0)
    def test_overlap_rejected(self):
        m=manifest();m['material_regions'][0]['bounds_mm'][2]=100
        with self.assertRaises(ValueError):validate_manifest(m)
    def test_nine_real_layout_hashes(self):
        layouts=[compile_layout({'leg_budget':a,'tail_budget':b}) for a in LEVELS for b in LEVELS]
        self.assertEqual(len({r['geometry_sha256'] for r in layouts}),9)
        self.assertEqual(len({r['topology_sha256'] for r in layouts}),1)
        self.assertTrue(all(r['cp'] is None and not r['certified'] for r in layouts))
    def test_directions_and_independence(self):
        for parameter,path_index in [('leg_budget',0),('tail_budget',4)]:
            values=[]; other=[]
            for level in LEVELS:
                params={'leg_budget':'medium','tail_budget':'medium'};params[parameter]=level
                layout=compile_layout(params)
                values.append(layout['source_paths'][path_index]['source_path_length_mm'])
                other.append(layout['source_paths'][4 if path_index==0 else 0]['points_mm'])
            self.assertTrue(values[0]<values[1]<values[2]); self.assertEqual(other[0],other[2])
    def test_legacy_direction(self):
        p=project_q4({'body_to_leg_ratio':'long','tail_ratio':'short'})
        self.assertEqual(p['implemented'],{'leg_budget':'short','tail_budget':'short'})
        self.assertTrue(p['approximation_notes'])
    def test_numeric_and_certified_requests_rejected(self):
        for value in [0.25,25,True,'extra_long']:
            with self.assertRaises(ValueError):compile_layout({'leg_budget':value,'tail_budget':'short'})
        with self.assertRaisesRegex(ValueError,'CERTIFIED_DOMAIN_EMPTY'):
            compile_layout({'leg_budget':'short','tail_budget':'short'},certified=True)
    def test_reproducible_and_head_fixed(self):
        a=compile_layout({'leg_budget':'short','tail_budget':'long'})
        self.assertEqual(a,compile_layout({'leg_budget':'short','tail_budget':'long'}))
        b=compile_layout({'leg_budget':'long','tail_budget':'short'})
        self.assertEqual(a['geometry']['material_regions'],b['geometry']['material_regions'])
    def test_cp_cross_region_mapping(self):
        mapped=import_cp(square(),['face-lower','face-upper'])
        totals={}
        for f in mapped['face_material_map']:
            self.assertEqual(sum(Fraction(p['face_fraction_exact']) for p in f['material_parts']),1)
            for p in f['material_parts']:totals[p['material_id']]=totals.get(p['material_id'],0)+Fraction(p['area_mm2_exact'])
        self.assertEqual(totals['MAT_BODY'],20000)
        self.assertEqual(totals['MAT_TAIL'],5000)
        self.assertEqual(sum(totals.values()),40000)
        self.assertFalse(mapped['physical_verified'])
    def test_invalid_cp_ids(self):
        with self.assertRaises(ValueError):import_cp(square(),['same','same'])
        d=square();d['faces_vertices']=[]
        with self.assertRaises(ValueError):import_cp(d,[])

if __name__=='__main__':unittest.main()