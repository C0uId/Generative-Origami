"""Curved rigid motions and analytic enclosures for continuous checking.

The path represented here is *explicitly* q(t) = q0 + t (q1-q0), evaluated
through Rodrigues forward kinematics.  It is not a vertex interpolation and
it is not implicitly projected onto the mechanism's closure manifold.

For a product of rotations with constant angular rates, ||R'||_2 <= S and
||R''||_2 <= S**2, where S is the sum of absolute rates.  Consequently every
material point of radius r has speed <= r*S, acceleration <= r*S**2, and
distance from its endpoint chord <= r*S**2*h**2/8.  These are whole-interval
bounds, not observations at a collection of frames.  Numerical guards and
outward nextafter protect floating arithmetic; this reference implementation
is not an independently verified, arbitrary-precision interval library.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation


_EPS = np.finfo(float).eps


def _interval(a: float, b: float) -> tuple[float, float]:
    a, b = float(a), float(b)
    if not (math.isfinite(a) and math.isfinite(b) and 0.0 <= a <= b <= 1.0):
        raise ValueError("expected 0 <= a <= b <= 1")
    return a, b


def _guard(scale: float, count: int = 1) -> float:
    return float(128 * _EPS * max(1.0, abs(float(scale))) * max(1, count))


def _outward(lo: np.ndarray, hi: np.ndarray, guard: float) -> tuple[np.ndarray, np.ndarray]:
    return np.nextafter(lo - guard, -np.inf), np.nextafter(hi + guard, np.inf)


def _angle_from_frobenius(value: float) -> float:
    # ||R-I||_F = 2 sqrt(2) sin(theta/2), 0 <= theta <= pi.
    return 2.0 * math.asin(min(1.0, max(0.0, value / (2.0 * math.sqrt(2.0)))))


class RigidMechanismInterval:
    """A true rigid, possibly non-closed bridge between two angle vectors.

    ``continuous_closure`` must pass before the bridge can be used as a
    continuously closed origami path.  Passing only its endpoint keyframes
    is insufficient.  Time is the normalized interval [0, 1].
    """

    motion_kind = "RODRIGUES_FK_LINEAR_FOLD_ANGLES"

    def __init__(self, mechanism: Any, q0: np.ndarray, q1: np.ndarray):
        self.mechanism = mechanism
        self.m = mechanism
        self.q0 = np.asarray(q0, dtype=float).copy()
        self.q1 = np.asarray(q1, dtype=float).copy()
        if self.q0.shape != (mechanism.n,) or self.q1.shape != (mechanism.n,):
            raise ValueError("fold angle vector has incorrect shape")
        if not (np.isfinite(self.q0).all() and np.isfinite(self.q1).all()):
            raise ValueError("fold angle vectors must be finite")
        self.dq = self.q1 - self.q0
        self.n = mechanism.n
        self.panel_count = mechanism.n
        self.local_triangles = []
        for panel in range(self.n):
            self.local_triangles.append(np.vstack([
                np.zeros(3),
                np.r_[mechanism.rays[panel]["point2"], 0.0],
                np.r_[mechanism.rays[(panel + 1) % self.n]["point2"], 0.0],
            ]))
        self._radii = [float(np.linalg.norm(tri, axis=1).max()) for tri in self.local_triangles]
        self._rates = [float(np.abs(self.dq[1:panel + 1]).sum()) for panel in range(self.n)]

    def _panel(self, panel: int) -> int:
        panel = int(panel)
        if panel < 0 or panel >= self.n:
            raise IndexError("invalid panel")
        return panel

    def q(self, t: float) -> np.ndarray:
        t, _ = _interval(t, t)
        return self.q0 + t * self.dq

    def joint_bounds(self, a: float = 0.0, b: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        """Exact convex-hull angle bounds for this explicitly linear bridge."""
        a, b = _interval(a, b)
        qa, qb = self.q(a), self.q(b)
        return np.minimum(qa, qb), np.maximum(qa, qb)

    @property
    def fixed_joint_values(self) -> np.ndarray:
        """NaN denotes a joint whose constancy has not been proved."""
        return np.where(self.dq == 0.0, self.q0, np.nan)

    def rotations(self, t: float) -> list[np.ndarray]:
        return self.m.panel_rotations(self.q(t))

    panel_rotations = rotations

    def rotation(self, panel: int, t: float) -> np.ndarray:
        return self.rotations(t)[self._panel(panel)]

    def triangle(self, panel: int, t: float) -> np.ndarray:
        panel = self._panel(panel)
        return self.local_triangles[panel] @ self.rotation(panel, t).T

    def radius(self, panel: int) -> float:
        return self._radii[self._panel(panel)]

    def angular_speed_bound(self, panel: int) -> float:
        return self._rates[self._panel(panel)]

    def speed_bound(self, panel: int) -> float:
        return self.radius(panel) * self.angular_speed_bound(panel)

    def curvature_bound(self, panel: int) -> float:
        """Bound on ||x''|| for every material point (time normalized to 1)."""
        return self.radius(panel) * self.angular_speed_bound(panel) ** 2

    acceleration_bound = curvature_bound

    def chord_error_bound(self, panel: int, a: float = 0.0, b: float = 1.0) -> float:
        a, b = _interval(a, b)
        return self.curvature_bound(panel) * (b - a) ** 2 / 8.0

    def vertex_bounds(self, panel: int, a: float = 0.0, b: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        """Per-material-vertex boxes containing its entire curved trajectory."""
        panel = self._panel(panel)
        a, b = _interval(a, b)
        ta, tb = self.triangle(panel, a), self.triangle(panel, b)
        tm = self.triangle(panel, (a + b) / 2.0)
        chord_error = self.chord_error_bound(panel, a, b)
        travel = self.speed_bound(panel) * (b - a) / 2.0
        lo = np.maximum(np.minimum(ta, tb) - chord_error, tm - travel)
        hi = np.minimum(np.maximum(ta, tb) + chord_error, tm + travel)
        return _outward(lo, hi, _guard(self.radius(panel), self.n))

    def triangle_bounds(self, panel: int, a: float = 0.0, b: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        """Swept AABB of the full filled triangle, not only its endpoints."""
        lo, hi = self.vertex_bounds(panel, a, b)
        return lo.min(axis=0), hi.max(axis=0)

    def rotation_bounds(self, panel: int, a: float = 0.0, b: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        panel = self._panel(panel)
        a, b = _interval(a, b)
        ra, rb = self.rotation(panel, a), self.rotation(panel, b)
        rm = self.rotation(panel, (a + b) / 2.0)
        s = self.angular_speed_bound(panel)
        err = s * s * (b - a) ** 2 / 8.0
        travel = s * (b - a) / 2.0
        lo = np.maximum(np.minimum(ra, rb) - err, rm - travel)
        hi = np.minimum(np.maximum(ra, rb) + err, rm + travel)
        return _outward(lo, hi, _guard(1.0, self.n))

    def _closing_rotation(self, t: float) -> np.ndarray:
        q = self.q(t)
        current = self.m.panel_rotations(q)[-1]
        axis = np.r_[self.m.rays[0]["unit2"], 0.0]
        # Equivalent to the world-axis FK, using the local right product.
        return current @ self.m._axis_rotation(axis, float(q[0]))

    def continuous_closure(self, a: float = 0.0, b: float = 1.0,
                           tolerance: float = 4e-6, max_depth: int = 8) -> dict[str, Any]:
        """Certify rotation closure AND the closing hinge endpoint gap.

        Tree hinges share their origin and radial edge exactly by construction.
        Closing rotation uses the full product including crease zero.  Its
        second derivative has operator norm <= (sum(abs(dq)))**2.  The
        Frobenius interpolation remainder is bounded by sqrt(3) times that
        quantity times h**2/8.  Endpoint gap is independently bounded using
        the radius and derivatives of the last panel.  Every leaf must have
        BOTH analytic upper bounds <= tolerance; samples can only reject.
        """
        a, b = _interval(a, b)
        if not math.isfinite(tolerance) or tolerance <= 0 or max_depth < 0:
            raise ValueError("positive finite tolerance and nonnegative depth required")
        s = float(np.abs(self.dq).sum())
        stree = self.angular_speed_bound(self.n - 1)
        hinge = np.r_[self.m.rays[0]["point2"], 0.0]
        hinge_radius = float(np.linalg.norm(hinge))
        roundoff = _guard(max(hinge_radius, 1.0), self.n)
        cache: dict[float, tuple[float, float, float]] = {}
        observed_angle, observed_gap, witness = 0.0, 0.0, None

        def evaluate(t: float) -> tuple[float, float, float]:
            nonlocal observed_angle, observed_gap, witness
            if t not in cache:
                c = self._closing_rotation(t)
                frob = float(np.linalg.norm(c - np.eye(3), ord="fro"))
                angle = _angle_from_frobenius(frob)
                rlast = self.rotation(self.n - 1, t)
                gap = float(np.linalg.norm(rlast @ hinge - hinge))
                cache[t] = (frob, angle, gap)
                observed_angle = max(observed_angle, angle)
                observed_gap = max(observed_gap, gap)
                if (angle > tolerance or gap > tolerance) and witness is None:
                    witness = {"t": t, "rotation_error": angle, "endpoint_gap": gap}
            return cache[t]

        def bounds(x: float, y: float) -> tuple[float, float]:
            left, right = evaluate(x), evaluate(y)
            h = y - x
            cfrob = max(left[0], right[0]) + math.sqrt(3.0) * s * s * h * h / 8.0 + roundoff
            cangle = _angle_from_frobenius(cfrob)
            gap = max(left[2], right[2]) + hinge_radius * stree * stree * h * h / 8.0 + roundoff
            return cangle, gap

        coarse_angle, coarse_gap = bounds(a, b)
        stack = [(a, b, 0)]
        subdivisions, leaves, max_used_depth = 0, 0, 0
        leaf_angle, leaf_gap = 0.0, 0.0
        unresolved = False
        while stack:
            x, y, depth = stack.pop()
            max_used_depth = max(max_used_depth, depth)
            angle_bound, gap_bound = bounds(x, y)
            # The midpoint is a rejection witness, NEVER a passing argument.
            evaluate((x + y) / 2.0)
            if witness is not None:
                return {
                    "status": "UNCERTAIN", "reason": "CLOSURE_TOLERANCE_VIOLATION_WITNESS",
                    "rotation_upper_bound": coarse_angle, "endpoint_gap_upper_bound": coarse_gap,
                    "continuous_upper_bound": max(coarse_angle, coarse_gap),
                    "observed_lower_bound": max(observed_angle, observed_gap),
                    "observed_rotation_error": observed_angle, "observed_endpoint_gap": observed_gap,
                    "witness": witness, "tree_hinge_gap_upper_bound": 0.0,
                    "tolerance": tolerance, "subdivisions": subdivisions,
                    "max_depth_used": max_used_depth, "evaluations": len(cache),
                    "method": "ANALYTIC_PRODUCT_DERIVATIVE_TAYLOR_BOUND",
                }
            if angle_bound <= tolerance and gap_bound <= tolerance:
                leaves += 1
                leaf_angle, leaf_gap = max(leaf_angle, angle_bound), max(leaf_gap, gap_bound)
            elif depth >= max_depth:
                unresolved = True
                leaves += 1
                leaf_angle, leaf_gap = max(leaf_angle, angle_bound), max(leaf_gap, gap_bound)
            else:
                mid = (x + y) / 2.0
                stack.extend([(mid, y, depth + 1), (x, mid, depth + 1)])
                subdivisions += 1
        return {
            "status": "UNCERTAIN" if unresolved else "PASS",
            "reason": "CLOSURE_BOUND_EXCEEDS_TOLERANCE_AT_DEPTH_LIMIT" if unresolved else "CONTINUOUS_CLOSURE_BOUNDED",
            "rotation_upper_bound": leaf_angle, "endpoint_gap_upper_bound": leaf_gap,
            "continuous_upper_bound": max(leaf_angle, leaf_gap),
            "observed_lower_bound": max(observed_angle, observed_gap),
            "observed_rotation_error": observed_angle, "observed_endpoint_gap": observed_gap,
            "tree_hinge_gap_upper_bound": 0.0, "tolerance": tolerance,
            "subdivisions": subdivisions, "leaves": leaves, "max_depth_used": max_used_depth,
            "evaluations": len(cache), "witness": witness,
            "method": "ANALYTIC_PRODUCT_DERIVATIVE_TAYLOR_BOUND",
        }


class RigidTriangleMotion:
    """Synthetic rigid triangle: R0 exp(t log(R0.T R1)) and linear translation.

    Provides the same triangle/bound interface as ``RigidMechanismInterval``.
    For this one-panel motion the panel index is always zero.  In particular
    a rotating triangle follows a curved trajectory, even with only two input
    transforms.  Endpoint rotations choose the shortest SO(3) arc.
    """

    motion_kind = "SO3_EXPONENTIAL_WITH_LINEAR_TRANSLATION"

    def __init__(self, local: np.ndarray, R0: np.ndarray | None = None,
                 R1: np.ndarray | None = None, translation0: np.ndarray | None = None,
                 translation1: np.ndarray | None = None):
        self.local = np.asarray(local, dtype=float).copy()
        self.R0 = np.eye(3) if R0 is None else np.asarray(R0, dtype=float).copy()
        self.R1 = np.eye(3) if R1 is None else np.asarray(R1, dtype=float).copy()
        self.translation0 = np.zeros(3) if translation0 is None else np.asarray(translation0, dtype=float).copy()
        self.translation1 = np.zeros(3) if translation1 is None else np.asarray(translation1, dtype=float).copy()
        if self.local.shape != (3, 3) or self.R0.shape != (3, 3) or self.R1.shape != (3, 3):
            raise ValueError("expected triangle (3,3) and rotations (3,3)")
        if self.translation0.shape != (3,) or self.translation1.shape != (3,):
            raise ValueError("expected translations (3,)")
        for r in (self.R0, self.R1):
            if not np.isfinite(r).all() or not np.allclose(r.T @ r, np.eye(3), atol=1e-10, rtol=0) or np.linalg.det(r) <= 0:
                raise ValueError("expected proper orthogonal rotations")
        if not all(np.isfinite(v).all() for v in (self.local, self.translation0, self.translation1)):
            raise ValueError("motion must be finite")
        self.rotvec = Rotation.from_matrix(self.R0.T @ self.R1).as_rotvec()
        self.angle = float(np.linalg.norm(self.rotvec))
        self.translation_delta = self.translation1 - self.translation0
        self._radius = float(np.linalg.norm(self.local, axis=1).max())
        self.n = self.panel_count = 1

    @staticmethod
    def _panel(panel: int) -> None:
        if panel != 0:
            raise IndexError("synthetic triangle motion has only panel 0")

    def rotation(self, panel: int, t: float) -> np.ndarray:
        self._panel(panel)
        _interval(t, t)
        return self.R0 @ Rotation.from_rotvec(float(t) * self.rotvec).as_matrix()

    def rotations(self, t: float) -> list[np.ndarray]:
        return [self.rotation(0, t)]

    def triangle(self, panel: int, t: float) -> np.ndarray:
        return self.local @ self.rotation(panel, t).T + self.translation0 + t * self.translation_delta

    def radius(self, panel: int = 0) -> float:
        self._panel(panel)
        return self._radius

    def angular_speed_bound(self, panel: int = 0) -> float:
        self._panel(panel)
        return self.angle

    def speed_bound(self, panel: int = 0) -> float:
        return self.radius(panel) * self.angle + float(np.linalg.norm(self.translation_delta))

    def curvature_bound(self, panel: int = 0) -> float:
        return self.radius(panel) * self.angle ** 2

    acceleration_bound = curvature_bound

    def chord_error_bound(self, panel: int = 0, a: float = 0.0, b: float = 1.0) -> float:
        a, b = _interval(a, b)
        return self.curvature_bound(panel) * (b - a) ** 2 / 8.0

    def vertex_bounds(self, panel: int = 0, a: float = 0.0, b: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        a, b = _interval(a, b)
        ta, tb = self.triangle(panel, a), self.triangle(panel, b)
        tm = self.triangle(panel, (a + b) / 2.0)
        err = self.chord_error_bound(panel, a, b)
        travel = self.speed_bound(panel) * (b - a) / 2.0
        return _outward(np.maximum(np.minimum(ta, tb) - err, tm - travel),
                        np.minimum(np.maximum(ta, tb) + err, tm + travel),
                        _guard(max(self._radius, np.linalg.norm(self.translation0), np.linalg.norm(self.translation1))))

    def triangle_bounds(self, panel: int = 0, a: float = 0.0, b: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        lo, hi = self.vertex_bounds(panel, a, b)
        return lo.min(axis=0), hi.max(axis=0)

    def rotation_bounds(self, panel: int = 0, a: float = 0.0, b: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        a, b = _interval(a, b)
        ra, rb, rm = self.rotation(panel, a), self.rotation(panel, b), self.rotation(panel, (a + b) / 2.0)
        err, travel = self.angle ** 2 * (b - a) ** 2 / 8.0, self.angle * (b - a) / 2.0
        return _outward(np.maximum(np.minimum(ra, rb) - err, rm - travel),
                        np.minimum(np.maximum(ra, rb) + err, rm + travel), _guard(1.0))