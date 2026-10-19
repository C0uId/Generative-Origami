"""Construct a joined hybrid rigid curve, never infer motion from frame samples."""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .adaptive_bridge import AdaptiveBridgeConfig, AdaptiveClosureBridge
from .ccd_motion import RigidMechanismInterval
from .spherical_bridge import BridgeUnavailable, SphericalClosureBridge


@dataclass(frozen=True)
class ClosurePathConfig:
    dependent: tuple[int, int, int] = (3, 4, 5)
    analytic_depth: int = 3
    closure_tolerance: float = 4e-6
    max_endpoint_correction: float = 1e-3
    join_tolerance: float = 2e-11

    def __post_init__(self):
        if self.analytic_depth < 0:
            raise ValueError("analytic depth must be nonnegative")
        if not all(math.isfinite(x) and x > 0 for x in
                   (self.closure_tolerance, self.max_endpoint_correction, self.join_tolerance)):
            raise ValueError("finite positive closure path tolerances required")


class RestrictedSphericalMotion:
    """Same analytic curve, with a certified cell normalized to [0,1]."""
    motion_kind = "REGULAR_SPHERICAL_3R_CLOSURE_CELL"

    def __init__(self, parent, a, b):
        self.parent, self.a, self.b = parent, float(a), float(b)
        self.m, self.n = parent.m, parent.n
        self.q0, self.q1 = parent.q(a), parent.q(b)

    def _time(self, t):
        t = float(t)
        if not math.isfinite(t) or not 0 <= t <= 1:
            raise ValueError("expected normalized time")
        return self.a + (self.b - self.a) * t

    def q(self, t):
        return self.parent.q(self._time(t))

    def triangle(self, panel, t):
        return self.parent.triangle(panel, self._time(t))

    def vertex_bounds(self, panel, a=0., b=1.):
        return self.parent.vertex_bounds(panel, self._time(a), self._time(b))

    def chord_error_bound(self, panel, a=0., b=1.):
        return self.parent.chord_error_bound(panel, self._time(a), self._time(b))

    def joint_bounds(self, a=0., b=1.):
        return self.parent.joint_bounds(self._time(a), self._time(b))

    @property
    def fixed_joint_values(self):
        return self.parent.fixed_joint_values

    def continuous_closure(self, a=0., b=1., tolerance=4e-6, **kwargs):
        return self.parent.continuous_closure(self._time(a), self._time(b), tolerance=tolerance)

    def exact_closing_hinge_certificate(self, a=0., b=1.):
        return self.parent.exact_closing_hinge_certificate(self._time(a), self._time(b))


def strict_sector_bounds(mechanism, lo, hi):
    return bool(np.all(np.isfinite(lo)) and np.all(np.isfinite(hi))
                and np.all(lo <= hi)
                and np.all(np.where(mechanism.signs > 0, lo, -hi) >= 0.)
                and np.all(np.maximum(np.abs(lo), np.abs(hi)) <= math.pi))


