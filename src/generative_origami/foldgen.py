from __future__ import annotations
import math
from typing import Any
from .models import TargetSpec

FAMILY_RAYS = {
    "QUADRUPED": 8,
    "BIRD": 8,
    "FISH": 8,
    "INSECT": 8,
    "FLOWER": 8,
    "BOX": 4,
    "VEHICLE": 8,
    "DINOSAUR": 8,
    "HUMANOID": 8,
    "GEOMETRIC": 8,
    "GENERIC": 4,
}

def _ray_square_intersection(theta: float) -> tuple[float,float]:
    dx, dy = math.cos(theta), math.sin(theta)
    ts = []
    if abs(dx) > 1e-12:
        for x in (0.0,1.0):
            t=(x-.5)/dx
            if t>0:
                y=.5+t*dy
                if -1e-9<=y<=1+1e-9: ts.append((t,x,min(1,max(0,y))))
    if abs(dy) > 1e-12:
        for y in (0.0,1.0):
            t=(y-.5)/dy
            if t>0:
                x=.5+t*dx
                if -1e-9<=x<=1+1e-9: ts.append((t,min(1,max(0,x)),y))
    _,x,y=min(ts,key=lambda z:z[0])
    return round(x,10), round(y,10)

def _perimeter_s(p: tuple[float,float]) -> float:
    x,y=p
    eps=1e-7
    if abs(y)<eps: return x
    if abs(x-1)<eps: return 1+y
    if abs(y-1)<eps: return 3-x
    return 4-y

def generate_fold(spec: TargetSpec) -> dict[str,Any]:
    n = FAMILY_RAYS.get(spec.family, 4)
    # Target-dependent rotation, while preserving equal sector angles.
    seed = sum(ord(c) for c in spec.canonical_name)
    rotation = (seed % 360) * math.pi/180.0 / max(n,4)

    boundary = [_ray_square_intersection(rotation + 2*math.pi*i/n) for i in range(n)]
    # Deduplicate rare corner collisions.
    uniq=[]
    for p in boundary:
        if p not in uniq: uniq.append(p)
    boundary=uniq
    n=len(boundary)
    if n % 2:
        boundary=boundary[:-1]
        n=len(boundary)

    # For a valid local single-vertex test use 4 or 8 equally spaced rays.
    center=(.5,.5)
    vertices=[list(center)] + [list(p) for p in boundary]

    # Sort boundary points around square perimeter and build boundary edges.
    perimeter_order=sorted(range(n), key=lambda i:_perimeter_s(boundary[i]))
    edges=[]
    assignments=[]
    roles=[]

    # radial creases
    # 4 rays: 3M/1V bird-foot pattern.
    # 8 rays: 5M/3V equal-angle local pattern; validator treats this as
    # necessary/local evidence only, not a finished-model certificate.
    radial_assign = (["M","M","M","V"] if n==4 else ["M","V","M","M","V","M","V","M"][:n])
    for i in range(n):
        edges.append([0,i+1])
        assignments.append(radial_assign[i % len(radial_assign)])
        roles.append("CREASE")

    # boundary edges between consecutive ray hits along square boundary.
    for a,b in zip(perimeter_order, perimeter_order[1:]+perimeter_order[:1]):
        edges.append([a+1,b+1])
        assignments.append("B")
        roles.append("BOUNDARY")

    feature_labels = {}
    if spec.family == "QUADRUPED" and n>=8:
        labels=["HEAD","FRONT_LEFT","FRONT_RIGHT","BODY_A","TAIL","REAR_RIGHT","REAR_LEFT","BODY_B"]
        feature_labels={str(i+1):labels[i] for i in range(min(n,len(labels)))}
    elif spec.family == "BIRD" and n>=8:
        labels=["HEAD","WING_L","WING_L2","TAIL_L","TAIL_R","WING_R2","WING_R","BODY"]
        feature_labels={str(i+1):labels[i] for i in range(min(n,len(labels)))}
    elif spec.family == "FISH" and n>=8:
        labels=["NOSE","FIN_L","BODY_L","TAIL_L","TAIL_R","BODY_R","FIN_R","BODY"]
        feature_labels={str(i+1):labels[i] for i in range(min(n,len(labels)))}

    return {
        "file_spec": 1.2,
        "file_creator": "Generative Origami MVP",
        "file_title": f"{spec.canonical_name} generated base candidate",
        "file_description": "Procedural single-vertex base candidate. It is not automatically a certified finished recognizable model.",
        "file_classes": ["singleModel"],
        "frame_classes": ["creasePattern"],
        "vertices_coords": vertices,
        "edges_vertices": edges,
        "edges_assignment": assignments,
        "edges_go:role": roles,
        "go:target": spec.to_dict(),
        "go:featureLabels": feature_labels,
        "go:generationStage": "PARAMETRIC_BASE_CANDIDATE",
    }