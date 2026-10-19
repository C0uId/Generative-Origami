import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
from generative_origami.semantic import parse_target
from generative_origami.foldgen import generate_fold
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.spherical_bridge import SphericalClosureBridge, BridgeUnavailable


class SphericalClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SingleVertexMechanism(generate_fold(parse_target("狗")))
        cls.frames = json.loads((REPO_ROOT / "experiments/current/baseline_inputs/dog_layer_order_keyframes.json").read_text())

    def bridge(self, i=15, dep=(3,4,5)):
        return SphericalClosureBridge(self.m, self.frames[i]["angles_rad"], self.frames[i+1]["angles_rad"], dep)

    def test_analytic_factorization_is_closed_and_material_points_stay_rigid(self):
        bridge = self.bridge()
        self.assertEqual(bridge.regularity()["status"], "PASS")
        self.assertEqual(bridge.continuous_closure()["status"], "PASS")
        self.assertEqual(bridge.exact_closing_hinge_certificate()["status"], "PASS")
        for t in np.linspace(0,1,13):
            q=bridge.q(float(t))
            closed=np.eye(3)
            for k in list(range(1,self.m.n))+[0]:
                closed=closed @ self.m._axis_rotation(bridge.axes[k],q[k])
            np.testing.assert_allclose(closed,np.eye(3),atol=2e-12,rtol=0)
            triangles=[bridge.triangle(p,float(t)) for p in range(8)]
            for p,tri in enumerate(triangles):
                for u,v in [(0,1),(1,2),(2,0)]:
                    self.assertAlmostEqual(np.linalg.norm(tri[u]-tri[v]),
                        np.linalg.norm(bridge.local_triangles[p][u]-bridge.local_triangles[p][v]),places=12)
                np.testing.assert_allclose(tri[2],triangles[(p+1)%8][1],atol=2e-12,rtol=0)

    def test_analytic_endpoints_are_recomputed_not_saved_frame_aliases(self):
        bridge=self.bridge()
        self.assertGreater(np.max(abs(bridge.q0-bridge.reference_q0)),0)
        self.assertLess(np.max(abs(bridge.q0-bridge.reference_q0)),1e-5)
        for k in bridge.free:
            self.assertEqual(bridge.q0[k],bridge.reference_q0[k])
            self.assertEqual(bridge.q1[k],bridge.reference_q1[k])

    def test_joint_vertex_and_curved_chord_enclosures(self):
        bridge=self.bridge(50)
        for a,b in [(0.,1.),(.2,.6),(.71,.73)]:
            qlo,qhi=bridge.joint_bounds(a,b)
            d=bridge.regularity(a,b)
            self.assertTrue(d["proven"])
            for t in np.linspace(a,b,11):
                q=bridge.q(float(t))
                self.assertTrue(np.all(q>=qlo) and np.all(q<=qhi))
            for p in [1,4,7]:
                lo,hi=bridge.vertex_bounds(p,a,b)
                err=bridge.chord_error_bound(p,a,b)
                ta,tb=bridge.triangle(p,a),bridge.triangle(p,b)
                for t in np.linspace(a,b,11):
                    tri=bridge.triangle(p,float(t)); s=(t-a)/(b-a)
                    self.assertTrue(np.all(tri>=lo) and np.all(tri<=hi))
                    self.assertLessEqual(float(np.linalg.norm(tri-((1-s)*ta+s*tb),axis=1).max()),err+2e-12)

    def test_singular_boundaries_fail_closed_and_no_blanket_projection(self):
        self.assertEqual(self.bridge(0).continuous_closure()["status"],"UNCERTAIN")
        last=self.bridge(161)
        self.assertEqual(last.regularity()["status"],"UNCERTAIN")
        self.assertEqual(last.exact_closing_hinge_certificate()["status"],"UNCERTAIN")
        with self.assertRaises(BridgeUnavailable):
            last.q(1.)
        with self.assertRaises(BridgeUnavailable):
            last.vertex_bounds(0)

    def test_unwrap_branch_cut_cannot_pass_from_domain_only(self):
        q=self.bridge().q(.5)
        shifted=q.copy(); shifted[3]+=2*math.pi
        bridge=SphericalClosureBridge(self.m,q,shifted)
        self.assertEqual(bridge.domain_certificate()["status"],"PASS")
        self.assertEqual(bridge.regularity()["status"],"UNCERTAIN")
        self.assertEqual(bridge.continuous_closure()["status"],"UNCERTAIN")

    def test_large_acos_domain_excess_is_never_clamped(self):
        q=np.zeros(8); q[2]=-math.pi
        bridge=SphericalClosureBridge(self.m,q,q)
        self.assertGreater(bridge.acos_jet(0.)[0],2.)
        with self.assertRaisesRegex(BridgeUnavailable,"ACOS_DOMAIN_VIOLATION"):
            bridge.q(.5)
        self.assertEqual(bridge.domain_certificate()["status"],"UNCERTAIN")
        self.assertEqual(bridge.continuous_closure()["status"],"UNCERTAIN")

    def test_target_derivative_and_domain_bounds(self):
        bridge=self.bridge(80)
        t=.413; h=1e-5
        T,D,E=bridge.target_jet(t)
        np.testing.assert_allclose(D,(bridge.target_jet(t+h)[0]-bridge.target_jet(t-h)[0])/(2*h),atol=1e-10,rtol=0)
        # A second derivative regression detects ordering/rate terms omitted
        # from the nonlinear acceleration enclosure.
        np.testing.assert_allclose(E,(bridge.target_jet(t+h)[1]-bridge.target_jet(t-h)[1])/(2*h),atol=1e-10,rtol=0)
        lo,hi=bridge.domain_bounds(.2,.7)
        for u in np.linspace(.2,.7,21):
            x=bridge.acos_jet(float(u))[0]
            self.assertLessEqual(lo,x); self.assertLessEqual(x,hi)

    def test_fixed_values_only_exactly_constant_free_joints(self):
        q=self.bridge(120).q(.5)
        bridge=SphericalClosureBridge(self.m,q,q)
        values=bridge.fixed_joint_values
        for k in bridge.dependent:
            self.assertTrue(math.isnan(values[k]))
        for k in bridge.free:
            self.assertEqual(values[k],q[k])
        with self.assertRaises(ValueError):
            SphericalClosureBridge(self.m,q,q,(1,3,4))


if __name__ == "__main__":
    unittest.main()