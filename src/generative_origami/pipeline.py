from __future__ import annotations
import json, re
from pathlib import Path
from .semantic import parse_target
from .foldgen import generate_fold
from .validate import validate_fold
from .tutorial import build_tutorial
from .svg import render_svg
from .fallback import fallback_links

def slugify(text: str) -> str:
    s=re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+","_",text.strip())
    return (s[:60] or "query")

def generate(query: str, output_root: str|Path|None=None) -> dict:
    spec=parse_target(query)
    fold=generate_fold(spec)
    validation=validate_fold(fold)
    tutorial=build_tutorial(spec,fold,validation)
    svg=render_svg(spec,fold,validation)

    # The system always returns a result. "generated" is honest about confidence.
    generation_status = (
        "GENERATED_BASE_VALIDATED_LOCALLY"
        if validation.passed else "GENERATION_REJECTED"
    )
    product_status = "RESULT_AVAILABLE"
    result={
        "query":query,
        "product_status":product_status,
        "generation_status":generation_status,
        "target":spec.to_dict(),
        "validation":validation.to_dict(),
        "tutorial":tutorial,
        "fallback_links":fallback_links(query),
        "guarantee":{
            "search_always_returns_result":True,
            "finished_model_universally_verified":False,
            "meaning":"当前可保证任何查询都有生成候选+兜底；只有通过对应高级求解器后才能宣称最终成品可折。"
        }
    }

    if output_root is not None:
        out=Path(output_root)/slugify(query)
        out.mkdir(parents=True,exist_ok=True)
        (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        (out/"candidate.fold").write_text(json.dumps(fold,ensure_ascii=False,indent=2),encoding="utf-8")
        (out/"tutorial.json").write_text(json.dumps(tutorial,ensure_ascii=False,indent=2),encoding="utf-8")
        (out/"preview.svg").write_text(svg,encoding="utf-8")
        result["artifact_dir"]=str(out)
        result["preview_svg"]="preview.svg"
    else:
        result["preview_svg_inline"]=svg
    return result