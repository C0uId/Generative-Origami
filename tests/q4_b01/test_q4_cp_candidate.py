import unittest
from q4_cp_candidate import build_medium_medium_cp, local_flat_foldability, audit_candidate, FACE_IDS
from base_intake import inspect

class Q4MediumCPTests(unittest.TestCase):
    def test_planar_complete_square(self):
        cp=build_medium_medium_cp()
        result=inspect(cp)
        self.assertTrue(result["passed"], result["errors"])
        self.assertEqual(result["exact_material_area"],"1")
        self.assertFalse(result["physical_base_certified"])

    def test_local_center_flat_foldability(self):
        local=local_flat_foldability(build_medium_medium_cp())
        self.assertEqual(local["incident_crease_count"],8)
        self.assertTrue(local["kawasaki_pass"])
        self.assertEqual(local["kawasaki_alternating_sums_deg"],[180,180])
        self.assertTrue(local["maekawa_pass"])
        self.assertEqual(local["maekawa_difference"],2)

    def test_traceable_stable_ids_and_materials(self):
        audit=audit_candidate()
        self.assertEqual(audit["base_id"],"Q4-B01")
        self.assertEqual(audit["candidate_version"],"0.1")
        self.assertEqual(audit["stable_face_ids"],list(FACE_IDS))
        self.assertEqual(len(set(audit["stable_face_ids"])),8)
        self.assertEqual(set(audit["stable_flap_ids"]),{"MAT_FL","MAT_FR","MAT_HL","MAT_HR","MAT_HEAD","MAT_TAIL"})
        mapped={p["material_id"] for face in audit["face_material_map"] for p in face["material_parts"]}
        self.assertEqual(mapped,{"MAT_FL","MAT_FR","MAT_HL","MAT_HR","MAT_HEAD","MAT_BODY","MAT_TAIL"})
        self.assertFalse(audit["physical_verified"])
        self.assertFalse(audit["continuous_motion_verified"])
        self.assertTrue(audit["unresolved"])

    def test_reproducible_hash(self):
        a=audit_candidate(); b=audit_candidate()
        self.assertEqual(a["cp_geometry_sha256"],b["cp_geometry_sha256"])
        self.assertEqual(a["cp_topology_sha256"],b["cp_topology_sha256"])

if __name__=="__main__": unittest.main()
