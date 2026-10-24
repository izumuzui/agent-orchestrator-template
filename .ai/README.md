# Shared agent environment

This directory is the source of truth for model-neutral project knowledge,
safety, workflows, verification, routing, and handoff contracts. Tool adapters
stay short and point here.

## Managed core and project overlay

This repository adopts the shared harness from `agent-orchestrator-template`.
Files listed in `.ai/harness.lock.json` are managed: change them in the
template and run `scripts/harness/sync.py sync <repo>` from the template, never
edit them in place. Project-owned slots, which the sync never overwrites:

| Slot | Purpose |
|---|---|
| `.ai/project.md` | product summary, authoritative documents, extra task routing, review focus |
| `.ai/standards/security-overlay.md` | repository-specific risk classes and forbidden operations |
| `.ai/verification/project.md` | product checks and the modes of `scripts/project/verify.sh` |
| `.ai/knowledge/repository-map.md` | where to look, what to ignore |
| `.ai/knowledge/decisions.md` | durable decisions of this repository |
| `.ai/knowledge/work-queue.md` | sanitized shared work queue |
| `scripts/project/verify.sh` | executable product verification (`full`, `ci`, extra modes) |
| `scripts/project/check.sh` | optional extra agent-environment checks |

Any other project file under `.ai/` (for example extra workflows) is also
project-owned. When a managed rule and a project overlay overlap, apply both;
the stricter safety rule wins.

## Instruction priority

1. Explicit user instruction for the current task
2. Safety, privacy, authorization, and non-destructive-operation constraints
3. The nearest tool adapter
4. This shared environment and repository-authoritative documents
5. General conventions

Do not resolve a material contradiction by guessing.

## Task routing

| Task shape | Workflow | Required evidence |
|---|---|---|
| Change or fix | `workflows/change.md` | acceptance + focused proof + common checks |
| User corrections / UI feedback | `workflows/feedback-loop.md` | scoped source + expected behavior + verified prevention |
| GitHub CI / native Codex review | `workflows/github-review.md` | actual CI and review results |
| Independent review | `workflows/review.md` | source-first review + diff + verification evidence |
| Multi-agent work | `workflows/orchestration.md` | bounded roles + one writer + final synthesis |
| Subscription scheduling / cross-machine resume | `workflows/subscription-scheduling.md` | observed quota + stopped writer + checkpoint |
| Role selection | `workflows/routing.md` | intended pattern + actual assignment + fallback reason |
| Project-specific task shapes | `.ai/project.md` | as declared there, plus the common contract |

## Before implementation

- Identify requirement sources without copying raw private content.
- Freeze versioned acceptance before the writer starts.
- Declare allowed and forbidden scope.
- Classify risk using `standards/security.md` and `standards/security-overlay.md`.
- Select a P0-P3 pattern and reserve routing for tracked tasks.
- State proof, stop conditions, and retry bounds.

## Knowledge lifecycle

Update stable facts only. At both implementation Done and review Done, ask
whether architecture, repository ownership, safety boundaries, verification,
or routing policy changed. Record policy changes in `knowledge/decisions.md`.
