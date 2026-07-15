# Claude Code adapter

Read `.ai/README.md`, then follow its task routing and verification contract.
Keep project facts and reusable workflows under `.ai/`; do not duplicate them
here.

<!-- SAFETY:START -->
- Never send secrets through model input or tool-output context.
- Use private data only with approved providers and retention settings.
- Route cloud-prohibited data only to approved local-only tools.
- Do not persist raw private content in handoffs, metrics, or reports.
- Require explicit approval for destructive or external-state changes.
- Keep one writer on the shared worktree.
- Report verification as passed, failed, skipped, or environment-blocked.
<!-- SAFETY:END -->

Claude-specific behavior:

- Treat `.ai/workflows/routing.md` as policy; do not infer roles from model names.
- Put temporary task state under `.agent-state/handoffs/`.
- Use a fresh instance for independent review.
- Give a reviewer only the bootstrap packet first; reveal frozen acceptance,
  diff, and verification evidence after the reviewer independently derives it.
- Do not lower the reasoning or safety profile to work around quota limits.
