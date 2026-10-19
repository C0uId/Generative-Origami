"""Scoped Q4 checks: local necessary conditions and a falsifiable motion probe.

No search-completeness, collision, contact, layer-order or physical certificate.
The existing single-vertex solver is used only for rotations/closure, never its
short-ray triangle collision proxy in place of the full Q4 material polygons.
"""
from collections import defaultdict
from fractions import Fraction
import copy
import math

import numpy as np

from base_intake import inspect
from q4_base import import_cp
from q4_cp_candidate import FACE_IDS
from generative_origami.simulation.single_vertex import SingleVertexMechanism

ANGLE_TOLERANCE_DEG = 1e-8
CLOSURE_TOLERANCE_RAD = 1e-8
SEAM_TOLERANCE_UNIT = 1e-8
SAMPLE_TIMES = tuple(i / 8 for i in range(9))


def local_vertex_checks(cp):
    """Measure sectors from coordinates at every non-boundary vertex.

    Kawasaki/Maekawa are necessary conditions for all incident M/V creases to
    be active in a flat fold. Degree-two collinear subdivisions are included.
    A failure here is not a proof against every possible partially active fold.
    """
    boundary = {v for edge, a in zip(cp['edges_vertices'], cp['edges_assignment'])
                if a == 'B' for v in edge}
    result = []
    for vi, p in enumerate(cp['vertices_coords']):
        if vi in boundary:
            continue
        incident = [i for i, e in enumerate(cp['edges_vertices']) if vi in e]
        assignments = [cp['edges_assignment'][i] for i in incident]
        angles = []
        for ei in incident:
            a, b = cp['edges_vertices'][ei]
            q = cp['vertices_coords'][b if a == vi else a]
            if math.dist(p, q) <= 1e-14:
                raise ValueError('ZERO_LENGTH_INCIDENT_EDGE')
            angles.append(math.degrees(math.atan2(q[1]-p[1], q[0]-p[0])) % 360)
        angles.sort()
        sectors = [(angles[(k+1) % len(angles)]-a) % 360
                   for k, a in enumerate(angles)]
        supported = len(angles) >= 2 and all(a in ('M', 'V') for a in assignments)
        even = len(angles) % 2 == 0
        sums = [sum(sectors[::2]), sum(sectors[1::2])]
        kawasaki = supported and even and all(abs(s-180) <= ANGLE_TOLERANCE_DEG for s in sums)
        difference = abs(assignments.count('M')-assignments.count('V'))
        maekawa = supported and difference == 2
        result.append({'vertex_id': f'V_Q4_MM_{vi:02d}', 'vertex_index': vi,
            'incident_edges': incident, 'degree': len(incident),
            'sector_angles_deg': sectors, 'alternating_sums_deg': sums,
            'mountain_count': assignments.count('M'), 'valley_count': assignments.count('V'),
            'maekawa_difference': difference,
            'kawasaki': ('PASS' if kawasaki else 'FAIL') if supported else 'UNKNOWN',
            'maekawa': ('PASS' if maekawa else 'FAIL') if supported else 'UNKNOWN',
            'scope': 'NECESSARY_LOCAL_ALL_ACTIVE_FLAT_FOLD_ONLY'})
    return result


