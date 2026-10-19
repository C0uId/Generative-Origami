"""Whole-time pair proofs in a panel's moving material frame.

The common left FK product cancels *algebraically*, before bounding angles.
The relative product keeps every original axis distinct.  A successful LP
merely proposes a plane: interval inequalities, not its sampled objective,
decide whether it separates the complete continuous motion.

The induced-hinge rule has one varying rotation and fixed goal rotations on
either side.  Fixed +/-pi rotations are represented by their planar
reflection identity.  For 0<|q|<pi the planes meet only on that actual axis;
every material point on the axis is fixed by the varying rotation, including
at its goal value.  At |q|=pi finite overlap is exactly the goal relative
material patch.  No almost-coincident axes are identified with each other.

Like the other research backends, interval operations use outward float64
rounding plus declared libm guards, not a formally verified interval libm.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.optimize import linprog

from .layer_contact import LayerContactModel, _barycentric, _convex_clip, _poly_area


def _out(lo, hi, padding=0.):
    return np.nextafter(np.asarray(lo)-padding, -np.inf), np.nextafter(np.asarray(hi)+padding, np.inf)


def _mul(al, ah, bl, bh):
    values = np.asarray([al*bl, al*bh, ah*bl, ah*bh])
    return _out(values.min(axis=0), values.max(axis=0))


def _matmul(al, ah, bl, bh):
    al, ah, bl, bh = map(np.asarray, (al, ah, bl, bh))
    low, high = np.zeros((al.shape[0], bl.shape[1])), np.zeros((al.shape[0], bl.shape[1]))
    for k in range(al.shape[1]):
        lo, hi = _mul(al[:, k, None], ah[:, k, None], bl[None, k, :], bh[None, k, :])
        low, high = _out(low+lo, high+hi)
    return low, high


def _sin_interval(a, b, guard):
    if b-a >= 2*math.pi:
        return -1., 1.
    values = [math.sin(a), math.sin(b)]
    for k in range(math.ceil((a-math.pi/2)/math.pi), math.floor((b-math.pi/2)/math.pi)+1):
        values.append(1. if k % 2 == 0 else -1.)
    return max(-1., float(np.nextafter(min(values)-guard, -np.inf))), min(1., float(np.nextafter(max(values)+guard, np.inf)))


def _rotation_bounds(axis, low, high, guard):
    axis = np.asarray(axis, float)
    axis = axis/np.linalg.norm(axis)
    x, y, z = axis
    cross = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
    base = np.outer(axis, axis)
    cos_part = np.eye(3)-base
    sl, sh = _sin_interval(low, high, guard)
    cl, ch = _sin_interval(low+math.pi/2, high+math.pi/2, guard*2)
    asl, ash = _mul(cross, cross, sl, sh)
    acl, ach = _mul(cos_part, cos_part, cl, ch)
    return _out(base+asl+acl, base+ash+ach, guard*4)


def _local_triangles(mechanism):
    return np.asarray([np.vstack([np.zeros(3), np.r_[mechanism.rays[p]['point2'], 0.],
        np.r_[mechanism.rays[(p+1) % mechanism.n]['point2'], 0.]]) for p in range(mechanism.n)])


def _time(a, b):
    a, b = float(a), float(b)
    if not math.isfinite(a+b) or not 0 <= a <= b <= 1:
        raise ValueError('expected finite 0 <= a <= b <= 1')
    return a, b


class RelativeContactSeparation:
    """Additional conservative pair proofs, with no pair-name whitelist.

    A failed proof returns UNCERTAIN and may be passed to general CCD.  The
    module does not replace the independent layer/material-gap gate.
    """
    def __init__(self, mechanism, *, layer_order=None, numerical_error=1e-12, material_tolerance=3e-5):
        self.m = mechanism
        self.n = mechanism.n
        self.guard = float(numerical_error)
        self.material_tolerance = float(material_tolerance)
        if not (math.isfinite(self.guard) and self.guard > 0 and
                math.isfinite(self.material_tolerance) and self.material_tolerance >= 0):
            raise ValueError('finite positive arithmetic guard and nonnegative material tolerance required')
        self.local = _local_triangles(mechanism)
        self.axes = np.asarray([np.r_[r['unit2'], 0.] for r in mechanism.rays])
        self.axes /= np.linalg.norm(self.axes, axis=1)[:, None]
        self.order = list(layer_order if layer_order is not None else [7, 6, 5, 0, 4, 1, 3, 2])
        if sorted(self.order) != list(range(self.n)):
            raise ValueError('layer order must be a permutation of every panel')
        self.rank = {panel: k for k, panel in enumerate(self.order)}
        edges = LayerContactModel(mechanism)._adjacent_order_edges()
        if not (all(self.rank[x] < self.rank[y] for x, y in edges) or
                all(self.rank[x] > self.rank[y] for x, y in edges)):
            raise ValueError('layer order contradicts M/V adjacency')
        goal = np.asarray(mechanism.panel_triangles(mechanism.goal))
        self.patches = {}
        for i, j in itertools.combinations(range(self.n), 2):
            polygon = _convex_clip(goal[i, :, :2], goal[j, :, :2])
            if len(polygon) < 3 or abs(_poly_area(polygon)) <= 1e-12:
                continue
            coordinates = []
            for point in polygon:
                if np.array_equal(point, np.zeros(2)):
                    wi = wj = np.array([1., 0., 0.])
                else:
                    wi, wj = _barycentric(point, goal[i, :, :2]), _barycentric(point, goal[j, :, :2])
                coordinates.append([wi.tolist(), wj.tolist()])
            reconstruction = max(float(np.linalg.norm(np.asarray(wi)@goal[i]-np.asarray(wj)@goal[j])) for wi, wj in coordinates)
            containment = min(float(min(np.min(wi), np.min(wj))) for wi, wj in coordinates)
            if reconstruction <= 1e-9 and containment >= -1e-9:
                self.patches[i, j] = {'material_coordinates': coordinates,
                    'patch_vertex_count': len(coordinates),
                    'material_mapping_error_diagnostic': reconstruction,
                    'minimum_barycentric_coordinate': containment,
                    'finite_patch_definition': 'intersection of the two finite triangles in their goal relative pose',
                    'polygon_scope': 'conditional float64 polygon diagnostics; halfplane layer proof covers the entire containing triangle'}

    def _pair(self, pair):
        i, j = tuple(pair)
        if not (isinstance(i, (int, np.integer)) and isinstance(j, (int, np.integer))
                and 0 <= i < j < self.n):
            raise ValueError('expected ordered distinct panel pair')
        return int(i), int(j)

    def _chains(self, motion, pair, a, b):
        i, j = self._pair(pair)
        yield i, j, list(range(i+1, j+1)), False
        exact = getattr(motion, 'exact_closing_hinge_certificate', None)
        proof = exact(a, b) if callable(exact) else None
        if proof and proof.get('status') == 'PASS':
            yield j, i, list(range(j+1, self.n))+[0]+list(range(1, i+1)), True

    def _relative(self, angles, chain):
        product = np.eye(3)
        for k in chain:
            product = product @ self.m._axis_rotation(self.axes[k], float(angles[k]))
        return product

    def relative_vertex_bounds(self, motion, pair, a=0., b=1., *, complement=False):
        """Bounds on target vertices in the anchor's moving material frame.

        The complement is available only when an exact cyclic-product
        identity was supplied by the motion, not a finite closure residual.
        """
        a, b = _time(a, b)
        choices = [x for x in self._chains(motion, pair, a, b) if x[3] == complement]
        if not choices:
            return None
        anchor, target, chain, cyclic = choices[0]
        low, high = map(np.asarray, motion.joint_bounds(a, b))
        if (low.shape != (self.n,) or high.shape != (self.n,) or
                not np.isfinite(low).all() or not np.isfinite(high).all() or np.any(low > high)):
            return None
        rl = rh = np.eye(3)
        for k in chain:
            al, ah = _rotation_bounds(self.axes[k], float(low[k]), float(high[k]), self.guard)
            rl, rh = _matmul(rl, rh, al, ah)
        vl, vh = _matmul(rl, rh, self.local[target].T, self.local[target].T)
        # The common material origin is exact; no radius around it is removed.
        vl[:, 0] = vh[:, 0] = 0.
        return {'anchor': anchor, 'target': target, 'chain': chain,
                'uses_exact_cyclic_closure': cyclic, 'lower': vl.T, 'upper': vh.T}

    def cone_certificate(self, motion, pair, a=0., b=1.):
        """Constant plane in a *moving* panel frame, verified for all time."""
        a, b = _time(a, b)
        i, j = self._pair(pair)
        for anchor, target, chain, cyclic in self._chains(motion, pair, a, b):
            bounds = self.relative_vertex_bounds(motion, pair, a, b, complement=cyclic)
            if bounds is None:
                continue
            A = self.local[anchor, 1:]
            B = self.local[target, 1:] @ self._relative(motion.q((a+b)/2), chain).T
            vectors = np.vstack([A/np.linalg.norm(A, axis=1)[:, None],
                                 -B/np.linalg.norm(B, axis=1)[:, None]])
            proposal = linprog([0., 0., 0., -1.], A_ub=np.c_[-vectors, np.ones(4)],
                b_ub=np.zeros(4), bounds=[(-1., 1.)]*3+[(0., 3.)], method='highs')
            if not proposal.success or proposal.x[-1] <= 100*self.guard:
                continue
            normal = proposal.x[:3]/np.linalg.norm(proposal.x[:3])
            # Floating products for the static triangle receive an explicit
            # guard too; the LP optimum is never accepted directly.
            positive = float(np.min(A@normal))-self.guard*100
            lo, hi = bounds['lower'][1:], bounds['upper'][1:]
            negative = np.sum(np.where(normal >= 0., normal*hi, normal*lo), axis=1)
            margin = min(positive, -float(np.max(negative))-self.guard*100)
            if margin > 100*self.guard:
                return {'status': 'PASS', 'reason': 'RELATIVE_FRAME_CONTINUOUS_SEPARATION',
                    'panels': [i, j], 'time_interval': [a, b], 'anchor': anchor,
                    'relative_chain': chain, 'uses_exact_cyclic_closure': cyclic,
                    'normal_in_anchor_material_frame': normal.tolist(),
                    'margin_lower_bound': margin, 'per_vertex_upper_bounds': negative.tolist(),
                    'allowed_contact': 'same exact material origin only',
                    'whole_panel_exemption': False, 'layer_order_gate_proven': True,
                    'layer_proof': {'status': 'PASS', 'basis': 'strict separation of all noncentral rays; only the common material origin can contact'},
                    'material_proof': {'status': 'PASS', 'allowed_set': 'the exact common material origin'},
                    'sampled_plane_used_as_proof': False,
                    'proof_basis': 'algebraic common-left-product cancellation and interval Rodrigues product',
                    'numeric_scope': 'conditional outward float64 reference with declared libm guards'}
        return {'status': 'UNCERTAIN', 'reason': 'RELATIVE_FRAME_CONE_SEPARATION_NOT_PROVEN',
                'panels': [i, j], 'time_interval': [a, b]}

    def _reflection(self, k):
        """Exact pi identity in the original axis, with no axis merging."""
        unit = self.axes[k, :2]
        value = np.zeros((3, 3))
        value[:2, :2] = 2*np.outer(unit, unit)-np.eye(2)
        value[2, 2] = -1.
        return value

    def induced_hinge_certificate(self, motion, pair, a=0., b=1.):
        a, b = _time(a, b)
        i, j = self._pair(pair)
        fixed = np.asarray(getattr(motion, 'fixed_joint_values', np.full(self.n, np.nan)))
        low, high = map(np.asarray, motion.joint_bounds(a, b))
        if (fixed.shape != (self.n,) or low.shape != (self.n,) or high.shape != (self.n,)
                or not np.isfinite(low).all() or not np.isfinite(high).all() or np.any(low > high)):
            return {'status': 'UNCERTAIN', 'reason': 'INDUCED_HINGE_ANGLE_BOUNDS_UNAVAILABLE', 'panels': [i, j]}
        rejections = []
        for anchor, target, chain, cyclic in self._chains(motion, pair, a, b):
            # Goal cyclic closure is not exact in the finite input geometry.
            # An exact identity on the candidate curve does not silently make
            # that input goal identity exact too. Keep this rule forward-only.
            if cyclic:
                continue
            varying = [k for k in chain if not (np.isfinite(fixed[k]) and fixed[k] == self.m.goal[k])]
            if len(varying) != 1:
                continue
            joint = varying[0]
            sign = float(self.m.signs[joint])
            signed_low, signed_high = sorted((sign*float(low[joint]), sign*float(high[joint])))
            if not 0. < signed_low <= signed_high <= math.pi:
                rejections.append('ANGLE_RANGE_CONTAINS_UNFOLDED_COPLANAR_STATE_OR_LEAVES_SECTOR')
                continue
            at = chain.index(joint)
            before, after = np.eye(3), np.eye(3)
            for k in chain[:at]:
                if abs(fixed[k]) != math.pi:
                    break
                before = before@self._reflection(k)
            else:
                for k in chain[at+1:]:
                    if abs(fixed[k]) != math.pi:
                        break
                    after = after@self._reflection(k)
                else:
                    # Finite material sets in the one-axis reference frame.
                    # They retain all original vertices and all distinct axes.
                    A, B = self.local[anchor]@before, self.local[target]@after.T
                    goal_relative = self._relative(self.m.goal, chain)
                    actual_goal = self.m.panel_rotations(self.m.goal)
                    declared_relative = actual_goal[anchor].T@actual_goal[target]
                    mismatch = float(np.linalg.norm(goal_relative-declared_relative, ord='fro'))
                    mapping_bound = mismatch*float(np.linalg.norm(self.local[target], axis=1).max())
                    mapping_bound += self.guard*1000*(len(chain)+1)
                    if mapping_bound > self.material_tolerance:
                        rejections.append('INDUCED_HINGE_GOAL_MATERIAL_MAP_NOT_PROVEN')
                        continue
                    patch = self.patches.get((i, j))
                    if patch is None:
                        rejections.append('FINITE_GOAL_MATERIAL_PATCH_UNAVAILABLE')
                        continue
                    layer = self._induced_layer_halfplane(pair, joint, before, after, chain, at, sign)
                    if layer['status'] != 'PASS':
                        rejections.append('INDUCED_HINGE_LAYER_APPROACH_NOT_PROVEN')
                        continue
                    # All point intersections in noncoplanar states lie on
                    # this actual axis, which is invariant under both q and
                    # q_goal. Thus the same two material points coincide at
                    # goal; no barycentric sampling or endpoint inference.
                    return {'status': 'PASS', 'reason': 'ANALYTIC_INDUCED_MATERIAL_HINGE',
                        'panels': [i, j], 'time_interval': [a, b], 'anchor': anchor,
                        'relative_chain': chain, 'varying_joint': joint,
                        'uses_exact_cyclic_closure': cyclic,
                        'signed_angle_range': [signed_low, signed_high],
                        'fixed_goal_joints': [k for k in chain if k != joint],
                        'axis_in_factored_frame': self.axes[joint].tolist(),
                        'factored_material_triangles': [A.tolist(), B.tolist()],
                        'allowed_interior_contact': 'finite triangle intersections on the invariant actual rotation axis',
                        'endpoint_contact': 'only goal-angle finite overlap; unfolded angle zero excluded',
                        'material_mapping': 'axis points invariant under the same varying and goal rotation',
                        'goal_material_mapping_error_upper_bound': mapping_bound,
                        'goal_cyclic_defect_propagated': cyclic,
                        'distinct_original_axes_retained': True,
                        'layer_order': [self.rank[i], self.rank[j]],
                        'layer_order_gate_proven': True,
                        'layer_proof': layer,
                        'material_proof': {'status': 'PASS', 'basis': 'same forward subchain at the declared goal; invariant material points on the actual axis', **patch},
                        **patch,
                        'whole_panel_exemption': False,
                        'numeric_scope': 'analytic plane/axis identity; conditional float64 finite material-map guard'}
        return {'status': 'UNCERTAIN', 'reason': 'SINGLE_VARYING_ROTATION_WITH_FIXED_GOAL_SUBCHAIN_NOT_PROVEN',
            'panels': [i, j], 'time_interval': [a, b], 'rejections': rejections}

    def _induced_layer_halfplane(self, pair, joint, before, after, chain, at, sign):
        """Prove the signed approach on a containing finite triangle.

        In the common moving frame, the goal normal has the exact z parity
        (-1)^i.  For a goal-paired point x=R(pi)y, the signed gap is
        -rank_sign*(-1)^i*sin(q)*(before@(axis cross y))_z. Equivalently it
        uses +rank_sign*(-1)^i*sin(q)*(before@(axis cross x))_z.
        If either entire containing material triangle has nonnegative linear
        coefficient, its finite overlap patch does too. An indexed original
        crease endpoint is an algebraic zero; no near-zero is rounded to zero.
        """
        i, j = pair
        rank_sign = 1. if self.rank[i] > self.rank[j] else -1.
        parity = (-1.)**i
        factor = rank_sign*parity*sign
        attempts = []
        for which in ('anchor', 'target'):
            if which == 'anchor':
                values = self.local[i]@before
                coefficients = factor*(np.cross(self.axes[joint], values)@before.T)[:, 2]
                # before is empty: an original boundary ray has exactly the
                # same axis by crease index, independent of FP normalization.
                structural_axis = (at == 0)
                panel = i
            else:
                values = self.local[j]@after.T
                coefficients = -factor*(np.cross(self.axes[joint], values)@before.T)[:, 2]
                structural_axis = (at == len(chain)-1)
                panel = j
            lower = []
            symbolic_zeros = [0]
            for vertex, value in enumerate(coefficients):
                ray_index = panel if vertex == 1 else (panel+1) % self.n if vertex == 2 else None
                if vertex == 0 or (structural_axis and ray_index == joint):
                    lower.append(0.)
                    if vertex:
                        symbolic_zeros.append(vertex)
                else:
                    lower.append(float(np.nextafter(value-self.guard*1000*(len(chain)+1), -np.inf)))
            attempts.append({'triangle': which, 'coefficient_lower_bounds': lower,
                             'diagnostic_coefficients': coefficients.tolist(),
                             'symbolic_zero_vertices': symbolic_zeros})
            if min(lower) >= 0. and any(x > 0. for x in lower):
                return {'status': 'PASS', 'basis': 'affine signed-gap coefficient nonnegative on an entire containing finite triangle',
                    'signed_gap_lower_bound': 0., 'coefficient_lower_bounds': lower,
                    'containing_triangle': which, 'containing_panel': panel,
                    'symbolic_zero_vertices': symbolic_zeros,
                    'zero_basis': 'exact origin and same original crease index, never a near-coincident axis',
                    'rank_sign': rank_sign, 'goal_anchor_normal_z_parity': parity,
                    'sin_angle_sign': sign,
                    'signed_gap_formula': 'rank_sign * goal_anchor_normal_z * (pi_z-pj_z); sine has the declared M/V sign; goal endpoint sine is exactly zero',
                    'frame_scope': 'material frame transported from the flat-folded goal; common left rigid rotation cancels',
                    'whole_interval': True, 'goal_material_patch_subset_of_proved_triangle': True}
        return {'status': 'UNCERTAIN', 'reason': 'FINITE_PATCH_LAYER_APPROACH_COEFFICIENT_NOT_PROVEN', 'attempts': attempts}

    def certify_pair(self, motion, pair, a=0., b=1.):
        hinge = self.induced_hinge_certificate(motion, pair, a, b)
        if hinge['status'] == 'PASS':
            return hinge
        return self.cone_certificate(motion, pair, a, b)


def certify_material_pair(mechanism, motion, pair, *, layer_order=None, a=0., b=1.):
    """Small hook used by ContactChartMotion; independent of sampled frames."""
    cache = getattr(motion, '_relative_contact_separation', None)
    order = list(layer_order if layer_order is not None else [7, 6, 5, 0, 4, 1, 3, 2])
    if cache is None or cache.m is not mechanism or cache.order != order:
        cache = RelativeContactSeparation(mechanism, layer_order=order)
        try:
            motion._relative_contact_separation = cache
        except (AttributeError, TypeError):
            pass
    return cache.certify_pair(motion, pair, a, b)
