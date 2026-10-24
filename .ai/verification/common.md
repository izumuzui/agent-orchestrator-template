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
scripts/agent/verify-change.sh agent-env   # harness integrity only
scripts/agent/verify-change.sh ci          # harness gate + project `ci` mode
scripts/agent/verify-change.sh full        # harness gate + project `full` mode
scripts/agent/verify-change.sh <mode>      # project-specific mode
```

`agent-env` validates the shared environment. `ci` and `full` also run the
harness regression tests and `scripts/project/verify.sh <mode>`. Product
checks and extra modes are declared in `.ai/verification/project.md`.

`scripts/project/verify.sh` contract: exit 0 when every check it ran passed,
exit 3 when a required check could not run in this environment (report it as
`blocked`), any other non-zero exit when a check failed. Without the script,
product verification is reported as `[SKIPPED]` and the result must not be
presented as a verified product change.

During iteration, run the smallest focused proof first. Before completion, run
the applicable full proof. Report actual commands and results separately as:

- passed
- failed due to this change
- verified pre-existing failure
- skipped because it was predeclared non-required
- environment-blocked

The default goal loop is capped at three implementation/verification rounds.
After the same failure twice, revisit the requirement, diagnosis, or design.
