#!/usr/bin/env python3
"""Workspace-wide harness guard for Claude Code and Codex hooks.

SessionStart: inject the harness entry point and the repository's harness
state as additional context.
PreToolUse (file-editing tools): deny edits in a workspace repository that has
never adopted the harness, and deny in-place edits of managed harness files.

Fails open on any internal error so a broken guard never blocks unrelated work.
Set AGENT_HARNESS_GUARD=off in the agent's environment to bypass temporarily.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync  # noqa: E402

SYNC_CMD = "python3 ~/work/agent-orchestrator-template/scripts/harness/sync.py"
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$", re.MULTILINE)


def workspace_root() -> Path:
    return Path(os.path.expanduser(sync.WORKSPACE["root"])).resolve()


def repo_root(path: Path) -> Path | None:
    root = workspace_root()
    current = path if path.is_dir() else path.parent
    while True:
        try:
            current.relative_to(root)
        except ValueError:
            return None
        if current == root:
            return None
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def nearest_existing(path: Path) -> Path:
    while not path.exists() and path.parent != path:
        path = path.parent
    return path


def emit(event: str, **fields) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, **fields}}, ensure_ascii=False))


def session_start(data: dict) -> None:
    cwd = Path(data.get("cwd") or os.getcwd()).resolve()
    root = workspace_root()
    repo = repo_root(cwd)
    if repo is None:
        try:
            cwd.relative_to(root)
        except ValueError:
            return
        emit("SessionStart", additionalContext=(
            f"[agent-harness] {root.name}/ 以下の全プロジェクトは agent-orchestrator-template の"
            f"ハーネスに従う。各リポジトリでは AGENTS.md の管理ブロック → .ai/README.md → "
            f".ai/project.md の順に読む。状態確認: {SYNC_CMD} status"))
        return
    state = sync.status(repo)
    name = repo.name
    if state["state"] in ("exempt",):
        return
    lines = [f"[agent-harness] repository={name} state={state['state']}"]
    if state["state"] in ("synced", "source", "outdated", "modified", "unmerged"):
        lines.append("作業前に AGENTS.md の HARNESS ブロック、.ai/README.md、.ai/project.md を読み、"
                     "そのタスクルーティング・acceptance・検証契約（scripts/agent/verify-change.sh）に従うこと。"
                     "管理ファイル（.ai/harness.lock.json に列挙）はこのリポジトリで直接編集せず、テンプレート側で変更して sync する。")
    if state["state"] == "outdated":
        lines.append(f"テンプレートが更新されている。ユーザーに `{SYNC_CMD} sync {repo}` の実行を提案すること。")
    if state["state"] == "modified":
        lines.append("管理ファイルがローカルで編集されている。内容をプロジェクト所有スロットへ移すか、テンプレートへ反映するよう報告すること。")
    if state["state"] == "unmerged":
        lines.append("このブランチにはまだハーネスが無いが、別のブランチでは導入済み。"
                     "ユーザーへ導入済みブランチ（通常 main）の取り込みを提案し、"
                     "それまでも同じ規約（acceptance → 実装 → verify → 独立レビュー）で作業すること。")
    if state["state"] == "missing":
        lines.append(f"ハーネス未導入のため、ファイル編集はフックで拒否される。"
                     f"まず `{SYNC_CMD} install {repo}` で導入し、プロジェクト所有スロットを埋めること。")
    for detail in state["details"][:8]:
        lines.append(f"- {detail}")
    emit("SessionStart", additionalContext="\n".join(lines))


def target_paths(data: dict) -> list[Path]:
    cwd = Path(data.get("cwd") or os.getcwd())
    tool_input = data.get("tool_input") or {}
    raw: list[str] = []
    if isinstance(tool_input, dict):
        for key in ("file_path", "notebook_path", "path"):
            value = tool_input.get(key)
            if isinstance(value, str):
                raw.append(value)
        values = [v for v in tool_input.values() if isinstance(v, str)]
    else:
        values = [str(tool_input)]
    for value in values:
        raw.extend(PATCH_FILE.findall(value))
    paths = []
    for item in raw:
        path = Path(os.path.expanduser(item))
        paths.append((path if path.is_absolute() else cwd / path).resolve())
    return paths


def pre_tool_use(data: dict) -> None:
    if data.get("tool_name") not in sync.WORKSPACE.get("guarded_tools", []):
        return
    for path in target_paths(data):
        repo = repo_root(nearest_existing(path))
        if repo is None or sync.is_source(repo) or repo.name in sync.WORKSPACE.get("exempt", []):
            continue
        lock = sync.read_lock(repo)
        rel = path.relative_to(repo).as_posix()
        if lock is None:
            if sync.adopted_elsewhere(repo):
                continue
            emit("PreToolUse", permissionDecision="deny", permissionDecisionReason=(
                f"[agent-harness] {repo.name} はハーネス未導入です。編集前に "
                f"`{SYNC_CMD} install {repo}` を実行し、.ai/project.md などを埋めてください。"))
            return
        if rel in lock.get("files", {}):
            emit("PreToolUse", permissionDecision="deny", permissionDecisionReason=(
                f"[agent-harness] {rel} はテンプレート管理ファイルです。"
                f"~/work/agent-orchestrator-template 側で変更し `{SYNC_CMD} sync {repo}` で反映してください。"
                f"プロジェクト固有の内容は .ai/project.md などのプロジェクト所有スロットへ書いてください。"))
            return


def main() -> int:
    if os.environ.get("AGENT_HARNESS_GUARD") == "off":
        return 0
    try:
        data = json.load(sys.stdin)
        event = data.get("hook_event_name")
        if event == "SessionStart":
            session_start(data)
        elif event == "PreToolUse":
            pre_tool_use(data)
    except Exception as error:  # fail open
        print(f"[agent-harness] guard error ignored: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
