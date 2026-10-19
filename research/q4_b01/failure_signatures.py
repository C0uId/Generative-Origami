"""Read-only prioritization of continuous certificates; never issues PASS."""
import collections
import hashlib
import json
from pathlib import Path

def failing_leaves(node, pointer):
    if node.get("status") in {"PASS", "SAFE"}:
        return
    children = node.get("children", [])
    failed = [(i, c) for i, c in enumerate(children) if c.get("status") not in {"PASS", "SAFE"}]
    if failed:
        for i, child in failed:
            yield from failing_leaves(child, f"{pointer}/children/{i}")
    else:
        yield pointer, node

def summarize(directory):
    groups, counts, sources, seen = {}, collections.Counter(), [], set()
    for path in sorted(Path(directory).glob("interval_*.json")):
        raw = path.read_bytes()
        doc = json.loads(raw)
        index = doc["interval"]
        if index in seen:
            raise ValueError("duplicate interval")
        seen.add(index)
        counts[doc["status"]] += 1
        sources.append({"file": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest()})
        for ci, cell in enumerate(doc["cell_certificates"]):
            for pi, pair in enumerate(cell["pairs"]):
                for pointer, leaf in failing_leaves(pair, f"/cell_certificates/{ci}/pairs/{pi}"):
                    panels = tuple(pair["panels"])
                    reason = leaf.get("reason", "UNSPECIFIED")
                    mode = leaf.get("contact_mode", leaf.get("state")) or "UNKNOWN"
                    key = (panels, reason, mode)
                    group = groups.setdefault(key, {"pair": panels, "reason": reason, "contact_mode": mode,
                        "intervals": set(), "leaf_count": 0, "evidence": []})
                    group["intervals"].add(index)
                    group["leaf_count"] += 1
                    group["evidence"].append({"interval": index, "cell": ci, "pointer": pointer,
                        "time_interval": leaf.get("time_interval"),
                        "source_parameter_interval": cell.get("source_parameter_interval"),
                        "material_patch": leaf.get("material_patch"), "witness": leaf.get("witness"),
                        "missing_fields_are_unknown": True})
    for group in groups.values():
        group["intervals"] = sorted(group["intervals"])
        group["affected_interval_count"] = len(group["intervals"])
    ranked = sorted(groups.values(), key=lambda g: (-g["affected_interval_count"], -g["leaf_count"], g["pair"], g["reason"]))
    return {"scope": "CCD failing leaves only; historical world-z diagnostics excluded; source pointers retain full witnesses",
        "certification_changed": False, "observed_status_counts": dict(counts),
        "complete_interval_coverage": seen == set(range(162)), "sources": sources,
        "ranking_metric": "distinct affected intervals, then failing leaves; counts overlap across pairs",
        "clusters": ranked}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("certificates")
    parser.add_argument("output")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(summarize(args.certificates), ensure_ascii=False, indent=2), encoding="utf-8")