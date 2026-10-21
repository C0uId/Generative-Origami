# PROJECT_STATUS

Date: 2026-10-20

## Repository
Migration status: COMPLETE.

`main` is now the authoritative Generative Origami project baseline. The repository contains the current source, tests, Q4-B01 research implementation, current POC01-007C3-C experiment, required baseline inputs, current Q4 experiments, assets, tools, governance, and current/final documentation.

Superseded C1/C2/C3-A/C3-B experiment trees, chat transcripts, duplicate recommendations, old project-control snapshots, ZIP duplicates, runtime outputs, caches, and other obsolete material are intentionally excluded from the current tree.

## Current engineering stage
PoC-01 mid-stage.

- Q4-B01 medium/medium planar CP and scoped global assessment are accepted (PR #7/#9); physical Base remains `UNVERIFIED_PHYSICAL_BASE`.
- POC01-010A completed finite-grid six-endpoint tree-layout screening.
- No certified physical Q4 crease pattern or independent physical refold evidence exists yet.
- Current retained C3 version: `POC01-007C3-C`.
- Current C3 status: `CONTINUOUS_RIGID_PATH_NOT_CERTIFIED`.
- Existing interval evidence: PASS=71, COLLISION=0, UNCERTAIN=91; continuous closure 162/162 PASS.
- Sequence Planner has not started.

## Verified repository regression
- Core regression: 112/112 PASS.
- Q4 regression on the current task branch: 55/55 PASS (10 new bounded-search tests); merged PR #9 has 45/45 PASS.
- CI is configured to run both suites on pull requests and pushes to `main`.

## Current main bottleneck
Physical BaseCompiler and the Parameter-to-Geometry link are not yet established for a real foldable Q4-B01 base.

## Next engineering task
Issue #8 was independently accepted by TD-PR9-20261020-01; PR #9 merged with Owner authorization as 8aa98005f5d328dd9ce96bcdd4504acdb4a14d21. Its uniform-angle path remains FAIL, and alternate global paths, continuous collision/contact/layers and final material flow remain UNKNOWN.

Owner released Issue #10, Q4-B01-ALTERNATIVE-RIGID-PATH. The bounded forward/backward search is complete and submitted for independent review: each sweep accepts only 2/33 target knots (endpoints), rejects 31 interior targets, and its endpoint interpolant FAILS. No CP infeasibility is inferred; no physical or continuous-path certificate exists. No downstream product or Sequence Planner task is released.
