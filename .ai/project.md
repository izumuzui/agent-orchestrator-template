# Project overlay: agent-orchestrator-template

This repository is the source of the shared harness for every project under
`~/work`. Changes here propagate to other repositories through
`scripts/harness/sync.py`, so a harness change is a cross-repository change.

## Authoritative documents

| Topic | Document |
|---|---|
| Overview and adoption | `README.md` |
| Managed vs seeded files | `scripts/harness/manifest.json` |
| Workspace scope and exemptions | `scripts/harness/workspace.json` |

## Additional task routing

| Task shape | Workflow | Required evidence |
|---|---|---|
| Harness contract change | `workflows/change.md` at P1+ | `scripts/agent/verify-change.sh full` here, then `sync.py sync --dry-run` on each adopted repo |

## Review focus

- A managed-file change must keep working in every adopted repository; check
  `python3 scripts/harness/sync.py status` and the dry-run diff.
- `scripts/harness/guard.py` must fail open and must never block editing this
  template or exempt repositories.
