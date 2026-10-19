# REVIEW_RESULT template

Required fields: review id, task id, outcome (PASS / REVISE / ESCALATE / HALT), direction check, acceptance check, regression check, evidence check, blocking issues, required changes, next task, escalation reason, confidence.

Routing semantics:
- PASS: close current task and release the next dependency-unlocked task.
- REVISE: return current task with required corrections.
- ESCALATE: pause at a decision boundary and notify Owner.
- HALT: stop because a project gate is violated or required evidence is missing.
