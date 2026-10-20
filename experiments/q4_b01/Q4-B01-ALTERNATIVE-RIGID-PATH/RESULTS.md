# Q4-B01 alternative rigid-path investigation

Issue #10; unchanged CP from accepted PR #7 and reviewed PR #9. Baseline merge:
`8aa98005f5d328dd9ce96bcdd4504acdb4a14d21`.

## Result

The bounded search found **no accepted interior target configuration**. Each
direction retained 2/33 requested knots (only t=0 and t=1), rejected all 31
interior targets, and produced a FAIL for the linear interpolant between its
retained endpoints. There is no new continuous rigid path certificate.

This is a finite-search result, not CP infeasibility. Global foldability,
continuous rigid-path existence, collision/contact/signed-gap/layer order,
final semantic material flow and physical certification remain UNKNOWN or
unverified. The existing seven uniform-path counterexamples remain intact.

At requested t=1/2, both sweeps returned closure residual 0.00352681525521 rad,
full-face seam gap 0.00124281149343 sheet units, and actual mean signed-angle
progress 0.466898926315 instead of 0.5. All exceed their 1e-8 acceptance
tolerances. The lower closure residual than the previous uniform probe is
not a validated path improvement. The maximum retained-knot angle jump is
8.88576587632 rad (L2), spanning the entire unresolved interval.

## Predeclared bounded method

- Two sweeps, forward and backward, each with 33 targets t=i/32.
- Progress is mean(sign_k*q_k)/pi. Signed angles are bounded to [0, pi].
- Existing checked fan adapter and SingleVertexMechanism closure residual;
  scipy least_squares TRF, ftol=xtol=gtol=1e-12.
- At most 300 actual residual evaluations per interior solve, **including**
  finite-difference evaluations. The explicit counter interrupts the solver
  and retains the best evaluated trial at exhaustion. No hidden retries.
- Initial signed angles are the last accepted state plus pi*delta_t, clipped
  strictly inside the bounds. Both endpoints are directly evaluated.
- Independent acceptance uses SciPy quaternion rotation products about fixed
  material axes, full original polygon shared-vertex gaps and pairwise face
  distance preservation, M/V bounds and progress. Solver status is diagnostic,
  not acceptance. Some optimizer terminations still fail these gates.
- Each retained-knot segment is checked at 1/4, 1/2 and 3/4. A counterexample
  gives FAIL for that interpolant; finite passing samples could only give UNKNOWN.

Actual residual calls: forward 8,725; backward 8,763. All accepted and rejected
target trials, initial guesses, solver termination, actual call count, full-face
IDs, original crease-angle IDs and independent checks are in search_report.json.
The two sweeps are not independent strategy proofs. Because neither accepts
an interior target, most initial guesses reduce to the same uniform seed;
symmetry and the limited budget may explain stagnation. No exhaustive search,
branch selection theorem or global impossibility argument was attempted.

The checker additionally has a positive analytic control: folding only the
two opposite collinear valley half-rays by pi/2 is a closing straight hinge.
It uses two creases and is not the requested all-crease endpoint connection.
This control reinforces why failure of the search must not imply CP infeasibility.

## Traceability and regression

The original CP and accepted evidence are unchanged. Each state retains all
eight original face IDs and their full material polygons; material ownership
references the already verified stable_ids.json (seven regions, 40,000 mm2).
No shortened solver triangles are used for collision claims. No physical
evidence records are populated or reclassified.

New regressions cover known negative and positive configurations, independent
matrix agreement, wrong-progress and full-turn rejection, nonfinite inputs,
strict budget exhaustion and failure retention, interpolation counterexamples,
UNKNOWN preservation, replay of every stored trial and exact-byte hashes.

Reproduce from repository root using requirements-research.txt:

```text
python experiments/q4_b01/run_q4_rigid_path_search.py
PYTHONPATH=src:research/q4_b01:. python -m unittest discover -s tests/q4_b01 -v
```

On Windows, PYTHONPATH uses semicolons. Runtime versions and exact source/data
hashes accompany the report. Numerical reproduction is assessed at declared
tolerances across dependency versions; same-environment replay is deterministic.

## Handoff and stop

The two released sweeps are complete; no further unbudgeted search is run.
Acceptance metric: accepted interior target count remains zero. Conservatively
counting the prior uniform formula and these two sweeps gives three unsuccessful
investigations, below the five-no-improvement escalation threshold. Reproduction
and unit-test controls are not new search strategies or new successes.

Independent Technical Director should review the bounded negative evidence and
decide PASS / REVISE / ESCALATE / HALT. A future seeded/asymmetric continuation
needs explicit scope and remaining experiment budget. No Base strategy,
architecture or key gate change is proposed. Downstream tasks remain gated.
