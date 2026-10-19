"""Deflated flat-end charts and fail-closed whole-interval derivative bounds.

The mathematical motion is the implicit analytic 3R curve, with
``h(t) = (1 - acos_argument(t))/t**2`` continuously extended at zero.
The flat chart factors ``1 - acos_argument(t) = t**2 * h(t)``.  Taylor
coefficients and an analytic exponential tail enclose h, h' and h'', so the
singular endpoint never divides by sin(beta).  Samples are construction
diagnostics only. q()/triangle() are bounded numerical evaluators of that
ideal curve, not a definition of a finite-polynomial replacement motion.
Every material point is evaluated through rigid FK. Joint, vertex and CCD
chord enclosures include the complete evaluator error.

Arithmetic uses outward nextafter rounding and a declared libm guard. This
is a conservative floating reference certificate, not a formal proof about
the host's transcendental implementation. An unresolved chart returns no
replacement motion; the caller must retain and label its earlier motion.
"""
from __future__ import annotations

from dataclasses import dataclass
import itertools
import math

import numpy as np

from .spherical_bridge import BridgeUnavailable, SphericalClosureBridge, _skew, _time


def _down(x):
    return float(np.nextafter(float(x), -np.inf))


def _up(x):
    return float(np.nextafter(float(x), np.inf))


class _I:
    """Small outward-rounded scalar interval, with no sampled extrema."""
    __slots__ = ("lo", "hi")

    def __init__(self, lo, hi=None):
        self.lo, self.hi = float(lo), float(lo if hi is None else hi)
        if not math.isfinite(self.lo) or not math.isfinite(self.hi) or self.lo > self.hi:
            raise BridgeUnavailable("NONFINITE_OR_REVERSED_INTERVAL")

    @staticmethod
    def cast(x):
        return x if isinstance(x, _I) else _I(x)

    def __add__(self, other):
        other = self.cast(other)
        return _I(_down(self.lo + other.lo), _up(self.hi + other.hi))

    __radd__ = __add__

    def __neg__(self):
        return _I(-self.hi, -self.lo)

    def __sub__(self, other):
        return self + -self.cast(other)

    def __rsub__(self, other):
        return self.cast(other) + -self

    def __mul__(self, other):
        other = self.cast(other)
        vals = [self.lo * other.lo, self.lo * other.hi,
                self.hi * other.lo, self.hi * other.hi]
        return _I(_down(min(vals)), _up(max(vals)))

    __rmul__ = __mul__

    def reciprocal(self):
        if self.lo <= 0 <= self.hi:
            raise BridgeUnavailable("INTERVAL_DIVISION_BY_ZERO")
        return _I(_down(1 / self.hi), _up(1 / self.lo))

    def __truediv__(self, other):
        return self * self.cast(other).reciprocal()

    def __rtruediv__(self, other):
        return self.cast(other) * self.reciprocal()

    def square(self):
        lo = 0. if self.lo <= 0 <= self.hi else min(self.lo*self.lo, self.hi*self.hi)
        return _I(max(0., _down(lo)), _up(max(self.lo*self.lo, self.hi*self.hi)))

    def sqrt(self):
        if self.lo < 0:
            raise BridgeUnavailable("INTERVAL_SQRT_DOMAIN")
        return _I(max(0., _down(math.sqrt(self.lo))), _up(math.sqrt(self.hi)))

    def magnitude(self):
        return max(abs(self.lo), abs(self.hi))

    def sin(self):
        if self.hi-self.lo >= 2*math.pi:
            return _I(-1., 1.)
        vals = [math.sin(self.lo), math.sin(self.hi)]
        for k in range(math.ceil((self.lo-math.pi/2)/math.pi),
                       math.floor((self.hi-math.pi/2)/math.pi)+1):
            vals.append(1. if k % 2 == 0 else -1.)
        guard = 8*np.finfo(float).eps
        return _I(max(-1., _down(min(vals)-guard)), min(1., _up(max(vals)+guard)))

    def cos(self):
        return (self + math.pi/2).sin()

    def as_list(self):
        return [self.lo, self.hi]


