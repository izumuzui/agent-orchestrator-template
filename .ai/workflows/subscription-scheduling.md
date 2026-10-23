# Plus / Pro scheduling and cross-machine handoff

This extension targets Codex with ChatGPT Plus and Claude Code with Claude Pro.
Use each tool's subscription login. API billing and additional usage purchases
are separate choices; this extension never calls provider APIs, buys credits,
launches agents, or changes billing settings.

## Observe, then recommend

One account has one budget across Mac and Ubuntu. Run scheduling on one
coordinator machine. Do not independently maintain quota snapshots on both
machines or copy live state databases between them.

Read the provider's usage display, then record remaining percentages (not used
percentages) and each actual reset timestamp, including timezone:

```bash
python3 scripts/agent/quota.py record codex session --remaining 65 --resets-at 2030-01-01T18:00:00+09:00
python3 scripts/agent/quota.py record codex week --remaining 40 --resets-at 2030-01-05T09:00:00+09:00
python3 scripts/agent/quota.py record claude session --remaining 80 --resets-at 2030-01-01T19:00:00+09:00
python3 scripts/agent/quota.py record claude week --remaining 60 --resets-at 2030-01-06T09:00:00+09:00
python3 scripts/agent/quota.py select --candidates codex claude
python3 scripts/agent/quota.py show
```

Dates and percentages above are illustrative: replace them with observed values.
Do not run these example observations unchanged. If a weekly window is absent,
leave it unknown; the conservative selector requests a refresh/manual decision.
Never invent a 100% weekly budget to bypass that check.

First qualify providers for the role using `routing.md`; pass only those
candidates. The selector recommends the largest minimum of session/week
remaining percentages. This is a simple heuristic, not a comparison of token
capacity or a promise that a task will fit. Default reserve is 10%; observations
expire after 60 minutes. Configure with `--reserve-percent` and
`--max-age-minutes`. At a passed reset timestamp, observe again rather than
assuming a refill. Missing, stale, exhausted, or future-dated observations do
not qualify. A null recommendation means wait, refresh, or make an explicit
manual scheduling decision; never silently lower review requirements.

Refresh after substantial work, before dispatch, and when another PC uses the
account. Account activity elsewhere can make even recent observations inaccurate.
Recommendations do not reserve capacity and do not grant a writer lease.
The initial version intentionally has no automatic quota scraping or automatic
provider switching. No continuous token-consuming polling is needed.

## Useful work queue

Maintain a sanitized, Git-tracked `.ai/knowledge/work-queue.md` per project, listing task ID, scope, acceptance, priority, and
status. Keep implementation, review, investigation, and documentation tasks
available. Assign independent work to separate branches/checkouts. Within one
checkout, keep exactly one writer. Do not repeatedly ask both tools to solve
the same task solely to spend unused allowance.

## Move work from Mac to Ubuntu (or between providers)

1. Finish a coherent checkpoint, run available proof, and record actual results.
2. Fill the handoff's Resume checkpoint with repository-relative paths, branch,
   commit, next action, blockers, current writer, and review requirements.
3. Stop the previous writer explicitly before the receiver starts editing.
4. Commit intended source changes to a task branch. Transfer through the
   project's approved Git remote or another approved private channel. Pushing
   requires the user's authorization; a scheduling recommendation is not it.
5. Local handoffs and quota observations live in ignored `.agent-state/`.
   They do not travel with Git. For a shareable handoff, manually sanitize a
   copy into `.ai/handoffs/<task-id>.md`, review it, and include it with the
   checkpoint. Never share credentials, raw logs, machine paths, or quota state.
6. The receiver verifies the branch/commit and handoff, reruns relevant checks,
   claims the writer role, and continues with the recorded next action.

Do not copy `.git`, authentication files, or either product's complete home
configuration as a synchronization mechanism. Resolve paths on each machine.
Use Bash 3.2+ and Python 3.9+ on macOS/Linux; no extra Python packages are needed.
Skills and shared personal memory synchronization are a separate extension;
this version shares repository knowledge and sanitized handoffs only.
