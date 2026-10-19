from pathlib import Path
import sys
import unittest
import numpy as np

REPO_ROOT=Path(__file__).resolve().parents[2]
ROOT=REPO_ROOT
sys.path.insert(0,str(REPO_ROOT/"src"))
from generative_origami.simulation.motion_cache import MemoizedMotion


class MotionCacheTests(unittest.TestCase):
    def test_cache_reuses_identical_queries_and_cannot_be_poisoned_by_callers(self):
        class Motion:
            calls=0
            motion_kind="PURE_QUERY_TEST"
            def triangle(self,p,t):
                self.calls+=1
                return np.ones((3,3))*(p+t)
            def vertex_bounds(self,p,a,b):
                return np.ones((3,3))*a,np.ones((3,3))*b
            def joint_bounds(self,a,b):
                return np.array([a]),np.array([b])
            def chord_error_bound(self,p,a,b):
                return (b-a)**2
        base=Motion()
        cache=MemoizedMotion(base)
        cache.triangle(1,.5)[:]=99.
        np.testing.assert_array_equal(cache.triangle(1,.5),np.ones((3,3))*1.5)
        self.assertEqual(base.calls,1)
        cache.vertex_bounds(0,.2,.4)[0][:]=99.
        self.assertEqual(cache.vertex_bounds(0,.2,.4)[0][0,0],.2)
        cache.joint_bounds(.2,.4)[0][:]=99.
        self.assertEqual(cache.joint_bounds(.2,.4)[0][0],.2)
        self.assertEqual(cache.motion_kind,base.motion_kind)
        self.assertEqual(cache.chord_error_bound(0,.2,.4),.2**2)
        cache.triangle(1,.6)
        self.assertEqual(base.calls,2)


if __name__=="__main__":
    unittest.main()