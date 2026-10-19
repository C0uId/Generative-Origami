"""Finite exact six-terminal tree-distance layout screening, not a CP solver."""
from fractions import Fraction as F
from itertools import combinations, product
from q4_base import project_q4
from base_intake import digest

IDS=('MAT_FL','MAT_FR','MAT_HL','MAT_HR','MAT_HEAD','MAT_TAIL')

def tree(leg,tail):
    # Independent experimental tree lengths, not inherited from source-guide measurements.
    lengths=[F(str(v)) for v in (leg,tail)]
    if any(v<=0 for v in lengths): raise ValueError('POSITIVE_TREE_LENGTHS_REQUIRED')
    leg,tail=lengths
    return [('FRONT','REAR',F(50)),('FRONT','MAT_HEAD',F(25)),
            ('REAR','MAT_TAIL',tail)]+[(('FRONT' if i in ('MAT_FL','MAT_FR') else 'REAR'),i,leg) for i in IDS[:4]]

def distances(edges):
    graph={}
    for a,b,w in edges:
        graph.setdefault(a,[]).append((b,w)); graph.setdefault(b,[]).append((a,w))
    result={}
    for a,b in combinations(IDS,2):
        stack=[(a,None,F(0))]
        while stack:
            node,parent,d=stack.pop()
            if node==b: result[a,b]=d;break
            stack.extend((n,node,d+w) for n,w in graph[node] if n!=parent)
    return result

def check(points,required):
    records=[]
    for (a,b),distance in required.items():
        squared=sum((F(str(points[a][k]))-F(str(points[b][k])))**2 for k in (0,1))
        residual=squared-distance**2
        records.append({'pair':[a,b],'tree_distance_mm':str(distance),
                        'squared_distance_mm2':str(squared),'squared_margin_mm2':str(residual),'passed':residual>=0})
    return records

def solve_lengths(leg,tail):
    edges=tree(leg,tail); required=distances(edges)
    feasible=[]; failures=[]
    # Symmetric four-corner leaf placements in region closures, head/tail tips fixed.
    grid=(F(0),F('12.5'),F(25),F('37.5'))
    for x,inset in product(grid,repeat=2):
        points={'MAT_FL':(x,200-inset),'MAT_FR':(200-x,200-inset),
                'MAT_HL':(x,inset),'MAT_HR':(200-x,inset),
                'MAT_HEAD':(F(100),F(200)),'MAT_TAIL':(F(100),F(0))}
        checks=check(points,required)
        if all(r['passed'] for r in checks): feasible.append((x+inset,x,inset,points,checks))
        else: failures.append({'x_mm':str(x),'inset_mm':str(inset),'failed_pairs':[r for r in checks if not r['passed']]})
    result={'status':'GRID_LAYOUT_FEASIBLE' if feasible else 'NO_LAYOUT_ON_SEARCH_GRID',
            'scope':'15 pairwise tree-distance inequalities only; not sufficient for a foldable base',
            'searched_count':16,'feasible_count':len(feasible),'rejected':failures,
            'tree_edges':[{'a':a,'b':b,'length_mm':str(w)} for a,b,w in edges],
            'physical_verified':False,'cp':None,'grid_infeasibility_is_not_global_infeasibility':True}
    if feasible:
        # Exhaustively optimal only for this finite grid and this compactness objective.
        score,x,inset,points,checks=max(feasible,key=lambda r:r[:3])
        result.update({'points_mm':{k:[str(v) for v in p] for k,p in points.items()},'checks':checks,
                       'objective':'maximize x + inset; ties maximize x, then inset', 'objective_value_mm':str(score)})
    result['input_sha256']=digest(result['tree_edges'])
    return result

def solve(requested):
    p=project_q4(requested)
    # Separate design assumption table; no claim that these are physical presets.
    values={'short':12.5,'medium':25,'long':37.5}
    result=solve_lengths(values[p['implemented']['leg_budget']],values[p['implemented']['tail_budget']])
    result['projection']=p
    result['assumptions']={'head_length_mm':25,'body_tree_length_mm':50,'source':'new exploratory tree hypothesis',
                           'body_river_geometry':'NOT_CONSTRUCTED','material_flow':'NOT_PROVEN'}
    return result