from __future__ import annotations
from typing import Any

def build_tutorial(spec, fold, validation) -> dict[str,Any]:
    if not validation.passed:
        return {
            "status":"REJECTED",
            "steps":[],
            "warning":"Geometry validation failed; no tutorial is emitted."
        }

    crease_ids=[i for i,a in enumerate(fold["edges_assignment"]) if a in {"M","V"}]
    return {
        "status":"BASE_CONSTRUCTION_ONLY",
        "certified_finished_model":False,
        "steps":[
            {
                "step":1,
                "action":"ORIENT",
                "instruction":"将正方形纸平放，中心点作为 C0。",
                "verified":True
            },
            {
                "step":2,
                "action":"PRECREASE",
                "crease_edges":crease_ids,
                "instruction":"按生成折痕图建立预折线；山/谷方向见 FOLD 数据。",
                "verified":"local_geometry_only"
            },
            {
                "step":3,
                "action":"COLLAPSE_BASE",
                "instruction":"沿中心单顶点折痕收拢为参数化基础形。",
                "verified":"local_single_vertex_rules"
            },
            {
                "step":4,
                "action":"SHAPING_GATE",
                "instruction":"进入造型阶段前必须由刚性路径/碰撞求解器验证；当前版本不伪造该步骤。",
                "verified":False
            }
        ],
        "warning":"这是可执行的生成基础形教程，不等于已验证的最终可识别成品教程。"
    }