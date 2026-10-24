# Shared work queue

Keep task descriptions sanitized and repository-relative. Local quota state is
not a task status or writer lock. Only mark done after required verification
and review. One coordinator assigns work; stop the old writer before takeover.

| Task ID | Priority | Scope / acceptance | Status | Owner / branch | Next action |
|---|---|---|---|---|---|

Statuses: queued, active, handoff, review, blocked, done.
