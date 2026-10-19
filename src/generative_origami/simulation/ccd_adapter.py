"""Conservative, replaceable CCD adapter for *linear surrogate* trajectories.

This module never calls a chord a rigid motion.  A caller certifying a curved
rigid trajectory must enclose that trajectory and add its chord-deviation bound
to ``minimum_separation``.  SAFE covers the whole normalized interval [0, 1];
POSSIBLE_HIT is deliberately not a statement that a collision really occurred.

The reference backend uses distance Lipschitz bounds and swept AABBs, rather
than Tight-Inclusion's inclusion root finder.  Its floating-point guarantee is
conditional on the reported numerical error allowance (not an exact-arithmetic
proof).  Ill-conditioned distance computations fail closed.  A future native
binding can implement the same query contract without changing callers.

Native contract: module ``generative_origami._tight_inclusion`` exports
``vertex_face`` and ``edge_edge`` with the same arguments.  Return bool False
only when the complete linear query is collision free, bool True for a possible
hit, or a CCDResult / dict with this module's status schema.  See the upstream
semantics: https://github.com/Continuous-Collision-Detection/Tight-Inclusion .
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import math
from typing import Any

import numpy as np


STATUSES = frozenset({"SAFE", "POSSIBLE_HIT", "UNCERTAIN"})


@dataclass(frozen=True)
class CCDResult:
    status: str
    reason: str
    time_interval: tuple[float, float] = (0.0, 1.0)
    lower_bound: float | None = None
    stats: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"Unknown CCD status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "time_interval": list(self.time_interval),
            "lower_bound": self.lower_bound,
            "stats": dict(self.stats),
        }


class BackendUnavailable(RuntimeError):
    """An explicitly requested native backend could not be loaded."""


def _norm(v) -> float:
    return float(np.linalg.norm(v))


def _point_segment_distance(p, a, b) -> float:
    ab = b - a
    denominator = float(np.dot(ab, ab))
    if denominator == 0.0:
        return _norm(p - a)
    t = float(np.clip(np.dot(p - a, ab) / denominator, 0.0, 1.0))
    return _norm(p - (a + t * ab))


def point_triangle_distance(point, a, b=None, c=None) -> float:
    """Ericson closest-feature point/triangle distance; accepts (point, triangle).

    This public helper returns a floating-point distance, not a certificate.
    Degenerate triangles are interpreted as the union of their three edges.
    """
    p = np.asarray(point, dtype=float)
    if b is None and c is None:
        a, b, c = np.asarray(a, dtype=float)
    else:
        a, b, c = (np.asarray(v, dtype=float) for v in (a, b, c))
    ab, ac, ap = b - a, c - a, p - a
    if _norm(np.cross(ab, ac)) <= np.finfo(float).eps * max(
        float(np.dot(ab, ab)), float(np.dot(ac, ac)), np.finfo(float).tiny
    ):
        return min(_point_segment_distance(p, a, b),
                   _point_segment_distance(p, b, c),
                   _point_segment_distance(p, c, a))
    d1, d2 = float(np.dot(ab, ap)), float(np.dot(ac, ap))
    if d1 <= 0 and d2 <= 0:
        return _norm(ap)
    bp = p - b
    d3, d4 = float(np.dot(ab, bp)), float(np.dot(ac, bp))
    if d3 >= 0 and d4 <= d3:
        return _norm(bp)
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        return _norm(p - (a + (d1 / (d1 - d3)) * ab))
    cp = p - c
    d5, d6 = float(np.dot(ab, cp)), float(np.dot(ac, cp))
    if d6 >= 0 and d5 <= d6:
        return _norm(cp)
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        return _norm(p - (a + (d2 / (d2 - d6)) * ac))
    va = d3 * d6 - d5 * d4
    if va <= 0 and d4 - d3 >= 0 and d5 - d6 >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return _norm(p - (b + w * (c - b)))
    denominator = va + vb + vc
    if denominator <= 0 or not math.isfinite(denominator):
        # A public best estimate; the certification routine rejects this
        # conditioning before relying on it as a lower bound.
        return 0.0
    v, w = vb / denominator, vc / denominator
    return _norm(p - (a + ab * v + ac * w))


def segment_segment_distance(p1, q1, p2=None, q2=None) -> float:
    """Ericson segment/segment distance; also accepts two (2, 3) arrays."""
    if p2 is None and q2 is None:
        first, second = np.asarray(p1, dtype=float), np.asarray(q1, dtype=float)
        p1, q1, p2, q2 = first[0], first[1], second[0], second[1]
    else:
        p1, q1, p2, q2 = (np.asarray(v, dtype=float) for v in (p1, q1, p2, q2))
    d1, d2, r = q1 - p1, q2 - p2, p1 - p2
    a, e = float(np.dot(d1, d1)), float(np.dot(d2, d2))
    if a == 0:
        return _point_segment_distance(p1, p2, q2)
    if e == 0:
        return _point_segment_distance(p2, p1, q1)
    b, c, f = float(np.dot(d1, d2)), float(np.dot(d1, r)), float(np.dot(d2, r))
    # The cross-product expression avoids subtracting nearly equal a*e, b*b.
    denominator = float(np.dot(np.cross(d1, d2), np.cross(d1, d2)))
    if denominator == 0.0:
        return min(_point_segment_distance(p1, p2, q2),
                   _point_segment_distance(q1, p2, q2),
                   _point_segment_distance(p2, p1, q1),
                   _point_segment_distance(q2, p1, q1))
    # A cross-product numerator is more stable for nearly parallel segments.
    s = float(np.clip(np.dot(np.cross(p2 - p1, d2), np.cross(d1, d2)) / denominator, 0, 1))
    t = (b * s + f) / e
    if t < 0:
        t, s = 0.0, float(np.clip(-c / a, 0, 1))
    elif t > 1:
        t, s = 1.0, float(np.clip((b - c) / a, 0, 1))
    return _norm((p1 + s * d1) - (p2 + t * d2))


def _validate(start, end, minimum_separation, tolerance, max_subdivisions, numerical_error):
    try:
        start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
        if start.shape != (4, 3) or end.shape != (4, 3):
            return None, "INPUT_SHAPE_MUST_BE_4_BY_3"
        if not np.all(np.isfinite(start)) or not np.all(np.isfinite(end)):
            return None, "NONFINITE_INPUT"
        if max(float(np.max(np.abs(start))), float(np.max(np.abs(end)))) > 1e50:
            return None, "COORDINATES_OUTSIDE_REFERENCE_NUMERIC_RANGE"
        for value in (minimum_separation, tolerance, numerical_error):
            if not math.isfinite(value) or value < 0:
                return None, "INVALID_NUMERICAL_PARAMETER"
        if tolerance == 0:
            return None, "TOLERANCE_MUST_BE_POSITIVE"
        if isinstance(max_subdivisions, bool) or int(max_subdivisions) != max_subdivisions or max_subdivisions < 0:
            return None, "INVALID_SUBDIVISION_BUDGET"
        return (start, end), None
    except (ValueError, TypeError, OverflowError):
        return None, "INVALID_INPUT"


def _aabb_lower(a0, a1, b0, b1, margin):
    amin, amax = np.minimum(a0.min(axis=0), a1.min(axis=0)), np.maximum(a0.max(axis=0), a1.max(axis=0))
    bmin, bmax = np.minimum(b0.min(axis=0), b1.min(axis=0)), np.maximum(b0.max(axis=0), b1.max(axis=0))
    gap = np.maximum(np.maximum(bmin - amax, amin - bmax), 0)
    return max(0.0, _norm(gap) - margin)


def _projection_lower(kind, positions, margin):
    """Independent supporting-plane lower bound, for any chosen axes.

    Even an inaccurate closest-feature branch cannot make this quantity exceed
    the real separation: projection of a convex primitive is the interval of
    its vertex projections.  The axis need not be optimal, only finite.
    """
    if kind == "vertex_face":
        first, second = positions[:1], positions[1:]
        edges = [second[1] - second[0], second[2] - second[1], second[0] - second[2]]
        normal = np.cross(edges[0], edges[1])
        axes = [normal] + [np.cross(normal, edge) for edge in edges]
        axes.extend(first[0] - vertex for vertex in second)
    else:
        first, second = positions[:2], positions[2:]
        edge1, edge2 = first[1] - first[0], second[1] - second[0]
        normal = np.cross(edge1, edge2)
        axes = [normal, np.cross(normal, edge1), np.cross(normal, edge2)]
        axes.extend(a - b for a in first for b in second)
    origin = positions[0]
    lower = 0.0
    for axis in axes:
        length = _norm(axis)
        if not math.isfinite(length) or length <= np.finfo(float).tiny:
            continue
        unit = axis / length
        proj_a, proj_b = (first - origin) @ unit, (second - origin) @ unit
        gap = max(float(proj_a.min() - proj_b.max()), float(proj_b.min() - proj_a.max()))
        # The norm upper allowance also prevents a rounded-up unit norm from
        # causing an overly large Euclidean lower bound.
        unit_norm_upper = float(np.nextafter(_norm(unit) + 32 * np.finfo(float).eps, math.inf))
        lower = max(lower, max(0.0, gap - margin) / unit_norm_upper)
    return max(0.0, lower - margin)


def _distance_lower(kind, positions, margin):
    if kind == "vertex_face":
        ab, ac = positions[2] - positions[1], positions[3] - positions[1]
        size2 = max(float(np.dot(ab, ab)), float(np.dot(ac, ac)))
        area = _norm(np.cross(ab, ac))
        if size2 == 0 or area <= 1e-7 * size2:
            return 0.0, None, "DEGENERATE_OR_ILL_CONDITIONED_FACE"
        condition = max(1.0, size2 / area)
        distance = point_triangle_distance(positions[0], positions[1:])
    else:
        d1, d2 = positions[1] - positions[0], positions[3] - positions[2]
        length_product = _norm(d1) * _norm(d2)
        cross = _norm(np.cross(d1, d2))
        if length_product == 0 or cross <= 1e-7 * length_product:
            return 0.0, None, "DEGENERATE_OR_NEAR_PARALLEL_EDGES"
        condition = max(1.0, length_product / cross)
        distance = segment_segment_distance(positions[:2], positions[2:])
    if not math.isfinite(distance):
        return 0.0, None, "NONFINITE_DISTANCE"
    # Squared conditioning compensates the dot-product/determinant formulas.
    allowance = margin * condition * condition
    # Cap the closest-feature estimate by an independent supporting-plane
    # certificate.  Sampling a distance alone never proves a time interval.
    return min(max(0.0, distance - allowance), _projection_lower(kind, positions, margin)), distance, None


class PythonReferenceBackend:
    """Whole-interval bounds, with finite work and conservative uncertainty."""

    name = "python_reference"

    def backend_info(self):
        return {
            "name": self.name,
            "native": False,
            "algorithm": "swept_aabb_and_distance_lipschitz_subdivision",
            "trajectory_scope": "linear_vertex_surrogate_only",
            "guarantee_scope": "conditional_float64_error_allowance; ill_conditioned_queries_fail_closed",
            "is_tight_inclusion_library": False,
            "safe_semantics": "all_time_cells_have_separation_lower_bound_above_minimum_separation",
            "possible_hit_is_definite_collision": False,
        }

    def vertex_face(self, start, end, minimum_separation=0, tolerance=1e-9,
                    max_subdivisions=128, numerical_error=1e-12):
        return self._query("vertex_face", start, end, minimum_separation,
                           tolerance, max_subdivisions, numerical_error)

    def edge_edge(self, start, end, minimum_separation=0, tolerance=1e-9,
                  max_subdivisions=128, numerical_error=1e-12):
        return self._query("edge_edge", start, end, minimum_separation,
                           tolerance, max_subdivisions, numerical_error)

    def _query(self, kind, start, end, minimum_separation, tolerance,
               max_subdivisions, numerical_error):
        stats = {"backend": self.name, "primitive": kind, "native": False,
                 "trajectory_scope": "linear_vertex_surrogate_only",
                 "subdivisions": 0, "cells_tested": 0, "safe_leaves": 0,
                 "aabb_safe_leaves": 0, "distance_safe_leaves": 0,
                 "numerical_error_requested": numerical_error}
        query, error = _validate(start, end, minimum_separation, tolerance,
                                 max_subdivisions, numerical_error)
        if error:
            return CCDResult("UNCERTAIN", error, stats=stats)
        start, end = query
        split = 1 if kind == "vertex_face" else 2
        velocity = end - start
        scale = max(1.0, float(np.max(np.abs(start))), float(np.max(np.abs(end))))
        margin = float(numerical_error + 512 * np.finfo(float).eps * scale)
        stats["roundoff_allowance_base"] = margin
        # Hausdorff movement of each convex primitive is at most the largest
        # movement of one of its vertices.  This covers every material point.
        speed = max(map(_norm, velocity[:split])) + max(map(_norm, velocity[split:]))
        speed = float(np.nextafter(speed + margin, math.inf))
        stats["distance_lipschitz_speed_upper_bound"] = speed
        stack = [(0.0, 1.0)]
        certified_lower = math.inf
        while stack:
            lo, hi = stack.pop()
            stats["cells_tested"] += 1
            first, last = start + lo * velocity, start + hi * velocity
            box_bound = _aabb_lower(first[:split], last[:split], first[split:], last[split:], margin)
            if box_bound > minimum_separation:
                stats["safe_leaves"] += 1
                stats["aabb_safe_leaves"] += 1
                certified_lower = min(certified_lower, box_bound)
                continue
            mid = (lo + hi) / 2
            lower, measured, distance_error = _distance_lower(kind, start + mid * velocity, margin)
            movement_radius = float(np.nextafter(speed * ((hi - lo) / 2) + margin, math.inf))
            cell_bound = max(box_bound, max(0.0, lower - movement_radius))
            if cell_bound > minimum_separation:
                stats["safe_leaves"] += 1
                stats["distance_safe_leaves"] += 1
                certified_lower = min(certified_lower, cell_bound)
                continue
            if measured is not None and measured <= minimum_separation + margin:
                stats["witness_time"] = mid
                stats["witness_distance"] = measured
                return CCDResult("POSSIBLE_HIT", "MIDPOINT_WITHIN_SEPARATION_ALLOWANCE",
                                 (lo, hi), cell_bound, stats)
            if stats["subdivisions"] >= max_subdivisions:
                stats["unresolved_pending_cells"] = len(stack) + 1
                if distance_error:
                    stats["distance_failure"] = distance_error
                return CCDResult("UNCERTAIN", "SUBDIVISION_BUDGET_EXHAUSTED",
                                 (lo, hi), cell_bound, stats)
            if hi - lo <= tolerance or mid == lo or mid == hi:
                if distance_error:
                    stats["distance_failure"] = distance_error
                return CCDResult("UNCERTAIN", "TIME_INTERVAL_TOLERANCE_WITHOUT_SEPARATION_PROOF",
                                 (lo, hi), cell_bound, stats)
            stats["subdivisions"] += 1
            stack.extend(((mid, hi), (lo, mid)))
        return CCDResult("SAFE", "ALL_TIME_CELLS_PROVED_SEPARATED", (0.0, 1.0),
                         certified_lower, stats)


class NativeTightInclusionBackend:
    """Explicit native binding; never silently switches to Python."""

    name = "native_tight_inclusion"

    def __init__(self, module_name="generative_origami._tight_inclusion"):
        try:
            self.module = importlib.import_module(module_name)
        except (ImportError, OSError) as exc:
            raise BackendUnavailable(f"Native CCD backend unavailable: {module_name}: {exc}") from exc
        if not all(callable(getattr(self.module, method, None)) for method in ("vertex_face", "edge_edge")):
            raise BackendUnavailable(f"Native CCD backend does not implement the adapter ABI: {module_name}")
        self.module_name = module_name

    def backend_info(self):
        return {"name": self.name, "native": True, "module": self.module_name,
                "trajectory_scope": "linear_vertex_surrogate_only",
                "guarantee_scope": "native_binding_must_honor_tight_inclusion_false_means_no_hit_contract",
                "possible_hit_is_definite_collision": False}

    def vertex_face(self, start, end, minimum_separation=0, tolerance=1e-9,
                    max_subdivisions=128, numerical_error=1e-12):
        return self._query("vertex_face", start, end, minimum_separation,
                           tolerance, max_subdivisions, numerical_error)

    def edge_edge(self, start, end, minimum_separation=0, tolerance=1e-9,
                  max_subdivisions=128, numerical_error=1e-12):
        return self._query("edge_edge", start, end, minimum_separation,
                           tolerance, max_subdivisions, numerical_error)

    def _query(self, kind, start, end, minimum_separation, tolerance, max_subdivisions, numerical_error):
        stats = {"backend": self.name, "native": True, "module": self.module_name}
        query, error = _validate(start, end, minimum_separation, tolerance, max_subdivisions, numerical_error)
        if error:
            return CCDResult("UNCERTAIN", error, stats=stats)
        try:
            value = getattr(self.module, kind)(*query, minimum_separation=minimum_separation,
                tolerance=tolerance, max_subdivisions=max_subdivisions, numerical_error=numerical_error)
            if isinstance(value, (bool, np.bool_)):
                return CCDResult("POSSIBLE_HIT" if value else "SAFE",
                                 "NATIVE_POSSIBLE_HIT" if value else "NATIVE_NO_COLLISION", stats=stats)
            if isinstance(value, dict):
                value = CCDResult(**value)
            if isinstance(value, CCDResult):
                if value.status == "SAFE" and tuple(value.time_interval) != (0.0, 1.0):
                    return CCDResult("UNCERTAIN", "NATIVE_SAFE_RESULT_DID_NOT_COVER_FULL_INTERVAL", stats=stats)
                return CCDResult(value.status, value.reason, value.time_interval,
                                 value.lower_bound, {**value.stats, **stats})
            return CCDResult("UNCERTAIN", "INVALID_NATIVE_RETURN_CONTRACT", stats=stats)
        except Exception as exc:
            return CCDResult("UNCERTAIN", "NATIVE_BACKEND_ERROR", stats={**stats, "error": str(exc)})


def get_backend(name="reference"):
    if name in {"reference", "python", "python_reference"}:
        return PythonReferenceBackend()
    if name in {"native", "tight_inclusion", "native_tight_inclusion"}:
        return NativeTightInclusionBackend()
    raise ValueError(f"Unknown CCD backend: {name}")


def backend_info(name="reference"):
    return get_backend(name).backend_info()