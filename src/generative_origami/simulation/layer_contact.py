from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import numpy as np
from scipy.optimize import linprog

from .single_vertex import SingleVertexMechanism


@dataclass
class LayerContactReport:
    feasible: bool
    order: list[int] | None
    inward_progress: float
    qdot: list[float] | None
    sample_count: int
    min_separation: float | None = None


def _orient(a, b, c):
    return float((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))


def _poly_area(poly):
    return 0.5 * sum(_orient(np.zeros(2), poly[i], poly[(i+1)%len(poly)]) for i in range(len(poly)))


def _line_intersection(a,b,c,d):
    # infinite AB with CD; used by convex clipping
    r=b-a; s=d-c
    den=r[0]*s[1]-r[1]*s[0]
    if abs(den)<1e-14:
        return (b+c)*0.5
    t=((c-a)[0]*s[1]-(c-a)[1]*s[0])/den
    return a+t*r


def _convex_clip(subject: np.ndarray, clip: np.ndarray) -> np.ndarray:
    output=[np.array(p,float) for p in subject]
    if not output:
        return np.empty((0,2))
    sign=1.0 if _poly_area(clip)>=0 else -1.0
    for k in range(len(clip)):
        cp1=np.array(clip[k],float);cp2=np.array(clip[(k+1)%len(clip)],float)
        inp=output;output=[]
        if not inp:break
        S=inp[-1]
        for E in inp:
            Ein=sign*_orient(cp1,cp2,E)>=-1e-10
            Sin=sign*_orient(cp1,cp2,S)>=-1e-10
            if Ein:
                if not Sin: output.append(_line_intersection(S,E,cp1,cp2))
                output.append(E)
            elif Sin:
                output.append(_line_intersection(S,E,cp1,cp2))
            S=E
    # dedupe
    clean=[]
    for p in output:
        if not clean or np.linalg.norm(p-clean[-1])>1e-9:
            clean.append(p)
    if len(clean)>1 and np.linalg.norm(clean[0]-clean[-1])<1e-9:
        clean.pop()
    return np.array(clean,float)


def _barycentric(p: np.ndarray, tri: np.ndarray) -> np.ndarray:
    M=np.array([[tri[0,0]-tri[2,0],tri[1,0]-tri[2,0]],
                [tri[0,1]-tri[2,1],tri[1,1]-tri[2,1]]],float)
    x=np.linalg.solve(M,np.asarray(p)-tri[2])
    return np.array([x[0],x[1],1-x.sum()])


def _all_topological_sorts(nodes: list[int], edges: list[tuple[int,int]]):
    succ={n:[] for n in nodes}; indeg={n:0 for n in nodes}
    for a,b in edges:
        succ[a].append(b);indeg[b]+=1
    out=[]
    def rec(order,ind):
        avail=[n for n in nodes if n not in order and ind[n]==0]
        for n in avail:
            ni=dict(ind)
            for v in succ[n]:ni[v]-=1
            rec(order+[n],ni)
        if len(order)==len(nodes):out.append(order)
    rec([],indeg)
    return out


