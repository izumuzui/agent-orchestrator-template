# Harness maintenance and evaluation (opt-in)

Use a separately scoped session after 5–10 cases, at a manual weekly checkpoint,
or for repeated/severe incidents. No background monitoring is installed. Read
selected sanitized records only; logs do not become always-on context.

## Current inventory and proposal gaps

Baseline: main at 761e66a. This is a source inspection, not a claim that any
provider feature or deployed project has been verified.

| Existing source | Already provides | Remaining gap / change slice |
|---|---|---|
| feedback.py, feedback-loop.md | scoped curated corrections, promotion with evidence/prevention, rejection/retirement | separate unconfirmed capture; observation helper PR |
| orchestration.md, review.md | one writer, bounded fresh read-only review | frozen feedback evidence, optional investigator and deferred triage guide PR |
| change.md, handoffs/template.md | source-first acceptance and versioning | seven-axis requirements/design milestone rubric PR |
| metrics/schema.md, routing.md | task outcomes, calibration, review policy | comparable harness experiments, rule cost/retirement; this guide PR |
| sync.py health, guard.py, manifest.json | distribution integrity and operating health | health is not quality evaluation; use the experiment below |
| session-notes tooling | session note extraction | notes are not classified feedback or proof of cause |
| AGENTS.md / CLAUDE.md | thin adapters and safety parity check | no new blanket rule needed for these opt-in extensions |

The four slices may be reviewed independently. Existing feedback is sufficient
for verified defects; a second curated lesson store would duplicate it. Reuse
local task state for observations. Provider-specific agent definitions, hooks
and automatic rewriting remain deferred until pilot evidence warrants them.

## Placement and consolidation

Inventory each candidate instruction by source, scope, trigger, owner, actual
mechanism and overlap. Specs/decisions belong in project docs/ADRs; repeated
procedures in a workflow or Skill; always-needed routing/safety in thin adapters;
mechanical quality in tests/lint/CI; dangerous operations in actual permissions
or hooks with explicit approval. A written prohibition is not enforcement, and
a Skill is not automatically a guardrail. Avoid absolute adapter line targets.

Before adding a rule, check existing equivalent/contradictory rules, whether
they were available and followed, and alternative causes: ambiguous spec,
missing information, environment, permissions, test gaps or one-off judgment.
For each proposed change choose retain/merge/reword/move/automate/remove/defer,
with evidence and owner. Current safety duplication between adapters is already
mechanically checked; do not remove it merely to shorten files. Do not promote
an observation without the existing feedback evidence/prevention gate.

## Bounded comparative pilot

Freeze 5–10 sanitized representative tasks and expected outcomes before changes.
Include requirements/design ambiguity, known correction, uncertain observation,
no-issue case and repeat failure. Use identical task/revision, evidence access,
model/version/configuration, permission profile and scoring for baseline and
candidate; record unavoidable differences and do not claim causality from them.
Repeat cases when feasible to report variability, not only a single mean.

For each run record locally: task/case ID, harness revision, direct vs investigator
mode, outcome/violations, rework rounds, missed consequential choices, irrelevant
questions, elapsed time, measured tokens (or unavailable), evidence usefulness,
recording burden and reviewer agreement. Keep raw content outside Git. Report
aggregates with sample size, failures and variation; no invented usage values.

Predeclare project-specific thresholds for success, maximum added time/tokens
and acceptable detection/rework improvement. Never relax safety or required
proof for an experiment. If thresholds are absent, the result is exploratory
and cannot justify rollout. Direct capture minimizes cost but has thinner
evidence; investigation can improve diagnosis at added time/context cost.

## Decision, rollout and rollback

Compare baseline/candidate using the same rubric and human review of sampled
candidates. No finding count target; zero useful findings is valid. Propose a
small reviewed PR with placement rationale, results/limitations, owner, review
trigger and rollback. Do not auto-edit adapters, Skills or permissions.

Remove/merge ineffective or stale rules after checking their safety purpose and
remaining coverage. Reassess after model or contract updates and repeated
failures. Keep superseded decisions and retired lesson history traceable.
Rollback reverts the reviewed change and optional invocation, reruns required
checks and preserves local observations under the project's retention policy.
Cross-repository deployment requires separate scope and reviewed sync dry-runs;
these PRs do not authorize modifying adopted repositories or global settings.

This template-local extension is opt-in and not distributed automatically.
Use a project-specific routing entry to adopt it. Do not turn the weekly review
suggestion into an automation without explicit user authorization.
