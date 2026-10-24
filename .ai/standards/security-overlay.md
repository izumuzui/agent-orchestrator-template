# Repository security overlay

## Private data

None stored here. Seeds and examples must stay generic; never copy a
project's private overlay content into the template.

## Forbidden without explicit owner scope

- Running `sync.py sync` against another repository's working tree that has
  uncommitted work (use a separate worktree/branch).
- Pushing, merging, or changing GitHub settings of adopted repositories.
- Editing global agent configuration (`~/.claude`, `~/.codex`).

## External state and rollback

The guard hook is global. Roll back by removing its entries from the global
hook configuration or setting `AGENT_HARNESS_GUARD=off`.
