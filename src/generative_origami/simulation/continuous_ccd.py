"""Fail-closed continuous certification of an explicitly defined rigid bridge.

Stored keyframes do not define a continuous manifold path. The default bridge
is q-linear / Rodrigues FK; C3-B may supply a nonlinear bridge with its own
proved whole-time joint and point bounds. Neither case certifies by sampling
or treats vertex chords as the actual rigid motion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import itertools
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog

from .ccd_motion import RigidMechanismInterval
from .ccd_adapter import PythonReferenceBackend
from .layer_contact import LayerContactModel, _barycentric, _convex_clip, _poly_area


@dataclass(frozen=True)
class CertificationConfig:
    closure_tolerance: float = 4e-6
    numerical_error: float = 1e-11
    material_tolerance: float = 3e-5
    minimum_separation: float = 0.0
    curve_tolerance: float = 1e-5
    max_curve_depth: int = 3
    max_feature_subdivisions: int = 64
    max_pair_nodes: int = 31

    def __post_init__(self):
        values = (self.closure_tolerance, self.numerical_error,
                  self.material_tolerance, self.minimum_separation, self.curve_tolerance)
        if not all(math.isfinite(x) and x >= 0 for x in values):
            raise ValueError("All numerical tolerances must be finite and nonnegative")
        if self.max_curve_depth < 0 or self.max_feature_subdivisions < 1 or self.max_pair_nodes < 1:
            raise ValueError("Subdivision budgets must be positive (depth may be zero)")
        if self.minimum_separation != 0:
            raise ValueError("This path contact model is zero thickness; positive physical clearance requires a different contact model")


def _interval_dot(normal: np.ndarray, lo: np.ndarray, hi: np.ndarray):
    low = np.sum(np.where(normal >= 0, normal * lo, normal * hi), axis=-1)
    high = np.sum(np.where(normal >= 0, normal * hi, normal * lo), axis=-1)
    return np.nextafter(low, -np.inf), np.nextafter(high, np.inf)


def _interval_mul(al, ah, bl, bh):
    terms = np.array([al * bl, al * bh, ah * bl, ah * bh])
    return np.nextafter(terms.min(axis=0), -np.inf), np.nextafter(terms.max(axis=0), np.inf)


def _interval_cross(al, ah, bl, bh):
    lo, hi = np.zeros(3), np.zeros(3)
    for k, i, j in ((0, 1, 2), (1, 2, 0), (2, 0, 1)):
        pl, ph = _interval_mul(al[i], ah[i], bl[j], bh[j])
        ql, qh = _interval_mul(al[j], ah[j], bl[i], bh[i])
        lo[k], hi[k] = np.nextafter(pl - qh, -np.inf), np.nextafter(ph - ql, np.inf)
    return lo, hi


def _backend_result(result):
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if isinstance(result, dict):
        return result
    return {"status": result.status, "reason": result.reason}


class MaterialContactValidator:
    """Finite material patches and exact topological contacts, never pair masks."""

    def __init__(self, mechanism, layer: LayerContactModel, order: list[int], config):
        self.m, self.layer, self.config = mechanism, layer, config
        if sorted(order) != list(range(mechanism.n)):
            raise ValueError("Layer order must be a permutation of all panels")
        self.order = order
        self.rank = {p: i for i, p in enumerate(order)}
        edges = layer._adjacent_order_edges()
        if not (all(self.rank[a] < self.rank[b] for a, b in edges) or
                all(self.rank[a] > self.rank[b] for a, b in edges)):
            raise ValueError("Layer order contradicts the mechanism's M/V adjacency constraints")
        self.goal = np.asarray(mechanism.panel_triangles(mechanism.goal))
        self.patches = {}
        for i, j in itertools.combinations(range(mechanism.n), 2):
            a, b = self.goal[i, :, :2], self.goal[j, :, :2]
            poly = _convex_clip(a, b)
            if len(poly) >= 3 and abs(_poly_area(poly)) > 1e-12:
                self.patches[i, j] = [(_barycentric(p, a), _barycentric(p, b)) for p in poly]

    def material_point(self, triangles, pair, point):
        i, j = pair
        weights, reconstruction_errors = [], []
        for k in (i, j):
            A = np.vstack((triangles[k].T, np.ones(3)))
            w, *_ = np.linalg.lstsq(A, np.r_[point, 1.0], rcond=None)
            weights.append(w)
            reconstruction_errors.append(float(np.linalg.norm(w @ triangles[k] - point)))
        wi, wj = weights
        mapping = float(np.linalg.norm(wi @ self.goal[i] - wj @ self.goal[j]))
        contained = all(np.min(w) >= -1e-9 and np.max(w) <= 1 + 1e-9 for w in weights)
        return {
            "weights": [wi.tolist(), wj.tolist()],
            "reconstruction_errors": reconstruction_errors,
            "goal_material_distance": mapping,
            "within_finite_triangles": bool(contained),
            "legal_candidate_only": bool(contained and max(reconstruction_errors) <= self.config.numerical_error * 100
                                          and mapping <= self.config.material_tolerance),
        }

    def persistent_goal_patch(self, motion, pair):
        i, j = pair
        # Common left product cancels: R_i^-1 R_j = product R_(i+1)..R_j.
        # Exact equality of the generating joint parameters is required here.
        # A near-zero sampled gap is deliberately insufficient.
        # Equal endpoints cannot prove constancy for a nonlinear bridge.
        values = np.asarray(getattr(motion, "fixed_joint_values", np.full(self.m.n, np.nan)))
        fixed = values.shape == (self.m.n,) and np.array_equal(values[i + 1:j + 1], self.m.goal[i + 1:j + 1])
        if not fixed or pair not in self.patches:
            return None
        return {"status": "PASS", "reason": "ANALYTIC_FIXED_GOAL_RELATIVE_POSE",
                "patch_vertex_count": len(self.patches[pair]),
                "material_mapping": "identical relative Rodrigues product for every material point",
                "layer_order": [self.rank[i], self.rank[j]],
                "signed_gap": "identically zero; no relative motion and no side crossing",
                "whole_panel_exemption": False}

    def adjacent_hinge(self, motion, pair):
        i, j = pair
        closing = pair == (0, self.m.n - 1)
        if j != i + 1 and not closing:
            return None
        closure_structure = None
        if closing:
            prove = getattr(motion, "exact_closing_hinge_certificate", None)
            closure_structure = prove(0., 1.) if callable(prove) else None
            if not closure_structure or closure_structure.get("status") != "PASS":
                return None  # finite-tolerance closure cannot grant exact hinge topology
        bounds = getattr(motion, "joint_bounds", None)
        if not callable(bounds):
            return None
        low, high = bounds(0., 1.)
        joint = 0 if closing else j
        qa, qb = float(low[joint]), float(high[joint])
        sign = float(self.m.signs[joint])
        if min(sign * qa, sign * qb) < 0 or max(sign * qa, sign * qb) > math.pi:
            return None
        # For a connected pair of triangular sectors the supporting planes
        # meet only along the actual shared hinge while |q|<pi. At q=0 the
        # reference sectors are disjoint; q=goal yields exactly the goal
        # relative material map. We do not omit the entire pair from analysis.
        local = np.asarray(self.m.panel_triangles(self.m.flat))
        shared = local[0, 1] if closing else local[i, 2]
        side_a = np.cross(shared, local[0, 2] if closing else local[i, 1])[2]
        side_b = np.cross(shared, local[-1, 1] if closing else local[j, 2])[2]
        if not side_a * side_b < 0:
            return None
        at_goal = any(abs(q) == math.pi for q in (qa, qb))
        if at_goal and pair not in self.patches:
            return None
        return {"status": "PASS", "reason": "ANALYTIC_CLOSED_SEAM_HINGE_SECTOR" if closing else "ANALYTIC_SHARED_HINGE_SECTOR",
                "joint": joint, "angle_range": [min(qa, qb), max(qa, qb)],
                "allowed_set": "exact shared material hinge; final finite overlap only at goal relative angle",
                "goal_patch_vertices": len(self.patches.get(pair, [])),
                "closure_structure": closure_structure,
                "whole_panel_exemption": False}

    def patch_audit(self, motion, pair, a=0., b=1.):
        if pair not in self.patches:
            return {"status": "NOT_APPLICABLE", "reason": "NO_FINAL_AREA_PATCH"}
        fixed = self.persistent_goal_patch(motion, pair)
        if fixed:
            return fixed
        i, j = pair
        li, hi = motion.vertex_bounds(i, a, b)
        lj, hj = motion.vertex_bounds(j, a, b)
        s = 1. if self.rank[i] > self.rank[j] else -1.
        lower, upper = [], []
        for wi, wj in self.patches[pair]:
            # A shared center is one exact material point, not a finite ball.
            if np.array_equal(wi, np.array([1., 0., 0.])) and np.array_equal(wj, np.array([1., 0., 0.])):
                lower.append(0.); upper.append(0.); continue
            il, ih = _interval_dot(wi, li[:, 2], hi[:, 2])
            jl, jh = _interval_dot(wj, lj[:, 2], hj[:, 2])
            gl, gh = float(il - jh), float(ih - jl)
            lower.append(min(s * gl, s * gh)); upper.append(max(s * gl, s * gh))
        return {"status": "PASS" if min(lower) >= 0. else "UNCERTAIN",
                "reason": "SIGNED_GAP_INTERVAL" if min(lower) >= 0. else "SIGNED_GAP_NOT_PROVEN",
                "patch_vertex_count": len(lower), "signed_gap_lower_bound": min(lower),
                "signed_gap_upper_bound": max(upper),
                "material_mapping": "finite goal-overlap vertices; affine material patch",
                "not_a_collision_exemption": True}


class ContinuousPathCertifier:
    def __init__(self, mechanism, *, layer_order, config=None, backend=None):
        self.m = mechanism
        self.config = config or CertificationConfig()
        self.backend = backend or PythonReferenceBackend()
        layer = LayerContactModel(mechanism)
        self.contact = MaterialContactValidator(mechanism, layer, layer_order, self.config)

    def _cone_separator(self, motion, pair, a, b):
        i, j = pair
        tm = (a + b) * .5
        A = motion.triangle(i, tm)[1:]
        B = motion.triangle(j, tm)[1:]
        vectors = np.vstack((A / np.linalg.norm(A, axis=1)[:, None], -B / np.linalg.norm(B, axis=1)[:, None]))
        solution = linprog([0., 0., 0., -1.], A_ub=np.c_[-vectors, np.ones(4)], b_ub=np.zeros(4),
                           bounds=[(-1., 1.)] * 3 + [(0., 3.)], method="highs")
        if not solution.success or solution.x[-1] <= self.config.numerical_error * 100:
            return None
        normal = solution.x[:3]
        normal /= np.linalg.norm(normal)
        al, ah = motion.vertex_bounds(i, a, b)
        bl, bh = motion.vertex_bounds(j, a, b)
        amin, _ = _interval_dot(normal, al[1:], ah[1:])
        _, bmax = _interval_dot(normal, bl[1:], bh[1:])
        margin = min(float(np.min(amin)), -float(np.max(bmax)))
        return {"normal": normal.tolist(), "margin_lower_bound": margin,
                "passed": margin > self.config.numerical_error * 100,
                "allowed_contact": "shared origin only, no radius exclusion"}

    def _shared_origin_edges(self, motion, pair, endpoints, a, b):
        i, j = pair
        ei, ej = endpoints
        ai = ei[1] if ei[0] == 0 else ei[0]
        bj = ej[1] if ej[0] == 0 else ej[0]
        al, ah = motion.vertex_bounds(i, a, b)
        bl, bh = motion.vertex_bounds(j, a, b)
        cl, ch = _interval_cross(al[ai], ah[ai], bl[bj], bh[bj])
        delta = self.config.numerical_error * 100
        if np.any(cl > delta) or np.any(ch < -delta):
            return {"status": "SAFE", "reason": "RADIAL_EDGES_NONCOLLINEAR_FOR_WHOLE_INTERVAL"}
        dl, dh = _interval_mul(al[ai], ah[ai], bl[bj], bh[bj])
        if float(np.sum(dh)) < -delta:
            return {"status": "SAFE", "reason": "RADIAL_EDGES_OPPOSITE_FOR_WHOLE_INTERVAL"}
        return {"status": "UNCERTAIN", "reason": "SHARED_ORIGIN_DOES_NOT_EXEMPT_POSSIBLE_RAY_OVERLAP"}

    def _transverse_witness(self, motion, pair, t):
        tris = [motion.triangle(k, t) for k in range(self.m.n)]
        i, j = pair
        guard = self.config.numerical_error * 1000
        for ia, ib in ((i, j), (j, i)):
            A, B = tris[ia], tris[ib]
            for e0, e1 in ((0, 1), (1, 2), (2, 0)):
                d, u, v = A[e1] - A[e0], B[1] - B[0], B[2] - B[0]
                M = np.column_stack((d, -u, -v))
                scale = max(np.linalg.norm(M, ord=2), 1.)
                if abs(np.linalg.det(M)) < guard * scale ** 3:
                    continue
                x = np.linalg.solve(M, B[0] - A[e0])
                if not (guard < x[0] < 1 - guard and x[1] > guard and x[2] > guard and x[1] + x[2] < 1 - guard):
                    continue
                p = A[e0] + x[0] * d
                if np.array_equal(p, np.zeros(3)):
                    continue
                mapping = self.contact.material_point(tris, pair, p)
                if mapping["goal_material_distance"] > self.config.material_tolerance + guard:
                    return {"time": t, "point": p.tolist(), "edge_panel": ia, "face_panel": ib,
                            "edge": [e0, e1], "parameters": x.tolist(), "material_validation": mapping,
                            "reason": "TRANSVERSE_INTERSECTION_OUTSIDE_LEGAL_MATERIAL_PATCH"}
        return None

    def _features(self, motion, pair, a, b):
        i, j = pair
        starts = [motion.triangle(k, a) for k in pair]
        ends = [motion.triangle(k, b) for k in pair]
        curvature = motion.chord_error_bound(i, a, b) + motion.chord_error_bound(j, a, b)
        ms = self.config.minimum_separation + curvature
        kwargs = {"minimum_separation": ms, "tolerance": self.config.numerical_error * 100,
                  "max_subdivisions": self.config.max_feature_subdivisions,
                  "numerical_error": self.config.numerical_error}
        records = []
        for pa, pb in ((0, 1), (1, 0)):
            for vertex in (1, 2):
                start = np.vstack((starts[pa][vertex], starts[pb]))
                end = np.vstack((ends[pa][vertex], ends[pb]))
                r = _backend_result(self.backend.vertex_face(start, end, **kwargs))
                records.append({"feature": "VERTEX_FACE", "vertex_panel": pair[pa], "vertex": vertex,
                                "face_panel": pair[pb], **r})
        edges = ((0, 1), (1, 2), (2, 0))
        for ei, ej in itertools.product(edges, repeat=2):
            if 0 in ei and 0 in ej:
                r = self._shared_origin_edges(motion, pair, (ei, ej), a, b)
            else:
                start = np.vstack((starts[0][list(ei)], starts[1][list(ej)]))
                end = np.vstack((ends[0][list(ei)], ends[1][list(ej)]))
                r = _backend_result(self.backend.edge_edge(start, end, **kwargs))
            records.append({"feature": "EDGE_EDGE", "edges": [list(ei), list(ej)], **r})
        return {"all_safe": all(r["status"] == "SAFE" for r in records), "records": records,
                "surrogate": "linear chords with minimum-separation inflated by rigid curvature bound",
                "curvature_inflation": curvature, "effective_minimum_separation": ms,
                "exact_shared_vertex_queries": 2,
                "shared_vertex_reason": "identical material origin for all t, not a finite ball exemption"}

    def certify_pair(self, motion, pair):
        stats = {"nodes": 0, "broad_phase_checks": 0, "broad_phase_rejects": 0,
                 "vertex_face_queries": 0, "edge_edge_queries": 0, "max_depth": 0}

        def visit(a, b, depth):
            stats["nodes"] += 1
            stats["max_depth"] = max(stats["max_depth"], depth)
            if stats["nodes"] > self.config.max_pair_nodes:
                return {"status": "UNCERTAIN", "reason": "PAIR_SUBDIVISION_BUDGET", "time_interval": [a, b]}
            i, j = pair
            al, ah = motion.vertex_bounds(i, a, b)
            bl, bh = motion.vertex_bounds(j, a, b)
            stats["broad_phase_checks"] += 1
            alo, ahi, blo, bhi = al.min(axis=0), ah.max(axis=0), bl.min(axis=0), bh.max(axis=0)
            padding = self.config.minimum_separation + self.config.numerical_error * 100
            if np.any(ahi + padding < blo) or np.any(bhi + padding < alo):
                stats["broad_phase_rejects"] += 1
                return {"status": "PASS", "reason": "SWEPT_AABB_SEPARATION", "time_interval": [a, b]}
            fixed = self.contact.persistent_goal_patch(motion, pair)
            if fixed:
                return {**fixed, "time_interval": [a, b]}
            adjacent = self.contact.adjacent_hinge(motion, pair)
            if adjacent:
                return {**adjacent, "time_interval": [a, b]}
            provider = getattr(motion, "contact_pair_certificate", None)
            if callable(provider):
                contact = provider(pair, a, b)
                allowed = {"ACTIVE_SET_FIXED_GOAL_MATERIAL_PATCH", "ANALYTIC_INDUCED_MATERIAL_HINGE",
                           "RELATIVE_FRAME_CONTINUOUS_SEPARATION"}
                if (contact and contact.get("status") == "PASS" and contact.get("reason") in allowed
                        and contact.get("whole_panel_exemption") is False
                        and (contact["reason"] != "ANALYTIC_INDUCED_MATERIAL_HINGE"
                             or contact.get("layer_order_gate_proven") is True)):
                    return {"status": "PASS", "reason": contact["reason"], "time_interval": [a,b],
                            "contact_certificate": contact}
            cone = self._cone_separator(motion, pair, a, b)
            if cone and cone["passed"]:
                return {"status": "PASS", "reason": "CONTINUOUS_CONE_SEPARATION", "time_interval": [a, b], **cone}
            witness = next((w for t in (a, (a + b) / 2, b)
                            if (w := self._transverse_witness(motion, pair, t)) is not None), None)
            if witness:
                return {"status": "COLLISION", "reason": witness["reason"], "time_interval": [a, b], "witness": witness}
            features = self._features(motion, pair, a, b)
            stats["vertex_face_queries"] += 4
            stats["edge_edge_queries"] += 9
            initial = self._cone_separator(motion, pair, a, a)
            initial_disjoint = bool(initial and initial["passed"])
            features["initial_disjointness_proven"] = initial_disjoint
            if features["all_safe"] and initial_disjoint:
                return {"status": "PASS", "reason": "ALL_CONTINUOUS_FEATURE_QUERIES_SAFE", "time_interval": [a, b], "features": features}
            if depth < self.config.max_curve_depth and features["curvature_inflation"] > self.config.curve_tolerance:
                mid = (a + b) / 2
                left, right = visit(a, mid, depth + 1), visit(mid, b, depth + 1)
                status = "COLLISION" if any(x["status"] == "COLLISION" for x in (left, right)) else (
                    "PASS" if all(x["status"] == "PASS" for x in (left, right)) else "UNCERTAIN")
                return {"status": status, "reason": "CURVED_RIGID_INTERVAL_SUBDIVISION", "time_interval": [a, b], "children": [left, right]}
            return {"status": "UNCERTAIN", "reason": "CONTINUOUS_FEATURE_OR_CONTACT_NOT_PROVEN", "time_interval": [a, b],
                    "features": features, "material_patch": self.contact.patch_audit(motion, pair, a, b)}

        result = visit(0., 1., 0)
        return {"panels": list(pair), **result, "stats": stats}

    def certify_interval(self, q0, q1, index):
        motion = RigidMechanismInterval(self.m, q0, q1)
        return self.certify_defined_motion(motion, index)

    def certify_defined_motion(self, motion, index):
        """Audit a declared continuous curve with its own whole-time enclosures.

        In particular nonlinear fold angles cannot reuse endpoint-only sector,
        constant-contact, speed, curvature, or closing-hinge assumptions.
        """
        low, high = motion.joint_bounds(0., 1.)
        sector = bool(np.all(np.isfinite(low)) and np.all(np.isfinite(high))
                      and np.all(low <= high)
                      and np.all(np.where(self.m.signs > 0, low, -high) >= 0.)
                      and np.all(np.maximum(np.abs(low), np.abs(high)) <= math.pi))
        closure = motion.continuous_closure(tolerance=self.config.closure_tolerance)
        pairs = [self.certify_pair(motion, pair) for pair in itertools.combinations(range(self.m.n), 2)]
        states = [p["status"] for p in pairs]
        reasons = sorted({p["reason"] for p in pairs if p["status"] != "PASS"})
        if closure["status"] != "PASS":
            reasons.append(closure.get("reason", "CONTINUOUS_CLOSURE_NOT_PROVEN"))
        if not sector:
            reasons.append("M_V_SECTOR_VIOLATION")
        status = "COLLISION" if "COLLISION" in states else "PASS" if not reasons else "UNCERTAIN"
        return {"interval": index, "keyframes": [index, index + 1], "status": status,
                "reasons": reasons or ["ALL_CONTINUOUS_GATES_PASS"], "sector_passed": bool(sector),
                "hinge_closure": closure, "pairs": pairs,
                "motion_model": motion.motion_kind,
                "joint_bounds": {"lower": low.tolist(), "upper": high.tolist()},
                "uses_vertex_linear_interpolation_as_motion": False}

    def certify_frames(self, frames, *, source_path=None, source_status="RIGID_PATH_LAYER_ORDER_VALIDATED", progress_callback=None):
        if len(frames) < 2:
            raise ValueError("At least two rigid keyframes are required")
        angles = []
        reconstruction = []
        for i, frame in enumerate(frames):
            q = np.asarray(frame["angles_rad"], dtype=float)
            xyz = np.asarray(frame["panels_xyz"], dtype=float)
            if q.shape != (self.m.n,) or xyz.shape != (self.m.n, 3, 3) or not np.all(np.isfinite(q)) or not np.all(np.isfinite(xyz)):
                raise ValueError(f"Malformed or nonfinite keyframe {i}")
            if frame.get("index", i) != i:
                raise ValueError("Keyframe indices must be contiguous and ordered")
            expected = np.asarray(self.m.panel_triangles(q))
            error = float(np.max(np.linalg.norm(expected - xyz, axis=-1)))
            if error > self.config.numerical_error * 100:
                raise ValueError(f"Keyframe {i} not reconstructed by the declared rigid mechanism ({error})")
            reconstruction.append(error)
            angles.append(q)
        intervals = []
        for i, (a, b) in enumerate(zip(angles, angles[1:])):
            certificate = self.certify_interval(a, b, i)
            intervals.append(certificate)
            if progress_callback:
                progress_callback(certificate)
        counts = {s: sum(x["status"] == s for x in intervals) for s in ("PASS", "COLLISION", "UNCERTAIN")}
        all_pass = bool(intervals) and counts["PASS"] == len(intervals)
        return {
            "schema_version": 1, "experiment_id": "POC01-007C3-A_CONTINUOUS_CCD",
            "status": "CONTINUOUS_RIGID_PATH_COLLISION_CERTIFIED" if all_pass else "CONTINUOUS_RIGID_PATH_NOT_CERTIFIED",
            "source_status": source_status, "effective_motion_status": "CONTINUOUS_RIGID_PATH_COLLISION_CERTIFIED" if all_pass else (
                "RIGID_PATH_LAYER_ORDER_VALIDATED" if source_status == "RIGID_PATH_LAYER_ORDER_VALIDATED" else "CONTINUOUS_RIGID_PATH_NOT_CERTIFIED"),
            "continuous_collision_detection_certified": all_pass,
            "keyframe_count": len(frames), "interval_count": len(intervals), "panel_count": self.m.n,
            "counts": counts, "layer_order": self.contact.order,
            "source_sha256": hashlib.sha256(Path(source_path).read_bytes()).hexdigest() if source_path else None,
            "max_keyframe_reconstruction_error": max(reconstruction), "config": asdict(self.config),
            "backend": self.backend.backend_info(), "native_tight_inclusion_used": bool(self.backend.backend_info().get("native", False)),
            "motion_definition": "Piecewise linear hinge angles evaluated through rigid FK; no sample projection or vertex lerp. Closure is a separate continuous gate.",
            "numeric_scope": "Conservative analytic bounds with documented floating-point guard; reference implementation, not the third-party Tight-Inclusion proof or a formal interval arithmetic proof.",
            "certification_gate": "Every pair AND continuous closure AND sector must PASS on EVERY input interval. POSSIBLE_HIT is never promoted to COLLISION or PASS.",
            "intervals": intervals,
        }