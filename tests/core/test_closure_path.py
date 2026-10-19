import copy
import json
import itertools
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(ROOT))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.ccd_motion import RigidMechanismInterval
from generative_origami.simulation.closure_path import HybridClosurePath, ClosurePathConfig
from generative_origami.simulation.continuous_ccd import ContinuousPathCertifier
from tools.motion_repair.repair_motion import aggregate_cells


class ClosurePathIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = SingleVertexMechanism(generate_fold(parse_target("狗")))
        cls.source = json.loads((REPO_ROOT / "experiments/current/baseline_inputs/dog_layer_order_keyframes.json").read_text(encoding="utf-8"))
        cls.builder = HybridClosurePath(cls.m)
        cls.nodes, cls.changes = cls.builder.repair_nodes([f["angles_rad"] for f in cls.source])

    def certifier(self):
        return ContinuousPathCertifier(self.m,layer_order=[7,6,5,0,4,1,3,2])

    def test_source_changes_are_recorded_and_joint_sectors_are_strict(self):
        self.assertEqual(len(self.nodes),163)
        for q, change in zip(self.nodes,self.changes):
            self.assertTrue(self.m.sector_valid(q,tol=0.))
            np.testing.assert_array_equal(q,change["repaired"])
            self.assertLess(change["correction_norm"],1e-3)
        self.assertGreater(max(c["correction_norm"] for c in self.changes),0.)

    def test_repaired_interval_15_has_full_time_closure_and_joined_subcurves(self):
        motions,plan = self.builder.build_interval(self.nodes[15],self.nodes[16],15)
        self.assertTrue(plan["continuous_join_passed"])
        for motion in motions:
            proof=motion.continuous_closure(tolerance=4e-6)
            self.assertEqual(proof["status"],"PASS")
            self.assertLessEqual(proof["continuous_upper_bound"],4e-6)
        for a,b in zip(motions,motions[1:]):
            np.testing.assert_allclose(a.q1,b.q0,atol=2e-11,rtol=0.)

    def test_nonlinear_equal_endpoints_do_not_prove_persistent_contact(self):
        class Curved:
            q0=self.m.goal.copy()
            q1=self.m.goal.copy()
            fixed_joint_values=np.full(self.m.n,np.nan)
        self.assertIsNone(self.certifier().contact.persistent_goal_patch(Curved(),(0,2)))

    def test_finite_tolerance_bridge_never_gets_exact_seam_hinge_rule(self):
        motion=RigidMechanismInterval(self.m,self.nodes[15],self.nodes[16])
        self.assertIsNone(self.certifier().contact.adjacent_hinge(motion,(0,7)))
        motions,plan=self.builder.build_interval(self.nodes[40],self.nodes[41],40)
        analytic=[motion for motion,cell in zip(motions,plan["cells"]) if cell["kind"]=="ANALYTIC_SPHERICAL_3R"]
        self.assertTrue(analytic)
        self.assertEqual(self.certifier().contact.adjacent_hinge(analytic[0],(0,7))["status"],"PASS")

    def test_nonlinear_sector_requires_whole_interval_bounds(self):
        m=self.m
        class BadCurve:
            motion_kind="NONLINEAR_COUNTEREXAMPLE"
            def joint_bounds(self,a,b):
                lo=np.where(m.signs>0,0.,-math.pi)
                hi=np.where(m.signs>0,math.pi,0.)
                hi[1]=math.pi+.1
                return lo,hi
            def continuous_closure(self,**kwargs):
                return {"status":"PASS"}
        certifier=self.certifier()
        with patch.object(certifier,"certify_pair",return_value={"status":"PASS"}):
            result=certifier.certify_defined_motion(BadCurve(),0)
        self.assertEqual(result["status"],"UNCERTAIN")
        self.assertIn("M_V_SECTOR_VIOLATION",result["reasons"])

    def test_one_unknown_or_failed_join_prevents_source_interval_pass(self):
        plan={"continuous_join_passed":True,"cells":[
            {"source_parameter_interval":[0.,.5],"construction_status":"PASS"},
            {"source_parameter_interval":[.5,1.],"construction_status":"PASS"}]}
        pairs=[{"panels":list(p),"status":"PASS"} for p in itertools.combinations(range(8),2)]
        certs=[{"status":"PASS","reasons":[],"hinge_closure":{"status":"PASS"},"pairs":copy.deepcopy(pairs),"sector_passed":True},
               {"status":"UNCERTAIN","reasons":["UNPROVEN_CONTACT"],"hinge_closure":{"status":"PASS"},"pairs":copy.deepcopy(pairs),"sector_passed":True}]
        self.assertEqual(aggregate_cells(0,plan,certs)["status"],"UNCERTAIN")
        certs[1]["status"]="PASS"
        plan["continuous_join_passed"]=False
        self.assertEqual(aggregate_cells(0,plan,certs)["status"],"UNCERTAIN")
        plan["continuous_join_passed"]=True
        self.assertEqual(aggregate_cells(0,plan,certs,False)["status"],"UNCERTAIN")
        self.assertEqual(aggregate_cells(0,plan,certs)["status"],"PASS")
        plan["cells"][1]["source_parameter_interval"][0]=.6
        self.assertEqual(aggregate_cells(0,plan,certs)["status"],"UNCERTAIN")
        plan["cells"][1]["source_parameter_interval"][0]=.5
        certs[0]["pairs"][1]["panels"]=certs[0]["pairs"][0]["panels"]
        self.assertEqual(aggregate_cells(0,plan,certs)["status"],"UNCERTAIN")
        certs[0]["pairs"]=copy.deepcopy(pairs)
        certs[0]["pairs"][0]["status"]="UNCERTAIN"
        rejected=aggregate_cells(0,plan,certs)
        self.assertEqual(rejected["status"],"UNCERTAIN")
        self.assertIn("UNDERLYING_SECTOR_OR_PAIR_NOT_PASS",rejected["reasons"])


if __name__=="__main__":
    unittest.main()