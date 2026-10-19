"""Strict unit-square planar CP intake, not a foldability certificate.

Coordinates are checked exactly as the decimal values stored in JSON.
Scope: simple CCW faces, no cuts, coincident vertices or unassigned creases.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def orient(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])

def on_segment(a, b, p):
    return orient(a,b,p) == 0 and all(min(a[k],b[k]) <= p[k] <= max(a[k],b[k]) for k in (0,1))

def inspect(fold):
    errors = []
    def fail(reason, **details):
        errors.append(dict(reason=reason, **details))
    try:
        raw = fold['vertices_coords']
        if not raw or any(len(p)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in p) for p in raw):
            raise ValueError('2D finite numeric coordinates required')
        v = [tuple(F(str(x)) for x in p) for p in raw]
        e, assignments = fold['edges_vertices'], fold['edges_assignment']
        if len(e) != len(assignments):
            raise ValueError('edge assignment count')
        if any(len(edge)!=2 or any(type(i) is not int or not 0<=i<len(v) for i in edge) for edge in e):
            raise ValueError('edge index')
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return {'passed': False, 'scope': 'PLANAR_SQUARE_CP_ONLY', 'errors': [{'reason': 'INVALID_SCHEMA', 'detail': str(exc)}]}
    if len(set(v)) != len(v): fail('COINCIDENT_VERTICES')
    if any(not 0<=x<=1 for p in v for x in p): fail('OUTSIDE_UNIT_SQUARE')
    keys = [tuple(sorted(edge)) for edge in e]
    if len(set(keys)) != len(keys): fail('DUPLICATE_EDGES')
    for i, (a,b) in enumerate(e):
        if v[a] == v[b]: fail('ZERO_LENGTH_EDGE', edge=i)
        if assignments[i] not in {'B','M','V','F'}: fail('UNSUPPORTED_ASSIGNMENT', edge=i)
        for j,p in enumerate(v):
            if j not in (a,b) and on_segment(v[a],v[b],p): fail('UNSPLIT_VERTEX_ON_EDGE', edge=i, vertex=j)
        for k,(c,d) in enumerate(e[:i]):
            if {a,b}&{c,d}: continue
            o1,o2 = orient(v[a],v[b],v[c]),orient(v[a],v[b],v[d])
            o3,o4 = orient(v[c],v[d],v[a]),orient(v[c],v[d],v[b])
            if o1*o2<0 and o3*o4<0: fail('CROSSING_EDGES', edges=[k,i])
    sides = defaultdict(list)
    for i,(a,b) in enumerate(e):
        if assignments[i] != 'B': continue
        matching = [(axis,side) for axis in (0,1) for side in (F(0),F(1)) if v[a][axis]==v[b][axis]==side]
        if len(matching)!=1:
            fail('BOUNDARY_CHORD_NOT_ON_SQUARE', edge=i)
        else:
            axis,side = matching[0]
            sides[axis,side].append(tuple(sorted((v[a][1-axis],v[b][1-axis]))))
    for axis in (0,1):
        for side in (F(0),F(1)):
            cursor=F(0)
            spans=sorted(sides[axis,side])
            for lo,hi in spans:
                if lo != cursor or hi<=lo: fail('BOUNDARY_GAP_OR_OVERLAP', axis=axis, side=int(side))
                cursor=hi
            if cursor!=1: fail('INCOMPLETE_SQUARE_BOUNDARY', axis=axis, side=int(side))
    faces=fold.get('faces_vertices', [])
    total=F(0)
    incidence=defaultdict(list)
    if not faces: fail('EXPLICIT_MATERIAL_FACES_REQUIRED')
    edge_set=set(keys)
    for fi,face in enumerate(faces):
        if not isinstance(face,list) or len(face)<3 or len(set(face))!=len(face) or any(type(i)is not int or not 0<=i<len(v) for i in face):
            fail('INVALID_FACE', face=fi)
            continue
        area=F(0)
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)))
            if key not in edge_set: fail('FACE_EDGE_MISSING', face=fi, edge=[a,b])
            incidence[key].append((a,b))
            area += v[a][0]*v[b][1]-v[a][1]*v[b][0]
        if area<=0: fail('NONPOSITIVE_FACE_AREA', face=fi)
        total+=area/2
    if total!=1: fail('FACE_AREA_NOT_UNIT_SQUARE', exact_area=str(total))
    for i,key in enumerate(keys):
        uses=incidence[key]
        if assignments[i]=='B':
            if len(uses)!=1: fail('BOUNDARY_FACE_INCIDENCE', edge=i)
        elif len(uses)!=2 or uses[0] != uses[1][::-1]:
            fail('INTERIOR_FACE_INCIDENCE', edge=i)
    used={i for edge in e for i in edge}
    if used!=set(range(len(v))): fail('ISOLATED_VERTEX')
    topology={'edges_vertices':e, 'faces_vertices':faces}
    geometry={**topology, 'vertices_coords':[[str(x) for x in p] for p in v], 'edges_assignment':assignments}
    return {'passed':not errors, 'scope':'PLANAR_SQUARE_CP_ONLY', 'physical_base_certified':False,
            'continuous_motion_certified':False, 'geometry_sha256':digest(geometry),
            'topology_sha256':digest(topology), 'exact_material_area':str(total), 'errors':errors}

if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser()
    p.add_argument('fold'); p.add_argument('output')
    args=p.parse_args()
    data=json.loads(Path(args.fold).read_text(encoding='utf-8-sig'))
    Path(args.output).write_text(json.dumps(inspect(data), ensure_ascii=False, indent=2), encoding='utf-8')