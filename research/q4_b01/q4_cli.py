"""Reproducible Q4 material-layout candidate CLI, separate from CP generation."""
import argparse,json
from pathlib import Path
from q4_base import compile_layout,import_cp

def main():
    p=argparse.ArgumentParser(description=__doc__)
    commands=p.add_subparsers(dest='command',required=True)
    layout=commands.add_parser('layout')
    layout.add_argument('--leg',choices=['short','medium','long'],required=True)
    layout.add_argument('--tail',choices=['short','medium','long'],required=True)
    layout.add_argument('--output',required=True)
    cp=commands.add_parser('import-cp')
    cp.add_argument('--fold',required=True)
    cp.add_argument('--face-ids',required=True,help='JSON list of stable strings')
    cp.add_argument('--output',required=True)
    a=p.parse_args()
    if a.command=='layout':result=compile_layout({'leg_budget':a.leg,'tail_budget':a.tail})
    else:
        result=import_cp(json.loads(Path(a.fold).read_text(encoding='utf-8-sig')),json.loads(Path(a.face_ids).read_text(encoding='utf-8-sig')))
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()