class _Jet:
    """Value, first and second derivative interval automatic differentiation."""
    __slots__ = ("v", "d", "dd")

    def __init__(self, v, d=0., dd=0.):
        self.v, self.d, self.dd = map(_I.cast, (v, d, dd))

    @staticmethod
    def cast(x):
        return x if isinstance(x, _Jet) else _Jet(x)

    def __add__(self, x):
        x = self.cast(x)
        return _Jet(self.v+x.v, self.d+x.d, self.dd+x.dd)

    __radd__ = __add__

    def __neg__(self):
        return _Jet(-self.v, -self.d, -self.dd)

    def __sub__(self, x):
        return self + -self.cast(x)

    def __rsub__(self, x):
        return self.cast(x) + -self

    def __mul__(self, x):
        x = self.cast(x)
        return _Jet(self.v*x.v, self.d*x.v+self.v*x.d,
                    self.dd*x.v+2*self.d*x.d+self.v*x.dd)

    __rmul__ = __mul__

    def reciprocal(self):
        r = self.v.reciprocal()
        return _Jet(r, -self.d*r*r,
                    2*self.d.square()*r*r*r-self.dd*r*r)

    def __truediv__(self, x):
        return self * self.cast(x).reciprocal()

    def __rtruediv__(self, x):
        return self.cast(x) * self.reciprocal()

    def sin(self):
        s, c = self.v.sin(), self.v.cos()
        return _Jet(s, c*self.d, c*self.dd-s*self.d.square())

    def cos(self):
        s, c = self.v.sin(), self.v.cos()
        return _Jet(c, -s*self.d, -s*self.dd-c*self.d.square())

    def sqrt(self):
        r = self.v.sqrt()
        return _Jet(r, self.d/(2*r), self.dd/(2*r)-self.d.square()/(4*r*r*r))


def _asin(x):
    one = _I(1.)-x.v.square()
    den = one.sqrt()
    if x.v.lo < -1 or x.v.hi > 1 or den.lo <= 0:
        raise BridgeUnavailable("ASIN_BRANCH_OR_DERIVATIVE_UNRESOLVED")
    guard = 8*np.finfo(float).eps
    return _Jet(_I(_down(math.asin(x.v.lo)-guard), _up(math.asin(x.v.hi)+guard)),
                x.d/den, x.dd/den+x.v*x.d.square()/(den*den*den))


def _atan2(y, x):
    r2 = x.v.square()+y.v.square()
    if r2.lo <= 0 or (x.v.lo < 0 and y.v.lo <= 0 <= y.v.hi):
        raise BridgeUnavailable("ATAN2_BRANCH_OR_PROJECTION_UNRESOLVED")
    vals = [math.atan2(a, b) for a in (y.v.lo,y.v.hi) for b in (x.v.lo,x.v.hi)]
    if max(vals)-min(vals) >= math.pi:
        raise BridgeUnavailable("ATAN2_BRANCH_CUT")
    guard = 8*np.finfo(float).eps
    num = x.v*y.d-y.v*x.d
    d = num/r2
    dd = (x.v*y.dd-y.v*x.dd)/r2-num*(2*x.v*x.d+2*y.v*y.d)/(r2*r2)
    return _Jet(_I(_down(min(vals)-guard),_up(max(vals)+guard)), d, dd)