class LayerContactModel:
    """Infers a zero-thickness layer order and contact-compatible goal mode.

    Ordering convention is searched in both global directions because the
    previous W/C ordering graph has an arbitrary global 'above' convention.
    The selected order maximizes first-order inward progress subject to:
      * loop-closure tangent space,
      * every crease moving inward from +/-pi,
      * nonpenetration at every vertex of every final overlap polygon.
    """

    def __init__(self, mechanism: SingleVertexMechanism):
        self.m=mechanism
        self.goal_triangles=self.m.panel_triangles(self.m.goal)
        self.samples_by_pair=self._build_samples()
        self.samples=[(pair,wi,wj) for pair,vals in self.samples_by_pair.items() for wi,wj in vals]
        self.report=self._solve_goal_tangent()
        self.rank={p:i for i,p in enumerate(self.report.order)} if self.report.order else {}

    def _build_samples(self):
        result={}
        for pair in sorted(self.m.final_contact_pairs):
            i,j=pair
            a=self.goal_triangles[i][:,:2]; b=self.goal_triangles[j][:,:2]
            poly=_convex_clip(a,b)
            if len(poly)<3 or abs(_poly_area(poly))<1e-10:
                continue
            vals=[]
            for p in poly:  # vertices suffice for an affine separation function
                vals.append((_barycentric(p,a),_barycentric(p,b)))
            result[pair]=vals
        return result

    def _adjacent_order_edges(self):
        colors=['W' if i%2==0 else 'C' for i in range(self.m.n)]
        assignments=[r['assignment'] for r in self.m.rays]
        edges=[]
        for k,a in enumerate(assignments):
            prev=(k-1)%self.m.n; cur=k
            cp,cc=colors[prev],colors[cur]
            if a=='M':
                edge=(prev,cur) if (cp,cc)==('W','C') else (cur,prev)
            else:
                edge=(prev,cur) if (cp,cc)==('C','W') else (cur,prev)
            edges.append(edge)
        return edges

    def _contact_derivatives(self):
        qg=self.m.goal; h=1e-6
        D=np.zeros((len(self.samples),self.m.n))
        for k in range(self.m.n):
            qp=qg.copy();qm=qg.copy();qp[k]+=h;qm[k]-=h
            Tp=self.m.panel_triangles(qp);Tm=self.m.panel_triangles(qm)
            for r,(pair,wi,wj) in enumerate(self.samples):
                i,j=pair
                fp=float((wi@Tp[i]-wj@Tp[j])[2])
                fm=float((wi@Tm[i]-wj@Tm[j])[2])
                D[r,k]=(fp-fm)/(2*h)
        return D

    def _solve_goal_tangent(self):
        N,_,_=self.m.tangent_basis(self.m.goal)
        D=self._contact_derivatives()
        edges=self._adjacent_order_edges()
        nodes=list(range(self.m.n))
        orders=_all_topological_sorts(nodes,edges)
        orders += [list(reversed(o)) for o in orders]
        # dedupe
        unique=[];seen=set()
        for o in orders:
            t=tuple(o)
            if t not in seen:seen.add(t);unique.append(o)
        progress_vec=(-self.m.signs)@N
        best=None
        for order in unique:
            rank={p:i for i,p in enumerate(order)}
            rows=[]
            # sign*qdot <=0 means moving inward from +/-pi
            for i in range(self.m.n):
                rows.append(self.m.signs[i]*N[i])
            for r,(pair,wi,wj) in enumerate(self.samples):
                i,j=pair
                order_sign=1.0 if rank[i]>rank[j] else -1.0
                # order_sign * D qdot >=0
                rows.append(-order_sign*(D[r]@N))
            sol=linprog(-progress_vec,A_ub=np.asarray(rows),b_ub=np.zeros(len(rows)),
                        bounds=[(-1,1)]*N.shape[1],method='highs')
            if not sol.success:
                continue
            qdot=N@sol.x
            progress=float((-self.m.signs)@qdot)
            if best is None or progress>best[0]:
                best=(progress,order,qdot)
        if best is None or best[0]<=1e-9:
            return LayerContactReport(False,None,0.0,None,len(self.samples))
        qdot=best[2]
        norm=float(np.linalg.norm(qdot))
        if norm>1e-12:qdot=qdot/norm
        return LayerContactReport(True,list(best[1]),float(best[0]),[float(x) for x in qdot],len(self.samples))

    def pair_min_separation(self,q: np.ndarray,pair: tuple[int,int]) -> float:
        vals=self.samples_by_pair.get(tuple(sorted(pair)))
        if not vals or not self.rank:
            return float('-inf')
        i,j=tuple(sorted(pair));T=self.m.panel_triangles(q)
        order_sign=1.0 if self.rank[i]>self.rank[j] else -1.0
        return min(order_sign*float((wi@T[i]-wj@T[j])[2]) for wi,wj in vals)

    def min_separation(self,q: np.ndarray) -> float:
        if not self.samples_by_pair:return float('inf')
        return min(self.pair_min_separation(q,p) for p in self.samples_by_pair)



    @staticmethod
    def _barycentric3(point: np.ndarray, tri: np.ndarray) -> np.ndarray:
        # Solve point = w0*v0 + w1*v1 + w2*v2, sum w=1 in least squares.
        A=np.vstack([tri.T, np.ones(3)])
        b=np.r_[np.asarray(point,float),1.0]
        w, *_ = np.linalg.lstsq(A,b,rcond=None)
        return w

    def intersection_is_legal_contact(self,q: np.ndarray,pair: tuple[int,int],point: np.ndarray, mapping_tol: float = 3e-5) -> bool:
        pair=tuple(sorted(pair))
        if pair not in self.samples_by_pair or not self.rank:
            return False
        if self.pair_min_separation(q,pair)<-2e-7:
            return False
        current=self.m.panel_triangles(q);i,j=pair
        wi=self._barycentric3(point,current[i]);wj=self._barycentric3(point,current[j])
        # Intersection must lie on both finite triangles.
        if np.min(wi)<-2e-5 or np.min(wj)<-2e-5 or np.max(wi)>1+2e-5 or np.max(wj)>1+2e-5:
            return False
        gi=wi@self.goal_triangles[i];gj=wj@self.goal_triangles[j]
        # Only material points that are destined to meet in the verified final
        # flat contact are allowed to intersect during a sticking-contact phase.
        return bool(np.linalg.norm(gi-gj)<=mapping_tol)
    def goal_prefix(self, max_angle_step: float = 0.16):
        """Deterministic contact-compatible prefix from folded goal to first active-set event."""
        if not self.report.feasible or self.report.qdot is None:
            return []
        d=np.asarray(self.report.qdot,float)
        inward=-self.m.signs*d
        positive=inward[inward>1e-8]
        if len(positive)==0:
            return [self.m.goal.copy()]
        tmax=math.pi/float(np.max(positive))
        # choose enough frames so no fold angle changes more than max_angle_step
        steps=max(2,int(math.ceil(tmax*float(np.max(np.abs(d)))/max_angle_step)))
        out=[]
        for t in np.linspace(0.0,tmax,steps+1):
            q=self.m.goal+t*d
            if np.linalg.norm(self.m.closure_residual(q))>2e-6:
                break
            if self.min_separation(q)<-5e-7:
                break
            out.append(q)
        return out
    def goal_seeds(self,epsilons=(0.02,0.04,0.07,0.10,0.14)):
        if not self.report.feasible or self.report.qdot is None:return []
        d=np.asarray(self.report.qdot,float);out=[]
        for eps in epsilons:
            raw=self.m.goal+eps*d
            q,err=self.m.project(raw,anchor=raw,max_nfev=80)
            if err<5e-7 and self.m.sector_valid(q) and self.min_separation(q)>=-2e-7:
                out.append(q)
        return out