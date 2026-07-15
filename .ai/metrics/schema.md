# Task event schema

Task events are an append-only decision journal, not a model leaderboard.
Actual events live under `.agent-state/metrics/task-events.jsonl` or another
access-controlled durable store. The event log is pseudonymized, not anonymous.

## Privacy rules

- opaque task IDs only
- enum or bounded identifier fields only; no free-text friction field
- no prompt, source content, transcript, terminal output, private absolute path,
  secret, user identity, or private media-derived text
- capability profile IDs include a version but no credential or account ID

## `routing_reserved`

Required fields:

- `event`, `ts`, `task_id`, `policy_version`
- `area_id`, `task_type`, `risk`, `intended_pattern`
- `sentinel_counter_key`, `routing_sequence`, `sentinel_sequence`
- `non_trivial`, `calibration`, `sentinel`
- `review_required`, `review_reason`

Routing sequence is atomically reserved before implementation. The first 10
non-trivial tasks set `calibration=true`. After calibration, a separate
low-risk-only `sentinel_sequence` makes each fifth task per counter key a
sentinel. It is `null` for tasks outside that counter.

## `task_completed`

Required fields:

- reservation identity and routing fields
- versioned planner, writer, and reviewer capability profile IDs
- `reviewer_relation`, `review_outcome`, `review_rework_rounds`
- implementation, verification, and plan-correction retry counts
- verification `overall`, `passed`, `failed`, `skipped`, and
  `environment_blocked`
- `fallback_reason`, `rate_limit_hits`, and usage status/value/unit when exposed
- categorized human interventions
- `regression_of` when the task fixes an escaped defect

Do not use review finding count as a KPI. At checkpoints, inspect intervention,
rework, retry, blocked proof, rate limits, and escaped defects qualitatively.

## Allowed enums

- task type: `feature`, `bugfix`, `refactor`, `review`, `ops`, `docs`
- risk: `low`, `medium`, `high`
- pattern: `P0`, `P1`, `P2`, `P3`, `P3+P0`, `P3+P1`, `P3+P2`
- review relation: `none`, `fresh_same`, `cross_provider`
- review outcome: `none`, `accepted`, `changes_required`, `blocked`
- verification overall: `passed`, `failed`, `blocked`, `incomplete`
- fallback: `none`, `quota`, `rate_limit`, `availability`, `scope_reduced`
- usage status: `missing`, `approximate`, `reported`
- intervention: `permission_approval`, `scope_decision`,
  `acceptance_clarification`, `environment_recovery`, `safety_stop`
