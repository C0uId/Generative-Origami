from pathlib import Path
import json,sys,math
import numpy as np
REPO_ROOT=Path(__file__).resolve().parents[2]
ROOT=REPO_ROOT
sys.path.insert(0,str(REPO_ROOT/'src'))
from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation.single_vertex import SingleVertexMechanism
from generative_origami.simulation.singular_bridge import LocalChartMotion,SingularBridgeConfig,FlatSingularBridgeBuilder
m=SingleVertexMechanism(generate_fold(parse_target('狗')))
x=json.loads((REPO_ROOT/'experiments/current/baseline_inputs/repaired_source_knots.json').read_text(encoding='utf8'))
for i in [160,161,162]:print(i,x[i]['repaired'])
R=np.eye(3);virtual={}
for k in list(range(1,m.n))+[0]:
    axis=np.r_[m.rays[k]['unit2'],0.]
    virtual[k]=R@axis
    R=R@m._axis_rotation(axis,m.goal[k])
print('virtual',virtual,'goal identity error',np.linalg.norm(R-np.eye(3)))
print('original opposite-axis defects',[(k,np.linalg.norm(np.r_[m.rays[k]['unit2'],0.]+np.r_[m.rays[k+4]['unit2'],0.])) for k in range(4)])
print('virtual duplicate-axis defects',[(a,b,np.linalg.norm(virtual[a]-virtual[b])) for a,b in [(0,2),(0,4),(0,6),(1,3),(1,5),(1,7)]])

class VirtualMechanism:
    n=m.n
    signs=-m.signs
    flat=np.zeros(m.n)
    goal=signs*math.pi
    _axis_rotation=staticmethod(SingleVertexMechanism._axis_rotation)
    rays=[{**ray,'unit2':virtual[k][:2]} for k,ray in enumerate(m.rays)]
    def panel_rotations(self,q):
        rotations=[np.eye(3)];R=np.eye(3)
        for k in range(1,self.n):
            R=R@self._axis_rotation(np.r_[self.rays[k]['unit2'],0.],q[k]);rotations.append(R)
        return rotations

v=VirtualMechanism()
q=np.array(x[161]['repaired'])-m.goal
print('delta',q)
for dependent in [(k,(k+1)%m.n,(k+2)%m.n) for k in range(m.n)]:
    try:
        p=LocalChartMotion(v,np.zeros(m.n),q,SingularBridgeConfig(dependent=dependent))
        print('dep',dependent,'regularity',p.regularity(),'end error',np.max(abs(p.q(1.)-q)))
    except Exception as exc:
        print('dep',dependent,'error',str(exc))