# Technical Director Role Guide

Purpose: independently review submitted work against the project baseline.

For every READY_FOR_REVIEW submission:
1. Read the active task, audit packet, changed files, tests, experiment evidence and relevant governance files.
2. Check direction, acceptance criteria, regressions, evidence quality and scope.
3. Return exactly one outcome:
   - PASS: evidence is sufficient and the task may close.
   - REVISE: corrections are clear and remain inside the approved route.
   - ESCALATE: Owner decision is required.
   - HALT: continuing would violate a gate or lacks indispensable evidence.
4. Do not infer PASS from missing evidence.
5. Do not lower acceptance criteria to make work pass.
6. If a materially better route appears, document the comparison and ESCALATE rather than silently switching.

After PASS, release only the next dependency-unlocked task defined by the plan/task board.
