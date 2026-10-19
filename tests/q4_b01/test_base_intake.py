import copy
import unittest
from base_intake import inspect

def square():
    return {'vertices_coords':[[0,0],[1,0],[1,1],[0,1]],
            'edges_vertices':[[0,1],[1,2],[2,3],[3,0],[0,2]],
            'edges_assignment':['B','B','B','B','V'], 'faces_vertices':[[0,1,2],[0,2,3]]}

class IntakeTests(unittest.TestCase):
    def test_square_completion(self):
        from square_material_candidate import complete_square
        source={'vertices_coords':[[0.5,0.5],[1,0.5],[0.5,1],[0,0.5],[0.5,0]],
                'edges_vertices':[[0,1],[0,2],[0,3],[0,4],[1,2],[2,3],[3,4],[4,1]],
                'edges_assignment':['M','M','M','V']+['B']*4}
        original=copy.deepcopy(source)
        result=complete_square(source)
        self.assertEqual(source,original)
        self.assertTrue(inspect(result)['passed'])
        self.assertEqual(inspect(result)['exact_material_area'],'1')
        self.assertEqual(len(result['faces_vertices']),4)
        self.assertEqual(result,complete_square(source))
    def test_square(self):
        r=inspect(square()); self.assertTrue(r['passed']); self.assertFalse(r['physical_base_certified'])
    def test_metadata_does_not_change_geometry(self):
        a=square(); b=copy.deepcopy(a); b['go:target']={'animal':'fox'}
        self.assertEqual(inspect(a)['geometry_sha256'],inspect(b)['geometry_sha256'])
    def test_coordinate_changes_hash(self):
        a=square(); b=copy.deepcopy(a); b['vertices_coords'][2]=[0.9,1]
        self.assertNotEqual(inspect(a)['geometry_sha256'],inspect(b)['geometry_sha256'])
        self.assertEqual(inspect(a)['topology_sha256'],inspect(b)['topology_sha256'])
        self.assertFalse(inspect(b)['passed'])
    def test_invalid_inputs(self):
        for mutation in [lambda d:d['vertices_coords'][0].__setitem__(0,float('nan')),
                         lambda d:d['edges_vertices'][0].__setitem__(0,99),
                         lambda d:d['edges_assignment'].__setitem__(4,'U'),
                         lambda d:d['faces_vertices'].pop(),
                         lambda d:d['faces_vertices'][0].reverse()]:
            d=square(); mutation(d); self.assertFalse(inspect(d)['passed'])
    def test_crossing_diagonals(self):
        d=square(); d['edges_vertices'].append([1,3]); d['edges_assignment'].append('M')
        self.assertIn('CROSSING_EDGES',[e['reason'] for e in inspect(d)['errors']])
    def test_unsplit_vertex(self):
        d=square(); d['vertices_coords'].append([0.5,0])
        self.assertIn('UNSPLIT_VERTEX_ON_EDGE',[e['reason'] for e in inspect(d)['errors']])
    def test_duplicate_face(self):
        d=square(); d['faces_vertices'].append([0,1,2]); self.assertFalse(inspect(d)['passed'])
    def test_corner_clipping(self):
        d={'vertices_coords':[[0.5,0],[1,0.5],[0.5,1],[0,0.5]],
           'edges_vertices':[[0,1],[1,2],[2,3],[3,0]], 'edges_assignment':['B']*4,
           'faces_vertices':[[0,1,2,3]]}
        result=inspect(d)
        self.assertFalse(result['passed']); self.assertEqual(result['exact_material_area'],'1/2')
        self.assertIn('BOUNDARY_CHORD_NOT_ON_SQUARE',[e['reason'] for e in result['errors']])

if __name__=='__main__': unittest.main()