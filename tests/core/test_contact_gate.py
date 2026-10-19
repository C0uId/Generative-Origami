"""Regression for contact-mode scope, unknown proofs, and retained material gates."""
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
from generative_origami.simulation.contact_gate import merge_contact_modes
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.contact_bridge import GoalContactBridgeBuilder
import numpy as np


def persistent_fixture():
    pair = {"panels": [0, 1], "status": "PASS", "time_interval": [0., 1.],
        "reason": "ANALYTIC_FIXED_GOAL_RELATIVE_POSE", "patch_vertex_count": 3,
        "layer_order": [0, 1], "whole_panel_exemption": False}
    weights = [[[1., 0., 0.], [1., 0., 0.]], [[0., 1., 0.], [0., 1., 0.]],
               [[0., 0., 1.], [0., 0., 1.]]]
    material = {"status": "PASS", "layer_order": [0, 1], "pairs": [{
        "panels": [0, 1], "status": "PASS", "state": "CONTACT",
        "reason": "ACTIVE_SET_FIXED_GOAL_MATERIAL_PATCH", "patch_vertex_count": 3,
        "material_coordinates": weights, "layer_order": [0, 1],
        "whole_panel_exemption": False, "signed_gap_lower_bound": 0., "signed_gap_upper_bound": 0.,
        "relative_pose_identity": "R_i^-1 R_j = fixed goal Rodrigues product",
        "material_polygon_diagnostics": {"material_mapping_error_diagnostic": 0.,
                                          "minimum_barycentric_coordinate": 0.}}]}
    return pair, material


class ContactModeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = REPO_ROOT / "experiments/current/POC01-007C3-C_SINGULAR_CONTACT_EXACT_BRIDGE/certificates/interval_070.json"
        cls.interval70 = json.loads(path.read_text(encoding="utf8"))
        folder = path.parents[1]
        cls.interval80 = json.loads((folder / "certificates/interval_080.json").read_text(encoding="utf8"))
        cls.mechanism = SingleVertexMechanism(generate_fold(parse_target("狗")))
        records = json.loads((folder / "endpoint_knot_repairs.json").read_text(encoding="utf8"))
        nodes = [np.asarray(r["repaired"]) for r in records]
        builder = GoalContactBridgeBuilder(cls.mechanism)
        cls.motion80 = builder.build_interval(nodes[80], nodes[81], 80)[0][0]

    def test_real_interval70_free_separation_and_hinges_do_not_require_world_z_order(self):
        for cell in self.interval70["cell_certificates"]:
            audit = cell["whole_interval_bounds"]["active_set_contact_bounds"]
            audit = audit.get("original_material_audit", audit)
            self.assertEqual(audit["status"], "UNCERTAIN")
            self.assertTrue(any(p["signed_gap_lower_bound"] < 0. for p in audit["pairs"]))
            merged = merge_contact_modes(cell["pairs"], audit)
            self.assertEqual(merged["status"], "PASS", merged["pairs"])
            self.assertEqual(len(merged["pairs"]), 28)
            self.assertIn("FREE", {p["state"] for p in merged["pairs"]})
            self.assertIn("TOPOLOGICAL_HINGE", {p["state"] for p in merged["pairs"]})
            self.assertFalse(merged["world_z_goal_order_used_as_gate"])
            self.assertEqual(merged["original_material_audit"], audit)
            self.assertIn("not a nonpenetration condition", merged["scope_correction"])

    def test_material_pass_cannot_promote_unknown_or_unproved_ccd(self):
        pair, audit = persistent_fixture()
        for status, reason in [("UNCERTAIN", "CONTINUOUS_FEATURE_OR_CONTACT_NOT_PROVEN"),
                               ("PASS", "UNKNOWN_FUTURE_CONTACT_PROOF"),
                               ("UNKNOWN", "ANALYTIC_FIXED_GOAL_RELATIVE_POSE")]:
            broken = {**pair, "status": status, "reason": reason}
            result = merge_contact_modes([broken], audit, panel_count=2)
            self.assertEqual(result["status"], "UNCERTAIN")
            self.assertEqual(result["pairs"][0]["state"], "UNKNOWN")

    def test_persistent_contact_requires_finite_material_mapping_and_layer_ranks(self):
        pair, audit = persistent_fixture()
        self.assertEqual(merge_contact_modes([pair], audit, panel_count=2)["status"], "PASS")
        for mutate in [lambda p: p.update(layer_order=[1, 0]),
                       lambda p: p.update(material_coordinates=[]),
                       lambda p: p.update(whole_panel_exemption=True),
                       lambda p: p["material_polygon_diagnostics"].update(material_mapping_error_diagnostic=1e-3),
                       lambda p: p.update(state="FREE"),
                       lambda p: p.update(signed_gap_lower_bound=-1e-12)]:
            broken = deepcopy(audit)
            mutate(broken["pairs"][0])
            self.assertEqual(merge_contact_modes([pair], broken, panel_count=2)["status"], "UNCERTAIN")

    def test_complete_children_are_required_and_unknown_leaf_reason_is_rejected(self):
        pair, audit = persistent_fixture()
        audit["pairs"][0].update(state=None, status="UNCERTAIN", signed_gap_lower_bound=-1.)
        left = {**pair, "reason": "SWEPT_AABB_SEPARATION", "time_interval": [0., .5]}
        right = {**pair, "reason": "SWEPT_AABB_SEPARATION", "time_interval": [.5, 1.]}
        tree = {**pair, "reason": "CURVED_RIGID_INTERVAL_SUBDIVISION", "children": [left, right]}
        self.assertEqual(merge_contact_modes([tree], audit, panel_count=2)["status"], "PASS")
        for mutate in [lambda x: x["children"][1].update(time_interval=[.6, 1.]),
                       lambda x: x["children"][1].update(reason="UNRECOGNIZED_PASS"),
                       lambda x: x["children"][0].update(status="UNCERTAIN"),
                       lambda x: x.update(children=[])]:
            broken = deepcopy(tree)
            mutate(broken)
            self.assertEqual(merge_contact_modes([broken], audit, panel_count=2)["status"], "UNCERTAIN")

    def test_free_label_cannot_override_an_actual_persistent_material_contact(self):
        pair, audit = persistent_fixture()
        pair.update(reason="SWEPT_AABB_SEPARATION")
        result = merge_contact_modes([pair], audit, panel_count=2)
        self.assertEqual(result["status"], "UNCERTAIN")
        self.assertEqual(result["pairs"][0]["reason"], "FREE_PROOF_CONTRADICTS_PERSISTENT_MATERIAL_CONTACT")

    def test_all_feature_queries_safe_label_requires_initial_separation_and_features(self):
        pair, audit = persistent_fixture()
        pair.update(reason="ALL_CONTINUOUS_FEATURE_QUERIES_SAFE",
                    features={"all_safe": True, "initial_disjointness_proven": True, "records": []})
        self.assertEqual(merge_contact_modes([pair], audit, panel_count=2)["status"], "UNCERTAIN")

    def test_hinge_contact_at_pi_requires_goal_material_patch_and_exact_seam(self):
        pair, audit = persistent_fixture()
        pair.update(reason="ANALYTIC_CLOSED_SEAM_HINGE_SECTOR", joint=0,
            angle_range=[-math.pi, -math.pi], goal_patch_vertices=3,
            allowed_set="exact shared material hinge; final finite overlap only at goal relative angle",
            closure_structure={"status": "PASS", "reason": "SPHERICAL_3R_CONTINUOUS_IDENTITY",
                               "continuous_upper_bound": 1e-10})
        self.assertEqual(merge_contact_modes([pair], audit, panel_count=2)["status"], "PASS")
        for mutate in [lambda p: p["closure_structure"].update(reason="SAMPLED_CLOSURE_ONLY"),
                       lambda p: p["closure_structure"].update(continuous_upper_bound=1e-3),
                       lambda p: p.update(angle_range=[-math.pi-1e-12, -math.pi]),
                       lambda p: p.update(whole_panel_exemption=True)]:
            broken = deepcopy(pair)
            mutate(broken)
            self.assertEqual(merge_contact_modes([broken], audit, panel_count=2)["status"], "UNCERTAIN")
        self.assertEqual(merge_contact_modes([pair], {"layer_order": [0, 1], "pairs": []}, panel_count=2)["status"], "UNCERTAIN")

    def test_missing_duplicate_or_malformed_pairs_are_not_a_complete_certificate(self):
        pair, audit = persistent_fixture()
        for pairs in [[], [pair, pair], [{**pair, "panels": [1, 0]}], [{**pair, "time_interval": None}]]:
            self.assertEqual(merge_contact_modes(pairs, audit, panel_count=2)["status"], "UNCERTAIN")

    def test_relative_material_frame_separation_requires_positive_continuous_bounds(self):
        pair, audit = persistent_fixture()
        audit["pairs"][0].update(state=None, status="UNCERTAIN", signed_gap_lower_bound=-1.)
        pair.update(reason="RELATIVE_FRAME_CONTINUOUS_SEPARATION", contact_certificate={
            "status": "PASS", "reason": "WHOLE_INTERVAL_RELATIVE_FRAME_CONE_SEPARATION",
            "panels": [0, 1], "time_interval": [0., 1.], "anchor": 0,
            "relative_chain": [1], "uses_exact_cyclic_closure": False,
            "normal_in_anchor_material_frame": [0., 0., 1.], "margin_lower_bound": .01,
            "per_vertex_upper_bounds": [-.01, -.02], "sampled_plane_used_as_proof": False,
            "allowed_contact": "same exact material origin only"})
        self.assertEqual(merge_contact_modes([pair], audit, panel_count=2)["status"], "PASS")
        for mutate in [lambda p: p.update(margin_lower_bound=0.),
                       lambda p: p.update(sampled_plane_used_as_proof=True),
                       lambda p: p.update(per_vertex_upper_bounds=[-.01, .01]),
                       lambda p: p.update(relative_chain=[0]),
                       lambda p: p.update(time_interval=[0., .5])]:
            broken = deepcopy(pair)
            mutate(broken["contact_certificate"])
            self.assertEqual(merge_contact_modes([broken], audit, panel_count=2)["status"], "UNCERTAIN")

    def test_induced_axis_material_identity_alone_cannot_skip_layer_proof(self):
        pair, audit = persistent_fixture()
        pair.update(reason="ANALYTIC_INDUCED_MATERIAL_HINGE", contact_certificate={
            "status": "PASS", "reason": "ANALYTIC_INDUCED_MATERIAL_HINGE",
            "panels": [0, 1], "time_interval": [0., 1.], "anchor": 0,
            "relative_chain": [1], "uses_exact_cyclic_closure": False,
            "layer_order_gate_proven": False, "whole_panel_exemption": False,
            "distinct_original_axes_retained": True})
        result = merge_contact_modes([pair], audit, panel_count=2)
        self.assertEqual(result["status"], "UNCERTAIN")
        self.assertEqual(result["pairs"][0]["reason"], "INDUCED_CONTACT_LAYER_OR_FINITE_MATERIAL_PATCH_NOT_PROVEN")

    def test_real_induced_hinges_require_finite_patch_and_unilateral_layer_evidence(self):
        old = self.interval80["cell_certificates"][0]
        audit = old["whole_interval_bounds"]["active_set_contact_bounds"]
        audit = audit.get("original_material_audit", audit)
        targets = [(1, 3), (2, 4), (5, 7)]
        for pair in targets:
            proof = self.motion80.contact_pair_certificate(pair)
            self.assertEqual(proof["reason"], "ANALYTIC_INDUCED_MATERIAL_HINGE")
            wrapped = {"panels": list(pair), "status": "PASS", "time_interval": [0., 1.],
                       "reason": proof["reason"], "contact_certificate": proof}

            def target_result(node):
                pairs = [node if p["panels"] == list(pair) else p for p in old["pairs"]]
                merged = merge_contact_modes(pairs, audit)
                return next(p for p in merged["pairs"] if p["panels"] == list(pair))

            accepted = target_result(wrapped)
            self.assertEqual(accepted["status"], "PASS", accepted)
            self.assertEqual(accepted["state"], "MATERIAL_HINGE")
            for mutate in [lambda p: p.update(layer_order_gate_proven=False),
                           lambda p: p.update(layer_order=list(reversed(p["layer_order"]))),
                           lambda p: p.update(material_coordinates=[]),
                           lambda p: p["material_proof"].update(status="UNCERTAIN"),
                           lambda p: p["layer_proof"].update(whole_interval=False),
                           lambda p: p["layer_proof"]["coefficient_lower_bounds"].__setitem__(1, -1e-12),
                           lambda p: p["layer_proof"].update(symbolic_zero_vertices=[0]),
                           lambda p: p.update(goal_material_mapping_error_upper_bound=1e-3)]:
                broken = deepcopy(wrapped)
                mutate(broken["contact_certificate"])
                self.assertEqual(target_result(broken)["status"], "UNCERTAIN")


if __name__ == "__main__":
    unittest.main()