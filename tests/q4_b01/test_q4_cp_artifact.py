import json
import unittest
from pathlib import Path

from base_intake import inspect
from q4_cp_candidate import build_medium_medium_cp, audit_candidate

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "experiments/q4_b01/Q4-B01-CP-MEDIUM-MEDIUM"


class Q4MediumCPArtifactTests(unittest.TestCase):
    def test_committed_candidate_matches_builder(self):
        committed = json.loads((ARTIFACT_DIR / "candidate.fold").read_text(encoding="utf-8"))
        self.assertEqual(committed, build_medium_medium_cp())

    def test_committed_audit_hashes_match_candidate(self):
        committed = json.loads((ARTIFACT_DIR / "candidate.fold").read_text(encoding="utf-8"))
        persisted = json.loads((ARTIFACT_DIR / "audit.json").read_text(encoding="utf-8"))
        calculated = inspect(committed)
        runtime = audit_candidate()

        self.assertTrue(calculated["passed"], calculated["errors"])
        self.assertEqual(persisted["cp_geometry_sha256"], calculated["geometry_sha256"])
        self.assertEqual(persisted["cp_topology_sha256"], calculated["topology_sha256"])
        self.assertEqual(persisted["cp_geometry_sha256"], runtime["cp_geometry_sha256"])
        self.assertEqual(persisted["cp_topology_sha256"], runtime["cp_topology_sha256"])
        self.assertEqual(persisted["claim_boundary"], "REAL_PLANAR_CP_CANDIDATE_ONLY_NOT_PHYSICAL_BASE")
        self.assertFalse(persisted["physical_verified"])
        self.assertFalse(persisted["continuous_motion_verified"])


if __name__ == "__main__":
    unittest.main()
