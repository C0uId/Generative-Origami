"""Complete a radial research CP's square boundary; not a Q4 base."""
import copy
from fractions import Fraction as F
from base_intake import inspect

def perimeter(p):
    x,y=map(lambda x:F(str(x)),p)
    if y==0: return x
    if x==1: return 1+y
    if y==1: return 3-x
    if x==0: return 4-y
    raise ValueError('ray endpoint must be on unit square')

def complete_square(source):
    v=copy.deepcopy(source['vertices_coords'])
    if v[0]!=[0.5,0.5]: raise ValueError('only centered radial research fixtures supported')
    radial=[]
    for edge,a in zip(source['edges_vertices'],source['edges_assignment']):
        if a=='B': continue
        if edge[0]!=0 or a not in {'M','V','F'}: raise ValueError('not a supported radial graph')
        radial.append((edge[1],a))
    if {i for i,_ in radial}!=set(range(1,len(v))) or len(radial)!=len(v)-1:
        raise ValueError('each boundary vertex needs exactly one radial crease')
    for p in v[1:]: perimeter(p)
    for corner in [[0,0],[1,0],[1,1],[0,1]]:
        if corner not in v: v.append(corner)
    boundary=sorted(range(1,len(v)),key=lambda i:perimeter(v[i]))
    tips=sorted((i for i,_ in radial),key=lambda i:perimeter(v[i]))
    faces=[]
    for start,end in zip(tips,tips[1:]+tips[:1]):
        pos=boundary.index(start); chain=[start]
        while chain[-1]!=end:
            pos=(pos+1)%len(boundary); chain.append(boundary[pos])
        faces.append([0]+chain)
    edges=[[0,i] for i,_ in radial]+[[a,b] for a,b in zip(boundary,boundary[1:]+boundary[:1])]
    result={'file_spec':1.2, 'file_creator':'POC01-009 square material audit',
        'frame_classes':['creasePattern'], 'vertices_coords':v, 'edges_vertices':edges,
        'edges_assignment':[a for _,a in radial]+['B']*len(boundary), 'faces_vertices':faces,
        'go:baseStatus':'RESEARCH_RADIAL_ONLY_NOT_Q4',
        'go:motionStatus':'REQUIRES_NEW_MOTION_CERTIFICATION',
        'faces_go:stableId':[f'radial-sector-from-vertex-{i}' for i in tips],
        'vertices_go:stableId':[f'source-vertex-{i}' if i<len(source['vertices_coords']) else f'paper-corner-{v[i][0]}-{v[i][1]}' for i in range(len(v))]}
    report=inspect(result)
    if not report['passed']: raise ValueError(report['errors'])
    result['go:geometrySha256']=report['geometry_sha256']
    return result