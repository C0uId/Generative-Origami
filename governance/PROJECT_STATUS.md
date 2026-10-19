# PROJECT_STATUS

Date: 2026-10-19

## Repository
Migration status: COMPLETE.

`main` is now the authoritative Generative Origami project baseline. The repository contains the current source, tests, Q4-B01 research implementation, current POC01-007C3-C experiment, required baseline inputs, current Q4 experiments, assets, tools, governance, and current/final documentation.

Superseded C1/C2/C3-A/C3-B experiment trees, chat transcripts, duplicate recommendations, old project-control snapshots, ZIP duplicates, runtime outputs, caches, and other obsolete material are intentionally excluded from the current tree.

## Current engineering stage
PoC-01 mid-stage.

- Q4-B01 remains `TREE_LAYOUT_SCREENED_ONLY` / `UNVERIFIED_PHYSICAL_BASE`.
- POC01-010A completed finite-grid six-endpoint tree-layout screening.
- No certified physical Q4 crease pattern or independent physical refold evidence exists yet.
- Current retained C3 version: `POC01-007C3-C`.
- Current C3 status: `CONTINUOUS_RIGID_PATH_NOT_CERTIFIED`.
- Existing interval evidence: PASS=71, COLLISION=0, UNCERTAIN=91; continuous closure 162/162 PASS.
- Sequence Planner has not started.

## Verified repository regression
- Core regression: 112/112 PASS.
- Q4 / POC01-010A regression: 28/28 PASS.
- CI is configured to run both suites on pull requests and pushes to `main`.

## Current main bottleneck
Physical BaseCompiler and the Parameter-to-Geometry link are not yet established for a real foldable Q4-B01 base.

## Next engineering task
Use the medium/medium screened layout as the first crease-pattern design candidate. Establish the FRONT-REAR body material channel and the leg/head/tail crease units, validate compatibility with the fixed semantic material regions, then produce the first real CP candidate without claiming physical certification prematurely.
