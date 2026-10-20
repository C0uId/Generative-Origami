"""Rebuild the review evidence and diagnostic refold kit from the committed CP."""
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'research/q4_b01')]

import numpy
import scipy
from q4_cp_candidate import FACE_IDS
from q4_global_validation import validation_report
from q4_base import manifest as material_manifest

OUTPUT = ROOT / 'experiments/q4_b01/Q4-B01-GLOBAL-VALIDATION'
SOURCE = ROOT / 'experiments/q4_b01/Q4-B01-CP-MEDIUM-MEDIUM/candidate.fold'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def printable_svg(cp):
    # Actual page: A4, with a true 200 x 200 mm square. Guides are not creases.
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">',
             '<rect width="210" height="297" fill="white"/>',
             '<g font-family="sans-serif" fill="#111">',
             '<text x="5" y="10" font-size="4">Q4-B01 / diagnostic CP / NOT a certified folding sequence</text>',
             '<text x="5" y="17" font-size="3">Print 100% / no fit-to-page. Square must measure 200 x 200 mm.</text>']
    def point(v):
        x, y = cp['vertices_coords'][v]
        return 5+200*x, 225-200*y
    for region in material_manifest()['material_regions']:
        x0,y0,x1,y1 = region['bounds_mm']
        parts.append(f'<rect x="{5+x0}" y="{225-y1}" width="{x1-x0}" height="{y1-y0}" fill="#eef3f7" stroke="#aaa" stroke-width="0.2" stroke-dasharray="1 2"/>')
        label_x = 5+x0+(x1-x0)*0.3
        parts.append(f'<text x="{label_x}" y="{225-y1+8}" font-size="2.5" fill="#687888">{region["id"]}</text>')
    for i, ((a,b), assignment) in enumerate(zip(cp['edges_vertices'], cp['edges_assignment'])):
        x1,y1 = point(a); x2,y2 = point(b)
        color = {'B':'#111','M':'#b42318','V':'#175cd3','F':'#777'}[assignment]
        dash = ' stroke-dasharray="2 1"' if assignment == 'V' else ''
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="0.35"{dash}/>')
        parts.append(f'<text x="{(x1+x2)/2+0.8}" y="{(y1+y2)/2-0.8}" font-size="2.2">E{i:02d}</text>')
    for i in range(len(cp['vertices_coords'])):
        x,y = point(i)
        label_x = min(x+1, 198)
        parts.append(f'<circle cx="{x}" cy="{y}" r="0.65"/><text x="{label_x}" y="{y+3}" font-size="2.5">V{i:02d}</text>')
    for face_id, face in zip(FACE_IDS, cp['faces_vertices']):
        xy = [point(v) for v in face]
        x = sum(p[0] for p in xy)/len(xy); y = sum(p[1] for p in xy)/len(xy)
        parts.append(f'<text x="{x}" y="{y+4}" text-anchor="middle" font-size="2.5">{face_id}</text>')
    parts.extend(['<text x="5" y="239" font-size="3">Black solid B: boundary (no cutting). Red solid M: mountain.</text>',
        '<text x="5" y="246" font-size="3">Blue dashed V: valley. Grey dotted boxes: material guides, NOT creases.</text>',
        '<text x="5" y="253" font-size="3">View: marked front of paper; origin lower-left; +x right, +y up.</text>',
        '<text x="5" y="260" font-size="3">IDs: Vxx = V_Q4_MM_xx; Exx = E_Q4_MM_xx. See stable_ids.json.</text>',
        '<text x="5" y="267" font-size="3">M ridges toward viewer; V hollows toward viewer. Back reverses M/V view.</text>',
        '<text x="5" y="274" font-size="3">Uniform-angle trial FAILED closure. Do not follow it as folding instructions.</text>',
        '</g></svg>'])
    return '\n'.join(parts)+'\n'


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cp = json.loads(SOURCE.read_text(encoding='utf-8'))
    report = validation_report(cp)
    write_json(OUTPUT / 'global_validation.json', report)
    (OUTPUT / 'candidate.fold').write_bytes(SOURCE.read_bytes())
    (OUTPUT / 'printable_cp.svg').write_text(printable_svg(cp), encoding='utf-8', newline='\n')
    write_json(OUTPUT / 'stable_ids.json', {
        'geometry_sha256': report['cp_geometry_sha256'],
        'vertices': {f'V_Q4_MM_{i:02d}': p for i,p in enumerate(cp['vertices_coords'])},
        'edges': {f'E_Q4_MM_{i:02d}': {'vertices': [f'V_Q4_MM_{v:02d}' for v in e], 'assignment': a}
                  for i,(e,a) in enumerate(zip(cp['edges_vertices'], cp['edges_assignment']))},
        'faces': {fid: [f'V_Q4_MM_{v:02d}' for v in f] for fid,f in zip(FACE_IDS, cp['faces_vertices'])},
        'face_material_map': report['material_traceability']['face_material_map'],
        'id_scope': 'Fixed candidate geometry/topology; preserve original arrays when recording evidence.'})
    trial = {'status':'NOT_RUN', 'operator':None, 'date':None, 'paper':None,
        'independent_of_design_specimen':None, 'independent_of_other_refolds':None,
        'front_back_crosscheck':None, 'mv_crosscheck':None, 'complete_sequence_media':[],
        'macro_actions':[], 'final_face_material_correspondence':[], 'result':'UNKNOWN',
        'failure_edge_vertex_ids':[], 'evidence_files_and_sha256':[], 'notes':None}
    write_json(OUTPUT / 'physical_evidence_template.json', {
        'task_id':report['task_id'], 'geometry_sha256':report['cp_geometry_sha256'],
        'physical_base_certified':False, 'validated_folding_sequence_available':False,
        'design_specimen':trial, 'independent_refold_1':trial, 'independent_refold_2':trial,
        'provenance_license':{'cp_source':'Project baseline merged PR #7',
                             'media_rights_and_release_permission':None}})
    write_json(OUTPUT / 'environment.json', {'python':platform.python_version(),
        'numpy':numpy.__version__, 'scipy':scipy.__version__, 'seed':0,
        'command':'python experiments/q4_b01/run_q4_global_validation.py',
        'baseline_commit':'fede5447080749890fb1e509ea42319a35ad1552'})
    paths = [p for p in OUTPUT.iterdir() if p.is_file() and p.name != 'evidence_manifest.json']
    sources = ['.gitattributes', 'research/q4_b01/q4_global_validation.py', 'research/q4_b01/q4_cp_candidate.py',
        'research/q4_b01/base_intake.py', 'research/q4_b01/q4_base.py',
        'src/generative_origami/simulation/single_vertex.py',
        'tests/q4_b01/test_q4_global_validation.py',
        'experiments/q4_b01/run_q4_global_validation.py',
        'assets/bases/q4_b01/manifest.json', str(SOURCE.relative_to(ROOT)).replace('\\','/')]
    paths += [ROOT / p for p in sources]
    write_json(OUTPUT / 'evidence_manifest.json', {'schema_version':'q4-evidence-manifest-1.0',
        'task_id':report['task_id'], 'hash_algorithm':'sha256-exact-file-bytes',
        'cp_geometry_sha256':report['cp_geometry_sha256'],
        'files': {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(paths)}})
    print('Local vertices:', [(v['vertex_index'],v['kawasaki'],v['maekawa']) for v in report['local_vertices']])
    print('Uniform path:', report['motion_probe']['status'], '; global foldability: UNKNOWN; physical: unverified')


if __name__ == '__main__':
    main()
