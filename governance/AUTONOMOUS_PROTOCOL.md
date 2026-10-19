# Autonomous R&D Review Protocol v1.0

## Roles
- Developer: implements the current approved task and produces evidence.
- Technical Director: reviews evidence against project baseline and acceptance gates.
- Orchestrator: converts the review result into the next repository state.
- Owner: handles only escalated decisions.

## State machine

BACKLOG -> READY -> IN_PROGRESS -> READY_FOR_REVIEW -> REVIEWING

Review outcomes:
- PASS: current task closes and the next dependency-unlocked task becomes READY.
- REVISE: current task returns to IN_PROGRESS with required corrections.
- ESCALATE: work pauses at the decision boundary and an Owner decision record is requested.
- HALT: work stops because continuing would violate a project gate or lacks required evidence.

## Audit packet
Each completed execution cycle records:
- task_id
- objective
- baseline references
- commit/ref
- changed files
- tests and experiments
- evidence paths
- known failures
- unresolved questions
- architecture_change
- baseline_change
- recommended_next_task

## Review result
Each review records:
- review_id
- task_id
- outcome
- direction_check
- acceptance_check
- regression_check
- evidence_check
- blocking issues
- required changes
- next task when PASS
- escalation reason when ESCALATE/HALT
- confidence

## Escalation triggers
Owner review is requested when one or more of these occur:
- a proposed change materially changes project goal, architecture, Base strategy, or acceptance gate;
- two or more materially different routes remain viable and the choice changes project strategy;
- a new route appears materially better but requires changing the approved baseline;
- the same task receives three consecutive REVISE results;
- five consecutive experiments show no material improvement on the blocking metric;
- required physical/licensing/source evidence cannot be obtained;
- the current route becomes infeasible under the accepted constraints.

## Authority levels
- L0: implementation details and ordinary bug fixes.
- L1: local design changes inside an approved module.
- L2: module-level redesign that preserves project goal and acceptance gates; record it in the decision log.
- L3: project goal, architecture, Base strategy, major schedule/cost/quality tradeoff, or acceptance-gate change; route to Owner.