def fan_adapter(cp, face_ids=FACE_IDS):
    """Prove the supported radial fan contract, retaining full material faces.

    The solver requires the central vertex at array index zero. Other interior
    vertices must be collinear degree-two subdivisions with identical M/V on
    both segments. Every face must occupy exactly one complete radial sector.
    This adapter does not silently accept a general multi-vertex mechanism.
    """
    planar = inspect(cp)
    if not planar['passed']:
        raise ValueError('PLANAR_GATE_FAILED')
    boundary = {v for e, a in zip(cp['edges_vertices'], cp['edges_assignment']) if a == 'B' for v in e}
    interior = set(range(len(cp['vertices_coords']))) - boundary
    degree = {v: sum(v in e for e in cp['edges_vertices']) for v in interior}
    centers = [v for v in interior if degree[v] > 2]
    if len(centers) != 1:
        raise ValueError('ONE_BRANCHING_VERTEX_REQUIRED')
    center = centers[0]
    origin = np.asarray(cp['vertices_coords'][center], float)
    for vi in interior - {center}:
        incident = [i for i, e in enumerate(cp['edges_vertices']) if vi in e]
        if len(incident) != 2:
            raise ValueError('DEGREE_TWO_SUBDIVISION_REQUIRED')
        vectors = []
        for i in incident:
            e = cp['edges_vertices'][i]
            other = e[1] if e[0] == vi else e[0]
            vectors.append(np.asarray(cp['vertices_coords'][other])-cp['vertices_coords'][vi])
        a, b = vectors
        if abs(float(a[0]*b[1]-a[1]*b[0])) > 1e-12 or float(a @ b) >= 0:
            raise ValueError('COLLINEAR_SUBDIVISION_REQUIRED')
        labels = [cp['edges_assignment'][i] for i in incident]
        if labels[0] != labels[1] or labels[0] not in ('M', 'V'):
            raise ValueError('SUBDIVISION_MV_MISMATCH')
    order = [center] + [v for v in range(len(cp['vertices_coords'])) if v != center]
    inverse = {old: new for new, old in enumerate(order)}
    adapted = copy.deepcopy(cp)
    adapted['vertices_coords'] = [cp['vertices_coords'][v] for v in order]
    adapted['edges_vertices'] = [[inverse[v] for v in e] for e in cp['edges_vertices']]
    adapted['faces_vertices'] = [[inverse[v] for v in f] for f in cp['faces_vertices']]
    mechanism = SingleVertexMechanism(adapted)
    if len(face_ids) != len(cp['faces_vertices']) or len(set(face_ids)) != len(face_ids):
        raise ValueError('UNIQUE_STABLE_FACE_IDS_REQUIRED')
    if mechanism.n != len(cp['faces_vertices']):
        raise ValueError('ONE_FACE_PER_SECTOR_REQUIRED')
    sectors = []
    for face in cp['faces_vertices']:
        if center not in face:
            raise ValueError('FAN_FACE_MUST_CONTAIN_CENTER')
        centroid = np.mean([cp['vertices_coords'][v] for v in face if v != center], axis=0)-origin
        angle = math.atan2(centroid[1], centroid[0]) % (2*math.pi)
        matches = []
        for k, ray in enumerate(mechanism.rays):
            width = (mechanism.rays[(k+1) % mechanism.n]['angle']-ray['angle']) % (2*math.pi)
            if 0 < (angle-ray['angle']) % (2*math.pi) < width:
                offsets = []
                for v in face:
                    delta = np.asarray(cp['vertices_coords'][v])-origin
                    if np.linalg.norm(delta) > 1e-14:
                        offset = (math.atan2(delta[1], delta[0])-ray['angle']) % (2*math.pi)
                        if abs(offset-2*math.pi) < 1e-10:
                            offset = 0.
                        offsets.append(offset)
                if any(o > width+1e-10 for o in offsets):
                    raise ValueError('FACE_CROSSES_SECTOR')
                if min(offsets) > 1e-10 or abs(max(offsets)-width) > 1e-10:
                    raise ValueError('FACE_DOES_NOT_SPAN_SECTOR')
                matches.append(k)
        if len(matches) != 1:
            raise ValueError('AMBIGUOUS_FACE_SECTOR')
        sectors.append(matches[0])
    if len(set(sectors)) != mechanism.n:
        raise ValueError('DUPLICATE_FACE_SECTOR')
    return mechanism, center, sectors


