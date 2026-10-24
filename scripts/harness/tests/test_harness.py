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


if __name__ == "__main__":
    unittest.main()
