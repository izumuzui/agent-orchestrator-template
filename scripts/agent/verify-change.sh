#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

mode="${1:-agent-env}"
PROJECT_VERIFY=scripts/project/verify.sh

usage() {
  cat <<'USAGE'
usage: scripts/agent/verify-change.sh [agent-env|ci|full|<project-mode>]

  agent-env  harness integrity only
  ci         harness gate + scripts/project/verify.sh ci
  full       harness gate + scripts/project/verify.sh full
  other      forwarded to scripts/project/verify.sh (see .ai/verification/project.md)
USAGE
}

harness_gate() {
  scripts/agent/check-agent-env.sh
  python3 scripts/agent/feedback.py check
  python3 -m unittest discover -s scripts/agent/tests -p 'test_*.py'
  echo "[PASS] harness regression tests"
}

project_verify() {
  if [[ ! -x "$PROJECT_VERIFY" ]]; then
    echo "[SKIPPED] project verification is not configured ($PROJECT_VERIFY missing)"
    echo "[OVERALL] incomplete: product checks did not run"
    return 0
  fi
  local status=0
  "$PROJECT_VERIFY" "$1" || status=$?
  case "$status" in
    0) echo "[PASS] project verification ($1)"; echo "[OVERALL] passed" ;;
    3) echo "[BLOCKED] project verification ($1) could not run in this environment" >&2
       echo "[OVERALL] blocked" ;;
    *) echo "[FAIL] project verification ($1) exited $status" >&2
       echo "[OVERALL] failed" ;;
  esac
  return "$status"
}

case "$mode" in
  -h|--help)
    usage
    ;;
  agent-env)
    scripts/agent/check-agent-env.sh
    ;;
  ci|full)
    harness_gate
    project_verify "$mode"
    ;;
  *)
    if [[ -x "$PROJECT_VERIFY" ]]; then
      project_verify "$mode"
    else
      usage >&2
      exit 2
    fi
    ;;
esac
