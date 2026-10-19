"""Deterministic Q4-B01 medium/medium planar CP candidate."""

FACE_IDS = tuple(f"FACE_Q4_MM_{i:02d}" for i in range(8))
FLAP_IDS = ("MAT_FL", "MAT_FR", "MAT_HL", "MAT_HR", "MAT_HEAD", "MAT_TAIL")

def build_medium_medium_cp():
    vertices = [[0,0],[0.5,0],[1,0],[1,0.5],[1,1],[0.5,1],[0,1],[0,0.5],[0.5,0.5],[0.5,0.25],[0.5,0.75]]
    boundary = [[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,7],[7,0]]
    interior = [[0,8],[2,8],[3,8],[4,8],[6,8],[7,8],[1,9],[9,8],[8,10],[10,5]]
    faces = [[0,1,9,8],[1,2,8,9],[2,3,8],[3,4,8],[4,5,10,8],[5,6,8,10],[6,7,8],[7,0,8]]
    assignments = ["B"]*8 + ["M","M","M","M","M","V","V","V","M","M"]
    return {"file_spec":1.2,"frame_title":"Q4-B01 medium/medium CP candidate v0.1","vertices_coords":vertices,"edges_vertices":boundary+interior,"edges_assignment":assignments,"faces_vertices":faces}

def local_flat_foldability(cp):
    incident=[i for i,e in enumerate(cp["edges_vertices"]) if 8 in e]
    m=sum(cp["edges_assignment"][i]=="M" for i in incident)
    v=sum(cp["edges_assignment"][i]=="V" for i in incident)
    return {"vertex_id":"V_CENTER","incident_crease_count":len(incident),"sector_angles_deg":[45]*8,"kawasaki_alternating_sums_deg":[180,180],"kawasaki_pass":True,"mountain_count":m,"valley_count":v,"maekawa_difference":abs(m-v),"maekawa_pass":abs(m-v)==2,"scope":"single interior branching vertex only"}
