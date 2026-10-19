"""Q4-B01 material geometry and CP intake. Design guides are never creases."""
from pathlib import Path
from fractions import Fraction as F
import json
import math
from base_intake import inspect, digest

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSET = REPO_ROOT / 'assets/bases/q4_b01/manifest.json'
LEVELS = ('short', 'medium', 'long')

def manifest():
    return json.loads(ASSET.read_text(encoding='utf-8'))

def validate_manifest(m):
    required = {'MAT_FL','MAT_FR','MAT_HL','MAT_HR','MAT_HEAD','MAT_BODY','MAT_TAIL'}
    regions=m['material_regions']
    if m['paper_mm'] != [200,200] or {r['id'] for r in regions} != required or len(regions)!=7:
        raise ValueError('INVALID_PAPER_OR_REGION_IDS')
    occupied=set()
    for r in regions:
        x0,y0,x1,y1=r['bounds_mm']
        values=[F(str(x))/F('12.5') for x in (x0,y0,x1,y1)]
        if any(x.denominator!=1 for x in values): raise ValueError('OFF_GRID_REGION')
        a,b,c,d=map(int,values)
        if not 0<=a<c<=16 or not 0<=b<d<=16: raise ValueError('INVALID_REGION_BOUNDS')
        cells={(x,y) for x in range(a,c) for y in range(b,d)}
        if occupied & cells: raise ValueError('OVERLAPPING_REGIONS')
        occupied |= cells
    if len(occupied)!=256: raise ValueError('INCOMPLETE_PAPER_COVERAGE')
    return True

def material_at(x,y,m=None):
    """Half-open ownership, outer upper edge included; camera independent."""
    m=m or manifest()
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (x,y)):
        raise ValueError('INVALID_POINT')
    if not 0<=x<=200 or not 0<=y<=200: raise ValueError('POINT_OUTSIDE_PAPER')
    for r in m['material_regions']:
        a,b,c,d=r['bounds_mm']
        if a<=x and (x<c or x==c==200) and b<=y and (y<d or y==d==200): return r['id']
    raise ValueError('UNMAPPED_POINT')

def project_q4(requested):
    """Only named design levels; never reinterpret historical 0.25 as mm."""
    if set(requested)=={'body_to_leg_ratio','tail_ratio'}:
        if any(v not in LEVELS for v in requested.values()): raise ValueError('NAMED_LEVELS_REQUIRED')
        implemented={'leg_budget':dict(zip(LEVELS,reversed(LEVELS)))[requested['body_to_leg_ratio']],
                     'tail_budget':requested['tail_ratio']}
        notes=['body_to_leg_ratio order is inverted for leg_budget; qualitative mapping only, not a physical ratio.']
    elif set(requested)=={'leg_budget','tail_budget'}:
        if any(v not in LEVELS for v in requested.values()): raise ValueError('NAMED_LEVELS_REQUIRED')
        implemented=dict(requested); notes=[]
    else: raise ValueError('EXACTLY_TWO_SUPPORTED_PARAMETERS_REQUIRED')
    return {'requested':dict(requested),'implemented':implemented,'approximation_notes':notes,
            'domain':'EXPLORATORY_LAYOUT_ONLY'}

