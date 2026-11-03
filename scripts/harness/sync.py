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


def git_out(repo: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def default_refs(repo: Path) -> tuple[str, list[str]] | None:
    """Default branch name and its existing local/remote refs."""
    head = git_out(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    names = [head.split("/", 1)[1]] if head and "/" in head else []
    for name in names + ["main", "master"]:
        refs = [ref for ref in (name, f"origin/{name}")
                if git_out(repo, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}") is not None]
        if refs:
            return name, refs
    return None


TASK_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
TASK_EVENTS = {"routing_reserved", "task_completed"}
REVIEW_RELATIONS = {"none", "fresh_same", "cross_provider"}


def parse_ts(value: object) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        ts = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)


def valid_event(event: object) -> bool:
    """Shape check so that only opaque IDs and enums reach the report."""
    if not (isinstance(event, dict) and isinstance(event.get("event"), str)
            and event["event"] in TASK_EVENTS and isinstance(event.get("task_id"), str)
            and TASK_ID.fullmatch(event["task_id"]) and isinstance(event.get("calibration"), bool)):
        return False
    if event["event"] == "routing_reserved":
        return parse_ts(event.get("ts")) is not None
    return isinstance(event.get("reviewer_relation"), str) and event["reviewer_relation"] in REVIEW_RELATIONS


def read_events(repo: Path) -> tuple[list[dict], int]:
    """Valid task events plus the count of skipped lines. Raises OSError when unreadable."""
    path = repo / ".agent-state/metrics/task-events.jsonl"
    events, malformed = [], 0
    if not path.is_file():
        return events, malformed
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            # ValueError covers bad JSON and oversized integers; deep nesting raises RecursionError.
            event = json.loads(line)
            ok = valid_event(event)
        except (ValueError, RecursionError, TypeError):
            ok = False
        if ok:
            events.append(event)
        else:
            malformed += 1
    return events, malformed


def health(repo: Path, stale_days: int, now: dt.datetime | None = None,
           calibration_size: int = 10, checkpoint_every: int = 10) -> dict:
    """Read-only operating report: sync state, task-event bookkeeping, Git hygiene."""
    repo = repo.resolve()
    now = now or dt.datetime.now(dt.timezone.utc)
    report: dict = {"state": status(repo)["state"], "warnings": []}
    warn = report["warnings"].append
    if report["state"] in {"missing", "unmerged", "modified", "outdated"}:
        warn(f"harness state is {report['state']}")

    linked = (repo / ".git").is_file()
    if linked:
        common = git_out(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
        report["worktree_of"] = Path(common).parent.name if common else "unknown"
    else:
        listing = git_out(repo, "worktree", "list", "--porcelain") or ""
        prunable = sum(1 for line in listing.splitlines() if line.startswith("prunable"))
        report["prunable_worktrees"] = prunable
        if prunable:
            warn(f"{prunable} prunable worktree(s); run git worktree prune")

    if (repo / LOCK).is_file() and not is_source(repo):
        base = default_refs(repo)
        # Adopted once either the local or the remote default branch carries the lock,
        # so a stale local branch alone does not raise the warning.
        if base and all(git_out(repo, "cat-file", "-e", f"{ref}:{LOCK}") is None for ref in base[1]):
            warn(f"harness adoption is not merged into {base[0]}")

    try:
        events, malformed = read_events(repo)
    except OSError:
        events, malformed = [], 0
        warn("task-event journal is unreadable")
    reserved = {e["task_id"]: e for e in events if e["event"] == "routing_reserved"}
    completed = {e["task_id"]: e for e in events if e["event"] == "task_completed"}
    open_ids = sorted(set(reserved) - set(completed))
    stale = []
    for task_id in open_ids:
        ts = parse_ts(reserved[task_id].get("ts"))
        if ts and (now - ts).days >= stale_days:
            stale.append(task_id)
    done = len(completed)
    report["tasks"] = {
        "reserved": len(reserved),
        "completed": done,
        "reserved_ids": sorted(reserved),
        "completed_ids": sorted(completed),
        "open": open_ids,
        "stale_open": stale,
        "malformed_lines": malformed,
        "calibration_completed": sum(1 for e in completed.values() if e.get("calibration") is True),
        "calibration_size": calibration_size,
        "next_checkpoint": (done // checkpoint_every + 1) * checkpoint_every,
        "cross_provider_reviews": sum(1 for e in completed.values()
                                      if e.get("reviewer_relation") == "cross_provider"),
    }
    if stale:
        warn(f"{len(stale)} reservation(s) open for {stale_days}+ days without task_completed")
    if malformed:
        warn(f"{malformed} malformed task-event line(s) skipped")
    return report


def print_health(name: str, item: dict) -> None:
    label = item["state"] + (f", worktree of {item['worktree_of']}" if "worktree_of" in item else "")
    print(f"{name} ({label})")
    tasks = item["tasks"]
    if tasks["reserved"] or tasks["completed"]:
        print(f"  tasks: reserved {tasks['reserved']}, completed {tasks['completed']}, "
              f"open {len(tasks['open'])}")
        print(f"  calibration: {tasks['calibration_completed']}/{tasks['calibration_size']} completed; "
              f"next checkpoint at {tasks['next_checkpoint']} completed")
        print(f"  cross-provider reviews: {tasks['cross_provider_reviews']}/{tasks['completed']}")
        if tasks["completed_ids"]:
            print(f"  completed: {', '.join(tasks['completed_ids'])}")
        for task_id in tasks["open"]:
            mark = " (stale)" if task_id in tasks["stale_open"] else ""
            print(f"  open: {task_id}{mark}")
    else:
        print("  tasks: no task events")
    for warning in item["warnings"]:
        print(f"  ! {warning}")


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
    cmd = sub.add_parser("health", help="read-only operating report: task events, calibration, Git hygiene")
    cmd.add_argument("repos", type=Path, nargs="*")
    cmd.add_argument("--json", action="store_true")
    cmd.add_argument("--stale-days", type=int, default=3,
                     help="flag reservations open this many days without task_completed (default 3)")
    args = parser.parse_args()

    if args.command in ("install", "sync"):
        return sync(args.repo, args.force, args.dry_run)

    repos = args.repos or workspace_repos()
    if args.command == "health":
        if args.stale_days < 0:
            parser.error("--stale-days must not be negative")
        report = {str(r.resolve().name): health(r, args.stale_days) for r in repos
                  if r.resolve().name not in WORKSPACE.get("exempt", [])}
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            for name, item in report.items():
                print_health(name, item)
        return 1 if any(item["warnings"] for item in report.values()) else 0

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
