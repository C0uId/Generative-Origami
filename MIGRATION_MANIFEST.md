# Project Migration Manifest

This tree is the canonical current-state snapshot assembled from the supplied project archives and documents.

## Version precedence used
1. Current engine source and tests from the latest executable C3-C-compatible project snapshot.
2. `POC01-007C3-C` is the only retained C3 experiment version.
3. Q4-B01 v0.2 changes are applied to the current project.
4. POC01-010A changes supersede corresponding Q4-B01 v0.2 files.
5. Current standalone repair/demo files supplement the engine where still referenced.
6. Only current/final project documents are retained.

## Intentionally removed
- POC01-007C1, POC01-007C2, POC01-007C3-A, POC01-007C3-B directories;
- superseded end-to-end snapshots whose useful behavior is already covered by current tests/assets;
- chat transcripts and conversation exports;
- old ROADMAP / DECISIONS / project-control snapshots;
- duplicate recommendations already covered by the final implementation plan and current engineering priorities;
- duplicate ZIP snapshots, runtime outputs, work backups, `__pycache__`, `.pyc` files.

## Large evidence policy
Only current C3-C large generated evidence is tracked by immutable hashes in `experiments/large_evidence_manifest.json`.
The payload itself belongs in Git LFS or dedicated artifact storage; older C3-A/B evidence is not retained as part of the current repository.

## Migration acceptance
The repository is considered the authoritative project baseline only when source, tests, current experiments, current documentation and current large-evidence references are all present and regression tests pass.

## Verified after current-state pruning
- Core regression: 112/112 PASS.
- Q4 / POC01-010A regression: 28/28 PASS.
- No current test or tool path depends on `experiments/legacy/`.