def motion_probe(cp, face_ids=FACE_IDS):
    """Test q_k(t)=sign_k*pi*t; a failing sample disproves THIS exact path.

    Passing finitely many samples would still return UNKNOWN for a continuous
    path. Failure does not prove the CP has no alternative rigid folding path.
    """
    try:
        mechanism, center, sectors = fan_adapter(cp, face_ids)
    except ValueError as exc:
        return {'status': 'UNKNOWN', 'reason': str(exc), 'samples': [],
                'global_foldability': 'UNKNOWN', 'continuous_motion_certified': False}
    origin = np.r_[cp['vertices_coords'][center], 0.]
    rows = []
    for t in SAMPLE_TIMES:
        q = mechanism.signs * (math.pi*t)
        rotations = mechanism.panel_rotations(q)
        copies = defaultdict(list)
        full_faces = []
        for face_id, face, sector in zip(face_ids, cp['faces_vertices'], sectors):
            coords = []
            for v in face:
                p = rotations[sector] @ (np.r_[cp['vertices_coords'][v], 0.]-origin) + origin
                copies[v].append(p)
                coords.append([round(float(x), 12) for x in p])
            full_faces.append({'face_id': face_id, 'vertex_indices': face, 'vertices_coords': coords})
        seam = max((float(np.linalg.norm(p-q)) for points in copies.values()
                    for p in points for q in points), default=0.)
        closure = float(np.linalg.norm(mechanism.closure_residual(q)))
        good = closure <= CLOSURE_TOLERANCE_RAD and seam <= SEAM_TOLERANCE_UNIT
        rows.append({'t': t, 'status': 'PASS' if good else 'FAIL',
            'closure_residual_rad': round(closure, 12), 'max_shared_vertex_gap_unit': round(seam, 12),
            'fold_angles_rad': [round(float(x), 12) for x in q], 'full_faces': full_faces})
    failed = [r['t'] for r in rows if r['status'] == 'FAIL']
    return {'status': 'FAIL' if failed else 'UNKNOWN',
        'definition': 'q_k(t) = sign_k * pi * t, t in [0,1]; V=+1, M=-1',
        'scope': 'ONE_DEFINED_UNIFORM_ANGLE_PATH_ONLY_NOT_CP_INFEASIBILITY',
        'solver': 'generative_origami.simulation.single_vertex.SingleVertexMechanism',
        'adapter': {'center_original_index': center, 'solver_center_index': 0,
                    'face_to_sector': dict(zip(face_ids, sectors)), 'degree': mechanism.n},
        'closure_tolerance_rad': CLOSURE_TOLERANCE_RAD,
        'seam_tolerance_unit': SEAM_TOLERANCE_UNIT,
        'failed_sample_times': failed, 'samples': rows,
        'global_foldability': 'UNKNOWN', 'continuous_motion_certified': False,
        'collision': 'UNKNOWN', 'contact': 'UNKNOWN', 'layer_order': 'UNKNOWN',
        'reason': 'Nonzero closure/seam counterexample to the tested path.' if failed else
                  'Finite samples cannot certify the continuous interval.'}


def validation_report(cp, face_ids=FACE_IDS):
    planar = inspect(cp)
    if not planar['passed']:
        raise ValueError('PLANAR_GATE_FAILED')
    local = local_vertex_checks(cp)
    motion = motion_probe(cp, face_ids)
    mapped = import_cp(cp, face_ids)
    totals = defaultdict(Fraction)
    for face in mapped['face_material_map']:
        for part in face['material_parts']:
            totals[part['material_id']] += Fraction(part['area_mm2_exact'])
    return {'schema_version': 'q4-global-validation-1.0',
        'task_id': 'Q4-B01-GLOBAL-VALIDATION', 'seed': 0,
        'cp_geometry_sha256': planar['geometry_sha256'],
        'cp_topology_sha256': planar['topology_sha256'],
        'planar': planar, 'local_vertices': local,
        'local_scope': 'ALL_INTERIOR_VERTICES; boundary vertices excluded from interior theorems',
        'motion_probe': motion,
        'material_traceability': {'planar_ownership': 'PASS',
            'face_material_map': mapped['face_material_map'],
            'total_area_mm2_exact': {k: str(v) for k, v in sorted(totals.items())},
            'probe_rigid_face_ids_preserved': bool(motion['samples']),
            'assembled_folded_material_flow': 'UNKNOWN',
            'scope': 'Full original polygons retain face/material IDs under per-face rigid rotations; '
                     'nonclosing trial is not an assembled physical folded model.'},
        'global_foldability': 'UNKNOWN', 'physical_verified': False,
        'continuous_motion_verified': False,
        'claim_boundary': 'SCOPED_GLOBAL_ASSESSMENT_NOT_PHYSICAL_BASE',
        'unresolved': ['Alternative globally closing rigid path has not been established.',
            'Collision, contact, signed gaps and layer order are UNKNOWN.',
            'Final semantic material flow is UNKNOWN.',
            'No validated human folding sequence or physical refolds exist.',
            'At least two independent successful refolds are needed before physical certification.']}
