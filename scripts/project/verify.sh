#!/usr/bin/env bash
# Template-owned verification of the sync/guard tooling.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

case "${1:-full}" in
  full|ci)
    bash -n scripts/project/verify.sh scripts/harness/seeds/scripts/project/verify.sh
    python3 -m unittest discover -s scripts/harness/tests -p 'test_*.py'
    ;;
  *)
    echo "unknown mode: $1" >&2
    exit 2
    ;;
esac
