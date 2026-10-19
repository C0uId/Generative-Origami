"""Goal active-set charts with explicit material and whole-interval contact audits.

A chart is an actual Rodrigues rigid motion with a spherical 3R closure
identity. Contact is never inferred from endpoint coincidence or sampled
frames. Unresolved chart singularities and signed gaps remain UNCERTAIN.
The bounds inherit the documented conditional float64 guards of the C3-B
spherical reference implementation; they are not formal interval arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import itertools
import math

import numpy as np

from .closure_path import RestrictedSphericalMotion, strict_sector_bounds
from .layer_contact import LayerContactModel, _barycentric, _convex_clip, _poly_area
from .spherical_bridge import BridgeUnavailable, SphericalClosureBridge


class ContactState(str, Enum):
    FREE = "FREE"
    CONTACT = "CONTACT"
    RELEASE = "RELEASE"


@dataclass(frozen=True)
class GoalContactBridgeConfig:
    dependent: tuple[int, int, int] = (0, 1, 2)
    max_depth: int = 9
    closure_tolerance: float = 4e-6
    join_tolerance: float = 2e-11
    boundary_snap_tolerance: float = 2e-8
    max_endpoint_correction: float = 1e-3
    numerical_error: float = 1e-12

    def __post_init__(self):
        if self.max_depth < 0:
            raise ValueError("nonnegative chart depth required")
        for name in ("closure_tolerance", "join_tolerance", "boundary_snap_tolerance",
                     "max_endpoint_correction", "numerical_error"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"positive finite {name} required")


def _dot_interval(weights, lo, hi):
    weights = np.asarray(weights)
    lower = np.sum(np.where(weights >= 0., weights * lo, weights * hi))
    upper = np.sum(np.where(weights >= 0., weights * hi, weights * lo))
    return float(np.nextafter(lower, -np.inf)), float(np.nextafter(upper, np.inf))


class GoalMaterialContact:
    """Finite contact polygons for every panel pair, including adjacent pairs.

    C3-B's nonadjacent final-pair list cannot describe an adjacent hinge that
    has reached pi. A finite overlap patch is constructed explicitly here.
    Its vertices have material barycentric coordinates on both panels.
    """
    def __init__(self, mechanism, layer_order=None):
        self.m = mechanism
        self.order = list(layer_order if layer_order is not None else [7, 6, 5, 0, 4, 1, 3, 2])
        if sorted(self.order) != list(range(mechanism.n)):
            raise ValueError("layer order must contain each panel exactly once")
        self.rank = {p: i for i, p in enumerate(self.order)}
        edges = LayerContactModel._adjacent_order_edges(self)
        if not (all(self.rank[a] < self.rank[b] for a, b in edges) or
                all(self.rank[a] > self.rank[b] for a, b in edges)):
            raise ValueError("layer order contradicts M/V adjacency")
        goal = mechanism.panel_triangles(mechanism.goal)
        self.patches = {}
        self.patch_diagnostics = {}
        for pair in itertools.combinations(range(mechanism.n), 2):
            i, j = pair
            poly = _convex_clip(goal[i][:, :2], goal[j][:, :2])
            if len(poly) < 3 or abs(_poly_area(poly)) <= 1e-10:
                continue
            patch = []
            for point in poly:
                # The exact common origin is one material vertex, not a ball.
                if np.linalg.norm(point) <= self.m.n * np.finfo(float).eps:
                    wi = wj = np.array([1., 0., 0.])
                else:
                    wi = _barycentric(point, goal[i][:, :2])
                    wj = _barycentric(point, goal[j][:, :2])
                patch.append((wi, wj))
            self.patches[pair] = patch
            self.patch_diagnostics[pair] = {
                "material_mapping_error_diagnostic": max(float(np.linalg.norm(wi@goal[i]-wj@goal[j])) for wi,wj in patch),
                "minimum_barycentric_coordinate": min(float(min(np.min(wi),np.min(wj))) for wi,wj in patch),
                "numeric_scope": "conditional float64 material polygon, with 1e-9 reconstruction guard; not formal interval geometry"}

    def fixed_goal_patch(self, motion, pair):
        pair = tuple(sorted(pair))
        i, j = pair
        values = np.asarray(motion.fixed_joint_values)
        if pair not in self.patches or values.shape != (self.m.n,):
            return None
        if not np.array_equal(values[i+1:j+1], self.m.goal[i+1:j+1]):
            return None
        diagnostics = self.patch_diagnostics[pair]
        if (diagnostics["material_mapping_error_diagnostic"] > 1e-9 or
                diagnostics["minimum_barycentric_coordinate"] < -1e-9):
            return None
        return {"status": "PASS", "reason": "ACTIVE_SET_FIXED_GOAL_MATERIAL_PATCH",
                "state": ContactState.CONTACT.value, "panels": list(pair),
                "patch_vertex_count": len(self.patches[pair]),
                "material_coordinates": [[a.tolist(), b.tolist()] for a, b in self.patches[pair]],
                "relative_pose_identity": "R_i^-1 R_j = fixed goal Rodrigues product",
                "material_mapping": "same material pair for every point of the finite goal overlap polygon",
                "layer_order": [self.rank[i], self.rank[j]],
                "signed_gap_lower_bound": 0., "signed_gap_upper_bound": 0.,
                "signed_gap_identity": "identically zero; fixed relative material pose",
                "whole_panel_exemption": False,
                "proof_scope": "finite material patch with analytically constant relative pose",
                "material_polygon_diagnostics": diagnostics}

    def audit_pair(self, motion, pair, a=0., b=1.):
        pair = tuple(sorted(pair))
        fixed = self.fixed_goal_patch(motion, pair)
        if fixed:
            return {**fixed, "time_interval": [float(a), float(b)]}
        if pair not in self.patches:
            return {"status": "NOT_APPLICABLE", "reason": "NO_FINITE_GOAL_PATCH",
                    "panels": list(pair), "state": ContactState.FREE.value}
        i, j = pair
        il, ih = motion.vertex_bounds(i, a, b)
        jl, jh = motion.vertex_bounds(j, a, b)
        sign = 1. if self.rank[i] > self.rank[j] else -1.
        lower, upper = [], []
        for wi, wj in self.patches[pair]:
            if np.array_equal(wi, [1., 0., 0.]) and np.array_equal(wj, [1., 0., 0.]):
                lower.append(0.); upper.append(0.); continue
            al, ah = _dot_interval(wi, il[:, 2], ih[:, 2])
            bl, bh = _dot_interval(wj, jl[:, 2], jh[:, 2])
            gl, gh = al-bh, ah-bl
            lower.append(min(sign*gl, sign*gh))
            upper.append(max(sign*gl, sign*gh))
        lo, hi = min(lower), max(upper)
        proved = lo >= 0.
        state = ContactState.FREE.value
        if proved and hasattr(motion, "parent"):
            release = any(e["event"] == "RELEASE" and i < e["joint"] <= j
                          for e in self.events(motion.parent))
            if release:
                state = ContactState.RELEASE.value
        return {"status": "PASS" if proved else "UNCERTAIN",
                "reason": "WHOLE_INTERVAL_MATERIAL_SIGNED_GAP" if proved else "SIGNED_GAP_NONNEGATIVITY_UNRESOLVED",
                "state": state if proved else None,
                "panels": list(pair), "time_interval": [float(a), float(b)],
                "patch_vertex_count": len(lower),
                "signed_gap_lower_bound": lo, "signed_gap_upper_bound": hi,
                "per_material_vertex_gap_bounds": list(map(list, zip(lower, upper))),
                "material_coordinates": [[x.tolist(), y.tolist()] for x, y in self.patches[pair]],
                "layer_order": [self.rank[i], self.rank[j]],
                "mapping_scope": "finite affine material goal patch; global collision proof remains separate",
                "endpoint_contact_exemption": False}

    def audit(self, motion, a=0., b=1.):
        pairs = [self.audit_pair(motion, pair, a, b) for pair in self.patches]
        return {"status": "PASS" if all(p["status"] == "PASS" for p in pairs) else "UNCERTAIN",
                "scope": "all finite goal material patches over the complete time interval",
                "pairs": pairs, "layer_order": self.order,
                "sampled_gap_used_as_proof": False,
                "material_contact_event_bounds": [
                    {"panels": p["panels"], "status": "PASS" if p["state"] == "CONTACT" else "UNCERTAIN",
                     "event": "PERSISTENT_MATERIAL_CONTACT" if p["state"] == "CONTACT" else "MATERIAL_GAP_ZERO_EVENT_NOT_ISOLATED",
                     "time_interval": [float(a), float(b)],
                     "reason": "analytic fixed relative material pose" if p["state"] == "CONTACT" else "whole-interval signed-gap bound does not exclude zero",
                     "endpoint_observation_used_as_event_proof": False}
                    for p in pairs if p["state"] == "CONTACT" or p["signed_gap_lower_bound"] <= 0.],
                "contact_event_isolation_scope": "free crease goal-boundary roots only; material zero-gap events separately enclosed above",
                "contact_event_parameterization": "source interval parameter, before cell normalization",
                "contact_event_isolation": self.events(motion.parent)}

    def events(self, parent):
        """Isolate exact events only in linear free chart coordinates.

        A nonlinear dependent angle is not assigned an event using endpoint
        equality. Its range is explicitly marked unresolved when appropriate.
        """
        events = []
        for k in range(self.m.n):
            if k in parent.free:
                left, rate, goal = parent.reference_q0[k], parent.dq[k], self.m.goal[k]
                if rate == 0.:
                    if left == goal:
                        events.append({"joint": k, "event": "PERSISTENT_BOUNDARY_CONTACT",
                                       "time_interval": [0., 1.], "status": "PASS",
                                       "from": ContactState.CONTACT.value, "to": ContactState.CONTACT.value,
                                       "basis": "identically fixed free chart coordinate"})
                    continue
                t = float((goal-left)/rate)
                if 0. <= t <= 1.:
                    arriving = self.m.signs[k]*rate > 0.
                    events.append({"joint": k, "event": "CONTACT" if arriving else "RELEASE",
                                   "time_interval": [t, t], "status": "PASS",
                                   "from": ContactState.FREE.value if arriving else ContactState.CONTACT.value,
                                   "to": ContactState.CONTACT.value if arriving else ContactState.RELEASE.value,
                                   "basis": "exact root of the declared linear free coordinate",
                                   "requires_tangent_and_chart_recomputation": True})
            else:
                ends = (parent.reference_q0[k], parent.reference_q1[k])
                if any(abs(x) == math.pi for x in ends):
                    events.append({"joint": k, "event": "DEPENDENT_CONTACT_EVENT_UNRESOLVED",
                                   "time_interval": [0., 1.], "status": "UNCERTAIN",
                                   "basis": "nonlinear chart coordinate; endpoint contact is insufficient"})
        return events


class ContactChartMotion(RestrictedSphericalMotion):
    motion_kind = "GOAL_CONTACT_ACTIVE_SET_EXACT_3R_CHART"

    def __init__(self, parent, a, b, contact):
        super().__init__(parent, a, b)
        self.contact = contact

    def speed_bound(self, panel, a=0., b=1.):
        return (self.b-self.a)*self.parent.speed_bound(panel, self._time(a), self._time(b))

    def acceleration_bound(self, panel, a=0., b=1.):
        return (self.b-self.a)**2*self.parent.acceleration_bound(panel, self._time(a), self._time(b))

    curvature_bound = acceleration_bound

    def contact_audit(self, a=0., b=1.):
        return self.contact.audit(self, a, b)

    def contact_pair_certificate(self, pair, a=0., b=1.):
        certificate = self.contact.fixed_goal_patch(self, pair)
        if certificate:
            return {**certificate, "time_interval": [float(a), float(b)]}
        from .contact_separation import certify_material_pair
        return certify_material_pair(self.m, self, pair, layer_order=self.contact.order, a=a, b=b)


class GoalContactBridgeBuilder:
    """Shared-knot repair and a finite atlas; no finite-tolerance fallback.

    Nodes 0..70 are immutable. Repairs are shared before any intervals are
    built, so adjacent intervals never silently receive different endpoints.
    A failed candidate returns no substitute curve and precise diagnostics.
    """
    def __init__(self, mechanism, config=None, layer_order=None):
        self.m = mechanism
        self.config = config or GoalContactBridgeConfig()
        self.contact = GoalMaterialContact(mechanism, layer_order)
        preferred = [self.config.dependent, (4, 5, 6), (1, 2, 3), (5, 6, 7),
                     (3, 4, 5), (7, 0, 1), (2, 3, 4), (6, 7, 0)]
        self.atlas = list(dict.fromkeys(preferred))

    def _tangent_chart(self, q, dependent, active):
        # Spatial angular-velocity columns of the exact cyclic product.
        product = np.eye(3)
        J = np.zeros((3, self.m.n))
        for k in list(range(1, self.m.n))+[0]:
            axis = np.r_[self.m.rays[k]["unit2"], 0.]
            J[:, k] = product@axis
            product = product@self.m._axis_rotation(axis, q[k])
        rows = [J]
        if active:
            rows.append(np.eye(self.m.n)[list(active)])
        constrained = np.vstack(rows)
        _, singular, vt = np.linalg.svd(constrained, full_matrices=True)
        rank = int(np.sum(singular > 1e-10))
        basis = vt[rank:].T
        return {"recomputed": True, "dependent": list(dependent),
                "active_boundary_joints": list(active), "constraint_rank": rank,
                "nullity": int(self.m.n-rank), "singular_values": singular.tolist(),
                "tangent_basis": basis.tolist(),
                "linearized_constraint_residual": float(np.linalg.norm(constrained@basis)),
                "scope": "local chart/tangent diagnostics; whole-time proof is the analytic branch enclosure"}

    def repair_nodes(self, nodes):
        repaired = [np.asarray(q, float).copy() for q in nodes]
        records = []
        for index, original in enumerate(nodes):
            original = np.asarray(original, float)
            if index <= 70 or index == len(nodes)-1:
                records.append({"index": index, "status": "PASS", "method": "IMMUTABLE_SOURCE_KNOT",
                                "delta": np.zeros(self.m.n).tolist(), "correction_norm": 0.,
                                "repaired": original.tolist()})
                continue
            seed = original.copy()
            snapped = []
            for k in range(self.m.n):
                if abs(seed[k]-self.m.goal[k]) <= self.config.boundary_snap_tolerance:
                    seed[k] = self.m.goal[k]; snapped.append(k)
            attempts = []
            for dependent in self.atlas:
                if any(k in snapped for k in dependent):
                    continue
                try:
                    parent = SphericalClosureBridge(self.m, seed, seed, dependent=dependent)
                    candidate = parent.q(0.)
                    delta = candidate-original
                    if not self.m.sector_valid(candidate, tol=0.):
                        raise BridgeUnavailable("REPAIRED_KNOT_OUTSIDE_STRICT_SECTOR")
                    if np.linalg.norm(delta) > self.config.max_endpoint_correction:
                        raise BridgeUnavailable("ENDPOINT_CORRECTION_LIMIT")
                    repaired[index] = candidate
                    records.append({"index": index, "status": "PASS", "method": "ACTIVE_SET_SHARED_ANALYTIC_KNOT",
                                    "dependent": list(dependent), "snapped_goal_joints": snapped,
                                    "delta": delta.tolist(), "correction_norm": float(np.linalg.norm(delta)),
                                    "original": original.tolist(), "repaired": candidate.tolist(),
                                    "closure_residual_diagnostic": float(np.linalg.norm(self.m.closure_residual(candidate))),
                                    "chart_after_active_set_update": self._tangent_chart(candidate, dependent, snapped)})
                    break
                except BridgeUnavailable as exc:
                    attempts.append({"dependent": list(dependent), "reason": str(exc)})
            else:
                records.append({"index": index, "status": "UNCERTAIN", "method": "SHARED_KNOT_REPAIR_UNAVAILABLE",
                                "delta": np.zeros(self.m.n).tolist(), "correction_norm": 0.,
                                "repaired": original.tolist(), "attempts": attempts})
        return repaired, records

    def build_interval(self, q0, q1, index):
        if not 70 <= index <= 161:
            raise ValueError("GoalContactBridgeBuilder only owns source intervals 70..161")
        q0, q1 = np.asarray(q0, float), np.asarray(q1, float)
        attempts = []
        for dependent in self.atlas:
            try:
                parent = SphericalClosureBridge(self.m, q0, q1, dependent=dependent)
                endpoint_error = max(float(np.max(abs(parent.q0-q0))), float(np.max(abs(parent.q1-q1))))
                if endpoint_error > self.config.join_tolerance:
                    raise BridgeUnavailable("ANALYTIC_ENDPOINT_BRANCH_OR_CLOSURE_MISMATCH")
                events = self.contact.events(parent)
                if any(e["status"] != "PASS" for e in events):
                    raise BridgeUnavailable("DEPENDENT_CONTACT_EVENT_NOT_ISOLATED")
                motions, cells = [], []
                cuts = sorted({0., 1.}|{e["time_interval"][0] for e in events
                                               if e["time_interval"][0] == e["time_interval"][1]})

                def visit(a, b, depth):
                    proof = parent.regularity(a, b)
                    reason = proof["reason"]
                    if proof["status"] == "PASS":
                        motion = ContactChartMotion(parent, a, b, self.contact)
                        lo, hi = motion.joint_bounds()
                        closure = motion.continuous_closure(tolerance=self.config.closure_tolerance)
                        if strict_sector_bounds(self.m, lo, hi) and closure["status"] == "PASS":
                            active = tuple(k for k, v in enumerate(motion.fixed_joint_values) if v == self.m.goal[k])
                            motions.append(motion)
                            cells.append({"kind": "GOAL_CONTACT_ACTIVE_SET_EXACT_3R_CHART",
                                          "source_interval": index, "source_parameter_interval": [a, b],
                                          "construction_status": "PASS", "exact_seam_claimed": True,
                                          "q0": motion.q0.tolist(), "q1": motion.q1.tolist(),
                                          "dependent": list(dependent), "regularity": proof,
                                          "closure_certificate": closure,
                                          "chart_after_active_set_update": self._tangent_chart(motion.q0, dependent, active),
                                          "contact_active_joints": list(active)})
                            return
                        reason = "WHOLE_INTERVAL_M_V_SECTOR_NOT_PROVEN" if not strict_sector_bounds(self.m, lo, hi) else closure["reason"]
                    if depth == self.config.max_depth:
                        raise BridgeUnavailable(f"{reason}; unresolved source parameter [{a},{b}]")
                    mid = (a+b)/2.
                    parent.q(mid)
                    visit(a, mid, depth+1); visit(mid, b, depth+1)

                for a, b in zip(cuts, cuts[1:]):
                    visit(a, b, 0)
                max_join, previous = 0., q0
                for motion in motions:
                    max_join = max(max_join, float(np.max(abs(previous-motion.q0))))
                    previous = motion.q1
                max_join = max(max_join, float(np.max(abs(previous-q1))))
                if max_join > self.config.join_tolerance:
                    raise BridgeUnavailable("LOCAL_CHART_CELL_JOIN_NOT_PROVEN")
                # Compute per-cell contact bounds after the geometric chart is
                # selected. A signed-gap failure is visible and never inferred
                # safe from the successful closure construction.
                for motion, cell in zip(motions, cells):
                    cell["contact_audit"] = motion.contact_audit()
                return motions, {"source_interval": index, "cells": cells,
                                  "continuous_join_passed": True, "max_join_error": max_join,
                                  "join_tolerance": self.config.join_tolerance,
                                  "active_set_events": events, "atlas_attempts": attempts,
                                  "active_set_switch_recomputes_tangent_and_chart": True,
                                  "whole_interval_contact_bounds_proven": all(c["contact_audit"]["status"] == "PASS" for c in cells),
                                  "uses_vertex_linear_interpolation_as_motion": False}
            except BridgeUnavailable as exc:
                attempts.append({"dependent": list(dependent), "reason": str(exc)})
        return [], {"source_interval": index, "cells": [], "continuous_join_passed": False,
                    "max_join_error": None, "join_tolerance": self.config.join_tolerance,
                    "construction_status": "UNCERTAIN", "reason": "NO_JOINED_REGULAR_CONTACT_CHART",
                    "atlas_attempts": attempts, "whole_interval_contact_bounds_proven": False,
                    "source_parameter_interval": [0., 1.], "finite_tolerance_fallback_created": False,
                    "uses_vertex_linear_interpolation_as_motion": False}

