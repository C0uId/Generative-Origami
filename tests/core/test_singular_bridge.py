"""Regression checks supplement analytic bounds; samples never certify motion."""
import json
import math
from pathlib import Path
import sys
import unittest

import numpy as np

REPO_ROOT=Path(__file__).resolve().parents[2]
ROOT=REPO_ROOT
sys.path.insert(0,str(REPO_ROOT/"src"))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation.single_vertex import SingleVertexMechanism
from generative_origami.simulation.singular_bridge import (
    FlatSingularBridgeBuilder,LocalChartMotion,SingularBridgeConfig)
from generative_origami.simulation.spherical_bridge import BridgeUnavailable


class SingularBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=SingleVertexMechanism(generate_fold(parse_target("狗")))
        data=json.loads((REPO_ROOT/"experiments/current/baseline_inputs/repaired_source_knots.json").read_text(encoding="utf8"))
        cls.nodes=[np.asarray(x["repaired"],float) for x in data]
        cls.flat=LocalChartMotion(cls.m,cls.nodes[0],cls.nodes[1])

    def test_deflation_proves_flat_endpoint_and_finite_derivatives(self):
        p=self.flat.regularity()
        self.assertTrue(p["proven"])
        self.assertGreater(p["deflated_h_bounds"][0],0.)
        self.assertEqual(self.flat.continuous_closure()["status"],"PASS")
        np.testing.assert_array_equal(self.flat.q(0.),self.m.flat)
        self.assertTrue(np.isfinite(p["joint_velocity_bounds"]).all())
        self.assertTrue(np.isfinite(p["joint_acceleration_bounds"]).all())
        self.assertLess(max(p["taylor_remainder_bounds"]),1e-30)
        self.assertIn("not formal",self.flat.continuous_closure()["numeric_scope"])
        seam=self.flat.exact_closing_hinge_certificate()
        self.assertFalse(seam["numerical_evaluator_is_motion_definition"])
        self.assertTrue(seam["evaluator_error_in_joint_vertex_and_chord_bounds"])

    def test_entire_interval_angle_enclosure_has_no_epsilon_hole_at_flat(self):
        lo,hi=self.flat.joint_bounds()
        self.assertTrue(np.all(np.where(self.m.signs>0,lo,-hi)>=0.))
        self.assertTrue(np.all(np.where(self.m.signs>0,lo,hi)==0.))
        for t in [0.,1e-9,1e-5,.1,.4,.8,1.]:
            q=self.flat.q(t)
            self.assertTrue(np.all(q>=lo) and np.all(q<=hi))
        np.testing.assert_allclose(self.flat.q(1.),self.nodes[1],atol=2e-11,rtol=0)

    def test_analytic_path_closes_and_preserves_material_distances(self):
        for t in [0.,1e-10,1e-5,.2,.6,1.]:
            q=self.flat.q(t); product=np.eye(3)
            for k in list(range(1,self.m.n))+[0]:
                product=product@self.m._axis_rotation(self.flat.axes[k],q[k])
            np.testing.assert_allclose(product,np.eye(3),atol=2e-12,rtol=0)
            tris=[self.flat.triangle(p,t) for p in range(self.m.n)]
            for p,tri in enumerate(tris):
                np.testing.assert_allclose(tri[2],tris[(p+1)%self.m.n][1],atol=2e-12,rtol=0)
                for a,b in [(0,1),(1,2),(2,0)]:
                    self.assertAlmostEqual(np.linalg.norm(tri[a]-tri[b]),
                        np.linalg.norm(self.flat.local_triangles[p][a]-self.flat.local_triangles[p][b]),places=12)

    def test_derivative_and_vertex_bounds_regress_against_interior_evaluations(self):
        proof=self.flat.regularity(); vb=np.asarray(proof["joint_velocity_bounds"])
        ab=np.asarray(proof["joint_acceleration_bounds"])
        for t in [.1,.3,.5,.8]:
            h=1e-4
            derivative=(self.flat.q(t+h)-self.flat.q(t-h))/(2*h)
            second=(self.flat.q(t+h)-2*self.flat.q(t)+self.flat.q(t-h))/h**2
            self.assertTrue(np.all(derivative>=vb[:,0]-1e-9) and np.all(derivative<=vb[:,1]+1e-9))
            self.assertTrue(np.all(second>=ab[:,0]-2e-7) and np.all(second<=ab[:,1]+2e-7))
        for p in [0,2,5,7]:
            lo,hi=self.flat.vertex_bounds(p)
            for t in [.1,.5,.9]:
                triangle=self.flat.triangle(p,t)
                self.assertTrue(np.all(triangle>=lo) and np.all(triangle<=hi))
        p=7
        ideal_chord=self.flat.curvature_bound(p)/8
        full_chord=self.flat.chord_error_bound(p)
        evaluator_error=proof["evaluation_error_bound"]*max(1.,self.flat.radius(p))
        self.assertGreaterEqual(full_chord,ideal_chord+evaluator_error)
        # Chords are a bound used by CCD; the actual geometry follows FK.
        p=6
        chord=(self.flat.triangle(p,0.)+self.flat.triangle(p,1.))/2
        self.assertGreater(float(np.linalg.norm(self.flat.triangle(p,.5)-chord)),1e-6)

    def test_builder_has_finite_bounds_and_arc_length_mode_seed_diagnostics(self):
        motions,plan=FlatSingularBridgeBuilder(self.m).build_interval(self.nodes[0],self.nodes[1],0)
        self.assertTrue(plan["continuous_join_passed"])
        self.assertEqual(len(motions),1)
        self.assertEqual(plan["continuation"]["jacobian_rank"],2)
        self.assertFalse(plan["continuation"]["diagnostics_are_certification"])
        self.assertLess(plan["continuation"]["tangent_equation_residual_diagnostic"],1e-12)
        bounds=plan["cells"][0]["bounds"]
        self.assertEqual(len(bounds["contact_bounds"]),28)
        self.assertFalse(bounds["sample_extrema_used"])
        self.assertTrue(all(not x["contact_legal_claimed"] for x in bounds["contact_bounds"]))
        self.assertGreater(motions[0].speed_bound(7),0.)
        self.assertGreater(motions[0].acceleration_bound(7),0.)

    def test_unproved_regular_chart_never_emits_a_q_linear_replacement(self):
        builder=FlatSingularBridgeBuilder(self.m,SingularBridgeConfig(max_depth=0))
        motions,plan=builder.build_interval(self.nodes[1],self.nodes[2],1)
        self.assertEqual(motions,[])
        self.assertEqual(plan["construction_status"],"UNCERTAIN")
        self.assertFalse(plan["q_linear_fallback_used"])
        self.assertTrue(plan["failures"])

    def test_large_low_order_taylor_tail_blocks_closure_certification(self):
        # Its analytic branch can be bounded, but the implemented finite
        # series is too coarse. The general arithmetic guard alone would
        # miss this deliberate truncation error by several orders.
        chart=LocalChartMotion(self.m,self.nodes[0],8*self.nodes[1],
                               SingularBridgeConfig(taylor_order=6))
        proof=chart.regularity()
        self.assertTrue(proof["proven"])
        propagation=proof["series_evaluation_error"]
        self.assertGreater(propagation["h_truncation_error_bound"],1e-5)
        self.assertGreater(propagation["taylor_factorization_rotation_error_bound"],
                           1000*proof["arithmetic_reference_guard"])
        self.assertEqual(chart.continuous_closure()["status"],"UNCERTAIN")
        limited=LocalChartMotion(self.m,self.nodes[0],self.nodes[1],
            SingularBridgeConfig(max_point_evaluation_error=1e-12))
        self.assertEqual(limited.continuous_closure()["status"],"UNCERTAIN")
        self.assertEqual(limited.exact_closing_hinge_certificate()["status"],"UNCERTAIN")
        self.assertEqual(limited.continuous_closure()["reason"],
            "EVALUATOR_ERROR_EXCEEDS_COLLISION_WITNESS_GUARD")

    def test_modified_dependent_endpoint_fails_join_instead_of_overwriting_it(self):
        bad=self.nodes[1].copy();bad[3]+=.01
        motions,plan=FlatSingularBridgeBuilder(self.m).build_interval(self.nodes[0],bad,0)
        self.assertEqual(motions,[])
        self.assertFalse(plan["continuous_join_passed"])
        self.assertTrue(any(x["reason"]=="EXACT_CHART_ENDPOINT_JOIN_NOT_PROVEN" for x in plan["failures"]))

    def test_protected_intervals_and_invalid_inputs_are_rejected(self):
        builder=FlatSingularBridgeBuilder(self.m)
        with self.assertRaises(ValueError): builder.build_interval(self.nodes[9],self.nodes[10],9)
        with self.assertRaises(ValueError): builder.build_interval([math.nan]*8,self.nodes[1],0)
        with self.assertRaises(ValueError): self.flat.joint_bounds(.7,.3)
        with self.assertRaises(ValueError): SingularBridgeConfig(taylor_order=2)
        with self.assertRaises(ValueError): self.flat.continuous_closure(tolerance=0.)


if __name__=="__main__":
    unittest.main()