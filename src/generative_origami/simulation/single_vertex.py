from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from scipy.optimize import linprog


@dataclass(frozen=True)
class EndpointConeReport:
    feasible: bool
    margin: float
    rank: int
    nullity: int
    singular_values: list[float]
    direction: list[float] | None


class SingleVertexMechanism:
    """Rigid kinematics for one origami vertex.

    The model fixes panel 0 and propagates neighboring panel orientations
    around the central vertex. The final closure residual is the rotation
    vector needed to bring the last panel back to panel 0 across crease 0.

    This is a research/kinematics model. It intentionally does not claim that
    a single-vertex base is a complete recognizable origami object.
    """

    def __init__(self, fold: dict[str, Any]):
        self.fold = fold
        self.vertices = np.asarray(fold["vertices_coords"], dtype=float)
        self.center = self.vertices[0]
        self.rays = self._extract_rays()
        self.n = len(self.rays)
        if self.n < 4 or self.n % 2:
            raise ValueError("single-vertex mechanism requires even degree >= 4")
        self.signs = np.asarray(
            [1.0 if r["assignment"] == "V" else -1.0 for r in self.rays],
            dtype=float,
        )
        self.flat = np.zeros(self.n, dtype=float)
        self.goal = self.signs * math.pi
        self._adjacent_pairs = {
            tuple(sorted((i, (i + 1) % self.n))) for i in range(self.n)
        }
        self.final_contact_pairs = self._compute_final_contact_pairs()

    def _extract_rays(self) -> list[dict[str, Any]]:
        rays: list[dict[str, Any]] = []
        for ei, edge in enumerate(self.fold["edges_vertices"]):
            assignment = self.fold["edges_assignment"][ei]
            if assignment not in {"M", "V"} or 0 not in edge:
                continue
            other = edge[1] if edge[0] == 0 else edge[0]
            vec = self.vertices[other] - self.center
            length = float(np.linalg.norm(vec))
            if length <= 1e-12:
                raise ValueError("zero-length radial crease")
            angle = math.atan2(float(vec[1]), float(vec[0]))
            if angle < 0:
                angle += 2 * math.pi
            rays.append(
                {
                    "angle": angle,
                    "edge": ei,
                    "vertex": other,
                    "assignment": assignment,
                    "unit2": vec / length,
                    "point2": vec,
                }
            )
        rays.sort(key=lambda x: x["angle"])
        return rays

    @staticmethod
    def _axis_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
        axis = np.asarray(axis, dtype=float)
        axis /= np.linalg.norm(axis)
        x, y, z = axis
        K = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
        sa, ca = math.sin(angle), math.cos(angle)
        return np.eye(3) + sa * K + (1.0 - ca) * (K @ K)

    @staticmethod
    def _rotation_log(R: np.ndarray) -> np.ndarray:
        cos_angle = float(np.clip((np.trace(R) - 1.0) * 0.5, -1.0, 1.0))
        angle = math.acos(cos_angle)
        vee = np.array([R[2,1]-R[1,2], R[0,2]-R[2,0], R[1,0]-R[0,1]], dtype=float)
        if angle < 1e-8:
            return 0.5 * vee
        sin_angle = math.sin(angle)
        if abs(sin_angle) > 1e-7:
            return (angle / (2.0 * sin_angle)) * vee
        # Rare near-pi fallback.
        diag = np.maximum((np.diag(R) + 1.0) * 0.5, 0.0)
        axis = np.sqrt(diag)
        if axis[0] >= axis[1] and axis[0] >= axis[2] and axis[0] > 1e-8:
            axis[1] = math.copysign(axis[1], R[0,1] + R[1,0])
            axis[2] = math.copysign(axis[2], R[0,2] + R[2,0])
        elif axis[1] >= axis[2] and axis[1] > 1e-8:
            axis[0] = math.copysign(axis[0], R[0,1] + R[1,0])
            axis[2] = math.copysign(axis[2], R[1,2] + R[2,1])
        elif axis[2] > 1e-8:
            axis[0] = math.copysign(axis[0], R[0,2] + R[2,0])
            axis[1] = math.copysign(axis[1], R[1,2] + R[2,1])
        norm = np.linalg.norm(axis)
        if norm < 1e-12:
            return np.zeros(3)
        return angle * axis / norm

    def panel_rotations(self, q: np.ndarray) -> list[np.ndarray]:
        q = np.asarray(q, dtype=float)
        if q.shape != (self.n,):
            raise ValueError(f"expected {self.n} fold angles")
        rots = [np.eye(3)]
        current = np.eye(3)
        for k in range(1, self.n):
            local_axis = np.r_[self.rays[k]["unit2"], 0.0]
            world_axis = current @ local_axis
            current = self._axis_rotation(world_axis, float(q[k])) @ current
            rots.append(current)
        return rots

    def closure_residual(self, q: np.ndarray) -> np.ndarray:
        rots = self.panel_rotations(q)
        current = rots[-1]
        local_axis = np.r_[self.rays[0]["unit2"], 0.0]
        world_axis = current @ local_axis
        closed = self._axis_rotation(world_axis, float(q[0])) @ current
        return self._rotation_log(closed)

    def numerical_jacobian(self, q: np.ndarray, h: float = 2e-6) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        J = np.zeros((3, self.n), dtype=float)
        for i in range(self.n):
            qp = q.copy(); qm = q.copy()
            qp[i] += h; qm[i] -= h
            J[:, i] = (self.closure_residual(qp) - self.closure_residual(qm)) / (2*h)
        return J

    def tangent_basis(self, q: np.ndarray, tol: float = 1e-7):
        J = self.numerical_jacobian(q)
        _, singular, vt = np.linalg.svd(J, full_matrices=True)
        rank = int(np.sum(singular > tol))
        return vt[rank:].T, rank, singular

    def sector_valid(self, q: np.ndarray, tol: float = 1e-7) -> bool:
        q = np.asarray(q, dtype=float)
        return bool(
            np.all(self.signs * q >= -tol)
            and np.all(np.abs(q) <= math.pi + tol)
        )

    def endpoint_cone(self, q: np.ndarray, outward: bool) -> EndpointConeReport:
        """Find a tangent direction that stays inside the M/V angle box.

        At the flat endpoint `outward=True`: sign_i * dq_i >= margin.
        At the folded endpoint `outward=False`: sign_i * dq_i <= -margin.
        The linear program maximizes the common margin over the endpoint tangent
        null-space. A positive margin is a strong seeding certificate.
        """
        N, rank, singular = self.tangent_basis(q)
        nullity = N.shape[1]
        direction_sign = 1.0 if outward else -1.0
        # variables [z..., margin], z bounded for scale normalization.
        A = np.zeros((self.n, nullity + 1), dtype=float)
        A[:, :nullity] = -(direction_sign * self.signs)[:, None] * N
        A[:, nullity] = 1.0
        objective = np.zeros(nullity + 1)
        objective[nullity] = -1.0
        res = linprog(
            objective,
            A_ub=A,
            b_ub=np.zeros(self.n),
            bounds=[(-1.0, 1.0)] * nullity + [(-10.0, 10.0)],
            method="highs",
        )
        if not res.success:
            return EndpointConeReport(
                False, float("-inf"), rank, nullity,
                [float(x) for x in singular], None,
            )
        direction = N @ res.x[:nullity]
        norm = float(np.linalg.norm(direction))
        if norm > 1e-12:
            direction /= norm
        margin = float(-res.fun)
        return EndpointConeReport(
            margin > 1e-8 and norm > 1e-12,
            margin,
            rank,
            nullity,
            [float(x) for x in singular],
            [float(x) for x in direction] if norm > 1e-12 else None,
        )

    def project(
        self,
        raw: np.ndarray,
        *,
        anchor: np.ndarray | None = None,
        near_weight: float = 0.07,
        max_nfev: int = 120,
    ) -> tuple[np.ndarray, float]:
        """Project an ambient angle vector onto closure(q)=0.

        Uses a minimum-norm Newton correction J^T(JJ^T)^-1 C. Starting
        from `raw` already provides the proximity objective, so we avoid a
        costly general nonlinear least-squares solve on every RRT microstep.
        """
        q = np.asarray(raw, dtype=float).copy()
        low = np.where(self.signs > 0, 0.0, -math.pi)
        high = np.where(self.signs > 0, math.pi, 0.0)
        q = np.clip(q, low, high)
        best_q = q.copy()
        best_err = float(np.linalg.norm(self.closure_residual(q)))
        max_iter = min(int(max_nfev), 16)
        for _ in range(max_iter):
            c = self.closure_residual(q)
            err = float(np.linalg.norm(c))
            if err < best_err:
                best_err, best_q = err, q.copy()
            if err <= 2e-8:
                return q, err
            J = self.numerical_jacobian(q, h=1e-6)
            gram = J @ J.T + 1e-10 * np.eye(3)
            try:
                delta = -J.T @ np.linalg.solve(gram, c)
            except np.linalg.LinAlgError:
                delta = -np.linalg.pinv(J, rcond=1e-8) @ c
            if np.linalg.norm(delta) < 1e-12:
                break
            accepted = False
            for alpha in (1.0, 0.5, 0.25, 0.125):
                cand = np.clip(q + alpha * delta, low, high)
                cand_err = float(np.linalg.norm(self.closure_residual(cand)))
                if cand_err < err:
                    q = cand
                    accepted = True
                    break
            if not accepted:
                break
        return best_q, best_err

    def endpoint_seeds(
        self,
        *,
        goal_side: bool,
        count: int = 12,
        epsilon: float = 0.12,
        seed: int = 7,
    ) -> tuple[list[np.ndarray], EndpointConeReport]:
        base = self.goal if goal_side else self.flat
        toward = self.flat if goal_side else self.goal
        report = self.endpoint_cone(base, outward=not goal_side)
        if not report.feasible or report.direction is None:
            return [], report
        basis, _, _ = self.tangent_basis(base)
        main = np.asarray(report.direction, dtype=float)
        rng = np.random.default_rng(seed)
        seeds: list[np.ndarray] = []
        for k in range(800):
            if len(seeds) >= count:
                break
            direction = main.copy()
            if k:
                noise = basis @ rng.normal(size=basis.shape[1])
                nn = float(np.linalg.norm(noise))
                if nn > 1e-12:
                    noise /= nn
                    direction = direction + 0.12 * noise
                    direction /= np.linalg.norm(direction)
            if np.dot(direction, toward - base) < 0:
                direction = -direction
            raw = base + epsilon * direction
            if not self.sector_valid(raw, tol=1e-5):
                continue
            q, err = self.project(raw, anchor=raw, near_weight=0.05, max_nfev=180)
            if err > 5e-7 or not self.sector_valid(q):
                continue
            if np.linalg.norm(q - base) < 1e-3:
                continue
            if all(np.linalg.norm(q - prev) > 1e-3 for prev in seeds):
                seeds.append(q)
        return seeds, report

    def panel_triangles(self, q: np.ndarray) -> list[np.ndarray]:
        rots = self.panel_rotations(q)
        triangles: list[np.ndarray] = []
        origin = np.zeros(3)
        for i in range(self.n):
            p0 = np.r_[self.rays[i]["point2"], 0.0]
            p1 = np.r_[self.rays[(i + 1) % self.n]["point2"], 0.0]
            R = rots[i]
            triangles.append(np.vstack([origin, R @ p0, R @ p1]))
        return triangles

    @staticmethod
    def _aabb_overlap(a: np.ndarray, b: np.ndarray, tol: float = 1e-9) -> bool:
        return bool(
            np.all(a.max(axis=0) + tol >= b.min(axis=0))
            and np.all(b.max(axis=0) + tol >= a.min(axis=0))
        )

    @staticmethod
    def _segment_triangle_intersection(
        p0: np.ndarray,
        p1: np.ndarray,
        tri: np.ndarray,
        eps: float = 1e-9,
    ) -> np.ndarray | None:
        # Moller-Trumbore for a finite segment.
        v0, v1, v2 = tri
        direction = p1 - p0
        e1 = v1 - v0
        e2 = v2 - v0
        h = np.cross(direction, e2)
        det = float(np.dot(e1, h))
        if abs(det) < eps:
            return None
        inv = 1.0 / det
        s = p0 - v0
        u = inv * float(np.dot(s, h))
        if u < -eps or u > 1 + eps:
            return None
        q = np.cross(s, e1)
        v = inv * float(np.dot(direction, q))
        if v < -eps or u + v > 1 + eps:
            return None
        t = inv * float(np.dot(e2, q))
        if t < -eps or t > 1 + eps:
            return None
        return p0 + t * direction

    @staticmethod
    def _orient2(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        return float((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))

    @classmethod
    def _point_in_triangle_2d(cls, p: np.ndarray, tri: np.ndarray, eps: float = 1e-10) -> bool:
        c1 = cls._orient2(tri[0], tri[1], p)
        c2 = cls._orient2(tri[1], tri[2], p)
        c3 = cls._orient2(tri[2], tri[0], p)
        return ((c1 >= -eps and c2 >= -eps and c3 >= -eps) or
                (c1 <= eps and c2 <= eps and c3 <= eps))

    @classmethod
    def _segments_intersect_2d(cls, a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray, eps: float = 1e-10) -> bool:
        o1 = cls._orient2(a,b,c); o2 = cls._orient2(a,b,d)
        o3 = cls._orient2(c,d,a); o4 = cls._orient2(c,d,b)
        return (o1*o2 < -eps and o3*o4 < -eps)

    @classmethod
    def _triangles_overlap_2d(cls, a: np.ndarray, b: np.ndarray) -> bool:
        # Ignore the shared central vertex; detect positive-area overlap by
        # non-center vertices or proper edge crossings.
        for p in a[1:]:
            if cls._point_in_triangle_2d(p, b):
                return True
        for p in b[1:]:
            if cls._point_in_triangle_2d(p, a):
                return True
        for i in range(3):
            for j in range(3):
                if cls._segments_intersect_2d(a[i],a[(i+1)%3],b[j],b[(j+1)%3]):
                    return True
        return False

    def _compute_final_contact_pairs(self) -> set[tuple[int,int]]:
        triangles = self.panel_triangles(self.goal)
        pairs: set[tuple[int,int]] = set()
        # All final triangles should be coplanar; choose XY after numerical cleanup.
        for i in range(self.n):
            for j in range(i+1,self.n):
                pair = tuple(sorted((i,j)))
                if pair in self._adjacent_pairs:
                    continue
                if self._triangles_overlap_2d(triangles[i][:,:2], triangles[j][:,:2]):
                    pairs.add(pair)
        return pairs

    def collision_report(
        self,
        q: np.ndarray,
        *,
        center_epsilon: float = 2e-5,
        goal_contact_epsilon: float = 0.0,
        contact_aware: bool = False,
        contact_progress_threshold: float = 0.55,
        layer_model = None,
    ) -> dict[str, Any]:
        exact_goal = np.linalg.norm(q - self.goal) <= goal_contact_epsilon if goal_contact_epsilon > 0 else False
        if exact_goal:
            return {"collision": False, "pairs_checked": 0, "contact_exemption": "EXACT_GOAL"}
        triangles = self.panel_triangles(q)
        progress = float(np.mean(np.abs(q)) / math.pi)
        pairs_checked = 0
        for i in range(self.n):
            for j in range(i + 1, self.n):
                pair = tuple(sorted((i, j)))
                if pair in self._adjacent_pairs:
                    continue
                if contact_aware and progress >= contact_progress_threshold and pair in self.final_contact_pairs:
                    continue
                a, b = triangles[i], triangles[j]
                if not self._aabb_overlap(a, b):
                    continue
                pairs_checked += 1
                # Edge/triangle intersections catch all non-coplanar triangle intersections.
                for tri_a, tri_b, ia, ib in ((a, b, i, j), (b, a, j, i)):
                    for k in range(3):
                        p0 = tri_a[k]
                        p1 = tri_a[(k + 1) % 3]
                        hit = self._segment_triangle_intersection(p0, p1, tri_b)
                        if hit is None:
                            continue
                        if np.linalg.norm(hit) <= center_epsilon:
                            continue
                        current_pair=tuple(sorted((ia,ib)))
                        if layer_model is not None and current_pair in self.final_contact_pairs:
                            if layer_model.intersection_is_legal_contact(q,current_pair,hit):
                                continue
                        return {
                            "collision": True,
                            "panels": [ia, ib],
                            "point": [float(x) for x in hit],
                            "pairs_checked": pairs_checked,
                            "kind": "EDGE_TRIANGLE",
                        }
                # Coplanar overlap is handled conservatively using projected area.
                na = np.cross(a[1] - a[0], a[2] - a[0])
                nb = np.cross(b[1] - b[0], b[2] - b[0])
                nna = np.linalg.norm(na); nnb = np.linalg.norm(nb)
                if nna > 1e-12 and nnb > 1e-12:
                    na /= nna; nb /= nnb
                    if abs(abs(float(np.dot(na, nb))) - 1.0) < 1e-7:
                        plane_dist = max(abs(float(np.dot(x - a[0], na))) for x in b)
                        if plane_dist < 1e-7:
                            # Project onto the dominant coordinate plane and compute area
                            # with a tiny dependency-free shoelace/intersection fallback:
                            # for this PoC, detect if one non-center vertex lies inside the
                            # other triangle after projection.
                            drop = int(np.argmax(np.abs(na)))
                            keep = [k for k in range(3) if k != drop]
                            aa = a[:, keep]; bb = b[:, keep]
                            def inside(p, t):
                                def cross2(x,y,z):
                                    return (y[0]-x[0])*(z[1]-x[1])-(y[1]-x[1])*(z[0]-x[0])
                                c1,c2,c3 = cross2(t[0],t[1],p),cross2(t[1],t[2],p),cross2(t[2],t[0],p)
                                return (c1 >= -1e-10 and c2 >= -1e-10 and c3 >= -1e-10) or (c1 <= 1e-10 and c2 <= 1e-10 and c3 <= 1e-10)
                            for p3,p2 in zip(a[1:], aa[1:]):
                                if np.linalg.norm(p3) > center_epsilon and inside(p2, bb):
                                    if layer_model is not None and pair in self.final_contact_pairs and layer_model.intersection_is_legal_contact(q,pair,p3):
                                        continue
                                    return {"collision": True, "panels":[i,j], "point":[float(x) for x in p3], "pairs_checked":pairs_checked, "kind":"COPLANAR_OVERLAP"}
                            for p3,p2 in zip(b[1:], bb[1:]):
                                if np.linalg.norm(p3) > center_epsilon and inside(p2, aa):
                                    if layer_model is not None and pair in self.final_contact_pairs and layer_model.intersection_is_legal_contact(q,pair,p3):
                                        continue
                                    return {"collision": True, "panels":[i,j], "point":[float(x) for x in p3], "pairs_checked":pairs_checked, "kind":"COPLANAR_OVERLAP"}
        return {"collision": False, "pairs_checked": pairs_checked, "contact_exemption": None}