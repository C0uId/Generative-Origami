"""POC01-007C3-A: audit the provided rigid keyframes continuously.

Exit 0: every interval certified; 2: completed audit but NOT certified;
3: unavailable backend or invalid input. Exit 2 is an expected research result.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
sys.path.insert(0, str(REPO_ROOT / "src"))

from generative_origami.foldgen import generate_fold
from generative_origami.semantic import parse_target
from generative_origami.simulation import SingleVertexMechanism
from generative_origami.simulation.ccd_adapter import BackendUnavailable, get_backend
from generative_origami.simulation.continuous_ccd import CertificationConfig, ContinuousPathCertifier

DEFAULT_INPUT = REPO_ROOT / "experiments" / "current" / "baseline_inputs" / "dog_layer_order_keyframes.json"
DEFAULT_OUTPUT = REPO_ROOT / "experiments" / "legacy" / "POC01-007C3-A_CONTINUOUS_CCD"


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Conservative continuous rigid-path certification; never certify from frames alone")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--backend", choices=["reference", "native"], default="reference")
    parser.add_argument("--curve-depth", type=int, default=3)
    parser.add_argument("--feature-budget", type=int, default=64)
    parser.add_argument("--closure-tolerance", type=float, default=4e-6)
    parser.add_argument("--layer-order", default="7,6,5,0,4,1,3,2")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    try:
        backend = get_backend(args.backend)
        config = CertificationConfig(closure_tolerance=args.closure_tolerance,
                                     max_curve_depth=args.curve_depth,
                                     max_feature_subdivisions=args.feature_budget)
        frames = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(frames, list):
            raise ValueError("Input must contain the saved list of rigid keyframe records")
        mechanism = SingleVertexMechanism(generate_fold(parse_target("狗")))
        order = [int(x.strip()) for x in args.layer_order.split(",")]
        certifier = ContinuousPathCertifier(mechanism, layer_order=order, config=config, backend=backend)
        counts = Counter()
        def checkpoint(certificate):
            counts[certificate["status"]] += 1
            i = certificate["interval"]
            write_json(args.out / "certificates" / f"interval_{i:03d}.json", certificate)
            if i % 10 == 0 or i == len(frames) - 2:
                print(f"interval {i:03d}/{len(frames)-2:03d}: {certificate['status']}; counts={dict(counts)}", flush=True)
        report = certifier.certify_frames(frames, source_path=args.input, progress_callback=checkpoint)
        report["elapsed_seconds"] = time.perf_counter() - started
        report["source_file"] = str(args.input.relative_to(ROOT)) if args.input.is_relative_to(ROOT) else args.input.name
        write_json(args.out / "interval_certificates.json", report)
        summary = {k: v for k, v in report.items() if k != "intervals"}
        summary["reason_counts"] = dict(Counter(r for c in report["intervals"] for r in c["reasons"]))
        summary["feature_statistics"] = {
            key: sum(p["stats"][key] for c in report["intervals"] for p in c["pairs"])
            for key in ("broad_phase_checks", "broad_phase_rejects", "vertex_face_queries", "edge_edge_queries")
        }
        write_json(args.out / "report.json", summary)
        table = ["# Continuous interval certificates", "", "Each row references its complete JSON certificate.", "",
                 "| Interval | Keyframes | Result | Reasons |", "| --- | --- | --- | --- |"]
        for c in report["intervals"]:
            i = c["interval"]
            table.append(f"| [{i:03d}](certificates/interval_{i:03d}.json) | {i} → {i+1} | {c['status']} | {'; '.join(c['reasons'])} |")
        (args.out / "INTERVAL_SUMMARY.md").write_text("\n".join(table) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if report["continuous_collision_detection_certified"] else 2
    except (BackendUnavailable, ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "UNCERTAIN", "reason": "BACKEND_OR_INPUT_UNAVAILABLE",
                          "error": str(exc), "continuous_collision_detection_certified": False}, ensure_ascii=False), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())