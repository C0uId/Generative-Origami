from __future__ import annotations
import math
from typing import Any
from .models import ValidationReport

def _angle(a,b):
    d=(b-a)%(2*math.pi)
    return d

def validate_fold(fold: dict[str,Any]) -> ValidationReport:
    V=fold["vertices_coords"]
    E=fold["edges_vertices"]
    A=fold["edges_assignment"]
    checks=[]

    bounds=all(-1e-9<=x<=1+1e-9 and -1e-9<=y<=1+1e-9 for x,y in V)
    checks.append({"name":"vertices_in_unit_square","pass":bounds})

    center=V[0]
    crease_edges=[(ei,e) for ei,e in enumerate(E) if A[ei] in {"M","V"} and 0 in e]
    angles=[]
    for _,e in crease_edges:
        other=e[1] if e[0]==0 else e[0]
        dx=V[other][0]-center[0]
        dy=V[other][1]-center[1]
        t=math.atan2(dy,dx)
        if t<0:t+=2*math.pi
        angles.append(t)
    angles=sorted(angles)
    n=len(angles)
    even=(n>=4 and n%2==0)
    checks.append({"name":"even_single_vertex_degree","pass":even,"degree":n})

    kawasaki=False
    kaw_err=None
    if even:
        sectors=[_angle(angles[i],angles[(i+1)%n]) for i in range(n)]
        s0=sum(sectors[0::2]); s1=sum(sectors[1::2])
        kaw_err=max(abs(s0-math.pi),abs(s1-math.pi))
        kawasaki=kaw_err<1e-7
    checks.append({"name":"kawasaki_local","pass":kawasaki,"error":kaw_err})

    m=sum(1 for a in A if a=="M")
    v=sum(1 for a in A if a=="V")
    maekawa=abs(m-v)==2
    checks.append({"name":"maekawa_local","pass":maekawa,"M":m,"V":v})

    no_zero=True
    for i,j in E:
        if i==j or (abs(V[i][0]-V[j][0])<1e-12 and abs(V[i][1]-V[j][1])<1e-12):
            no_zero=False
            break
    checks.append({"name":"no_zero_length_edges","pass":no_zero})

    passed=all(c["pass"] for c in checks)
    # Highest honest claim here is local single-vertex necessary-rule validation.
    return ValidationReport(
        passed=passed,
        level="LOCAL_SINGLE_VERTEX_RULES_PASS" if passed else "FAILED",
        checks=checks,
        certified_finished_model=False,
    )