class HybridClosurePath:
    """Regular analytic cells, with explicit finite-tolerance fallback pieces.

    The source knots are repaired once and shared by neighboring intervals.
    There is no exact-manifold claim for fallback cells. Every cell retains
    its original interval/parameter mapping and its chosen motion definition.
    """

    def __init__(self, mechanism, config=None):
        self.m, self.config = mechanism, config or ClosurePathConfig()
        self.fallback = AdaptiveClosureBridge(mechanism, AdaptiveBridgeConfig(
            closure_tolerance=self.config.closure_tolerance,
            max_endpoint_correction=self.config.max_endpoint_correction))

    def repair_nodes(self, angles):
        low = np.where(self.m.signs > 0, 0., -math.pi)
        high = np.where(self.m.signs > 0, math.pi, 0.)
        nodes, records = [], []
        for index, raw in enumerate(angles):
            raw = np.asarray(raw, float)
            if raw.shape != (self.m.n,) or not np.isfinite(raw).all():
                raise ValueError("finite source fold angles required")
            clipped = np.clip(raw, low, high)
            method, reason = "ANALYTIC_3R_KNOT", None
            try:
                if np.array_equal(clipped, self.m.flat):
                    node, method = self.m.flat.copy(), "EXACT_FLAT_ENDPOINT"
                elif np.array_equal(clipped, self.m.goal):
                    node, method = self.m.goal.copy(), "DECLARED_GOAL_ENDPOINT"
                else:
                    node = SphericalClosureBridge(self.m, clipped, clipped,
                                                  dependent=self.config.dependent).q(0.)
                    if not self.m.sector_valid(node, tol=0.):
                        raise BridgeUnavailable("ANALYTIC_KNOT_OUTSIDE_STRICT_SECTOR")
            except BridgeUnavailable as exc:
                reason = str(exc)
                node, repair = self.fallback.repair_node(raw, source_index=index)
                method = "BOUNDED_NEWTON_KNOT"
                if repair["status"] != "PASS":
                    raise BridgeUnavailable(f"source knot {index}: {repair['reason']}")
            delta = node - raw
            if np.linalg.norm(delta) > self.config.max_endpoint_correction:
                raise BridgeUnavailable(f"source knot {index}: ENDPOINT_CORRECTION_LIMIT")
            nodes.append(node)
            records.append({"index": index, "method": method, "fallback_reason": reason,
                            "original": raw.tolist(), "sector_clipped": clipped.tolist(),
                            "repaired": node.tolist(), "delta": delta.tolist(),
                            "correction_norm": float(np.linalg.norm(delta)),
                            "clip_norm": float(np.linalg.norm(clipped - raw)),
                            "strict_sector_passed": bool(self.m.sector_valid(node, tol=0.))})
        return nodes, records

    def build_interval(self, q0, q1, index):
        parent = SphericalClosureBridge(self.m, q0, q1, dependent=self.config.dependent)
        motions, records = [], []

        def endpoint(t):
            if t == 0.:
                return np.asarray(q0).copy()
            if t == 1.:
                return np.asarray(q1).copy()
            return parent.q(t)

        def fallback(a, b, reason):
            left, right = endpoint(a), endpoint(b)
            built = self.fallback.build_interval(left, right, index)
            for segment in built["segments"]:
                sa, sb = segment["source_parameter_interval"]
                motion = RigidMechanismInterval(self.m, segment["q0"], segment["q1"])
                motions.append(motion)
                records.append({"kind": "FINITE_TOLERANCE_POLYLINE", "source_interval": index,
                    "source_parameter_interval": [a+(b-a)*sa, a+(b-a)*sb],
                    "analytic_unavailable_reason": reason, "exact_seam_claimed": False,
                    "construction_status": segment["status"],
                    "construction_reason": segment["reason"],
                    "q0": segment["q0"], "q1": segment["q1"],
                    "closure_certificate": segment["closure_certificate"],
                    "inserted_node_repairs": built["inserted_nodes"]})

        def visit(a, b, depth):
            proof = parent.regularity(a, b)
            reason = proof["reason"]
            if proof["status"] == "PASS":
                motion = RestrictedSphericalMotion(parent, a, b)
                lo, hi = motion.joint_bounds()
                joined = max(float(np.max(np.abs(motion.q0-endpoint(a)))),
                             float(np.max(np.abs(motion.q1-endpoint(b))))) <= self.config.join_tolerance
                closure = motion.continuous_closure(tolerance=self.config.closure_tolerance)
                if joined and strict_sector_bounds(self.m, lo, hi) and closure["status"] == "PASS":
                    motions.append(motion)
                    records.append({"kind": "ANALYTIC_SPHERICAL_3R", "source_interval": index,
                        "source_parameter_interval": [a,b], "exact_seam_claimed": True,
                        "construction_status": "PASS", "regularity": proof,
                        "q0": motion.q0.tolist(), "q1": motion.q1.tolist(),
                        "closure_certificate": closure})
                    return
                reason = ("ANALYTIC_ENDPOINT_BRANCH_MISMATCH" if not joined else
                          "NONLINEAR_SECTOR_BOUND_UNRESOLVED" if not strict_sector_bounds(self.m,lo,hi)
                          else closure["reason"])
                qm = parent.q((a+b)/2.)
                if min(min(abs(qm[k]), abs(abs(qm[k])-math.pi)) for k in parent.dependent) < 1e-9:
                    fallback(a,b,reason)
                    return
            if depth < self.config.analytic_depth:
                mid = (a+b)/2.
                try:
                    parent.q(mid)
                except BridgeUnavailable:
                    fallback(a,b,reason)
                    return
                visit(a,mid,depth+1)
                visit(mid,b,depth+1)
            else:
                fallback(a,b,reason)

        visit(0.,1.,0)
        continuity = True
        max_join = 0.
        previous = np.asarray(q0)
        for motion in motions:
            max_join = max(max_join, float(np.max(np.abs(previous-motion.q0))))
            previous = motion.q1
        max_join = max(max_join,float(np.max(np.abs(previous-np.asarray(q1)))))
        continuity = max_join <= self.config.join_tolerance
        if not continuity or any(r["construction_status"] != "PASS" for r in records):
            discarded = {"reason": "HYBRID_JOIN_OR_CONSTRUCTION_NOT_PROVEN",
                         "max_join_error": max_join, "discarded_cell_count": len(records)}
            motions.clear()
            records.clear()
            fallback(0.,1.,discarded["reason"])
            max_join, previous = 0., np.asarray(q0)
            for motion in motions:
                max_join = max(max_join,float(np.max(np.abs(previous-motion.q0))))
                previous = motion.q1
            max_join = max(max_join,float(np.max(np.abs(previous-np.asarray(q1)))))
            continuity = max_join <= self.config.join_tolerance
        else:
            discarded = None
        return motions, {"source_interval": index, "cells": records,
                          "continuous_join_passed": continuity, "max_join_error": max_join,
                          "join_tolerance": self.config.join_tolerance,
                          "discarded_hybrid_attempt": discarded}