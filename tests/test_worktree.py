import subprocess
import tempfile
import unittest
from pathlib import Path

from company_workbench.errors import WorktreeError
from company_workbench.worktree import GitWorktreeManager, _run_git


class GitWorktreeTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name) / "test_repo"
        self.repo_root.mkdir()

        # Initialize a real local git repo
        _run_git(["init", "-b", "main"], cwd=self.repo_root)
        _run_git(["config", "user.name", "Workbench Test"], cwd=self.repo_root)
        _run_git(["config", "user.email", "test@workbench.local"], cwd=self.repo_root)

        # Initial commit
        readme = self.repo_root / "README.md"
        readme.write_text("# Test Repo\n", encoding="utf-8")
        _run_git(["add", "README.md"], cwd=self.repo_root)
        _run_git(["commit", "-m", "Initial commit"], cwd=self.repo_root)

        self.manager = GitWorktreeManager(self.repo_root)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_rejects_non_git_directory(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            with self.assertRaises(WorktreeError):
                GitWorktreeManager(empty_dir)

    def test_create_worktree_and_verify_isolation(self):
        run_id = "RUN-test001"
        env = self.manager.create_worktree(run_id)

        self.assertTrue(env.worktree_path.exists())
        self.assertEqual(f"wb-run/{run_id}", env.branch_name)

        # Verify initial file exists in worktree
        worktree_readme = env.worktree_path / "README.md"
        self.assertTrue(worktree_readme.exists())
        self.assertEqual("# Test Repo\n", worktree_readme.read_text(encoding="utf-8"))

        # AI writes a new file in worktree
        new_file = env.worktree_path / "ai_output.py"
        new_file.write_text("print('hello from AI')\n", encoding="utf-8")

        # Verify source repo is completely clean and isolated!
        source_new_file = self.repo_root / "ai_output.py"
        self.assertFalse(source_new_file.exists(), "Source repo must remain clean and untouched!")

        # Verify worktree detects changed files
        changed = env.get_changed_files()
        self.assertTrue(any("ai_output.py" in f for f in changed))

        # Cleanup worktree
        env.cleanup()
        self.assertFalse(env.worktree_path.exists())

    def test_start_managed_run_with_isolated_worktree(self):
        from company_workbench.engine import WorkbenchEngine
        from company_workbench.runner import CodexCliRunner, ProcessResult, ProcessExecutor

        class FakeWorktreeExecutor:
            def __init__(self):
                self.calls = []

            def start(self, argv, *, cwd):
                # Write an AI file directly inside the target cwd (which should be the worktree)
                ai_file = cwd / "ai_patch.txt"
                ai_file.write_text("AI worktree content\n", encoding="utf-8")
                from company_workbench.runner import ProcessHandle
                import subprocess
                import tempfile
                stdout_file = tempfile.TemporaryFile("w+b")
                stderr_file = tempfile.TemporaryFile("w+b")
                proc = subprocess.Popen([sys.executable, "-c", "print('{\"ok\": true}')"], stdout=stdout_file, stderr=stderr_file)
                return ProcessHandle(proc, stdout_file, stderr_file)

        import sys
        engine = WorkbenchEngine(self.repo_root / ".workbench" / "test.db")
        ws = engine.create_workspace("GitWS")
        prj = engine.create_project(ws["id"], "GitPRJ")
        tkt = engine.create_ticket(prj["id"], "Git Task", "Do git task", ["Criterion"])

        runner = CodexCliRunner(executor=FakeWorktreeExecutor())
        run = engine.start_managed_run(
            tkt["id"],
            runner,
            "generate patch",
            cwd=self.repo_root,
            isolate_worktree=True,
        )

        self.assertEqual("completed", run["status"])
        # Check source checkout remains clean
        self.assertFalse((self.repo_root / "ai_patch.txt").exists())

        # Check events captured worktree info and diff
        events = engine.list_events(run["id"])
        start_event = next(e for e in events if e["kind"] == "run_started")
        self.assertIn("worktree_path", start_event["payload"])
        self.assertIn("branch_name", start_event["payload"])

        output_event = next(e for e in events if e["kind"] == "invocation_output")
        self.assertIn("changed_files", output_event["payload"])
        self.assertTrue(any("ai_patch.txt" in f for f in output_event["payload"]["changed_files"]))

    def test_automated_verification_pass_and_fail(self):
        import sys
        from company_workbench.engine import WorkbenchEngine
        from company_workbench.runner import CodexCliRunner, ProcessHandle

        class FakeExecutorWithScript:
            def __init__(self, code_to_write: str):
                self.code_to_write = code_to_write

            def start(self, argv, *, cwd):
                target = cwd / "calc.py"
                target.write_text(self.code_to_write, encoding="utf-8")
                import tempfile
                stdout_file = tempfile.TemporaryFile("w+b")
                stderr_file = tempfile.TemporaryFile("w+b")
                proc = subprocess.Popen([sys.executable, "-c", "print('{\"ok\": true}')"], stdout=stdout_file, stderr=stderr_file)
                return ProcessHandle(proc, stdout_file, stderr_file)

        engine = WorkbenchEngine(self.repo_root / ".workbench" / "test_v.db")
        ws = engine.create_workspace("AutoWS")
        prj = engine.create_project(ws["id"], "AutoPRJ")

        # 1. Test Passing Verification
        tkt_pass = engine.create_ticket(prj["id"], "Pass Ticket", "Goal", ["Criterion"])
        runner_pass = CodexCliRunner(executor=FakeExecutorWithScript("def add(a, b): return a + b\nassert add(1, 2) == 3\n"))
        run_p = engine.start_managed_run(
            tkt_pass["id"],
            runner_pass,
            "write add",
            cwd=self.repo_root,
            isolate_worktree=True,
            verification_command=f'"{sys.executable}" calc.py',
        )
        self.assertEqual("completed", run_p["status"])
        tkt_p_after = engine.get_ticket(tkt_pass["id"])
        self.assertEqual("verification", tkt_p_after["status"])

        # Check automated verification was recorded
        events_p = engine.list_events(run_p["id"])
        ver_event = next(e for e in events_p if e["kind"] == "verification_recorded")
        self.assertTrue(ver_event["payload"]["automated"])
        self.assertEqual("passed", ver_event["payload"]["status"])

        # 2. Test Failing Verification
        tkt_fail = engine.create_ticket(prj["id"], "Fail Ticket", "Goal", ["Criterion"])
        runner_fail = CodexCliRunner(executor=FakeExecutorWithScript("def add(a, b): return a - b\nassert add(1, 2) == 3\n"))
        run_f = engine.start_managed_run(
            tkt_fail["id"],
            runner_fail,
            "write broken add",
            cwd=self.repo_root,
            isolate_worktree=True,
            verification_command=f'"{sys.executable}" calc.py',
        )
        self.assertEqual("failed", run_f["status"])
        self.assertEqual("VERIFICATION-FAILED", run_f["error_code"])
        tkt_f_after = engine.get_ticket(tkt_fail["id"])
        self.assertEqual("ready", tkt_f_after["status"], "Failed verification must return ticket to ready")

    def test_worktree_cleaned_up_on_launch_error(self):
        from company_workbench.engine import WorkbenchEngine
        from company_workbench.errors import RunnerLaunchError

        class LaunchFailingRunner:
            def start_invocation(self, *args, **kwargs):
                raise RunnerLaunchError("Simulated missing API key or executable")

        engine = WorkbenchEngine(self.repo_root / ".workbench" / "test_cleanup.db")
        ws = engine.create_workspace("CleanupWS")
        prj = engine.create_project(ws["id"], "CleanupPRJ")
        tkt = engine.create_ticket(prj["id"], "Cleanup Ticket", "Goal", ["Criterion"])

        worktrees_dir = self.repo_root / ".workbench" / "worktrees"
        with self.assertRaises(RunnerLaunchError):
            engine.start_managed_run(
                tkt["id"],
                LaunchFailingRunner(),
                "should fail launch",
                cwd=self.repo_root,
                isolate_worktree=True,
            )

        # Confirm no orphaned worktree folders exist
        if worktrees_dir.exists():
            self.assertEqual([], list(worktrees_dir.iterdir()), "Worktree directory must be cleaned up on launch failure")


if __name__ == "__main__":
    unittest.main()
