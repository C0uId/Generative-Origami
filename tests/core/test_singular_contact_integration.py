"""Adversarial upgrade and protected-middle replay tests for C3-C."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import sys
import unittest

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "tools" / "motion_repair"))
sys.path.insert(0, str(REPO_ROOT / "src"))
from singular_contact_motion import final_gate, digest, replay_plan
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.contact_gate import merge_contact_modes


class UpgradeGateTests(unittest.TestCase):
    def fixture(self):
        order = [7, 6, 5, 0, 4, 1, 3, 2]
        pairs = [{"panels": list(p), "status": "PASS", "time_interval": [0., 1.],
                  "reason": "CONTINUOUS_CONE_SEPARATION", "passed": True,
                  "normal": [1., 0., 0.], "margin_lower_bound": 1.,
                  "allowed_contact": "shared origin only, no radius exclusion"}
                 for p in itertools.combinations(range(8), 2)]
        active = merge_contact_modes(pairs, {"layer_order": order, "pairs": []},
                                     panel_count=8, layer_order=order)
        return [{"interval": i, "status": "PASS", "closure_status": "PASS", "exact_bridge_passed": True,
                 "plan": {"continuous_join_passed": True, "cells": [
                     {"source_parameter_interval": [0., 1.], "construction_status": "PASS"}]},
                 "cell_certificates": [{"status": "PASS", "reasons": [],
                     "hinge_closure": {"status": "PASS", "continuous_upper_bound": 1e-9}, "sector_passed": True,
                     "whole_interval_bounds": {"point_speed_upper_bounds": [1.]*8,
                         "point_acceleration_upper_bounds": [2.]*8,
                         "exact_closing_seam": {"status": "PASS"},
                         "active_set_contact_bounds": deepcopy(active)},
                     "pairs": deepcopy(pairs), "uses_vertex_linear_interpolation_as_motion": False}]}
                for i in range(162)]

    def test_complete_evidence_and_no_unknown_required(self):
        data = self.fixture()
        self.assertTrue(final_gate(data, True, True))
        data[161]["status"] = "UNCERTAIN"
        self.assertFalse(final_gate(data, True, True))

    def test_unproven_material_gap_cannot_hide_behind_safe_ccd(self):
        data = self.fixture()
        data[100]["cell_certificates"][0]["whole_interval_bounds"]["active_set_contact_bounds"]["status"] = "UNCERTAIN"
        self.assertFalse(final_gate(data, True, True))

    def test_missing_or_duplicate_interval_cannot_promote(self):
        data = self.fixture()
        self.assertFalse(final_gate(data[:-1], True, True))
        data[161]["interval"] = 160
        self.assertFalse(final_gate(data, True, True))

    def test_unknown_pair_cannot_hide_behind_pass_label(self):
        data = self.fixture()
        data[92]["cell_certificates"][0]["pairs"][8]["status"] = "UNCERTAIN"
        self.assertFalse(final_gate(data, True, True))

    def test_finite_tolerance_endpoint_is_insufficient(self):
        data = self.fixture()
        data[0]["exact_bridge_passed"] = False
        self.assertFalse(final_gate(data, True, True))

    def test_changed_middle_or_failed_join_cannot_promote(self):
        data = self.fixture()
        self.assertFalse(final_gate(data, False, True))
        self.assertFalse(final_gate(data, True, False))
        data[80]["plan"]["continuous_join_passed"] = False
        self.assertFalse(final_gate(data, True, True))

    def test_closure_and_vertex_motion_cannot_bypass_gate(self):
        data = self.fixture()
        data[161]["cell_certificates"][0]["hinge_closure"]["status"] = "UNCERTAIN"
        self.assertFalse(final_gate(data, True, True))

    def test_missing_or_nonfinite_kinematic_enclosure_blocks_promotion(self):
        data = self.fixture()
        data[0]["cell_certificates"][0]["whole_interval_bounds"]["point_speed_upper_bounds"][0] = None
        self.assertFalse(final_gate(data, True, True))
        data = self.fixture()
        data[161]["cell_certificates"][0]["whole_interval_bounds"]["exact_closing_seam"]["status"] = "UNCERTAIN"
        self.assertFalse(final_gate(data, True, True))
        data = self.fixture()
        data[0]["cell_certificates"][0]["uses_vertex_linear_interpolation_as_motion"] = True
        self.assertFalse(final_gate(data, True, True))


class ProtectedMiddleTests(unittest.TestCase):
    def test_all_61_middle_plans_replay_same_rigid_curve(self):
        baseline = REPO_ROOT / "experiments/current/baseline_inputs"
        data = json.loads((baseline / "c3c_baseline_plans.json").read_text(encoding="utf-8"))
        nodes = [np.asarray(c["repaired"]) for c in json.loads(
            (baseline / "repaired_source_knots.json").read_text(encoding="utf-8"))]
        m = SingleVertexMechanism(generate_fold(parse_target("狗")))
        before = digest([c["plan"] for c in data["intervals"][9:70]])
        for i in range(9, 70):
            plan = data["intervals"][i]["plan"]
            motions = replay_plan(m, nodes, i, plan)
            self.assertTrue(motions)
            self.assertTrue(all(c["kind"] == "ANALYTIC_SPHERICAL_3R" for c in plan["cells"]))
            for motion in motions:
                # This compares reconstruction only; it is not continuous certification.
                for t in (0., .37, 1.):
                    triangles = m.panel_triangles(motion.q(t))
                    for k in range(m.n):
                        np.testing.assert_allclose(motion.triangle(k, t), triangles[k], rtol=0, atol=2e-14)
        self.assertEqual(before, digest([c["plan"] for c in data["intervals"][9:70]]))


if __name__ == "__main__":
    unittest.main()