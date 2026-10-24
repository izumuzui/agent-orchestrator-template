#!/usr/bin/env python3
"""Install the shared agent harness into a repository and keep it in sync.

Managed files are copied verbatim from this template and recorded with their
hashes in ``.ai/harness.lock.json``. Seeded files are created only when absent
and then belong to the project. The managed block between ``<!-- HARNESS:START
-->`` and ``<!-- HARNESS:END -->`` in AGENTS.md / CLAUDE.md is replaced; the
rest of each adapter is preserved.

The command never deletes files, never commits, and never touches Git remotes.
It refuses to overwrite a managed path that was edited locally or authored by
the project unless ``--force`` is given (the previous content is printed as a
diff first so it can be moved into a project-owned slot).
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((TEMPLATE / "scripts/harness/manifest.json").read_text(encoding="utf-8"))
SEEDS = TEMPLATE / "scripts/harness/seeds"
WORKSPACE = json.loads((TEMPLATE / "scripts/harness/workspace.json").read_text(encoding="utf-8"))
LOCK = ".ai/harness.lock.json"
BLOCK = re.compile(r"<!-- HARNESS:START -->\n.*?<!-- HARNESS:END -->\n?", re.DOTALL)
EXECUTABLE = (".sh", ".py")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def template_block(name: str) -> str:
    match = BLOCK.search((TEMPLATE / name).read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"template {name} has no harness block")
    text = match.group(0)
    return text if text.endswith("\n") else text + "\n"


def template_commit() -> str:
    try:
        commit = subprocess.run(["git", "-C", str(TEMPLATE), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(TEMPLATE), "status", "--porcelain"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return commit + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def is_source(repo: Path) -> bool:
    return repo.resolve() == TEMPLATE


def read_lock(repo: Path) -> dict | None:
    path = repo / LOCK
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"files": {}, "invalid": True}


def expected_files() -> dict[str, str]:
    files = {rel: sha((TEMPLATE / rel).read_bytes()) for rel in MANIFEST["managed"]}
    for name in MANIFEST["adapter_blocks"]:
        files[f"{name}#harness-block"] = sha(template_block(name).encode())
    return files


def current_hash(repo: Path, key: str) -> str | None:
    if key.endswith("#harness-block"):
        path = repo / key.split("#", 1)[0]
        if not path.is_file():
            return None
        match = BLOCK.search(path.read_text(encoding="utf-8"))
        if not match:
            return None
        text = match.group(0)
        return sha((text if text.endswith("\n") else text + "\n").encode())
    path = repo / key
    return sha(path.read_bytes()) if path.is_file() else None


def adopted_elsewhere(repo: Path) -> bool:
    """True when another local ref already contains the harness lock."""
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-list", "--all", "-1", "--", LOCK],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        return bool(out)
    except (OSError, subprocess.SubprocessError):
        return False


def status(repo: Path) -> dict:
    """Return {'state': ..., 'details': [...]} for one repository."""
    repo = repo.resolve()
    if is_source(repo):
        return {"state": "source", "details": []}
    if repo.name in WORKSPACE.get("exempt", []):
        return {"state": "exempt", "details": []}
    lock = read_lock(repo)
    if lock is None:
        if adopted_elsewhere(repo):
            return {"state": "unmerged",
                    "details": ["this branch predates the harness; merge the adopting branch (usually main)"]}
        return {"state": "missing", "details": ["harness is not installed"]}
    if lock.get("invalid"):
        return {"state": "modified", "details": [f"{LOCK} is not valid JSON"]}
    expected = expected_files()
    locked = lock.get("files", {})
    modified, outdated = [], []
    for key, want in expected.items():
        have = current_hash(repo, key)
        if have != locked.get(key):
            modified.append(key)
        elif have != want:
            outdated.append(key)
    if modified:
        return {"state": "modified", "details": [f"edited locally: {k}" for k in modified]}
    if outdated:
        return {"state": "outdated", "details": [f"template changed: {k}" for k in outdated]}
    return {"state": "synced", "details": []}


def show_diff(path: Path, new: str, label: str) -> None:
    old = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    sys.stdout.writelines(difflib.unified_diff(old, new.splitlines(keepends=True),
                                               f"{label} (current)", f"{label} (template)"))


def sync(repo: Path, force: bool, dry_run: bool) -> int:
    repo = repo.resolve()
    if is_source(repo):
        print("refusing to sync the template into itself", file=sys.stderr)
        return 2
    if not (repo / ".git").exists():
        print(f"not a Git repository root: {repo.name}", file=sys.stderr)
        return 2
    lock = read_lock(repo) or {"files": {}}
    locked = lock.get("files", {})
    actions: list[tuple[str, str]] = []
    conflicts: list[str] = []
    writes: dict[Path, tuple[str, bool]] = {}

    for rel in MANIFEST["managed"]:
        source = TEMPLATE / rel
        target = repo / rel
        new = source.read_text(encoding="utf-8")
        have = current_hash(repo, rel)
        if have == sha(new.encode()):
            continue
        if have is not None and have != locked.get(rel):
            conflicts.append(rel)
            show_diff(target, new, rel)
        actions.append(("update" if have else "create", rel))
        writes[target] = (new, rel.endswith(EXECUTABLE))

    today = dt.date.today().isoformat()
    for rel in MANIFEST["seeded"]:
        target = repo / rel
        if target.exists():
            continue
        text = (SEEDS / rel).read_text(encoding="utf-8").replace("{{DATE}}", today)
        actions.append(("seed", rel))
        writes[target] = (text, rel.endswith(EXECUTABLE))

    for name in MANIFEST["adapter_blocks"]:
        target = repo / name
        block = template_block(name)
        if target in writes:  # freshly seeded adapter
            text = writes[target][0]
        else:
            text = target.read_text(encoding="utf-8")
        if BLOCK.search(text):
            key = f"{name}#harness-block"
            have = current_hash(repo, key) if target not in writes else None
            if have is not None and have != locked.get(key) and have != sha(block.encode()):
                conflicts.append(key)
                show_diff(target, BLOCK.sub(lambda _: block, text, count=1), name)
            new_text = BLOCK.sub(lambda _: block, text, count=1)
        else:
            lines = text.split("\n", 1)
            if lines[0].startswith("# "):
                rest = lines[1] if len(lines) > 1 else ""
                new_text = f"{lines[0]}\n\n{block}\n{rest.lstrip(chr(10))}"
            else:
                new_text = f"{block}\n{text}"
        if new_text != text or target in writes:
            actions.append(("adapter", name))
            writes[target] = (new_text, False)

    gitignore = repo / ".gitignore"
    ignore_text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    missing = [line for line in MANIFEST["gitignore"] if line not in ignore_text.splitlines()]
    if missing:
        sep = "" if not ignore_text or ignore_text.endswith("\n") else "\n"
        new_ignore = ignore_text + sep + "\n# Agent harness private state\n" + "\n".join(missing) + "\n"
        actions.append(("gitignore", ".gitignore"))
        writes[gitignore] = (new_ignore, False)

    for kind, rel in actions:
        print(f"[{kind}] {rel}")
    if conflicts:
        print("\n[CONFLICT] project-edited managed content (diff above):", file=sys.stderr)
        for rel in conflicts:
            print(f"  {rel}", file=sys.stderr)
        if not force:
            print("Move project-specific content into a project-owned slot (.ai/README.md lists them), "
                  "then rerun with --force.", file=sys.stderr)
            return 1
    if dry_run:
        print("[dry-run] no files written")
        return 0

    for target, (text, executable) in writes.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if executable:
            target.chmod(target.stat().st_mode | 0o111)

    lock_data = {
        "schema": "agent-harness-lock/v1",
        "source": "izumuzui/agent-orchestrator-template",
        "template_commit": template_commit(),
        "synced_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "files": {key: current_hash(repo, key) for key in expected_files()},
    }
    (repo / LOCK).write_text(json.dumps(lock_data, indent=2) + "\n", encoding="utf-8")
    print(f"[lock] {LOCK}")
    print("Next: fill the project-owned slots, run scripts/agent/verify-change.sh full, review, commit.")
    return 0


def workspace_repos() -> list[Path]:
    root = Path(os.path.expanduser(WORKSPACE["root"]))
    return sorted(p for p in root.iterdir() if (p / ".git").exists())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "sync"):
        cmd = sub.add_parser(name, help="install or update the harness in a repository")
        cmd.add_argument("repo", type=Path)
        cmd.add_argument("--dry-run", action="store_true")
        cmd.add_argument("--force", action="store_true",
                         help="overwrite project-edited managed content after reviewing the diff")
    cmd = sub.add_parser("status", help="report harness state (default: every repo in the workspace)")
    cmd.add_argument("repos", type=Path, nargs="*")
    cmd.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command in ("install", "sync"):
        return sync(args.repo, args.force, args.dry_run)

    repos = args.repos or workspace_repos()
    report = {str(r.resolve().name): status(r) for r in repos}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for name, item in report.items():
            print(f"{item['state']:<9} {name}")
            for detail in item["details"]:
                print(f"          - {detail}")
    bad = {"missing", "unmerged", "modified", "outdated"}
    return 1 if any(item["state"] in bad for item in report.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
