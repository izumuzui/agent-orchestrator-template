# Task handoff

## Identity

- task_id: `{{TASK_ID}}`
- status: planned
- acceptance_version: 1

## Reviewer bootstrap packet

- requirement_sources:
- allowed_scope:
- forbidden_scope:
- risk_class:
- risk_overlay:

Do not include the writer's acceptance or plan in the bootstrap packet sent for
source-first derivation.

## Routing

- policy_version: v1
- area_id:
- task_type:
- intended_pattern:
- routing_sequence:
- sentinel_sequence:
- sentinel_counter_key:
- sentinel:
- review_required:
- actual_assignment:
- fallback_reason: none

## Frozen acceptance

| ID | Condition | Requirement source |
|---|---|---|
| A1 |  |  |

Changing meaning after the writer starts requires a new acceptance version and
a recorded scope decision.

## Proof and stop

- focused_proof:
- common_proof: `scripts/agent/verify-change.sh full`
- required_checks:
- non_required_checks:
- max_fix_rounds: 3
- same_failure_reconsider_after: 2

## Changes

Concise summary; no transcript, hidden reasoning, secrets, raw private content,
private absolute paths, or terminal dump.

## Verification

- overall: incomplete
- passed:
- failed:
- skipped:
- environment_blocked:

## Review

- reviewer_relation: none
- review_outcome: none
- rework_rounds: 0

## Remaining issues

- blockers:
- residual_risks:

## Changed files

Repository-relative paths only.
