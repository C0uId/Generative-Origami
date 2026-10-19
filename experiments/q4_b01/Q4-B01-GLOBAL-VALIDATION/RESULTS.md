# Q4-B01 global validation: scoped result

Baseline: merged PR #7 (`15346c22d2d57fa77711c93cf9b260f0939cce8a`), task release
`fede5447080749890fb1e509ea42319a35ad1552`. Candidate geometry and M/V are unchanged.

## Results and limits

| Gate | Result | Exact scope |
|---|---|---|
| Planar square intake | PASS | Complete unit-square faces; no physical implication |
| Interior V08, degree 8 | PASS | Measured Kawasaki 180/180 degrees; Maekawa 5M/3V |
| Interior V09, degree 2 | PASS | Collinear subdivision, 180/180 degrees; 0M/2V |
| Interior V10, degree 2 | PASS | Collinear subdivision, 180/180 degrees; 2M/0V |
| Defined uniform-angle path | FAIL | A nonzero closure/seam sample disproves this path |
| Existence of another global rigid path | UNKNOWN | No exhaustive search or infeasibility proof |
| Continuous collision/contact/layer order | UNKNOWN | No closed nontrivial path to certify |
| Planar semantic ownership | PASS | Exact original polygon overlap; seven stable material IDs |
| Final assembled 3D semantic material flow | UNKNOWN | Nonclosing transforms are not a folded specimen |
| Physical Base certification | UNVERIFIED | No specimen or independent refolds exist |

Local checks enumerate all interior vertices, excluding boundary vertices from
interior theorems. Sector angles come from actual coordinates, not preset 45
degree constants. Kawasaki/Maekawa are necessary all-active flat-fold checks,
not a sufficient global criterion or a general partial-fold infeasibility test.

## Solver assessment and experiment

`SingleVertexMechanism` supports even degree >= 4; the old input convention
assumes the branching center is vertex 0. The new adapter reindexes center V08,
checks that other interior vertices are collinear degree-two subdivisions with
matching M/V, and proves one original face occupies each radial sector. The
adapter declines unsupported general multi-vertex inputs rather than importing
a previous C3 certificate. Full original face polygons and material mappings
are retained. Solver ray triangles terminate at short subdivisions and are
therefore deliberately not used as Q4 collision geometry.

The tested continuous formula is q_k(t)=sign_k*pi*t, V=+1 and M=-1, t in [0,1].
Nine deterministic samples t=0,1/8,...,1 check rotation closure and every shared
vertex's copies in the full per-face rigid representation. Rotation tolerance
is 1e-8 rad; seam tolerance is 1e-8 normalized sheet units (0.000002 mm for
200 mm paper). The flat and fully folded endpoints pass closure, but every
intermediate sample fails. At t=1/2, closure residual is approximately
2.680409687897 rad and the maximum seam gap is 0.898408786493 sheet units.
These finite-tolerance counterexamples are far from the thresholds. Thus this
specific continuous formula is not a valid rigid folding path. Even if every
sample had passed, the interval result would remain UNKNOWN without continuous
bounds. Failure of this one path is not CP infeasibility and does not trigger
a Base-strategy change.

Per-face transforms preserve lengths, original face IDs and exact material
ownership. The machine report includes their complete vertices at each sample;
they do not assemble across a failed seam. No triangle collision result,
contact classification, signed-gap bound or layer order is promoted to PASS.
The existing hybrid/continuous solvers require a specified valid mechanism
curve and closure evidence; applying C3 interval results to this candidate
would not supply those missing inputs.

## Reproduction and evidence

From repository root, after installing `requirements-research.txt`:

```text
python experiments/q4_b01/run_q4_global_validation.py
PYTHONPATH=src:research/q4_b01:. python -m unittest discover -s tests/q4_b01 -v
PYTHONPATH=src:. python -m unittest discover -s tests/core -v
```

On Windows use semicolons in PYTHONPATH. `environment.json` records the run
versions; seed=0, probe times, formulas and tolerances are fixed. The manifest
uses exact-file SHA-256 for artifacts and implementation/solver sources, while
CP geometry/topology hashes retain the existing canonical intake convention.
Scoped `.gitattributes` entries require LF for all hashed text paths so exact
file checksums survive Windows/Linux checkouts without normalizing hash inputs.
Regenerate the manifest after changing any recorded source or kit file.

Local validation: Q4 regression 45/45 PASS (11 new tests); core regression
112/112 PASS. Software test PASS includes checking that the deliberately tested
uniform-angle path reports FAIL; it does not turn the path result into PASS.
Current-task GitHub PR checks are tracked separately in the PR/AUDIT_PACKET.

`candidate.fold`, `printable_cp.svg`, `stable_ids.json`, `REFOLD_CHECKLIST.md`
and `physical_evidence_template.json` form the diagnostic human-test package.
The SVG has a 200 mm square and an A4 page, M/V legend and front/back convention.
The blank template explicitly records no specimen or independent repeats.
It is not evidence that folding has occurred or a validated action sequence.

## Review handoff

Review the adequacy of the scoped checks and diagnostic package. Alternative
path construction, continuous contact/collision/closure certification, final
material flow and actual independent physical refolds remain unresolved.
Physical evidence is not the sole remaining gate. No strategy/architecture or
acceptance baseline change is proposed; no next task is released. Technical
Director decides PASS / REVISE / ESCALATE / HALT.
