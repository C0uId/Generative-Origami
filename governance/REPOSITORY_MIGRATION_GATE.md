# Repository Migration Gate

Status: COMPLETE on 2026-10-19.

The Generative Origami repository has been consolidated into a single current project tree and `main` is the authoritative project baseline.

## Completion evidence
- obsolete and duplicate snapshots removed from the current tree;
- only POC01-007C3-C retained as the current C3 experiment version;
- current source and tools committed;
- current core and Q4 tests committed;
- Q4-B01 / POC01-010A implementation and evidence committed;
- current FOLD/SVG/demo assets committed;
- current/final engineering and implementation-plan documents committed;
- governance and Agent audit protocol retained;
- large evidence policy represented by `experiments/large_evidence_manifest.json`;
- core regression verified at 112/112 PASS;
- Q4 / POC01-010A regression verified at 28/28 PASS.

## Repository policy going forward
Do not recreate parallel archive trees inside the repository. Git history is the history mechanism.

A superseded implementation or experiment directory should be removed from the current tree once its useful behavior/evidence is incorporated into the new current version and no current code depends on it.

Generated evidence too large for normal source history should use an immutable artifact/LFS-style store plus SHA-256 manifest and reproducibility metadata rather than duplicate ZIP snapshots.
