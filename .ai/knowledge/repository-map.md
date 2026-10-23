# Repository map

Use this file to limit exploration. Replace the example rows when adopting the
template; keep it short enough to scan before broad searches.

| Path | Responsibility | Usually read for |
|---|---|---|
| `README.md` | Product and development entry point | every substantial task |
| `.ai/` | Shared agent knowledge and process | agent-environment changes |
| `scripts/agent/` | Deterministic agent helpers | verification and orchestration |
| `.github/` | PR verification and PR template | GitHub integration |
| `.ai/feedback/` | Scoped corrections and verified lessons | before changes in the affected scope |
| `tests/` | Template scheduling and feedback regression tests | every behavior change |

Normally ignore generated artifacts, dependency caches, local databases,
private fixtures, and `.agent-state/` unless the task explicitly concerns them.
