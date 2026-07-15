#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
task_id="${1:-}"

if [[ -z "$task_id" ]]; then
  suffix="$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
  task_id="t_$(date -u +%Y%m%dT%H%M%SZ)_${suffix}"
fi

if [[ ! "$task_id" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "task ID must contain only letters, numbers, underscore, and hyphen" >&2
  exit 2
fi

umask 077
directory="$ROOT/.agent-state/handoffs"
output="$directory/$task_id.md"
mkdir -p "$directory"

if [[ -e "$output" ]]; then
  echo "handoff already exists: $output" >&2
  exit 1
fi

sed "s/{{TASK_ID}}/$task_id/g" "$ROOT/.ai/handoffs/template.md" >"$output"
echo "$output"
