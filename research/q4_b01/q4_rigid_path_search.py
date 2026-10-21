"""Bounded closure-only continuation; never a continuous or physical certificate."""
import math
from collections import defaultdict

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from q4_global_validation import fan_adapter
from q4_cp_candidate import FACE_IDS

TOL = 1e-8
DEFAULT_TARGETS = 33
MAX_CALLS = 300


def _check(cp, mechanism, center, sectors, q, target):
    q = np.asarray(q, dtype=float)
    if q.shape != (mechanism.n,) or not np.all(np.isfinite(q)):
        raise ValueError('FINITE_ANGLE_VECTOR_REQUIRED')
    if not math.isfinite(target) or not 0 <= target <= 1:
        raise ValueError('TARGET_OUT_OF_DOMAIN')
    # Independent propagation: quaternion-derived rotations about fixed material
    # axes, right multiplication. The solver uses world-axis Rodrigues rotations.
    rotations = [np.eye(3)]
    for k in range(1, mechanism.n):
        axis = np.r_[mechanism.rays[k]['unit2'], 0.]
        rotations.append(rotations[-1] @ Rotation.from_rotvec(axis*q[k]).as_matrix())
    axis0 = np.r_[mechanism.rays[0]['unit2'], 0.]
    closed = rotations[-1] @ Rotation.from_rotvec(axis0*q[0]).as_matrix()
    closure = float(Rotation.from_matrix(closed).magnitude())
    solver_closure = float(np.linalg.norm(mechanism.closure_residual(q)))
    origin = np.r_[cp['vertices_coords'][center], 0.]
    copies = defaultdict(list)
    rigid_error = 0.
    for face, sector in zip(cp['faces_vertices'], sectors):
        original = [np.r_[cp['vertices_coords'][v], 0.] for v in face]
        coords = [rotations[sector] @ (p-origin)+origin for p in original]
        for v, p in zip(face, coords):
            copies[v].append(p)
        for i in range(len(face)):
            for j in range(i):
                rigid_error = max(rigid_error, abs(float(np.linalg.norm(coords[i]-coords[j]) - np.linalg.norm(original[i]-original[j]))))
    seam = max((float(np.linalg.norm(a-b)) for values in copies.values() for a in values for b in values), default=0.)
    signed = mechanism.signs*q
    domain = bool(np.all(signed >= -TOL) and np.all(signed <= math.pi+TOL))
    progress = float(np.mean(signed)/math.pi)
    agreement = abs(closure-solver_closure)
    passed = domain and closure <= TOL and seam <= TOL and abs(progress-target) <= TOL and agreement <= TOL and rigid_error <= TOL
    return {'status': 'PASS' if passed else 'FAIL', 'target': float(target),
        'q_rad': q.tolist(), 'progress': progress, 'progress_error': abs(progress-target),
        'closure_rad': closure, 'solver_closure_rad': solver_closure,
        'independent_agreement_rad': agreement, 'shared_vertex_gap_unit': seam,
        'rigid_distance_error_unit': rigid_error, 'angle_domain_valid': domain,
        'strictly_active_creases': int(np.sum(signed > TOL)),
        'face_ids': list(FACE_IDS), 'scope': 'SAMPLED_CONFIGURATION_ONLY'}


def check_configuration(cp, q, target):
    mechanism, center, sectors = fan_adapter(cp)
    return _check(cp, mechanism, center, sectors, q, target)


def _interpolation(cp, mechanism, center, sectors, knots):
    endpoint_failures = [k['target'] for k in knots if _check(cp, mechanism, center, sectors, k['q_rad'], k['target'])['status'] == 'FAIL']
    rows = []
    for left, right in zip(knots, knots[1:]):
        a, b = np.asarray(left['q_rad']), np.asarray(right['q_rad'])
        for fraction in (.25, .5, .75):
            target = (1-fraction)*left['target'] + fraction*right['target']
            row = _check(cp, mechanism, center, sectors, (1-fraction)*a+fraction*b, target)
            row.update({'from_target': left['target'], 'to_target': right['target'], 'fraction': fraction})
            rows.append(row)
    failed = bool(endpoint_failures) or any(r['status'] == 'FAIL' for r in rows)
    return {'definition': 'piecewise linear interpolation in signed crease-angle coordinates',
        'status': 'FAIL' if failed else 'UNKNOWN',
        'continuous_closure': 'FAIL' if failed else 'UNKNOWN', 'failed_knot_targets': endpoint_failures,
        'samples': rows, 'continuous_certificate': False,
        'reason': 'Any failing interior sample refutes this interpolant; finite passing samples cannot certify it.'}


def evaluate_interpolation(cp, knots):
    if len(knots) < 2:
        raise ValueError('AT_LEAST_TWO_KNOTS_REQUIRED')
    mechanism, center, sectors = fan_adapter(cp)
    if any(b['target'] <= a['target'] for a,b in zip(knots, knots[1:])):
        raise ValueError('STRICTLY_INCREASING_TARGETS_REQUIRED')
    for knot in knots:
        _check(cp, mechanism, center, sectors, knot['q_rad'], knot['target'])
    return _interpolation(cp, mechanism, center, sectors, knots)


