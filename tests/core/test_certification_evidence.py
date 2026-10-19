"""Reaggregation rejects incomplete or edited Goal contact-mode evidence."""
from copy import deepcopy
import itertools
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))
from generative_origami.simulation.certification_evidence import (
    audit_goal_contact_evidence, validate_goal_contact_evidence)
from generative_origami.simulation.contact_gate import merge_contact_modes

ORDER = [7, 6, 5, 0, 4, 1, 3, 2]


def fixture():
    pairs = [{"panels": list(pair), "status": "PASS", "time_interval": [0., 1.],
              "reason": "CONTINUOUS_CONE_SEPARATION", "passed": True,
              "normal": [1., 0., 0.], "margin_lower_bound": 1.,
              "allowed_contact": "shared origin only, no radius exclusion"}
             for pair in itertools.combinations(range(8), 2)]
    original = {"status": "UNCERTAIN", "layer_order": ORDER, "pairs": []}
    merged = merge_contact_modes(pairs, original, panel_count=8, layer_order=ORDER)
    return {"pairs": pairs, "whole_interval_bounds": {"active_set_contact_bounds": merged}}


class GoalCertificationEvidenceTests(unittest.TestCase):
    def test_complete_continuous_proofs_are_merged_again(self):
        cell = fixture()
        self.assertTrue(validate_goal_contact_evidence(cell, ORDER))
        result = audit_goal_contact_evidence(cell, ORDER)
        self.assertEqual(result["pair_count"], 28)
        self.assertTrue(result["stored_audit_exactly_matches_fresh_merge"])

    def test_cached_pass_alone_or_missing_original_audit_is_rejected(self):
        for replacement in [None, {"status": "PASS"}, {"status": "PASS", "pairs": []}]:
            cell = fixture()
            cell["whole_interval_bounds"]["active_set_contact_bounds"] = replacement
            self.assertFalse(validate_goal_contact_evidence(cell, ORDER))
        cell = fixture()
        del cell["whole_interval_bounds"]["active_set_contact_bounds"]["original_material_audit"]
        self.assertFalse(validate_goal_contact_evidence(cell, ORDER))

    def test_dropped_duplicate_and_reversed_pair_coverage_is_rejected(self):
        for location in ("continuous", "stored"):
            for mutation in ("drop", "duplicate", "reverse"):
                cell = fixture()
                records = cell["pairs"] if location == "continuous" else cell["whole_interval_bounds"]["active_set_contact_bounds"]["pairs"]
                if mutation == "drop": records.pop()
                if mutation == "duplicate": records[-1] = deepcopy(records[0])
                if mutation == "reverse": records[0]["panels"].reverse()
                self.assertFalse(validate_goal_contact_evidence(cell, ORDER), (location, mutation))

    def test_unknown_or_edited_underlying_proof_cannot_keep_a_cached_pass(self):
        for mutate in [lambda p: p.update(reason="UNRECOGNIZED_FUTURE_PASS"),
                       lambda p: p.update(status="UNCERTAIN"),
                       lambda p: p.update(margin_lower_bound=0.),
                       lambda p: p.update(time_interval=[0., .9])]:
            cell = fixture()
            mutate(cell["pairs"][0])
            self.assertFalse(validate_goal_contact_evidence(cell, ORDER))

    def test_edited_stored_modes_cannot_claim_the_same_fresh_status(self):
        cell = fixture()
        active = cell["whole_interval_bounds"]["active_set_contact_bounds"]
        active["pairs"][0]["mode_segments"][0]["state"] = "CONTACT"
        self.assertEqual(active["status"], "PASS")
        self.assertFalse(validate_goal_contact_evidence(cell, ORDER))

    def test_layer_order_nonfinite_and_malformed_audits_fail_closed(self):
        cell = fixture()
        self.assertFalse(validate_goal_contact_evidence(cell, list(range(8))))
        self.assertFalse(validate_goal_contact_evidence(cell, [True] + list(range(1, 8))))
        cell["whole_interval_bounds"]["active_set_contact_bounds"]["original_material_audit"]["diagnostic"] = float("nan")
        self.assertFalse(validate_goal_contact_evidence(cell, ORDER))
        self.assertFalse(validate_goal_contact_evidence([], ORDER))


if __name__ == "__main__":
    unittest.main()