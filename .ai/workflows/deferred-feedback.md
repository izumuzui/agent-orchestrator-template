# Deferred process feedback (opt-in extension)

Use this extension for unresolved process concerns. Existing clear UI/review
corrections still follow the required feedback loop; this document does not
waive immediate fixes, verification, review or scoped correction recording.

## Capture and continue

Split a mixed correction into (a) current artifact behavior to correct and
(b) a process observation to investigate later. Do not turn a feeling into a
confirmed violation. Prioritize the artifact; capture observation, expected
outcome, phase, issue type and safe evidence handles without diagnosing cause.
Use the observation helper when installed, or keep equivalent sanitized local
JSON under ignored task state. Neither record is an active lesson.

Do not load the observation archive into normal development prompts. Read only
selected cases during an explicitly scoped investigation. Review weekly or at
5–10 accumulated cases; repeated/serious incidents may justify earlier review.
This is a manual cadence, not authorization for a scheduled job.

## Optional investigator

Default to parent capture. A child that merely appends an already complete
record adds little value. Use a fresh read-only investigator only when an
independent search of relevant rules, specification, diff and prior scoped
cases can improve evidence. Compare 5–10 cases against direct capture before
adopting the role. Set a time/token budget and stop after one bounded pass;
missing evidence is an unknown, not a reason for recursive delegation.

Before continuing edits, parent freezes approved evidence: safe repository ID,
commit, dirty-diff identity and recoverable local snapshot where allowed,
artifact revision, observation time, minimal sanitized correction and approved
reference handles. A commit or diff hash alone cannot recover uncommitted work.
Do not copy private material into Git. If a safe snapshot cannot be made, run
investigation serially or explicitly mark evidence incomplete. No full parent
conversation is assumed available to a child.

Bootstrap packet: case ID, phase, short observation/expected, allowed paths,
reference handles and snapshot identity, forbidden data/actions, budget/stop.
Investigator checks only those sources and separates:

- observed facts and source revision/position;
- relevant existing rules and sources actually checked;
- hypotheses, confidence and unknowns;
- candidate categories: ignored rule, missing rule, ambiguous specification,
  information/environment/permission gap, missing test, isolated judgment error.

Do not infer missing rules from failure alone. Investigator does not modify
source, harness, curated lessons or shared checkout. Return only case ID,
recording success and critical unknowns. Parent alone invokes the validated
capture helper for the short result; detailed sanitized investigation stays
in approved local evidence storage. This preserves the repository's one-writer
rule even when a provider supports custom agent definitions.

## Later maintenance and rollout

A separate maintenance session groups cases, checks duplicate/contradictory
rules and proposes tests/docs/procedures/permission changes. Keep findings as
candidates until evidence and required human/reviewer evaluation establish them.
No automatic agent config or permanent instruction edits. Start with direct
capture, then optionally trial investigator, milestone reviews and automation
in that order; each stage needs evidence of value. Roll back by disabling the
optional role/capture invocation, preserving existing corrections and proof.

Claude Code CLI, Claude Desktop's Code feature, ordinary Desktop chat and Codex
may expose different tools. Record observed version, ability to access a fresh
context, local files, permissions and background execution before provider
setup. Side conversations must not be assumed to persist logs. No provider
configuration or workspace deployment is performed by adopting this guide.

This file is an opt-in template-local extension, not automatically distributed
by the managed manifest. Adoption in another project requires its own reviewed
routing entry; do not silently sync other repositories.
