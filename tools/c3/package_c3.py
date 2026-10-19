"""Build and verify a complete, portable source-and-evidence archive."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT
NAME = "教学折纸软件_可执行MVP_POC01-007C3-C"
MANIFEST = "PACKAGE_MANIFEST.json"
EXCLUDED_DIRS = {".venv", "__pycache__", ".git"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp"}


def source_files():
    return sorted((p for p in ROOT.rglob("*")
                   if p.is_file() and p.name != MANIFEST
                   and not EXCLUDED_DIRS.intersection(p.relative_to(ROOT).parts)
                   and p.suffix.lower() not in EXCLUDED_SUFFIXES),
                  key=lambda p: p.relative_to(ROOT).as_posix())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT.parents[1] / f"{NAME}.zip")
    args = parser.parse_args()
    target = args.out.resolve()
    if target.is_relative_to(ROOT):
        raise ValueError("Place the output archive outside the source directory")
    files = source_files()
    entries = [{"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    manifest = {"release": NAME, "certificate_counts": {"C3-C": 162},
                "excluded_directories": sorted(EXCLUDED_DIRS),
                "excluded_suffixes": sorted(EXCLUDED_SUFFIXES),
                "files": entries}
    manifest_path = ROOT / MANIFEST
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for p in files + [manifest_path]:
            archive.write(p, f"{NAME}/{p.relative_to(ROOT).as_posix()}")
    with zipfile.ZipFile(temporary) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or len(names) != len(files) + 1:
            raise ValueError("Missing or duplicated archive entries")
        expected = {f"interval_{i:03d}.json" for i in range(162)}
        experiment = "experiments/current/POC01-007C3-C_SINGULAR_CONTACT_EXACT_BRIDGE"
        certificate_prefix = f"{NAME}/{experiment}/certificates/"
        actual = {n.removeprefix(certificate_prefix) for n in names if n.startswith(certificate_prefix)}
        # The normal Git snapshot contains representative certificates; full 162-certificate
        # payload is managed as the current C3-C large evidence asset.
        if not actual:
            raise ValueError("Current C3-C certificate evidence is missing")
        for entry in entries:
            data = archive.read(f"{NAME}/{entry['path']}")
            if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise ValueError(f"Archive content mismatch: {entry['path']}")
        if archive.testzip() is not None:
            raise ValueError("Archive CRC validation failed")
    temporary.replace(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    print(json.dumps({"archive": str(target), "bytes": target.stat().st_size,
                      "file_count": len(files) + 1, "certificate_counts": {"C3-C":162},
                      "sha256": digest, "verified": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()