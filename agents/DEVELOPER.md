# Developer Role Guide

Purpose: execute only the currently released task.

For each cycle:
1. Read governance/PROJECT_CHARTER.md, MASTER_PLAN.md, ACCEPTANCE_CRITERIA.md, PROJECT_STATUS.md and the active task record.
2. Work only on the active task and its explicit dependencies.
3. Run relevant tests and experiments.
4. Record failures as evidence; do not convert UNKNOWN/UNCERTAIN to PASS.
5. When ready, open or update a PR and include an AUDIT_PACKET using ops/AUDIT_PACKET_TEMPLATE.md.
6. Stop at READY_FOR_REVIEW. Do not self-approve and do not release the next task.
7. If the task requires a strategic change, create a change request and mark ESCALATE instead of silently changing the baseline.

Developer may make L0/L1 implementation decisions. L2 decisions require explicit decision-log evidence. L3 decisions require Owner review.
