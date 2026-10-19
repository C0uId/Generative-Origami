from pathlib import Path
import sys
REPO_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO_ROOT/"research"/"q4_b01"))
import json
from q4_tree_layout import solve

def run():
    out=Path(__file__).parent/'POC01-010A_TREE_LAYOUT_SCREEN'
    out.mkdir(parents=True,exist_ok=True)
    summary=[]
    for leg in ('short','medium','long'):
        for tail in ('short','medium','long'):
            result=solve({'leg_budget':leg,'tail_budget':tail})
            name=f'{leg}_{tail}'
            (out/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            summary.append({'case':name,'status':result['status'],'feasible_grid_points':result['feasible_count'],
                            'objective_mm':result.get('objective_value_mm'),'points_mm':result.get('points_mm')})
    (out/'report.json').write_text(json.dumps({'cases':summary,'cp_generated':False,'physical_verified':False},ensure_ascii=False,indent=2),encoding='utf-8')
    return summary

if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False))