class _BudgetExceeded(Exception):
    pass


def search(cp, targets=DEFAULT_TARGETS, max_calls=MAX_CALLS):
    if isinstance(targets, bool) or not isinstance(targets, int) or not 3 <= targets <= DEFAULT_TARGETS:
        raise ValueError('TARGET_BUDGET_MUST_BE_3_TO_33')
    if isinstance(max_calls, bool) or not isinstance(max_calls, int) or not 1 <= max_calls <= MAX_CALLS:
        raise ValueError('CALL_BUDGET_MUST_BE_1_TO_300')
    mechanism, center, sectors = fan_adapter(cp)
    sweeps = []
    for direction in ('forward', 'backward'):
        times = np.linspace(0., 1., targets)
        if direction == 'backward':
            times = times[::-1]
        previous = np.full(mechanism.n, times[0]*math.pi)
        previous_t = float(times[0])
        attempts, accepted = [], []
        for target in times:
            target = float(target)
            calls, best_norm = 0, math.inf
            raw = np.clip(previous + (target-previous_t)*math.pi, 1e-10, math.pi-1e-10)
            best = raw.copy()
            def residual(x):
                nonlocal calls, best_norm, best
                if calls >= max_calls:
                    raise _BudgetExceeded()
                calls += 1
                r = np.r_[mechanism.closure_residual(mechanism.signs*x), np.mean(x)/math.pi-target]
                norm = float(np.linalg.norm(r))
                if norm < best_norm:
                    best_norm, best = norm, x.copy()
                return r
            if target in (0., 1.):
                x = np.full(mechanism.n, math.pi*target)
                solver = {'status': 'EXACT_ENDPOINT', 'message': 'Endpoint explicitly checked; not used as evidence for intermediate closure.'}
            else:
                try:
                    fit = least_squares(residual, raw, bounds=(0., math.pi), method='trf',
                        ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=max_calls)
                    x = fit.x
                    solver = {'status': int(fit.status), 'message': fit.message, 'nfev': int(fit.nfev)}
                except _BudgetExceeded:
                    x = best
                    solver = {'status': 'BUDGET_EXHAUSTED', 'message': 'Strict residual-call cap, including finite-difference calls, reached.'}
            checked = _check(cp, mechanism, center, sectors, mechanism.signs*x, target)
            checked.update({'solver': solver, 'residual_calls': calls, 'initial_signed_angles_rad': raw.tolist()})
            attempts.append(checked)
            if checked['status'] == 'PASS':
                accepted.append(checked)
                previous, previous_t = x.copy(), target
        accepted.sort(key=lambda r: r['target'])
        interpolation = _interpolation(cp, mechanism, center, sectors, accepted)
        jumps = [float(np.linalg.norm(np.asarray(b['q_rad'])-a['q_rad'])) for a,b in zip(accepted, accepted[1:])]
        sweeps.append({'direction': direction, 'attempts': attempts, 'accepted_count': len(accepted),
            'rejected_targets': [r['target'] for r in attempts if r['status'] != 'PASS'],
            'all_requested_knots_close': len(accepted) == targets,
            'endpoint_coverage': [accepted[0]['target'], accepted[-1]['target']],
            'max_knot_jump_rad_l2': max(jumps, default=0.), 'interpolation': interpolation})
    return {'schema_version': 'q4-rigid-search-1.0', 'task_id': 'Q4-B01-ALTERNATIVE-RIGID-PATH',
        'angle_index_to_original_edge_id': [f'E_Q4_MM_{r["edge"]:02d}' for r in mechanism.rays],
        'angle_signs': mechanism.signs.tolist(), 'face_to_sector': dict(zip(FACE_IDS, sectors)),
        'settings': {'targets_per_sweep': targets, 'max_residual_calls_per_solve': max_calls,
            'directions': ['forward','backward'], 'randomness': 'none', 'tolerance': TOL,
            'progress_definition': 'mean(sign_k*q_k)/pi', 'solver': 'scipy least_squares trf; ftol=xtol=gtol=1e-12',
            'residual_definition': '[existing solver closure rotvec (3), mean(signed angles)/pi-target]',
            'initial_guess': 'previous accepted signed angles plus pi*delta_target; clipped strictly inside [0,pi]',
            'acceptance': 'independent quaternion closure + full original polygon seams/rigidity + M/V domain + progress; solver status alone is insufficient'},
        'sweeps': sweeps, 'global_foldability': 'UNKNOWN', 'continuous_rigid_path': 'UNKNOWN',
        'collision': 'UNKNOWN', 'contact': 'UNKNOWN', 'signed_gap': 'UNKNOWN', 'layer_order': 'UNKNOWN',
        'final_semantic_material_flow': 'UNKNOWN', 'physical_verified': False,
        'claim': 'Numerical configurations and explicitly tested interpolants only; no CP infeasibility or continuous-path certificate.'}
