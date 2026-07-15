# Repository agent adapter

Before changing files:

1. Read `.ai/README.md`.
2. Use `.ai/knowledge/repository-map.md` to limit exploration.
3. Select the workflow routed by `.ai/README.md`.
4. Define requirement sources, acceptance, proof, and a measurable stop condition.
5. Reserve routing before implementation when the task is tracked.

<!-- SAFETY:START -->
- Never send secrets through model input or tool-output context.
- Use private data only with approved providers and retention settings.
- Route cloud-prohibited data only to approved local-only tools.
- Do not persist raw private content in handoffs, metrics, or reports.
- Require explicit approval for destructive or external-state changes.
- Keep one writer on the shared worktree.
- Report verification as passed, failed, skipped, or environment-blocked.
<!-- SAFETY:END -->

For orchestration, follow `.ai/workflows/orchestration.md`. Parallel agents are
read-only explorers or reviewers. They must not edit the shared worktree.

Do not report completion from edits alone. Run `scripts/agent/verify-change.sh`
and report the overall result plus each classified check.
