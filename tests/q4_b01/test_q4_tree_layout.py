import unittest
from fractions import Fraction as F
from q4_tree_layout import tree,distances,check,solve,solve_lengths

class TreeTests(unittest.TestCase):
    def test_tree_distances(self):
        d=distances(tree(25,37.5))
        self.assertEqual(len(d),15)
        self.assertEqual(d['MAT_FL','MAT_FR'],50)
        self.assertEqual(d['MAT_FL','MAT_HL'],100)
        self.assertEqual(d['MAT_HEAD','MAT_TAIL'],F('112.5'))
    def test_exact_touch_and_penetration(self):
        d={('a','b'):F(25)}
        self.assertTrue(check({'a':[0,0],'b':[15,20]},d)[0]['passed'])
        self.assertFalse(check({'a':[0,0],'b':[15,'19.999999999999']},d)[0]['passed'])
    def test_impossible_search_is_not_global_claim(self):
        r=solve_lengths(500,500)
        self.assertEqual(r['status'],'NO_LAYOUT_ON_SEARCH_GRID')
        self.assertEqual(len(r['rejected']),16)
        self.assertTrue(r['grid_infeasibility_is_not_global_infeasibility'])
    def test_repeatability(self):
        p={'leg_budget':'medium','tail_budget':'long'}
        self.assertEqual(solve(p),solve(p))
    def test_all_presets_and_region_closures(self):
        for a in ('short','medium','long'):
            for b in ('short','medium','long'):
                r=solve({'leg_budget':a,'tail_budget':b})
                self.assertEqual(r['status'],'GRID_LAYOUT_FEASIBLE')
                self.assertEqual(len(r['checks']),15)
                self.assertTrue(all(c['passed'] for c in r['checks']))
                x,y=map(F,r['points_mm']['MAT_FL'])
                self.assertTrue(0<=x<50 and 150<y<=200)
                self.assertIsNone(r['cp'])
    def test_invalid_lengths(self):
        with self.assertRaises(ValueError):tree(0,25)

if __name__=='__main__':unittest.main()