# Project verification

`scripts/project/verify.sh <mode>` implements these modes. Exit 0 = passed,
exit 3 = environment-blocked, other non-zero = failed.

| Mode | Checks | Required for |
|---|---|---|
| `full` | not configured | completion |
| `ci` | not configured | GitHub Actions |

Manual checks that automation cannot cover (UI, devices) are listed here and
reported separately.
