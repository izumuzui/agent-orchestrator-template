#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

mode="${1:-agent-env}"

case "$mode" in
  agent-env)
    scripts/agent/check-agent-env.sh
    ;;
  full)
    scripts/agent/check-agent-env.sh
    if [[ -x scripts/project/verify.sh ]]; then
      scripts/project/verify.sh
      echo "[PASS] project verification"
    else
      echo "[SKIPPED] project verification is not configured (non-required in template)"
    fi
    ;;
  *)
    echo "usage: scripts/agent/verify-change.sh [agent-env|full]" >&2
    exit 2
    ;;
esac