def _mm(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(a, b):
    return [sum(a[i][k]*b[k] for k in range(3)) for i in range(3)]


def _transpose(a):
    return [list(x) for x in zip(*a)]


def _dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def _cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def _rotation(axis, q):
    K = _skew(np.asarray(axis))
    K2 = K @ K
    s,c = q.sin(),q.cos()
    return [[float(i == j)+s*K[i,j]+(1-c)*K2[i,j] for j in range(3)] for i in range(3)]


@dataclass(frozen=True)
class SingularBridgeConfig:
    dependent: tuple[int,int,int] = (3,4,5)
    max_depth: int = 6
    taylor_order: int = 18
    closure_tolerance: float = 4e-6
    join_tolerance: float = 2e-11
    numerical_error: float = 1e-12
    # Existing conservative CCD's default transverse-witness guard. If a
    # caller reduces that guard it must reduce this limit accordingly.
    max_point_evaluation_error: float = 1e-8

    def __post_init__(self):
        if self.max_depth < 0 or self.taylor_order < 6:
            raise ValueError("nonnegative depth and Taylor order >= 6 required")
        if not all(math.isfinite(x) and x > 0 for x in
                   (self.closure_tolerance,self.join_tolerance,self.numerical_error,
                    self.max_point_evaluation_error)):
            raise ValueError("finite positive chart tolerances required")


class LocalChartMotion(SphericalClosureBridge):
    """Same analytic 3R factorization, with coordinatewise interval jets.

    A flat initial state uses a deflated chart. Regular states use interval
    atan2/acos derivatives. The mathematical motion is the ideal implicit
    analytic branch; finite Taylor arithmetic is its bounded evaluator.
    No vertex coordinate is interpolated.
    """
    motion_kind = "DEFLATED_SINGULAR_OR_REGULAR_EXACT_LOCAL_CHART"

    def __init__(self, mechanism, q0, q1, config=None):
        self.config = config or SingularBridgeConfig()
        super().__init__(mechanism,q0,q1,self.config.dependent,self.config.numerical_error)
        self.flat_start = bool(np.array_equal(self.reference_q0, np.zeros(self.n)))
        self._jets_cache = {}
        self._chart_meta_cache = {}
        self._bound_cache = {}
        if self.flat_start:
            self._build_deflated_series()

    def _build_deflated_series(self):
        """Coefficient intervals of a.T @ inverse(free product) @ c.

        For k >= 0, |x^(k)| <= F**k/|A|. The exponential-tail bound
        therefore covers every omitted coefficient on the entire [0,1].
        The planar identities x(0)=1 and x'(0)=0 are symbolic, not rounded
        subtractions of values near one.
        """
        n = self.config.taylor_order
        ident = [[_I(float(i==j)) for j in range(3)] for i in range(3)]
        zero = lambda: [[_I(0.) for j in range(3)] for i in range(3)]
        coeff = [ident]+[zero() for _ in range(n)]
        for k in reversed(self.free):
            # inverse(P) = exp(-K_last*q_last)...exp(-K_first*q_first)
            K = -_skew(self.axes[k])*self.dq[k]
            powers=[ident]
            Ki=[[ _I(K[i,j]) for j in range(3)] for i in range(3)]
            for j in range(1,n+1):
                powers.append([[v/j for v in row] for row in _mm(powers[-1],Ki)])
            next_coeff=[]
            for j in range(n+1):
                total=zero()
                for h in range(j+1):
                    term=_mm(coeff[h],powers[j-h])
                    total=[[total[a][b]+term[a][b] for b in range(3)] for a in range(3)]
                next_coeff.append(total)
            coeff=next_coeff
        xcoeff=[_dot(self.a,_mv(term,self.c))/self.A for term in coeff]
        self._hcoeff=[-xcoeff[j] for j in range(2,n+1)]
        self._hcenters=[(x.lo+x.hi)/2 for x in self._hcoeff]
        F=self._free_rate
        # For h^(j), j=0,1,2, omitted x terms start at N+1.
        # (n-2)_j/n! <= 1/(n-j)! for n>=j+2; t<=1.
        self._htail=[]
        for j in range(3):
            k=n+1-j
            tail=math.exp(F)*F**(n+1)/math.factorial(k)/abs(self.A)
            self._htail.append(_up(tail))

    def _hjet(self,a,b):
        t=_I(a,b)
        vals=[]
        for derivative in range(3):
            v=_I(0.)
            for k in reversed(range(derivative,len(self._hcoeff))):
                multiplier=math.factorial(k)/math.factorial(k-derivative)
                v=v*t+self._hcoeff[k]*multiplier
            tail=self._htail[derivative]
            vals.append(v+_I(-tail,tail))
        return _Jet(*vals)

    def _beta_flat_value(self,t):
        h=float(np.polynomial.polynomial.polyval(t,self._hcenters))
        if h <= 0:
            raise BridgeUnavailable("DEFLATED_H_NOT_POSITIVE")
        z=t*math.sqrt(h/2)
        if not -1 <= z <= 1:
            raise BridgeUnavailable("DEFLATED_ASIN_DOMAIN")
        return self.beta_sign*2*math.asin(z)

    def q(self,t):
        """Bounded evaluator of the ideal implicit analytic joint curve.

        Finite h coefficients do not define a different mathematical path.
        Their distance from the implicit exact h is explicitly propagated
        in regularity(), and included in all enclosures consumed by CCD.
        """
        t=_time(t)
        if not self.flat_start:
            return super().q(t)
        if t == 0:
            return np.zeros(self.n)
        q=self.reference_q0+t*self.dq
        T=self.target_jet(t)[0]
        beta=self._beta_flat_value(t)
        Rb=self._R(self.dependent[1],beta)
        u,v=Rb@self.c,T@self.c
        up,vp=u-self.a*(self.a@u),v-self.a*(self.a@v)
        alpha=math.atan2(float(self.a@np.cross(up,vp)),float(up@vp))
        residual=(self._R(self.dependent[0],alpha)@Rb).T@T
        vee=np.array([residual[2,1]-residual[1,2],residual[0,2]-residual[2,0],residual[1,0]-residual[0,1]])
        gamma=math.atan2(float(self.c@vee)/2,(float(np.trace(residual))-1)/2)
        for k,v in zip(self.dependent,(alpha,beta,gamma)):
            q[k]=self._unwrap(v,q[k])
        return q

    def _jets(self,a,b):
        a,b=_time(a),_time(b)
        if b<a:
            raise ValueError("reversed interval")
        if (a,b) in self._jets_cache:
            return self._jets_cache[a,b]
        t=_Jet(_I(a,b),1.)
        q=[self.reference_q0[k]+t*self.dq[k] for k in range(self.n)]
        P=[[_Jet(float(i==j)) for j in range(3)] for i in range(3)]
        for k in self.free:
            P=_mm(P,_rotation(self.axes[k],q[k]))
        T=_transpose(P)
        if self.flat_start:
            h=self._hjet(a,b)
            if h.v.lo <= 0:
                raise BridgeUnavailable("DEFLATED_H_POSITIVITY_UNRESOLVED")
            beta=self.beta_sign*2*_asin(t*(h/2).sqrt())
        else:
            x=(_dot(self.a,_mv(T,self.c))-self.B)/self.A
            beta=self.beta_sign*(math.pi/2-_asin(x))
        Rb=_rotation(self.b,beta)
        u,v=_mv(Rb,self.c),_mv(T,self.c)
        up=[u[k]-self.a[k]*_dot(self.a,u) for k in range(3)]
        vp=[v[k]-self.a[k]*_dot(self.a,v) for k in range(3)]
        alpha=_atan2(_dot(self.a,_cross(up,vp)),_dot(up,vp))
        up_norm_lower=(sum(x.v.square() for x in up)).sqrt().lo
        Ra=_rotation(self.a,alpha)
        residual=_mm(_transpose(_mm(Ra,Rb)),T)
        vee=[residual[2][1]-residual[1][2],residual[0][2]-residual[2][0],residual[1][0]-residual[0][1]]
        gamma_y=_dot(self.c,vee)/2
        gamma_x=(sum(residual[k][k] for k in range(3))-1)/2
        gamma=_atan2(gamma_y,gamma_x)
        gamma_radius_lower=(gamma_x.v.square()+gamma_y.v.square()).sqrt().lo
        for k,v in zip(self.dependent,(alpha,beta,gamma)):
            reference=float(self.reference_q0[k]+(a+b)/2*self.dq[k])
            middle=(v.v.lo+v.v.hi)/2
            offset=2*math.pi*round((reference-middle)/(2*math.pi))
            q[k]=v+offset
        self._jets_cache[a,b]=q
        self._chart_meta_cache[a,b]={"alpha_projection_norm_lower":up_norm_lower,
                                    "gamma_atan2_radius_lower":gamma_radius_lower}
        return q

    def _flat_evaluation_error(self,a,b):
        """Propagate finite Taylor evaluation into a rotation closure bound.

        Actual q() uses midpoint coefficient floats. Both that polynomial
        and the ideal analytic h lie inside the coefficient/tail enclosure.
        beta_h <= t / (sqrt(2*h_min)*sqrt(1-z_max**2)).
        alpha_beta <= 1 / ||project_a_perp(Rb*c)||. For gamma, derivatives
        of its atan2 vector have norm <= 4*(1+alpha_beta); dividing by its
        proved radius bounds gamma_beta. Sum of the three angle errors
        bounds the cyclic rotation-product error by telescoping.
        """
        h=self._hjet(a,b)
        coefficient_error=0.; magnitude=0.
        for k,(coefficient,center) in enumerate(zip(self._hcoeff,self._hcenters)):
            coefficient_error=_up(coefficient_error+max(center-coefficient.lo,coefficient.hi-center)*b**k)
            magnitude=_up(magnitude+abs(center)*b**k)
        # Horner's floating arithmetic error is explicit, independently of
        # the general FK/transcendental reference guard.
        gamma_n=(4*len(self._hcoeff)*np.finfo(float).eps)
        horner_error=_up(gamma_n*magnitude/(1-gamma_n))
        h_error=_up(coefficient_error+self._htail[0]+horner_error)
        zmax=b*math.sqrt(h.v.hi/2)
        if h.v.lo<=0 or zmax>=1:
            raise BridgeUnavailable("DEFLATED_EVALUATION_ERROR_DOMAIN_UNRESOLVED")
        beta_error=_up(b*h_error/(math.sqrt(2*h.v.lo)*math.sqrt(1-zmax*zmax)))
        meta=self._chart_meta_cache[a,b]
        p,r=meta["alpha_projection_norm_lower"],meta["gamma_atan2_radius_lower"]
        if p<=0 or r<=0:
            raise BridgeUnavailable("DEFLATED_ERROR_PROPAGATION_DENOMINATOR_UNRESOLVED")
        factor=_up((1+1/p)*(1+4/r))
        return {"h_coefficient_center_error_bound":coefficient_error,
            "h_truncation_error_bound":self._htail[0],"h_horner_error_bound":horner_error,
            "h_evaluation_error_bound":h_error,"beta_evaluation_error_bound":beta_error,
            "angle_error_to_rotation_factor":factor,
            "taylor_factorization_rotation_error_bound":_up(beta_error*factor),**meta}

    def _require(self,a=0.,b=1.):
        proof=self.regularity(a,b)
        if not proof["proven"]:
            raise BridgeUnavailable(proof["reason"])
        return proof

    def regularity(self,a=0.,b=1.):
        a,b=_time(a),_time(b)
        if b<a:
            raise ValueError("reversed interval")
        if (a,b) in self._bound_cache:
            return self._bound_cache[a,b]
        result={"proven":False,"status":"UNCERTAIN","interval":[a,b],
                "reason":"LOCAL_CHART_BOUND_NOT_ESTABLISHED",
                "chart":"DEFLATED_FLAT_HALF_ANGLE" if self.flat_start else "REGULAR_SPHERICAL_INTERVAL_JET"}
        try:
            jets=self._jets(a,b)
            speed=[j.d.magnitude() for j in jets]
            accel=[j.dd.magnitude() for j in jets]
            arithmetic_guard=self.numerical_error*1024*(1+sum(speed)+sum(accel))
            series_error=self._flat_evaluation_error(a,b) if self.flat_start else {}
            guard=_up(arithmetic_guard+series_error.get("taylor_factorization_rotation_error_bound",0.))
            # Bound the symbolic series evaluation, interval arithmetic and
            # the reference libm/FK implementation under the declared guard.
            result.update(proven=True,status="PASS",reason="WHOLE_INTERVAL_LOCAL_CHART_JETS",
                joint_velocity_bounds=[j.d.as_list() for j in jets],
                joint_acceleration_bounds=[j.dd.as_list() for j in jets],
                angular_speed_l1_bound=sum(speed),dependent_acceleration_l1_bound=sum(accel),
                evaluation_error_bound=guard,arithmetic_reference_guard=arithmetic_guard,
                series_evaluation_error=series_error,
                proof_assumptions=["planar fixed unit axes","analytic 3R identity",
                    "outward floating arithmetic with declared libm guard; not formal directed libm"])
            if self.flat_start:
                h=self._hjet(a,b)
                result.update(deflated_h_bounds=h.v.as_list(),deflated_h_prime_bounds=h.d.as_list(),
                    deflated_h_second_bounds=h.dd.as_list(),taylor_order=self.config.taylor_order,
                    taylor_remainder_bounds=self._htail)
        except (BridgeUnavailable,OverflowError,ZeroDivisionError,ValueError) as exc:
            result["reason"]=str(exc)
        self._bound_cache[a,b]=result
        return result

    def joint_bounds(self,a=0.,b=1.):
        self._require(a,b)
        jets=self._jets(a,b)
        mid,h=(a+b)/2,(b-a)/2
        qm=self.q(mid)
        qa,qb=self.q(a),self.q(b)
        # q(mid) and q(endpoints) are evaluators, whereas the jet encloses
        # the ideal analytic curve. Intersections must retain its complete
        # evaluator error, including finite-series truncation propagation.
        guard=max(self.numerical_error*16,
                  self._require(a,b)["evaluation_error_bound"])
        lo,hi=np.empty(self.n),np.empty(self.n)
        for k,j in enumerate(jets):
            lower=max(j.v.lo,qm[k]-j.d.magnitude()*h-guard)
            upper=min(j.v.hi,qm[k]+j.d.magnitude()*h+guard)
            if j.d.lo >= 0:
                lower=max(lower,qa[k]-guard); upper=min(upper,qb[k]+guard)
            elif j.d.hi <= 0:
                lower=max(lower,qb[k]-guard); upper=min(upper,qa[k]+guard)
            # Exact symbolic flat endpoint and a derivative of known sign
            # establish a one-sided bound without a numerical epsilon hole.
            if self.flat_start and a == 0.:
                if j.d.lo >= 0: lower=max(lower,0.)
                if j.d.hi <= 0: upper=min(upper,0.)
            lo[k],hi[k]=lower,upper
        if np.any(lo>hi):
            raise BridgeUnavailable("INCONSISTENT_LOCAL_CHART_ENCLOSURE")
        return lo,hi

    def chord_error_bound(self,panel,a=0.,b=1.):
        """Ideal curved motion versus the chord of numerical endpoints.

        The usual acceleration*(b-a)^2/8 compares the ideal path with its
        ideal endpoint chord. A convex combination of two endpoint errors
        is bounded by their maximum, so add one full evaluator point bound.
        """
        proof=self._require(a,b)
        point_error=proof["evaluation_error_bound"]*max(1.,self.radius(panel))
        return _up(self.curvature_bound(panel,a,b)*(b-a)**2/8+point_error)

    def continuous_closure(self,a=0.,b=1.,tolerance=4e-6,**kwargs):
        if not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError("finite positive closure tolerance required")
        p=self.regularity(a,b)
        bound=p.get("evaluation_error_bound",float("inf"))
        gap=bound*self.radius(self.n-1)
        max_point_error=bound*max(1.,max(self.radius(k) for k in range(self.n)))
        evaluation_safe=max_point_error<=self.config.max_point_evaluation_error
        passed=p["proven"] and max(bound,gap)<=tolerance and evaluation_safe
        reason=p["reason"] if evaluation_safe else "EVALUATOR_ERROR_EXCEEDS_COLLISION_WITNESS_GUARD"
        return {"status":"PASS" if passed else "UNCERTAIN","reason":reason,
            "rotation_upper_bound":bound,"endpoint_gap_upper_bound":gap,
            "continuous_upper_bound":max(bound,gap),"observed_lower_bound":0.,
            "structural_identity":"ideal analytic 3R factorization; flat singularity deflated by 1-x=t^2*h",
            "mathematical_motion":"ideal implicit analytic 3R curve; h=(1-x)/t^2 with its analytic extension at flat",
            "numerical_evaluator":"finite Taylor h evaluation with explicit coefficient/truncation/roundoff propagation" if self.flat_start else "floating analytic 3R evaluation",
            "ideal_vs_evaluator_point_error_bound":max_point_error,
            "maximum_supported_collision_witness_error":self.config.max_point_evaluation_error,
            "collision_witness_guard_compatible":evaluation_safe,
            "regularity":p,"tolerance":tolerance,
            "numeric_scope":"outward floating reference with declared libm guard; not formal interval libm"}

    def exact_closing_hinge_certificate(self,a=0.,b=1.):
        """Structural hinge identity of the ideal motion, with evaluator bounds.

        A small finite-polynomial closure residual cannot establish this
        identity. It follows from the ideal implicit factorization proved
        by the chart. Numeric triangle evaluations carry a separate error
        enclosure in vertex_bounds and the feature chord inflation.
        """
        closure=self.continuous_closure(a,b)
        return {"status":closure["status"],"reason":closure["reason"],
            "identity":"ideal analytic dependent product equals inverse(free product); cyclic seam is exactly invariant",
            "mathematical_motion":closure["mathematical_motion"],
            "numerical_evaluator_is_motion_definition":False,
            "continuous_upper_bound":closure["continuous_upper_bound"],
            "evaluator_point_error_bound":closure["ideal_vs_evaluator_point_error_bound"],
            "evaluator_error_in_joint_vertex_and_chord_bounds":True,
            "numeric_scope":closure["numeric_scope"]}

    def whole_interval_bounds(self,a=0.,b=1.):
        proof=self._require(a,b)
        lo,hi=self.joint_bounds(a,b)
        contacts=[]
        for i,j in itertools.combinations(range(self.n),2):
            il,ih=self.vertex_bounds(i,a,b); jl,jh=self.vertex_bounds(j,a,b)
            # Every barycentric material point's z lies in its triangle's
            # vertex range; this enclosure makes no legal-contact claim.
            contacts.append({"panels":[i,j],"all_material_z_gap_bounds":
                [_down(float(il[:,2].min()-jh[:,2].max())),
                 _up(float(ih[:,2].max()-jl[:,2].min()))],
                "status":"BOUND_ONLY","contact_legal_claimed":False})
        return {"closure":self.continuous_closure(a,b),"angle_bounds":[lo.tolist(),hi.tolist()],
            "velocity_bounds":proof["joint_velocity_bounds"],
            "acceleration_bounds":proof["joint_acceleration_bounds"],
            "contact_bounds":contacts,"sample_extrema_used":False}


class RestrictedLocalChart:
    """A proved parent chart cell normalized to [0,1], including derivatives."""
    motion_kind="DEFLATED_OR_REGULAR_EXACT_LOCAL_CHART_CELL"

    def __init__(self,parent,a,b):
        self.parent,self.a,self.b=parent,float(a),float(b)
        self.m,self.n=parent.m,parent.n
        self.q0,self.q1=parent.q(a),parent.q(b)

    def _t(self,t): return self.a+(self.b-self.a)*_time(t)
    def q(self,t): return self.parent.q(self._t(t))
    def triangle(self,p,t): return self.parent.triangle(p,self._t(t))
    def vertex_bounds(self,p,a=0.,b=1.): return self.parent.vertex_bounds(p,self._t(a),self._t(b))
    def triangle_bounds(self,p,a=0.,b=1.): return self.parent.triangle_bounds(p,self._t(a),self._t(b))
    def joint_bounds(self,a=0.,b=1.): return self.parent.joint_bounds(self._t(a),self._t(b))
    def chord_error_bound(self,p,a=0.,b=1.): return self.parent.chord_error_bound(p,self._t(a),self._t(b))
    def speed_bound(self,p,a=0.,b=1.): return (self.b-self.a)*self.parent.speed_bound(p,self._t(a),self._t(b))
    def acceleration_bound(self,p,a=0.,b=1.): return (self.b-self.a)**2*self.parent.acceleration_bound(p,self._t(a),self._t(b))
    curvature_bound=acceleration_bound
    def continuous_closure(self,a=0.,b=1.,**kwargs): return self.parent.continuous_closure(self._t(a),self._t(b),**kwargs)
    def exact_closing_hinge_certificate(self,a=0.,b=1.): return self.parent.exact_closing_hinge_certificate(self._t(a),self._t(b))
    @property
    def fixed_joint_values(self): return self.parent.fixed_joint_values


class FlatSingularBridgeBuilder:
    """Construct local charts only; unresolved cells fail without fallback."""

    def __init__(self,mechanism,config=None):
        self.m,self.config=mechanism,config or SingularBridgeConfig()

    def _continuation_diagnostics(self,parent):
        """Null-space seeding and high-order/arc-length diagnostics only.

        The chart gives an exact analytic continuation. Its q',q'' jets
        provide second-order predictors; arc length is recorded with an
        interval enclosure, never inferred from chord sums.
        """
        q=parent.q(0.)
        axes=np.array(parent.axes).T
        if parent.flat_start:
            J=axes
        else:
            # Geometry of the exact product Jacobian, computed only for a
            # tangent predictor. It does not establish a continuous bound.
            R=np.eye(3); columns={}
            for k in list(range(1,self.m.n))+[0]:
                columns[k]=R@parent.axes[k]
                R=R@self.m._axis_rotation(parent.axes[k],q[k])
            J=np.column_stack([columns[k] for k in range(self.m.n)])
        _,s,vt=np.linalg.svd(J,full_matrices=True)
        rank=int(np.sum(s>1e-9)); N=vt[rank:].T
        direction=parent.dq.copy(); seed=N@(N.T@direction)
        if np.linalg.norm(seed)>0: seed/=np.linalg.norm(seed)
        try:
            jets=parent._jets(0.,0.)
            tangent=np.array([(j.d.lo+j.d.hi)/2 for j in jets])
            accel=np.array([(j.dd.lo+j.dd.hi)/2 for j in jets])
            speed=float(np.linalg.norm(tangent))
            tunit=tangent/speed if speed>0 else tangent
            # q(s+ds)=q+q_s ds+q_ss ds²/2, with q_ss removing
            # tangential acceleration. This is a construction predictor.
            qss=(accel-tunit*float(tunit@accel))/(speed*speed) if speed>0 else accel
            tangent_residual=float(np.linalg.norm(J@tangent))
        except (BridgeUnavailable,ValueError,ZeroDivisionError):
            tunit,qss,tangent_residual=seed,np.zeros(self.m.n),None
        return {"method":"NULL_SPACE_MODE_SEED_THEN_DEFLATED_ANALYTIC_CONTINUATION",
            "jacobian_rank":rank,"nullity":self.m.n-rank,"singular_values":s.tolist(),
            "null_space_seed":seed.tolist(),"arc_length_unit_tangent":tunit.tolist(),
            "second_order_arc_length_predictor":qss.tolist(),
            "tangent_equation_residual_diagnostic":tangent_residual,
            "arc_length_parameterization_used_for_motion":False,
            "diagnostics_are_certification":False,
            "continuation_representation":"high-order deflated Taylor chart with exponential remainder; regular interval jets"}

    def build_interval(self,q0,q1,index=0):
        if not 0<=int(index)<=8:
            raise ValueError("flat builder is restricted to source intervals 0..8")
        q0,q1=np.asarray(q0,float),np.asarray(q1,float)
        if q0.shape!=(self.m.n,) or q1.shape!=(self.m.n,) or not np.isfinite([q0,q1]).all():
            raise ValueError("finite mechanism angle vectors required")
        parent=LocalChartMotion(self.m,q0,q1,self.config)
        motions,records,failures=[],[],[]
        diagnostic=self._continuation_diagnostics(parent)

        def visit(a,b,depth):
            proof=parent.regularity(a,b)
            reason=proof["reason"]
            if proof["proven"]:
                closure=parent.continuous_closure(a,b,tolerance=self.config.closure_tolerance)
                try:
                    lo,hi=parent.joint_bounds(a,b)
                    strict=bool(np.all(np.where(self.m.signs>0,lo,-hi)>=0.) and
                                np.all(np.maximum(np.abs(lo),np.abs(hi))<=math.pi))
                    if strict and closure["status"]=="PASS":
                        motion=RestrictedLocalChart(parent,a,b)
                        motions.append(motion)
                        bounds=parent.whole_interval_bounds(a,b)
                        v=np.asarray(proof["joint_velocity_bounds"])
                        mins=np.where((v[:,0]<=0)&(v[:,1]>=0),0.,np.minimum(abs(v[:,0]),abs(v[:,1])))
                        maxs=np.maximum(abs(v[:,0]),abs(v[:,1]))
                        records.append({"kind":"FLAT_SINGULAR_DEFLATED_EXACT_CHART" if parent.flat_start else "REGULAR_EXACT_LOCAL_CHART",
                            "source_interval":int(index),"source_parameter_interval":[a,b],
                            "depth":depth,"construction_status":"PASS","exact_seam_claimed":True,
                            "regularity":proof,"closure_certificate":closure,"bounds":bounds,
                            "arc_length_bounds":[_down((b-a)*float(np.linalg.norm(mins))),_up((b-a)*float(np.linalg.norm(maxs)))],
                            "q0":motion.q0.tolist(),"q1":motion.q1.tolist()})
                        return
                    reason="STRICT_SECTOR_NOT_PROVEN" if not strict else closure["reason"]
                except BridgeUnavailable as exc:
                    reason=str(exc)
            if depth>=self.config.max_depth:
                failures.append({"source_parameter_interval":[a,b],"depth":depth,"reason":reason,"regularity":proof})
                return
            mid=(a+b)/2
            visit(a,mid,depth+1);visit(mid,b,depth+1)

        visit(0.,1.,0)
        max_join=0.
        previous=q0
        for motion in motions:
            max_join=max(max_join,float(np.max(abs(previous-motion.q0))))
            previous=motion.q1
        max_join=max(max_join,float(np.max(abs(previous-q1))))
        joined=not failures and bool(motions) and max_join<=self.config.join_tolerance
        if not joined:
            if not failures:
                failures.append({"source_parameter_interval":[0.,1.],"reason":"EXACT_CHART_ENDPOINT_JOIN_NOT_PROVEN","max_join_error":max_join})
            motions=[];records=[]
        return motions,{"source_interval":int(index),"cells":records,
            "continuous_join_passed":bool(joined),"max_join_error":max_join,
            "join_tolerance":self.config.join_tolerance,"construction_status":"PASS" if joined else "UNCERTAIN",
            "failures":failures,"continuation":diagnostic,
            "discrete_certification_used":False,"q_linear_fallback_used":False,
            "discarded_hybrid_attempt":None}