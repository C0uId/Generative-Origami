"""Adversarial CCD contract regressions, independent of the Dog path."""

import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))

from generative_origami.simulation.ccd_adapter import (
    BackendUnavailable, CCDResult, NativeTightInclusionBackend,
    PythonReferenceBackend, backend_info, get_backend,
    point_triangle_distance, segment_segment_distance,
)


class CCDAdapterTests(unittest.TestCase):
    def setUp(self):
        self.backend = PythonReferenceBackend()
        self.face = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])

    def vertex_query(self, p0, p1, **kwargs):
        return self.backend.vertex_face(np.vstack((p0, self.face)),
                                        np.vstack((p1, self.face)), **kwargs)

    def test_vertex_crosses_face_between_clear_endpoints(self):
        result = self.vertex_query([.25, .25, -1], [.25, .25, 1])
        self.assertEqual(result.status, "POSSIBLE_HIT", result.to_dict())
        self.assertEqual(result.stats["witness_time"], .5)
        self.assertNotEqual(result.status, "COLLISION")

    def test_fast_vertex_tunnel_not_visible_at_midpoint_is_rejected(self):
        result = self.vertex_query([.25, .25, -1], [.25, .25, 9])
        self.assertNotEqual(result.status, "SAFE", result.to_dict())
        self.assertGreater(result.stats["subdivisions"], 0)
        self.assertTrue(result.time_interval[0] <= .1 <= result.time_interval[1])

    def test_overestimated_distance_cannot_replace_supporting_plane_certificate(self):
        # An inaccurate closest-feature estimate must not manufacture a lower
        # bound: a separate projection bound still limits the SAFE decision.
        with patch("generative_origami.simulation.ccd_adapter.point_triangle_distance", return_value=100.):
            result = self.vertex_query([.25, .25, -1], [.25, .25, 9], max_subdivisions=32)
        self.assertNotEqual(result.status, "SAFE", result.to_dict())

    def test_edges_cross_between_clear_endpoints(self):
        start = np.array([[-1., 0, 0], [1., 0, 0], [0., -1, 1], [0., 1, 1]])
        end = start.copy()
        end[2:, 2] = -1
        result = self.backend.edge_edge(start, end)
        self.assertEqual(result.status, "POSSIBLE_HIT", result.to_dict())

    def test_fast_edge_tunnel_is_not_certified_safe(self):
        start = np.array([[-1., 0, 0], [1., 0, 0], [0., -1, -1], [0., 1, -1]])
        end = start.copy()
        end[2:, 2] = 9
        result = self.backend.edge_edge(start, end)
        self.assertNotEqual(result.status, "SAFE", result.to_dict())

    def test_swept_aabb_can_certify_entire_interval(self):
        result = self.vertex_query([.25, .25, 1], [3, 4, 2])
        self.assertEqual(result.status, "SAFE", result.to_dict())
        self.assertEqual(result.time_interval, (0, 1))
        self.assertGreater(result.lower_bound, 0)
        self.assertEqual(result.stats["aabb_safe_leaves"], 1)

    def test_near_miss_with_overlapping_swept_boxes_needs_interval_proof(self):
        # At z=0 the point is above the triangle.  Its swept box overlaps the
        # face's box, so a clear sample alone cannot certify this motion.
        result = self.vertex_query([-2, 2.2, -1], [2, .2, 1], max_subdivisions=256)
        self.assertEqual(result.status, "SAFE", result.to_dict())
        self.assertGreater(result.stats["subdivisions"], 0)
        self.assertGreater(result.stats["safe_leaves"], 1)

    def test_minimum_separation_is_enforced(self):
        clear = self.vertex_query([.25, .25, .1], [.25, .25, .1], minimum_separation=.05)
        close = self.vertex_query([.25, .25, .1], [.25, .25, .1], minimum_separation=.11)
        self.assertEqual(clear.status, "SAFE", clear.to_dict())
        self.assertEqual(close.status, "POSSIBLE_HIT", close.to_dict())

    def test_zero_budget_does_not_infer_safety_from_clear_samples(self):
        result = self.vertex_query([-2, 2.2, -1], [2, .2, 1], max_subdivisions=0)
        self.assertEqual(result.status, "UNCERTAIN", result.to_dict())
        self.assertEqual(result.reason, "SUBDIVISION_BUDGET_EXHAUSTED")

    def test_degenerate_geometry_fails_closed_unless_aabb_is_separated(self):
        query = np.array([[.5, 0, 0], [0., 0, 0], [1., 0, 0], [2., 0, 0]])
        uncertain = self.backend.vertex_face(query, query, max_subdivisions=0)
        self.assertEqual(uncertain.status, "UNCERTAIN", uncertain.to_dict())
        query[0, 2] = 1
        self.assertEqual(self.backend.vertex_face(query, query).status, "SAFE")

    def test_nonfinite_and_invalid_inputs_are_uncertain(self):
        query = np.vstack(([.1, .1, 1], self.face))
        for start, end, kwargs in ((query * np.nan, query, {}),
                                   (query[:, :2], query, {}),
                                   (query, query, {"minimum_separation": -1}),
                                   (query, query, {"max_subdivisions": -1}),
                                   (query, query, {"tolerance": 0})):
            self.assertEqual(self.backend.vertex_face(start, end, **kwargs).status, "UNCERTAIN")

    def test_reference_metadata_never_claims_native_tight_inclusion(self):
        info = backend_info()
        self.assertFalse(info["native"])
        self.assertFalse(info["is_tight_inclusion_library"])
        self.assertIn("linear_vertex_surrogate_only", info["trajectory_scope"])
        self.assertIn("conditional", info["guarantee_scope"])
        self.assertIsInstance(get_backend("reference"), PythonReferenceBackend)

    def test_explicit_unavailable_native_never_silently_falls_back(self):
        with self.assertRaises(BackendUnavailable):
            NativeTightInclusionBackend("_absent_native_ccd_73589")
        with patch.dict(sys.modules, {"_incomplete_ccd_binding": types.SimpleNamespace(vertex_face=lambda *_: False)}):
            with self.assertRaises(BackendUnavailable):
                NativeTightInclusionBackend("_incomplete_ccd_binding")

    def test_native_boolean_contract_and_errors(self):
        module = types.SimpleNamespace(vertex_face=lambda *a, **kw: False,
                                       edge_edge=lambda *a, **kw: True)
        query = np.vstack(([.1, .1, 1], self.face))
        with patch.dict(sys.modules, {"_mock_ccd_binding": module}):
            native = NativeTightInclusionBackend("_mock_ccd_binding")
            self.assertEqual(native.vertex_face(query, query).status, "SAFE")
            self.assertEqual(native.edge_edge(query, query).status, "POSSIBLE_HIT")
            self.assertTrue(native.backend_info()["native"])
            module.vertex_face = lambda *a, **kw: "false"
            self.assertEqual(native.vertex_face(query, query).status, "UNCERTAIN")
            module.vertex_face = lambda *a, **kw: CCDResult("SAFE", "partial", (.2, .3))
            self.assertEqual(native.vertex_face(query, query).status, "UNCERTAIN")

    def test_geometry_helpers_cover_interior_edges_and_degeneracy(self):
        self.assertAlmostEqual(point_triangle_distance([.2, .2, 2], self.face), 2)
        self.assertAlmostEqual(point_triangle_distance([2, 0, 0], self.face), 1)
        self.assertAlmostEqual(point_triangle_distance([.5, 1, 0], [[0, 0, 0], [1, 0, 0], [2, 0, 0]]), 1)
        self.assertAlmostEqual(segment_segment_distance([[-1, 0, 0], [1, 0, 0]], [[0, -1, 1], [0, 1, 1]]), 1)
        self.assertAlmostEqual(segment_segment_distance([[0, 0, 0], [1, 0, 0]], [[0, 1, 0], [1, 1, 0]]), 1)
        self.assertAlmostEqual(segment_segment_distance([[-1, 0, 0], [1, 0, 0]], [[-1, -1e-10, 0], [1, 1e-10, 0]]), 0)

    def test_serializable_result_has_certificate_fields(self):
        result = self.vertex_query([.25, .25, 1], [.25, .25, 2])
        data = json.loads(json.dumps(result.to_dict(), allow_nan=False))
        self.assertEqual(set(data), {"status", "reason", "time_interval", "lower_bound", "stats"})

    def test_random_safe_claims_have_no_dense_reference_hit(self):
        # Regression oracle only: these samples cannot create any SAFE result.
        rng = np.random.default_rng(2718)
        safe_count = 0
        for kind in ("vertex_face", "edge_edge"):
            for _ in range(30):
                start, end = rng.normal(size=(4, 3)), rng.normal(size=(4, 3))
                result = getattr(self.backend, kind)(start, end, minimum_separation=.01, max_subdivisions=64)
                if result.status != "SAFE":
                    continue
                safe_count += 1
                for t in np.linspace(0, 1, 101):
                    p = start + t * (end - start)
                    distance = (point_triangle_distance(p[0], p[1:]) if kind == "vertex_face"
                                else segment_segment_distance(p[:2], p[2:]))
                    self.assertGreater(distance, .01, result.to_dict())
        self.assertGreater(safe_count, 0)


if __name__ == "__main__":
    unittest.main()