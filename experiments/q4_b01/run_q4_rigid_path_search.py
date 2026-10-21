"""Run the two predeclared deterministic sweeps and retain all trial evidence."""
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'research/q4_b01')]
import numpy
import scipy
from base_intake import inspect
from q4_rigid_path_search import search

OUTPUT = ROOT/'experiments/q4_b01/Q4-B01-ALTERNATIVE-RIGID-PATH'
SOURCE = ROOT/'experiments/q4_b01/Q4-B01-CP-MEDIUM-MEDIUM/candidate.fold'


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cp = json.loads(SOURCE.read_text(encoding='utf-8'))
    report = search(cp)
    intake = inspect(cp)
    report['cp_geometry_sha256'] = intake['geometry_sha256']
    report['cp_topology_sha256'] = intake['topology_sha256']
    report['baseline_commit'] = '8aa98005f5d328dd9ce96bcdd4504acdb4a14d21'
    report['material_mapping_reference'] = 'experiments/q4_b01/Q4-B01-GLOBAL-VALIDATION/stable_ids.json'
    report['experiment_count'] = 2
    report['prior_known_failed_formula'] = 'q=sign*pi*t (Issue #8); never erased by this run'
    write(OUTPUT/'search_report.json', report)
    write(OUTPUT/'environment.json', {'python':platform.python_version(), 'numpy':numpy.__version__,
        'scipy':scipy.__version__, 'command':'python experiments/q4_b01/run_q4_rigid_path_search.py',
        'randomness':'none', 'actual_residual_calls':sum(r['residual_calls'] for s in report['sweeps'] for r in s['attempts'])})
    sources = ['research/q4_b01/q4_rigid_path_search.py','research/q4_b01/.gitattributes',
        'tests/q4_b01/test_q4_rigid_path_search.py','tests/q4_b01/.gitattributes',
        'experiments/q4_b01/run_q4_rigid_path_search.py','experiments/q4_b01/.gitattributes',
        'research/q4_b01/q4_global_validation.py','research/q4_b01/base_intake.py',
        'research/q4_b01/q4_cp_candidate.py','src/generative_origami/simulation/single_vertex.py',
        'experiments/q4_b01/Q4-B01-GLOBAL-VALIDATION/stable_ids.json', SOURCE.relative_to(ROOT).as_posix()]
    paths = [ROOT/p for p in sources] + [p for p in OUTPUT.iterdir() if p.is_file() and p.name!='evidence_manifest.json']
    write(OUTPUT/'evidence_manifest.json', {'task_id':report['task_id'],'hash_algorithm':'sha256-exact-file-bytes',
        'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}})
    for sweep in report['sweeps']:
        print(sweep['direction'], 'accepted', sweep['accepted_count'], '/33; rejected', sweep['rejected_targets'],
              '; interpolation', sweep['interpolation']['status'], '; max jump', sweep['max_knot_jump_rad_l2'])
    print('Continuous rigid path UNKNOWN; collisions UNKNOWN; physical unverified')


if __name__ == '__main__':
    main()
