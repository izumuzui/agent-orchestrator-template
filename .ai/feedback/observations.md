# Opt-in observation capture

Use this when a process concern is not yet a verified defect or lesson. Fix the
current artifact first; record only a short sanitized observation and expected
behavior. Cause analysis is optional and deferred. This is separate from the
existing curated feedback CLI and its active/proposed context selection.

Create a local JSON input under ignored `.agent-state/`, then run:

```bash
python3 scripts/agent/observe.py --input .agent-state/observation-input.json
```

Required fields: phase (requirements/design/implementation/review/operation),
issue_type (lowercase identifier), observation, expected. Optional string lists:
references, hypotheses, unknowns. References are opaque handles such as
`evidence:case-1`; they must resolve through an approved local evidence index.
Do not supply absolute paths, raw conversation, source excerpts or credentials.
The helper validates shape, not confidentiality: sanitize before invoking it.

The helper assigns a UUID and UTC time, serializes append operations with a
local POSIX lock and flushes the journal. It returns only ID and status. Local
records live under `.agent-state/observations/feedback.jsonl` and never enter
normal feedback context. Both CLI clients may invoke this helper; network
filesystems, multi-machine concurrent writes and hostile local writers are
unsupported. This helper is not a permission boundary. A disk failure can leave
a partial final line: capture then fails closed until an owner repairs the
journal from a preserved local backup. Do not silently discard damaged records.

An observation is pending with unconfirmed cause, even if hypotheses are
supplied. Later analysis may propose a sanitized scoped lesson through the
existing feedback workflow; promotion still needs evidence, prevention and
required review. No automatic ingestion, promotion or harness rewrite occurs.
Pilot with 5–10 cases before expanding automation. Roll back by stopping helper
invocation; existing feedback operations are unchanged. Retain/delete local
records according to the project's retention policy; never commit the journal.
