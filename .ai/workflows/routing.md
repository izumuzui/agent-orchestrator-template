# Quality routing and scheduling

Role structure is model-neutral. Agent assignment is an exchangeable policy.

## Role patterns

| Pattern | Structure | Use when |
|---|---|---|
| P0 | one instance plans, writes, and self-verifies | clear, low-risk, small change |
| P1 | one writer + fresh reviewer | independent review is required |
| P2 | planner + one writer + fresh reviewer | novel, cross-cutting, or non-trivial work |
| P3 | primary + at most two read-only explorers, then P0-P2 | two or more independent read-heavy investigations |

P0 self-verification is not independent review. A sentinel task is upgraded to
P1-equivalent review. P3 never creates multiple shared-worktree writers.

## Quality routing

| Risk and task shape | Pattern |
|---|---|
| high-risk, specification clear | P1 |
| high-risk, novel or cross-cutting | P2 |
| low-risk, clear and routine | P0 unless calibration, sentinel, or escalation applies |
| low-risk, novel or cross-cutting | P1; use P2 when plan separation adds value |
| at least two independent read-heavy investigations | P3 before the write pattern |

## Scheduling

After quality routing identifies qualified candidates, scheduling may consider
quota, rate limits, availability, and latency. Record:

- intended pattern
- actual assignment using versioned capability profile IDs
- fallback reason
- reviewer relation: none, fresh same-provider, or cross-provider

If no qualified candidate is available, wait, narrow scope, or return to the
owner. Never lower quality or safety to consume spare quota.

## Legacy initial assignment policy: v1

| Role | Assignment |
|---|---|
| Planner / acceptance draft | Codex capability profile |
| Writer / test / fix | Claude Code capability profile |
| Reviewer | fresh Codex capability profile; fresh same-provider fallback allowed |

This is Pattern C, an economic hypothesis for the current contracts. It is not
a permanent capability ranking.

## Calibration and sentinel policy

- First 10 non-trivial tasks: independent review required
- After calibration: high-risk always reviewed
- After calibration: every fifth low-risk task for each `area_id:task_type` key
  becomes a sentinel and requires independent review
- Escaped defect: the same counter key requires review for the next five tasks
- Re-evaluate every 10 terminal task events and on model or contract changes

`scripts/agent/reserve-routing.py` atomically reserves the per-key routing
sequence before implementation so review cannot be discovered too late. It
keeps a separate `sentinel_sequence` for post-calibration low-risk tasks, so
medium and high-risk work cannot accidentally consume a sentinel slot.

The v1 script automates calibration and periodic sentinels. Escaped-defect
escalation uses the explicit `escaped_defect` review override for the next five
matching tasks until a repository adds a durable defect-window counter.

## Adding another Agent

Check base conformance, then role-specific capability:

- can read the shared core through a thin adapter
- maps its permissions to repository risk classes
- can run common verification and return raw evidence
- can read and write the handoff contract without leaking private content
- records usage as observed or missing, never invented
- qualifies separately as planner, writer, reviewer, or read-only explorer

An Agent that cannot provide fresh review is excluded only from the reviewer
role, not automatically from every role.

## Subscription assignment policy: v2

For the Plus / Pro setup, planner, writer, and reviewer assignments are
exchangeable after role qualification. Start with Codex writing and Claude
reviewing, or reverse them when observed remaining capacity supports it.
Fresh-context review remains required wherever the reservation says so.
Use `--policy-version v2` for newly tracked tasks; keep existing v1 records.
Use `subscription-scheduling.md` and `scripts/agent/quota.py` after reserving
quality routing. Recommendations are advisory; they do not launch workers or
change the reservation's review requirements. Freeze the actual assignment and
fallback reason in the handoff. Never switch a running writer without a stopped
writer and a resume checkpoint.

## Default assignment policy: v3

Default for newly tracked tasks. Claude plans and implements; Codex tests and
fixes. Each provider's output is reviewed by the other.

| Role | Assignment |
|---|---|
| Planner / acceptance draft / role split | Claude Code capability profile |
| Writer (implementation) | Claude Code capability profile |
| Review of Claude's output | fresh Codex capability profile |
| Test / fix | Codex capability profile |
| Review of Codex's output (tests and fixes) | fresh Claude Code capability profile |

- Still one writer at a time. Implementation to test/fix is a writer handoff:
  stop the Claude writer, write a checkpoint, then start the Codex writer.
- Review is always cross-provider (`--reviewer-relation cross_provider`).
  Fresh same-provider review is a recorded fallback only when the other
  provider is unavailable; never skip review to save quota.
- Quality roles above override quota recommendations. Quota may delay a step
  or narrow scope but must not swap providers inside a role.
- Use `--policy-version v3`; keep existing v1/v2 records.

