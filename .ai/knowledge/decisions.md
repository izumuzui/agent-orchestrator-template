# Decision journal

Record durable decisions, not transcripts or hidden reasoning.

| Date | Decision | Status | Revisit trigger |
|---|---|---|---|
| 2026-07-15 | Separate quality routing from quota-aware scheduling | active | routing evidence contradicts the split |
| 2026-07-15 | Keep one writer; parallelize only read-only investigation and review | active | isolated worktrees replace the shared worktree |
| 2026-07-15 | Use Pattern C as the initial P2 assignment, not a model ranking | experiment | first 10 non-trivial tasks or model/contract change |
| 2026-07-15 | Require independent review for calibration tasks and high-risk changes | experiment | first 10-task checkpoint |
| 2026-07-15 | Store raw task events outside Git and commit only schema and aggregate decisions | active | approved durable telemetry store changes |

At each checkpoint, record what changed, what evidence supported it, and the
next review trigger. Do not use review finding counts as a success metric.
