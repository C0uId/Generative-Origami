"""Analytic spherical 3R closure candidate; diagnostics are not certification.

Three consecutive local crease rotations are solved, while all other fold
angles vary linearly.  The resulting points always use rigid Rodrigues FK.
The closed-form factorization requires coplanar local axes, nonzero A, an
acos domain in [-1, 1], and nondegenerate projected vectors.  Unproved
intervals, including singular endpoints, fail closed in ``domain_certificate``.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np


class BridgeUnavailable(ValueError):
    """No valid branch was established for the requested time or interval."""


def _skew(v: np.ndarray) -> np.ndarray:
    x, y, z = v
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def _time(t: float) -> float:
    t = float(t)
    if not math.isfinite(t) or not 0 <= t <= 1:
        raise ValueError("expected finite time in [0, 1]")
    return t


class SphericalClosureBridge:
    """Exact-algebra 3R candidate, with explicit numerical/proof limitations.

    ``dependent`` is consecutive in cyclic FK order [1, ..., n-1, 0].
    Each solved angle is unwrapped to the nearest source linear angle.  A
    continuous branch is certified only after whole-interval bounds exclude
    acos singularities and both alpha/gamma branch cuts.  Endpoints are
    recomputed rather than silently replacing the candidate by saved angles.
    """
    motion_kind = "SPHERICAL_3R_ANALYTIC_CLOSURE"

    def __init__(self, mechanism: Any, q0: np.ndarray, q1: np.ndarray,
                 dependent: tuple[int, int, int] = (3, 4, 5),
                 numerical_error: float = 1e-12):
        self.m = self.mechanism = mechanism
        self.n = self.panel_count = mechanism.n
        self.reference_q0, self.reference_q1 = (np.asarray(q, float).copy() for q in (q0, q1))
        if self.reference_q0.shape != (self.n,) or self.reference_q1.shape != (self.n,):
            raise ValueError("incorrect fold angle shape")
        if not np.isfinite(self.reference_q0).all() or not np.isfinite(self.reference_q1).all():
            raise ValueError("nonfinite fold angles")
        if not math.isfinite(numerical_error) or numerical_error <= 0:
            raise ValueError("positive finite numerical_error required")
        self.numerical_error = float(numerical_error)
        self.dq = self.reference_q1 - self.reference_q0
        self.dependent = tuple(int(x) for x in dependent)
        order = list(range(1, self.n)) + [0]
        start = order.index(self.dependent[0]) if self.dependent[0] in order else -1
        # Rotate full cyclic equation so even a seam-spanning triple is valid.
        if start < 0 or tuple((self.dependent[0] + k) % self.n for k in range(3)) != self.dependent:
            raise ValueError("dependent indices must be three consecutive cyclic creases")
        self.order = order[start:] + order[:start]
        self.free = self.order[3:]
        self.axes = [np.r_[r["unit2"], 0.] for r in self.m.rays]
        self.a, self.b, self.c = [self.axes[k] for k in self.dependent]
        self.ab, self.bc = float(self.a @ self.b), float(self.b @ self.c)
        self.A = float(self.a @ self.c) - self.ab * self.bc
        self.B = self.ab * self.bc
        if abs(float(self.a @ np.cross(self.b, self.c))) > numerical_error or abs(self.A) < 1e-10:
            raise BridgeUnavailable("DEGENERATE_OR_NONCOPLANAR_3R_AXES")
        self.beta_sign = float(mechanism.signs[self.dependent[1]])
        self.local_triangles = [np.vstack([np.zeros(3),
            np.r_[mechanism.rays[p]["point2"], 0.],
            np.r_[mechanism.rays[(p+1) % self.n]["point2"], 0.]]) for p in range(self.n)]
        self._free_rate = float(np.abs(self.dq[self.free]).sum())
        self._regularity_cache = {}

    @property
    def q0(self) -> np.ndarray:
        return self.q(0.)

    @property
    def q1(self) -> np.ndarray:
        return self.q(1.)

    @property
    def fixed_joint_values(self) -> np.ndarray:
        values = np.full(self.n, np.nan)
        for k in self.free:
            if self.dq[k] == 0.:
                values[k] = self.reference_q0[k]
        return values

    def _R(self, k: int, angle: float) -> np.ndarray:
        return self.m._axis_rotation(self.axes[k], float(angle))

    def target_jet(self, t: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """T = inverse(free product), with exact first/second derivatives."""
        t = _time(t)
        q = self.reference_q0 + t * self.dq
        P, D, E = np.eye(3), np.zeros((3, 3)), np.zeros((3, 3))
        for k in self.free:
            R = self._R(k, q[k]); K = _skew(self.axes[k]) * self.dq[k]
            R1, R2 = K @ R, K @ K @ R
            P, D, E = P @ R, D @ R + P @ R1, E @ R + 2 * D @ R1 + P @ R2
        return P.T, D.T, E.T

    def acos_jet(self, t: float) -> tuple[float, float, float]:
        T, D, E = self.target_jet(t)
        return ((float(self.a @ T @ self.c) - self.B) / self.A,
                float(self.a @ D @ self.c) / self.A,
                float(self.a @ E @ self.c) / self.A)

    @staticmethod
    def _unwrap(value: float, reference: float) -> float:
        return value + 2 * math.pi * round((reference - value) / (2 * math.pi))

    def q(self, t: float) -> np.ndarray:
        t = _time(t)
        q = self.reference_q0 + t * self.dq
        T = self.target_jet(t)[0]
        x = (float(self.a @ T @ self.c) - self.B) / self.A
        if x < -1 - self.numerical_error or x > 1 + self.numerical_error:
            raise BridgeUnavailable("ACOS_DOMAIN_VIOLATION")
        # Only a documented roundoff-sized excess can be rounded to the boundary.
        beta = self.beta_sign * math.acos(min(1., max(-1., x)))
        Rb = self._R(self.dependent[1], beta)
        u, v = Rb @ self.c, T @ self.c
        up, vp = u - self.a * float(self.a @ u), v - self.a * float(self.a @ v)
        if min(np.linalg.norm(up), np.linalg.norm(vp)) <= 1e-10:
            raise BridgeUnavailable("ALPHA_PROJECTION_SINGULARITY")
        alpha = math.atan2(float(self.a @ np.cross(up, vp)), float(up @ vp))
        Ra = self._R(self.dependent[0], alpha)
        residual = (Ra @ Rb).T @ T
        gamma = math.atan2(float(self.c @ np.array([residual[2,1]-residual[1,2],
            residual[0,2]-residual[2,0], residual[1,0]-residual[0,1]])) / 2,
            (float(np.trace(residual)) - 1.) / 2)
        for k, value in zip(self.dependent, (alpha, beta, gamma)):
            q[k] = self._unwrap(value, q[k])
        check = Ra @ Rb @ self._R(self.dependent[2], gamma)
        if np.linalg.norm(check - T, ord=2) > max(1e-9, 100 * self.numerical_error):
            raise BridgeUnavailable("FACTORIZATION_RESIDUAL_EXCEEDS_ROUNDOFF")
        return q

    def rotations(self, t: float) -> list[np.ndarray]:
        return self.m.panel_rotations(self.q(t))

    panel_rotations = rotations

    def rotation(self, panel: int, t: float) -> np.ndarray:
        return self.rotations(t)[panel]

    def triangle(self, panel: int, t: float) -> np.ndarray:
        return self.local_triangles[panel] @ self.rotation(panel, t).T

    def radius(self, panel: int) -> float:
        return float(np.linalg.norm(self.local_triangles[panel], axis=1).max())

    def domain_bounds(self, a: float = 0., b: float = 1.) -> tuple[float, float]:
        """Whole-interval acos argument Taylor enclosure, not sample extrema."""
        a, b = _time(a), _time(b)
        if b < a:
            raise ValueError("reversed interval")
        mid, h = (a+b)/2, (b-a)/2
        x, dx, _ = self.acos_jet(mid)
        guard = self.numerical_error * max(1., 1/abs(self.A))
        error = abs(dx)*h + self._free_rate**2 / abs(self.A)*h*h/2 + guard
        return float(np.nextafter(x-error, -np.inf)), float(np.nextafter(x+error, np.inf))

    def domain_certificate(self, a: float = 0., b: float = 1., max_depth: int = 12) -> dict:
        """Prove only nonsingular acos domain; branch/facet proof is separate.

        A PASS here cannot certify continuous closure by itself.  In
        particular no sampled bound or singular boundary is accepted.
        """
        a, b = _time(a), _time(b)
        if b < a or max_depth < 0:
            raise ValueError("invalid interval/depth")
        stack, leaves = [(a, b, 0)], []
        while stack:
            x, y, depth = stack.pop()
            lo, hi = self.domain_bounds(x, y)
            if -1 < lo and hi < 1:
                leaves.append({"a":x,"b":y,"lo":lo,"hi":hi})
            elif lo > 1 or hi < -1:
                return {"status":"UNCERTAIN","reason":"ACOS_DOMAIN_OUTSIDE","interval":[x,y]}
            elif depth >= max_depth:
                return {"status":"UNCERTAIN","reason":"ACOS_DOMAIN_OR_SINGULAR_ENDPOINT_UNRESOLVED","interval":[x,y],"bounds":[lo,hi]}
            else:
                mid=(x+y)/2; stack.extend([(x,mid,depth+1),(mid,y,depth+1)])
        return {"status":"PASS","reason":"ANALYTIC_ACOS_DOMAIN_INTERIOR","leaves":leaves,
                "scope":"domain only; continuous branch and closure still require proof"}

    def continuous_closure(self, a: float = 0., b: float = 1., tolerance: float = 4e-6,
                           max_depth: int = 12) -> dict:
        """Conditional analytic closure identity on a regular branch cell.

        This uses a declared floating-reference guard, not a formally verified
        arbitrary precision enclosure.  No sampled residual establishes PASS.
        """
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("positive finite tolerance required")
        proof = self.regularity(a,b)
        bound = proof.get("evaluation_error_bound", float("inf"))
        gap = bound * self.radius(self.n-1)
        passed = proof["proven"] and max(bound,gap) <= tolerance
        return {"status":"PASS" if passed else "UNCERTAIN",
                "reason":"SPHERICAL_3R_CONTINUOUS_IDENTITY" if passed else proof["reason"],
                "rotation_upper_bound":bound,"endpoint_gap_upper_bound":gap,
                "continuous_upper_bound":max(bound,gap),"observed_lower_bound":0.,
                "structural_identity":"dependent product = inverse(free product)",
                "regularity":proof,"tolerance":tolerance,
                "numeric_scope":"conditional floating reference guard; not verified interval arithmetic"}

    def regularity(self, a: float = 0., b: float = 1.) -> dict:
        """Whole-cell domain, inverse Jacobian, and angle branch certificate.

        For J's three unit columns, s1*s2 <= 3/2, so
        ||J^-1|| <= 1.5 / |det J| = 1.5 / (|A| |sin beta|).
        The point acceleration bound includes both squared angular velocity
        and angle acceleration; constant-rate formulas cannot be reused here.
        """
        a,b = _time(a),_time(b)
        if b<a:
            raise ValueError("reversed interval")
        key=(a,b)
        if key in self._regularity_cache:
            return self._regularity_cache[key]
        lo,hi = self.domain_bounds(a,b)
        result={"proven":False,"status":"UNCERTAIN","reason":"ACOS_DOMAIN_OR_SINGULAR_ENDPOINT_UNRESOLVED",
                "interval":[a,b],"acos_bounds":[lo,hi]}
        if not -1<lo<=hi<1:
            self._regularity_cache[key]=result
            return result
        sinmin=math.sqrt(max(0.,1-max(abs(lo),abs(hi))**2))
        K=1.5/(abs(self.A)*sinmin)
        F=self._free_rate
        dep_velocity=K*F
        Sall=F+math.sqrt(3)*dep_velocity
        accel_l1=math.sqrt(3)*K*(F*Sall+math.sqrt(3)*Sall*dep_velocity)
        mid,h=(a+b)/2,(b-a)/2
        try:
            qm=self.q(mid)
        except BridgeUnavailable as exc:
            result["reason"]=str(exc); self._regularity_cache[key]=result; return result
        reference=self.reference_q0+mid*self.dq
        branch_margin=min(math.pi-abs(qm[k]-reference[k])-(dep_velocity+abs(self.dq[k]))*h
                          for k in self.dependent)
        # With nonzero beta sine, the analytic alpha projection is nonzero:
        # its out-of-plane component has magnitude |b x c| |sin beta|.
        projection_lower=float(np.linalg.norm(np.cross(self.b,self.c)))*sinmin
        guard=self.numerical_error*512*(1+K)
        result.update(inverse_jacobian_bound=K,sin_beta_lower_bound=sinmin,
            dependent_speed_l2_bound=dep_velocity,angular_speed_l1_bound=Sall,
            dependent_acceleration_l1_bound=accel_l1,
            branch_margin=branch_margin,alpha_projection_lower_bound=projection_lower,
            evaluation_error_bound=guard,
            proof_assumptions=["coplanar fixed unit axes", "linear free angles", "floating reference guard"])
        if branch_margin>guard and projection_lower>guard:
            result.update(proven=True,status="PASS",reason="REGULAR_SPHERICAL_3R_BRANCH")
        else:
            result["reason"]="ANGLE_BRANCH_OR_PROJECTION_UNRESOLVED"
        self._regularity_cache[key]=result
        return result

    def _require(self,a:float,b:float)->dict:
        proof=self.regularity(a,b)
        if not proof["proven"]:
            raise BridgeUnavailable(proof["reason"])
        return proof

    def joint_bounds(self,a:float=0.,b:float=1.) -> tuple[np.ndarray,np.ndarray]:
        proof=self._require(a,b)
        mid,h=(a+b)/2,(b-a)/2
        qm=self.q(mid)
        error=proof["dependent_speed_l2_bound"]*h+proof["evaluation_error_bound"]
        lo,hi=qm-error,qm+error
        for k in self.free:
            qa=self.reference_q0[k]+a*self.dq[k]; qb=self.reference_q0[k]+b*self.dq[k]
            lo[k],hi[k]=min(qa,qb),max(qa,qb)
        return lo,hi

    def angular_speed_bound(self,panel:int,a:float=0.,b:float=1.) -> float:
        return self._require(a,b)["angular_speed_l1_bound"]

    def speed_bound(self,panel:int,a:float=0.,b:float=1.) -> float:
        return self.radius(panel)*self.angular_speed_bound(panel,a,b)

    def curvature_bound(self,panel:int,a:float=0.,b:float=1.) -> float:
        proof=self._require(a,b)
        return self.radius(panel)*(proof["angular_speed_l1_bound"]**2+proof["dependent_acceleration_l1_bound"])

    acceleration_bound=curvature_bound

    def chord_error_bound(self,panel:int,a:float=0.,b:float=1.) -> float:
        return self.curvature_bound(panel,a,b)*(b-a)**2/8

    def vertex_bounds(self,panel:int,a:float=0.,b:float=1.) -> tuple[np.ndarray,np.ndarray]:
        proof=self._require(a,b)
        ta,tb=self.triangle(panel,a),self.triangle(panel,b)
        tm=self.triangle(panel,(a+b)/2)
        chord=self.chord_error_bound(panel,a,b)
        travel=self.speed_bound(panel,a,b)*(b-a)/2
        guard=proof["evaluation_error_bound"]*max(1.,self.radius(panel))
        lo=np.maximum(np.minimum(ta,tb)-chord,tm-travel)
        hi=np.minimum(np.maximum(ta,tb)+chord,tm+travel)
        return np.nextafter(lo-guard,-np.inf),np.nextafter(hi+guard,np.inf)

    def triangle_bounds(self,panel:int,a:float=0.,b:float=1.) -> tuple[np.ndarray,np.ndarray]:
        lo,hi=self.vertex_bounds(panel,a,b)
        return lo.min(axis=0),hi.max(axis=0)

    def exact_closing_hinge_certificate(self,a:float=0.,b:float=1.) -> dict:
        closure=self.continuous_closure(a,b)
        return {"status":closure["status"],"reason":closure["reason"],
                "identity":"full cyclic rotation product equals identity, hence the seam radial edge is invariant",
                "continuous_upper_bound":closure["continuous_upper_bound"],
                "numeric_scope":closure["numeric_scope"]}