# Repository map

Use this file to limit exploration. Keep it short enough to scan.

| Path | Responsibility | Usually read for |
|---|---|---|
| `AGENTS.md` / `CLAUDE.md` | managed harness block + project rules | every task |
| `.ai/` | shared agent knowledge and process | process questions |
| `scripts/agent/` | managed harness helpers | verification and orchestration |
| `scripts/project/` | product verification entry point | every behavior change |

Normally ignore generated artifacts, dependency caches, local databases,
private fixtures, and `.agent-state/` unless the task explicitly concerns them.
