import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))
import guard  # noqa: E402
import sync  # noqa: E402


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.workspace = patch.dict(sync.WORKSPACE, {"root": str(self.root), "exempt": ["notes"]})
        self.workspace.start()
        self.repo = self.root / "app"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        (self.repo / "AGENTS.md").write_text("# App rules\n\nNever add a backend.\n")

    def tearDown(self):
        self.workspace.stop()
        self.tmp.cleanup()

    def run_sync(self, *flags):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = sync.sync(self.repo, force="--force" in flags, dry_run="--dry-run" in flags)
        return code, out.getvalue()

    def hook(self, payload):
        out = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(out):
            guard.main()
        return json.loads(out.getvalue()) if out.getvalue().strip() else None

    def edit(self, path, tool="Write"):
        return self.hook({"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": str(self.repo),
                          "tool_input": {"file_path": str(path)}})

    def test_install_preserves_project_rules_and_passes_gate(self):
        self.assertEqual(sync.status(self.repo)["state"], "missing")
        code, _ = self.run_sync()
        self.assertEqual(code, 0)
        agents = (self.repo / "AGENTS.md").read_text()
        self.assertTrue(agents.startswith("# App rules\n\n<!-- HARNESS:START -->"))
        self.assertIn("Never add a backend.", agents)
        self.assertIn("@AGENTS.md", (self.repo / "CLAUDE.md").read_text())
        self.assertIn("/.agent-state/", (self.repo / ".gitignore").read_text())
        self.assertEqual(sync.status(self.repo)["state"], "synced")
        gate = subprocess.run(["bash", "scripts/agent/verify-change.sh", "agent-env"],
                              cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
        full = subprocess.run(["bash", "scripts/agent/verify-change.sh", "full"],
                              cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(full.returncode, 3, full.stdout + full.stderr)
        self.assertIn("[OVERALL] blocked", full.stdout)

    def test_resync_is_idempotent_and_local_edits_are_refused(self):
        self.run_sync()
        lock = (self.repo / sync.LOCK).read_text()
        code, out = self.run_sync()
        self.assertEqual(code, 0)
        self.assertNotIn("[update]", out)
        self.assertNotIn("[adapter]", out)
        self.assertEqual(json.loads(lock)["files"], json.loads((self.repo / sync.LOCK).read_text())["files"])

        review = self.repo / ".ai/workflows/review.md"
        review.write_text(review.read_text() + "\nlocal tweak\n")
        self.assertEqual(sync.status(self.repo)["state"], "modified")
        code, _ = self.run_sync()
        self.assertEqual(code, 1)
        self.assertIn("local tweak", review.read_text())
        code, _ = self.run_sync("--force")
        self.assertEqual(code, 0)
        self.assertEqual(sync.status(self.repo)["state"], "synced")

    def test_project_owned_slots_are_never_overwritten(self):
        self.run_sync()
        project = self.repo / ".ai/project.md"
        project.write_text("# mine\n")
        self.run_sync()
        self.assertEqual(project.read_text(), "# mine\n")

    def test_guard_denies_unadopted_repo_and_managed_files(self):
        result = self.edit(self.repo / "src/main.py")
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.run_sync()
        self.assertIsNone(self.edit(self.repo / "src/main.py"))
        self.assertIsNone(self.edit(self.repo / "AGENTS.md"))
        result = self.edit(self.repo / ".ai/workflows/review.md")
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        patch_text = "*** Begin Patch\n*** Update File: scripts/agent/quota.py\n@@\n*** End Patch\n"
        result = self.hook({"hook_event_name": "PreToolUse", "tool_name": "apply_patch",
                            "cwd": str(self.repo), "tool_input": {"input": patch_text}})
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_guard_ignores_exempt_outside_and_unguarded_tools(self):
        notes = self.root / "notes"
        notes.mkdir()
        git(notes, "init", "-q")
        self.assertIsNone(self.edit(notes / "a.md"))
        self.assertIsNone(self.edit(Path(tempfile.gettempdir()) / "x.txt"))
        self.assertIsNone(self.edit(self.repo / "src/main.py", tool="Read"))

    def test_guard_allows_branch_of_adopted_repo(self):
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "base")
        git(self.repo, "switch", "-q", "-c", "old-feature")
        git(self.repo, "switch", "-q", "-")
        self.run_sync()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "adopt")
        git(self.repo, "switch", "-q", "old-feature")
        self.assertFalse((self.repo / sync.LOCK).exists())
        self.assertEqual(sync.status(self.repo)["state"], "unmerged")
        self.assertIsNone(self.edit(self.repo / "src/main.py"))
        start = self.hook({"hook_event_name": "SessionStart", "cwd": str(self.repo)})
        self.assertIn("別のブランチでは導入済み", start["hookSpecificOutput"]["additionalContext"])

    def test_session_start_reports_state(self):
        start = self.hook({"hook_event_name": "SessionStart", "cwd": str(self.repo)})
        self.assertIn("state=missing", start["hookSpecificOutput"]["additionalContext"])
        self.run_sync()
        start = self.hook({"hook_event_name": "SessionStart", "cwd": str(self.repo / "src")})
        self.assertIn("state=synced", start["hookSpecificOutput"]["additionalContext"])

    def test_guard_fails_open(self):
        out = io.StringIO()
        with patch("sys.stdin", io.StringIO("not json")), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(guard.main(), 0)
        self.assertEqual(out.getvalue(), "")

    def commit_base(self):
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "add", "AGENTS.md")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "branch", "-M", "main")

    def write_events(self, *lines):
        path = self.repo / ".agent-state/metrics/task-events.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("".join((l if isinstance(l, str) else json.dumps(l)) + "\n" for l in lines))

    def run_main(self, *argv):
        out = io.StringIO()
        with patch("sys.argv", ["sync.py", *argv]), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            code = sync.main()
        return code, out.getvalue()

    def test_health_reports_task_bookkeeping(self):
        self.run_sync()
        reserve = lambda tid, ts, cal=True: {"event": "routing_reserved", "task_id": tid, "ts": ts,
                                             "calibration": cal}
        self.write_events(
            reserve("done-cross", "2026-11-01T00:00:00Z"),
            {"event": "task_completed", "task_id": "done-cross", "calibration": True,
             "reviewer_relation": "cross_provider"},
            reserve("done-same", "2026-11-01T00:00:00Z", cal=False),
            {"event": "task_completed", "task_id": "done-same", "calibration": False,
             "reviewer_relation": "fresh_same"},
            reserve("old-open", "2026-10-25T00:00:00Z"),
            reserve("new-open", "2026-11-02T12:00:00Z"),
            "{not json",
            "[1, 2]",
            {"event": "routing_reserved", "task_id": "private text\nline", "ts": "2026-10-01T00:00:00Z"},
            {"event": "routing_reserved", "task_id": "no-ts", "calibration": True},
            {"event": [], "task_id": "a"},
            '{"event": "task_completed", "n": ' + "1" * 5000 + "}",
            "[" * 100000 + "]" * 100000,
            {"event": "task_completed", "task_id": "old-open"},
            {"event": "task_completed", "task_id": "old-open", "calibration": True, "reviewer_relation": []},
        )
        now = sync.dt.datetime(2026, 11, 3, tzinfo=sync.dt.timezone.utc)
        before = sorted(p.relative_to(self.repo) for p in self.repo.rglob("*"))
        tasks = sync.health(self.repo, stale_days=3, now=now)["tasks"]
        self.assertEqual(sorted(p.relative_to(self.repo) for p in self.repo.rglob("*")), before)
        self.assertEqual((tasks["reserved"], tasks["completed"]), (4, 2))
        self.assertEqual(tasks["open"], ["new-open", "old-open"])
        self.assertEqual(tasks["stale_open"], ["old-open"])
        self.assertEqual(tasks["malformed_lines"], 9)
        self.assertEqual(tasks["completed_ids"], ["done-cross", "done-same"])
        self.assertEqual(tasks["calibration_completed"], 1)
        self.assertEqual(tasks["cross_provider_reviews"], 1)
        self.assertEqual(tasks["next_checkpoint"], 10)
        warnings = sync.health(self.repo, stale_days=3, now=now)["warnings"]
        self.assertTrue(any("1 reservation(s) open" in w for w in warnings))
        self.assertTrue(any("9 malformed" in w for w in warnings))

    def test_health_clean_repo_exits_zero_and_json(self):
        self.run_sync()
        code, out = self.run_main("health", "--json", str(self.repo))
        self.assertEqual(code, 0)
        report = json.loads(out)["app"]
        self.assertEqual(report["state"], "synced")
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["tasks"]["reserved"], 0)
        code, out = self.run_main("health", str(self.repo / "missing-is-not-a-repo-but-path"))
        self.assertEqual(code, 1)

    def test_health_flags_unmerged_adoption(self):
        self.commit_base()
        git(self.repo, "switch", "-q", "-c", "adopt")
        self.run_sync()
        warnings = sync.health(self.repo, stale_days=3)["warnings"]
        self.assertIn("harness adoption is not merged into main", warnings)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "adopt")
        git(self.repo, "switch", "-q", "main")
        git(self.repo, "merge", "-q", "adopt")
        self.assertEqual(sync.health(self.repo, stale_days=3)["warnings"], [])

    def test_health_accepts_adoption_on_remote_default_with_stale_local(self):
        self.commit_base()
        git(self.repo, "switch", "-q", "-c", "adopt")
        self.run_sync()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "adopt")
        git(self.repo, "update-ref", "refs/remotes/origin/main", "adopt")
        self.assertEqual(sync.health(self.repo, stale_days=3)["warnings"], [])

    def test_health_survives_unreadable_journal(self):
        self.run_sync()
        self.write_events({"event": "routing_reserved", "task_id": "a", "ts": "2026-11-01T00:00:00Z"})
        real = sync.Path.read_text

        def deny(path, *args, **kwargs):
            if path.name == "task-events.jsonl":
                raise PermissionError("denied")
            return real(path, *args, **kwargs)

        with patch.object(sync.Path, "read_text", deny):
            report = sync.health(self.repo, stale_days=3)
        self.assertIn("task-event journal is unreadable", report["warnings"])
        self.assertEqual(report["tasks"]["reserved"], 0)

    def test_health_labels_worktrees_and_counts_prunable(self):
        self.commit_base()
        self.run_sync()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "adopt")
        linked = self.root / "app-linked"
        gone = self.root / "app-gone"
        git(self.repo, "worktree", "add", "-q", str(linked), "-b", "side")
        git(self.repo, "worktree", "add", "-q", str(gone), "-b", "gone")
        subprocess.run(["rm", "-rf", str(gone)], check=True)
        self.assertEqual(sync.health(linked, stale_days=3)["worktree_of"], "app")
        main = sync.health(self.repo, stale_days=3)
        self.assertNotIn("worktree_of", main)
        self.assertEqual(main["prunable_worktrees"], 1)
        self.assertIn("1 prunable worktree(s); run git worktree prune", main["warnings"])


if __name__ == "__main__":
    unittest.main()