def compile_layout(requested, *, certified=False):
    m=manifest(); validate_manifest(m)
    if certified: raise ValueError('CERTIFIED_DOMAIN_EMPTY')
    projection=project_q4(requested)
    params=projection['implemented']
    # Experimental source-path probes only. They do not claim folded flap length.
    leg=m['exploration']['source_inset_mm'][params['leg_budget']]
    tail=m['exploration']['source_inset_mm'][params['tail_budget']]
    paths=[]
    for region,corner,sign in [('MAT_FL',(0,200),(1,-1)),('MAT_FR',(200,200),(-1,-1)),
                               ('MAT_HL',(0,0),(1,1)),('MAT_HR',(200,0),(-1,1))]:
        paths.append({'id':region+'_SOURCE_GUIDE','material_id':region,
                      'points_mm':[list(corner),[corner[0]+sign[0]*leg,corner[1]+sign[1]*leg]],
                      'source_path_length_mm':leg*math.sqrt(2), 'folded_flap_length_mm':None})
    paths.append({'id':'MAT_TAIL_SOURCE_GUIDE','material_id':'MAT_TAIL',
                  'points_mm':[[100,0],[100,tail]],'source_path_length_mm':tail,'folded_flap_length_mm':None})
    geometry={'paper_mm':m['paper_mm'],'material_regions':m['material_regions'],
              'source_paths':[{'id':p['id'],'points_mm':p['points_mm']} for p in paths]}
    topology={'regions':[r['id'] for r in m['material_regions']], 'source_paths':[p['id'] for p in paths]}
    return {'base_id':m['base_id'],'base_version':m['version'],'manifest_sha256':digest(m),
            'status':'MATERIAL_LAYOUT_CANDIDATE_NOT_CP','projection':projection,'geometry':geometry,
            'geometry_sha256':digest(geometry),'topology_sha256':digest(topology),'source_paths':paths,
            'seed':0,'certified':False,'cp':None,'motion_certificate':None}

def clip_rect(poly, bounds):
    """Exact convex clipping for area mapping; concave faces may be imported only
    when their clipping representation is simple (intake limits apply)."""
    for axis,threshold,lower in [(0,bounds[0],True),(0,bounds[2],False),(1,bounds[1],True),(1,bounds[3],False)]:
        if not poly: break
        result=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            ina=a[axis]>=threshold if lower else a[axis]<=threshold
            inb=b[axis]>=threshold if lower else b[axis]<=threshold
            if ina: result.append(a)
            if ina!=inb:
                t=(threshold-a[axis])/(b[axis]-a[axis])
                result.append(tuple(a[k]+t*(b[k]-a[k]) for k in (0,1)))
        poly=result
    return poly

def area(poly):
    return abs(sum((a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1])),F(0)))/2

def import_cp(fold, face_ids):
    """Map a separately supplied normalized CP to materials, never certify it."""
    audit=inspect(fold)
    if not audit['passed']: raise ValueError('CP_PLANAR_GATE_FAILED')
    faces=fold['faces_vertices']
    if len(face_ids)!=len(faces) or any(not isinstance(s,str) or not s.strip() for s in face_ids) or len(set(face_ids))!=len(face_ids):
        raise ValueError('UNIQUE_STABLE_FACE_IDS_REQUIRED')
    m=manifest(); validate_manifest(m)
    mappings=[]
    for face_id, face in zip(face_ids,faces):
        poly=[tuple(F(str(x))*200 for x in fold['vertices_coords'][i]) for i in face]
        # Restrict this importer to convex faces to avoid disconnected clipped polygons.
        turns=[(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]) for a,b,c in zip(poly,poly[1:]+poly[:1],poly[2:]+poly[:2])]
        if any(t<0 for t in turns): raise ValueError('CONVEX_FACE_REQUIRED_SPLIT_WITH_STABLE_IDS')
        parts=[]
        for region in m['material_regions']:
            cut=clip_rect(poly,[F(str(x)) for x in region['bounds_mm']])
            size=area(cut)
            if size: parts.append({'material_id':region['id'],'area_mm2_exact':str(size),'face_fraction_exact':str(size/area(poly))})
        if sum((F(p['area_mm2_exact']) for p in parts),F(0)) != area(poly): raise ValueError('MATERIAL_MAPPING_AREA_MISMATCH')
        mappings.append({'face_id':face_id,'material_parts':parts})
    return {'base_id':m['base_id'],'base_version':m['version'],'manifest_sha256':digest(m),
            'geometry_sha256':audit['geometry_sha256'],'face_material_map':mappings,
            'status':'CP_MATERIAL_MAPPING_ONLY','physical_verified':False,'motion_verified':False}