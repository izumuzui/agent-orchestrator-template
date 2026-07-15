# Independent review workflow

The reviewer is a different Agent instance with fresh context. Same-provider
review qualifies; cross-provider review is preferred when available but remains
an observed hypothesis, not an invariant.

## Stage 1: source-first derivation

Give the reviewer only:

- task ID
- requirement sources
- allowed and forbidden scope
- risk class and repository overlay

The reviewer independently derives acceptance and important boundaries before
seeing the writer's acceptance, plan, diff, or conclusions.

## Stage 2: evidence review

Then reveal the frozen handoff, diff, and raw verification evidence. Review in
this order:

1. Requirement and scope compliance
2. Correctness, boundaries, and failure handling
3. Safety, privacy, authorization, and destructive behavior
4. Compatibility, recovery, idempotency, and operational rollback
5. Test and evidence quality, including skipped or blocked proof
6. Unnecessary complexity, dependencies, generated files, or unrelated edits
7. Knowledge and policy update requirements

Report actionable findings first, ordered by severity, with file and line. Do
not optimize for finding count. Use `accepted`, `changes_required`, or `blocked`
as the review outcome and record rework rounds separately.

The reviewer does not edit the shared worktree. The designated writer applies
accepted findings.
