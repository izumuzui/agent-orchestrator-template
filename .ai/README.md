# Shared agent environment

This directory is the source of truth for model-neutral project knowledge,
safety, workflows, verification, routing, and handoff contracts. Tool adapters
stay short and point here.

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

## Before implementation

- Identify requirement sources without copying raw private content.
- Freeze versioned acceptance before the writer starts.
- Declare allowed and forbidden scope.
- Classify risk using `standards/security.md`.
- Select a P0-P3 pattern and reserve routing for tracked tasks.
- State proof, stop conditions, and retry bounds.

## Knowledge lifecycle

Update stable facts only. At both implementation Done and review Done, ask
whether architecture, repository ownership, safety boundaries, verification,
or routing policy changed. Record policy changes in `knowledge/decisions.md`.
