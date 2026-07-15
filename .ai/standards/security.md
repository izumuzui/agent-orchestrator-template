# Safety and privacy

## Invariants

- Never send secrets through model input, tool-output context, handoffs, or logs.
- Private source or data may be used only with an approved provider and
  retention configuration.
- Data prohibited from cloud transfer must be handled by approved local-only
  tools and agents.
- Do not persist raw private content, exact private paths, terminal dumps, or
  credentials in handoffs, task events, reports, or Git.
- Destructive and external-state changes require explicit owner authorization.
- A qualified agent being unavailable is not permission to lower the quality,
  privacy, sandbox, approval, or reasoning profile.

## Common high-risk classes

- destructive operation or bulk mutation
- private or regulated data boundary
- secret, credential, authentication, or authorization handling
- billing or financial behavior
- data schema, migration, transaction, or recovery behavior
- infrastructure, deployment, service control, or external state
- public API, file-format, or UI compatibility

High-risk changes require at least P1 and a fresh reviewer. Destructive actions
still require explicit human approval even after review.

## Repository overlay

Fill this section before using the template in a product repository. Add risks
specific to its data, infrastructure, activation, rollback, and compatibility
boundaries. Keep the overlay in this one authoritative location.
