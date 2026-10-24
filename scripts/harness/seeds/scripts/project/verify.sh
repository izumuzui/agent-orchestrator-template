#!/usr/bin/env bash
# Project-owned product verification. Contract: .ai/verification/project.md
# exit 0 = passed, 3 = environment-blocked, other = failed.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

case "${1:-full}" in
  full|ci)
    echo "[BLOCKED] product checks are not configured yet; edit scripts/project/verify.sh" >&2
    exit 3
    ;;
  *)
    echo "unknown mode: $1" >&2
    exit 2
    ;;
esac
