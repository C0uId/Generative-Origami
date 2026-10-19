"""Explicit piecewise rigid bridges with a finite continuous closure tolerance.

Projection constructs *nodes*, never the motion between them. Each emitted
segment is q-linear and uses the unchanged Rodrigues forward kinematics.
Only ``RigidMechanismInterval.continuous_closure`` can give a segment PASS.
This constructs a modified path; it is neither an exact manifold curve nor
a collision certificate. Source-interval parameters identify order only,
not equality with the original unprojected interpolation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Callable

import numpy as np
from scipy.spatial.transform import Rotation

from .ccd_motion import RigidMechanismInterval


@dataclass(frozen=True)
class AdaptiveBridgeConfig:
    closure_tolerance: float = 4e-6
    projection_tolerance: float = 2e-8
    max_bridge_depth: int = 10
    max_closure_checks_per_interval: int = 4096
    closure_bound_depth: int = 8
    projection_iterations: int = 16
    max_endpoint_correction: float = 1e-3
    max_midpoint_correction: float = 5e-2

    def __post_init__(self):
        for name in ("closure_tolerance", "projection_tolerance",
                     "max_endpoint_correction", "max_midpoint_correction"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
        if self.projection_tolerance >= self.closure_tolerance:
            raise ValueError("projection tolerance must leave a continuous-bound margin")
        for name in ("max_bridge_depth", "closure_bound_depth"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        for name in ("max_closure_checks_per_interval", "projection_iterations"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


class AdaptiveClosureBridge:
    """Bounded adaptive construction; every failed leaf is retained explicitly."""

    def __init__(self, mechanism, config: AdaptiveBridgeConfig | None = None):
        self.m = mechanism
        self.config = config or AdaptiveBridgeConfig()
        self.low = np.where(self.m.signs > 0, 0., -math.pi)
        self.high = np.where(self.m.signs > 0, math.pi, 0.)

    def _angles(self, q):
        q = np.asarray(q, dtype=float)
        if q.shape != (self.m.n,) or not np.isfinite(q).all():
            raise ValueError("finite angle vectors of the mechanism dimension required")
        return q.copy()

    def closure_residual(self, q):
        """Stable SO(3) log, including the near-zero 1e-8..1e-7 regime.

        The legacy mechanism log selects a near-pi axis fallback in that
        regime. Keep that historic implementation untouched and use scipy's
        stable rotation logarithm for construction only. Certificates still
        use the unchanged matrix-product analytic bounds.
        """
        last = self.m.panel_rotations(q)[-1]
        axis = np.r_[self.m.rays[0]["unit2"], 0.]
        return Rotation.from_matrix(last @ self.m._axis_rotation(axis, float(q[0]))).as_rotvec()

    def _project(self, clipped):
        q = clipped.copy()
        for _ in range(self.config.projection_iterations):
            residual = self.closure_residual(q)
            error = float(np.linalg.norm(residual))
            if error <= self.config.projection_tolerance:
                break
            jacobian = np.empty((3, self.m.n))
            h = 1e-6
            for j in range(self.m.n):
                offset = np.zeros(self.m.n)
                offset[j] = h
                jacobian[:, j] = (self.closure_residual(q + offset) -
                                  self.closure_residual(q - offset)) / (2 * h)
            delta = -np.linalg.pinv(jacobian, rcond=1e-10) @ residual
            accepted = False
            for alpha in (1., .5, .25, .125, .0625):
                candidate = np.clip(q + alpha * delta, self.low, self.high)
                if np.linalg.norm(self.closure_residual(candidate)) < error:
                    q = candidate
                    accepted = True
                    break
            if not accepted:
                break
        return q, float(np.linalg.norm(self.closure_residual(q)))

    def repair_node(self, raw, *, kind="ENDPOINT", source_index=None,
                    source_parameter=None):
        """Record initial sector clipping and aggregate Newton projection changes.

        The existing Newton implementation also clips trial iterates to the
        sector. That constraint is declared here, and the accepted final change
        is recorded in full. A failed/excessive change is never accepted.
        """
        raw = self._angles(raw)
        clipped = np.clip(raw, self.low, self.high)
        clipped_error = float(np.linalg.norm(self.closure_residual(clipped)))
        projected, reported_error = self._project(clipped)
        projected = self._angles(projected)
        error = float(np.linalg.norm(self.closure_residual(projected)))
        correction = float(np.linalg.norm(projected - raw))
        limit = (self.config.max_endpoint_correction if kind == "ENDPOINT"
                 else self.config.max_midpoint_correction)
        valid = (self.m.sector_valid(projected, tol=0.) and
                 error <= self.config.projection_tolerance and correction <= limit)
        record = {
            "kind": kind, "source_index": source_index,
            "source_parameter": source_parameter,
            "status": "PASS" if valid else "UNCERTAIN",
            "reason": ("NODE_REPAIR_ACCEPTED" if valid else
                       "NODE_CORRECTION_EXCEEDS_BUDGET" if correction > limit else
                       "NODE_PROJECTION_OR_STRICT_SECTOR_FAILED"),
            "original_angles": raw.tolist(), "clipped_angles": clipped.tolist(),
            "projected_angles": projected.tolist(),
            "clip_delta": (clipped - raw).tolist(),
            "projection_delta": (projected - clipped).tolist(),
            "total_correction_norm": correction, "correction_limit": limit,
            "changed": bool(np.any(projected != raw)),
            "original_closure_error": float(np.linalg.norm(self.closure_residual(raw))),
            "clipped_closure_error": clipped_error,
            "projected_closure_error": error, "projector_reported_error": float(reported_error),
            "strict_sector_passed": bool(self.m.sector_valid(projected, tol=0.)),
            "projection_method": "BOUNDED_MINIMUM_NORM_NEWTON_WITH_SECTOR_CLIPPED_TRIALS",
        }
        return projected if valid else raw.copy(), record

    def build_interval(self, q0, q1, index=0):
        """Endpoints must already be accepted repaired nodes, as build() ensures."""
        q0, q1 = self._angles(q0), self._angles(q1)
        segments, inserted = [], []
        calls = 0

        def emit(left, right, a, b, depth, certificate, reason=None):
            sector = self.m.sector_valid(left, tol=0.) and self.m.sector_valid(right, tol=0.)
            passed = certificate.get("status") == "PASS" and sector and reason is None
            segments.append({
                "source_interval": int(index), "source_parameter_interval": [a, b],
                "depth": depth, "q0": left.tolist(), "q1": right.tolist(),
                "status": "PASS" if passed else "UNCERTAIN",
                "reason": reason or ("CONTINUOUS_CLOSURE_AND_STRICT_SECTOR_BOUNDED" if passed
                                      else "STRICT_SECTOR_VIOLATION" if not sector
                                      else certificate.get("reason", "CONTINUOUS_CLOSURE_NOT_PROVEN")),
                "sector_passed": bool(sector), "closure_certificate": certificate,
                "motion_model": "q-linear joint angles evaluated through Rodrigues rigid FK",
                "collision_checked": False,
            })

        def visit(left, right, a, b, depth):
            nonlocal calls
            if calls >= self.config.max_closure_checks_per_interval:
                emit(left, right, a, b, depth,
                     {"status": "UNCERTAIN", "reason": "CLOSURE_CHECK_BUDGET_EXHAUSTED"},
                     "CLOSURE_CHECK_BUDGET_EXHAUSTED")
                return
            calls += 1
            certificate = RigidMechanismInterval(self.m, left, right).continuous_closure(
                tolerance=self.config.closure_tolerance, max_depth=self.config.closure_bound_depth)
            if certificate["status"] == "PASS":
                emit(left, right, a, b, depth, certificate)
                return
            if depth >= self.config.max_bridge_depth:
                emit(left, right, a, b, depth, certificate, "BRIDGE_SUBDIVISION_DEPTH_EXHAUSTED")
                return
            mid = (a + b) / 2.
            node, change = self.repair_node((left + right) / 2., kind="MIDPOINT",
                                            source_index=int(index), source_parameter=mid)
            inserted.append(change)
            if change["status"] != "PASS":
                emit(left, right, a, b, depth, certificate, change["reason"])
                return
            visit(left, node, a, mid, depth + 1)
            visit(node, right, mid, b, depth + 1)

        visit(q0, q1, 0., 1., 0)
        passed = bool(segments) and all(s["status"] == "PASS" for s in segments)
        return {"source_interval": int(index), "status": "PASS" if passed else "UNCERTAIN",
                "closure_checks": calls, "segment_count": len(segments),
                "max_depth_used": max(s["depth"] for s in segments),
                "inserted_nodes": inserted, "segments": segments}

    def build(self, angles, *, progress_callback: Callable | None = None):
        angles = [self._angles(q) for q in angles]
        if len(angles) < 2:
            raise ValueError("at least two source angle vectors required")
        repaired, repairs = [], []
        for i, q in enumerate(angles):
            node, repair = self.repair_node(q, source_index=i)
            repaired.append(node)
            repairs.append(repair)
        intervals = []
        for i in range(len(angles) - 1):
            result = self.build_interval(repaired[i], repaired[i + 1], i)
            if repairs[i]["status"] != "PASS" or repairs[i + 1]["status"] != "PASS":
                result["status"] = "UNCERTAIN"
                result["endpoint_repair_failed"] = True
            intervals.append(result)
            if progress_callback:
                progress_callback(result)
        segments = [s for interval in intervals for s in interval["segments"]]
        all_pass = all(x["status"] == "PASS" for x in intervals)
        return {
            "schema_version": 1, "experiment_id": "POC01-007C3-B_CLOSURE_BRIDGE",
            "status": "FINITE_TOLERANCE_CLOSURE_BRIDGE" if all_pass else "CLOSURE_BRIDGE_NOT_CERTIFIED",
            "continuous_closure_within_tolerance": all_pass,
            "exact_manifold_claimed": False, "collision_checked": False,
            "continuous_collision_detection_certified": False,
            "source_interval_count": len(intervals), "source_keyframe_count": len(angles),
            "segment_count": len(segments),
            "interval_counts": {s: sum(x["status"] == s for x in intervals) for s in ("PASS", "UNCERTAIN")},
            "segment_counts": {s: sum(x["status"] == s for x in segments) for s in ("PASS", "UNCERTAIN")},
            "endpoint_changes": sum(x["changed"] for x in repairs),
            "max_endpoint_correction": max(x["total_correction_norm"] for x in repairs),
            "closure_checks": sum(x["closure_checks"] for x in intervals),
            "config": asdict(self.config), "endpoint_repairs": repairs, "intervals": intervals,
            "motion_definition": "Ordered concatenation of emitted q-linear rigid FK segments; projected nodes change the original candidate bridge.",
            "mapping_scope": "Source interval and dyadic parameter retain ordering; they do not assert identity with the source interpolation.",
            "numeric_scope": "Finite closure tolerance with unchanged analytic reference enclosures and floating-point guard; not an exact manifold or formal interval arithmetic proof.",
        }