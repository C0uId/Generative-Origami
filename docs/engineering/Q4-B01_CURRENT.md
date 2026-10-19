# Q4-B01 Current Engineering Definition

Status: `TREE_LAYOUT_SCREENED_ONLY` / `UNVERIFIED_PHYSICAL_BASE`

This document is the current consolidated Q4-B01 engineering definition. It replaces the separate v0.1 material-definition document and the v0.2 review supplement for repository use.

## 1. Base identity and product boundary

- Base ID: `Q4-B01`
- Name: Generic Canid Quadruped Base / 简化犬科站立四足基础模型
- Intended family: dog / fox / simplified canid targets
- Paper: one 200 mm × 200 mm square sheet
- First version: no cutting, no glue
- Logical grid: 16 × 16, 12.5 mm per cell
- Current claim boundary: material semantics and finite layout screening only; no certified physical CP or continuous path has been established for Q4-B01.

## 2. Stable semantic material regions

| Stable ID | Role | Material-space range | Grid | Area |
|---|---|---|---|---:|
| `MAT_FL` | front-left leg | x=0–50, y=150–200 mm | C1–4 / R13–16 | 2,500 mm² |
| `MAT_HEAD` | head + short neck | x=50–150, y=150–200 mm | C5–12 / R13–16 | 5,000 mm² |
| `MAT_FR` | front-right leg | x=150–200, y=150–200 mm | C13–16 / R13–16 | 2,500 mm² |
| `MAT_BODY` | body core | x=0–200, y=50–150 mm | C1–16 / R5–12 | 20,000 mm² |
| `MAT_HL` | hind-left leg | x=0–50, y=0–50 mm | C1–4 / R1–4 | 2,500 mm² |
| `MAT_TAIL` | tail | x=50–150, y=0–50 mm | C5–12 / R1–4 | 5,000 mm² |
| `MAT_HR` | hind-right leg | x=150–200, y=0–50 mm | C13–16 / R1–4 | 2,500 mm² |

Total: 40,000 mm² = 100% of the sheet.

Coordinates use origin at the lower-left of the unfolded sheet. Stable material IDs are semantic identifiers and must not be replaced by rendering-array indices.

## 3. Boundary and ownership rules

- Point lookup uses left/bottom closed and right/top open region boundaries, with the outer sheet boundary included.
- Face/material mapping uses exact overlap area; zero-area shared boundaries do not duplicate material ownership.
- Material-region semantic ownership stays fixed within Q4-B01 v0.x.
- Parameter changes may alter effective material-source paths or internal crease geometry, but may not silently reassign semantic ownership between regions.
- If the physical CP requires materially different ownership or additional independent ear/nose/limb flaps, the Base version must change.

## 4. First-stage parameter contract

Only two material-budget dimensions are open initially:

- `leg_budget`: controls usable material path for the four leg regions. Increasing it must not reduce effective leg material length.
- `tail_budget`: controls usable material path for `MAT_TAIL`. Increasing it must not reduce effective tail material length.

`head_preset`, short-neck preset, ear preset, nose preset and stance are fixed in the first stage.

For research screening, short / medium / long map to candidate inward distances 12.5 / 25 / 37.5 mm. These are exploration values, not certified physical flap lengths.

The certified parameter domain is currently empty. Out-of-domain or unsupported requests must not be silently presented as certified samples.

## 5. Current finite-layout result

POC01-010A connects four legs, head and tail through a fixed FRONT/REAR tree and screens a finite 4×4 positional grid for each of the 3×3 leg/tail budget combinations.

All nine parameter combinations have at least one candidate satisfying the chosen tree-path distance inequalities on that finite grid.

This result proves only the stated finite layout inequalities. It does **not** prove:

- a valid crease pattern;
- flap/material-flow realizability;
- mountain/valley assignment;
- layer order;
- continuous collision-free folding;
- physical foldability.

Current state remains `TREE_LAYOUT_SCREENED_ONLY`.

## 6. Required Parameter-to-Geometry evidence

A parameterized Q4-B01 implementation is not accepted until:

- changing `leg_budget` or `tail_budget` changes real coordinates, crease structure or real material allocation by design;
- geometry and topology hashes are versioned and reproducible;
- directional invariants follow the physical parameter definition;
- boundary rejection / explicit approximation behavior is recorded;
- each retained preset has fixed seed/version and an independent evidence record;
- metadata-only or animal-name changes are never used as geometry-sensitivity evidence.

## 7. Physical Base gate

Before Q4-B01 may be called a physical Base, the project needs:

- a real foldable specimen from square paper;
- actual paper profile, thickness/weight where measurable, batch or traceable source;
- a complete CP reconstructed from the physical sheet;
- mountain/valley/boundary/front-back cross-check against FOLD data;
- full macro-action recording from flat sheet to final state;
- stable face/flap/material IDs throughout the sequence;
- evidence mapping all seven material regions to final semantic parts;
- at least two independent successful refolds beyond the first design specimen;
- provenance and rights records sufficient for intended project use.

For A/B/C configurations, each configuration needs its own repeatable geometry and physical/trajectory evidence before certification.

## 8. Immediate next task

Use the `medium/medium` screened layout only as the first controlled CP-design input. Construct a FRONT–REAR body material channel and explicit leg/head/tail crease units, test compatibility with the stable material regions, then generate a complete CP and run planar geometry, local fold constraints, global path validation and physical refolding.

Do not start Sequence Planner or treat APP work as the core path until the real Base and continuous-path gates are satisfied.