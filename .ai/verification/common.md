# Common verification contract

Verification is defined by evidence, not by the Agent that ran it.

## Overall status

- `passed`: every required proof passed
- `failed`: at least one required proof failed because of the change
- `blocked`: at least one required proof could not run in the environment
- `incomplete`: required proof was not attempted or evidence is missing

`skipped` is allowed only for checks declared non-required before
implementation. A required environment-blocked check makes the overall status
`blocked`, not `passed`.

## Standard entry point

```bash
scripts/agent/verify-change.sh agent-env
scripts/agent/verify-change.sh full
```

`agent-env` validates this shared environment. `full` also runs
`scripts/project/verify.sh` when a project supplies it; otherwise the project
check is reported as a non-required skip.

During iteration, run the smallest focused proof first. Before completion, run
the applicable full proof. Report actual commands and results separately as:

- passed
- failed due to this change
- verified pre-existing failure
- skipped because it was predeclared non-required
- environment-blocked

The default goal loop is capped at three implementation/verification rounds.
After the same failure twice, revisit the requirement, diagnosis, or design.
