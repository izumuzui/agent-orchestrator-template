#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

required=(
  README.md
  AGENTS.md
  CLAUDE.md
  .gitignore
  .ai/README.md
  .ai/knowledge/repository-map.md
  .ai/knowledge/decisions.md
  .ai/standards/security.md
  .ai/verification/common.md
  .ai/workflows/change.md
  .ai/workflows/review.md
  .ai/workflows/routing.md
  .ai/workflows/orchestration.md
  .ai/handoffs/template.md
  .ai/metrics/schema.md
  scripts/agent/check-agent-env.sh
  scripts/agent/create-handoff.sh
  scripts/agent/reserve-routing.py
  scripts/agent/record-completion.py
  scripts/agent/verify-change.sh
)

for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "[FAIL] missing required file: $path" >&2
    exit 1
  fi
done

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])

def safety_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- SAFETY:START -->\n(.*?)\n<!-- SAFETY:END -->",
        text,
        re.DOTALL,
    )
    if not match:
        raise SystemExit(f"[FAIL] missing safety block: {path.name}")
    return match.group(1)

if safety_block(root / "AGENTS.md") != safety_block(root / "CLAUDE.md"):
    raise SystemExit("[FAIL] AGENTS.md and CLAUDE.md safety blocks drifted")

for script in ("reserve-routing.py", "record-completion.py"):
    path = root / "scripts" / "agent" / script
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

reference_pattern = re.compile(r"`((?:\.ai|scripts/agent)/[^`\s]+)`")
reference_files = [root / "README.md", root / "AGENTS.md", root / "CLAUDE.md"]
reference_files.extend((root / ".ai").rglob("*.md"))
for source in reference_files:
    for target in reference_pattern.findall(source.read_text(encoding="utf-8")):
        target = target.rstrip(".,;:")
        if "<" in target or "{{" in target:
            continue
        if not (root / target).exists():
            raise SystemExit(
                f"[FAIL] broken local reference in {source.relative_to(root)}: {target}"
            )

event_path = root / ".agent-state" / "metrics" / "task-events.jsonl"
prohibited = {"prompt", "content", "transcript", "terminal_output", "secret", "private_path"}
if event_path.exists():
    seen_reservations: set[str] = set()
    seen_completions: set[str] = set()
    for number, line in enumerate(event_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"[FAIL] invalid event JSON at line {number}: {error}")
        if not isinstance(event, dict) or event.get("event") not in {"routing_reserved", "task_completed"}:
            raise SystemExit(f"[FAIL] invalid event type at line {number}")
        if prohibited.intersection(event):
            raise SystemExit(f"[FAIL] prohibited event field at line {number}")
        task_id = event.get("task_id")
        if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
            raise SystemExit(f"[FAIL] invalid task_id at line {number}")
        if event["event"] == "routing_reserved":
            if task_id in seen_reservations:
                raise SystemExit(f"[FAIL] duplicate routing reservation for {task_id}")
            seen_reservations.add(task_id)
        else:
            if task_id not in seen_reservations:
                raise SystemExit(f"[FAIL] completion without reservation for {task_id}")
            if task_id in seen_completions:
                raise SystemExit(f"[FAIL] duplicate completion for {task_id}")
            seen_completions.add(task_id)

print("[PASS] adapter safety parity, Python syntax, local references, and task-event integrity")
PY

if ! git check-ignore -q .agent-state/probe; then
  echo "[FAIL] .agent-state is not ignored" >&2
  exit 1
fi

if [[ -n "$(git ls-files -- .agent-state)" ]]; then
  echo "[FAIL] .agent-state contains tracked files" >&2
  exit 1
fi

bash -n scripts/agent/check-agent-env.sh \
  scripts/agent/create-handoff.sh scripts/agent/verify-change.sh

echo "[PASS] private state ignore and shell syntax"
