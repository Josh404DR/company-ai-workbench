import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from company_workbench.cli import main
from company_workbench.engine import WorkbenchEngine


class CliGoalsTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.engine = WorkbenchEngine(self.db_path)
        self.ws = self.engine.create_workspace("Test WS")
        self.prj = self.engine.create_project(self.ws["id"], "Test PRJ")

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, args: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--database", str(self.db_path)] + args)
        return code, out.getvalue(), err.getvalue()

    def test_goal_lifecycle_cli(self):
        # 1. Create Goal
        code, out, err = self.run_cli(["goal", "create", self.prj["id"], "My Long Goal", "--desc", "Full test"])
        self.assertEqual(0, code, err)
        goal_data = json.loads(out)
        self.assertEqual("My Long Goal", goal_data["title"])
        self.assertEqual("planned", goal_data["status"])
        goal_id = goal_data["id"]

        # 2. List Goals
        code, out, err = self.run_cli(["goal", "list", self.prj["id"]])
        self.assertEqual(0, code)
        goals = json.loads(out)
        self.assertEqual(1, len(goals))
        self.assertEqual(goal_id, goals[0]["id"])

        # 3. Create Ticket linked directly to Goal
        code, out, err = self.run_cli([
            "ticket", "create", self.prj["id"], "Step 1",
            "--goal", "finish step 1",
            "--criteria", "step 1 criteria",
            "--goal-id", goal_id,
            "--risk", "low",
        ])
        self.assertEqual(0, code, err)
        t1 = json.loads(out)
        self.assertEqual(goal_id, t1["goal_id"])

        # 4. Create Ticket 2 and link via goal link
        code, out, err = self.run_cli([
            "ticket", "create", self.prj["id"], "Step 2",
            "--goal", "finish step 2",
            "--criteria", "step 2 criteria",
            "--risk", "low",
        ])
        self.assertEqual(0, code)
        t2 = json.loads(out)
        self.assertIsNone(t2["goal_id"])

        code, out, err = self.run_cli(["goal", "link", t2["id"], goal_id, "--depends-on", t1["id"]])
        self.assertEqual(0, code)
        t2_linked = json.loads(out)
        self.assertEqual(goal_id, t2_linked["goal_id"])
        self.assertEqual(t1["id"], t2_linked["depends_on_ticket_id"])

        # 5. Show Goal
        code, out, err = self.run_cli(["goal", "show", goal_id])
        self.assertEqual(0, code)
        goal_detail = json.loads(out)
        self.assertEqual(2, goal_detail["total_tickets"])
        self.assertEqual(0, goal_detail["accepted_tickets"])

        # 6. Advance Goal with fake runner and passing verification
        verify_cmd = f'"{sys.executable}" -c "exit(0)"'
        code, out, err = self.run_cli([
            "goal", "advance", goal_id,
            "--runner", "fake",
            "--verify-cmd", verify_cmd,
            "--no-worktree",
            "--cwd", self.temp_dir.name,
        ])
        self.assertEqual(0, code, err)
        adv1 = json.loads(out)
        self.assertEqual("ran_ticket", adv1["action"])
        self.assertEqual(t1["id"], adv1["ticket_id"])
        self.assertTrue(adv1["loop_result"]["success"])

        # Advance again -> runs Step 2 (now unblocked)
        code, out, err = self.run_cli([
            "goal", "advance", goal_id,
            "--runner", "fake",
            "--verify-cmd", verify_cmd,
            "--no-worktree",
            "--cwd", self.temp_dir.name,
        ])
        self.assertEqual(0, code, err)
        adv2 = json.loads(out)
        self.assertEqual("ran_ticket", adv2["action"])
        self.assertEqual("achieved", adv2["goal"]["status"])
        self.assertEqual(100.0, adv2["goal"]["progress_pct"])

    def test_ticket_and_goal_deliver_cli(self):
        # Set up a real git repo
        repo_dir = Path(self.temp_dir.name) / "cli_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init", "-b", "master"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "CLI Tester"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "cli@test.local"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "init.txt").write_text("initial", encoding="utf-8")
        subprocess.run(["git", "add", "init.txt"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_dir, check=True, capture_output=True)

        # Create goal and ticket
        goal = self.engine.create_goal(self.prj["id"], "Deliverable Goal")
        t = self.engine.create_ticket(self.prj["id"], "Deliverable Ticket", "task", ["criteria"], goal_id=goal["id"])

        # Unaccepted ticket cannot be delivered (Invariant 9)
        code, out, err = self.run_cli(["ticket", "deliver", t["id"], "--repo", str(repo_dir)])
        self.assertEqual(1, code)
        self.assertIn("Invariant 9 requires explicit acceptance", err)

        # Complete, create branch, verify, accept
        run = self.engine.start_run(t["id"], runner="codex-cli")
        self.engine.complete_run(run["id"])
        subprocess.run(["git", "checkout", "-b", f"wb-run/{run['id']}"], cwd=repo_dir, check=True, capture_output=True)
        (repo_dir / "work.txt").write_text("delivered work", encoding="utf-8")
        subprocess.run(["git", "add", "work.txt"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "done"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "checkout", "master"], cwd=repo_dir, check=True, capture_output=True)

        self.engine.verify_run(
            run["id"], status="passed", evidence_ref="cmd://v", summary="v",
            verifier="v", verifier_provider="local-command", evidence_content=b"proof",
        )
        self.engine.accept_ticket(t["id"], accepted_by="Josh")

        # Now deliver ticket via CLI
        code, out, err = self.run_cli(["ticket", "deliver", t["id"], "--repo", str(repo_dir)])
        self.assertEqual(0, code, err)
        deliv_res = json.loads(out)
        self.assertEqual("delivered", deliv_res["delivery_result"]["status"])
        self.assertTrue((repo_dir / "work.txt").exists())

        # Deliver goal via CLI
        code, out, err = self.run_cli(["goal", "deliver", goal["id"], "--repo", str(repo_dir)])
        self.assertEqual(0, code, err)
        g_deliv = json.loads(out)
        self.assertEqual("achieved", g_deliv["goal"]["status"])

    def test_ui_and_serve_cli_dispatch(self):
        from unittest.mock import patch

        with patch("company_workbench.ui_server.serve_ui", return_value=0) as mock_serve:
            code, out, err = self.run_cli(["ui", "--port", "9099", "--host", "0.0.0.0", "--no-browser"])
            self.assertEqual(0, code)
            mock_serve.assert_called_once_with(
                database=self.db_path,
                host="0.0.0.0",
                port=9099,
                open_browser=False,
            )

        with patch("company_workbench.ui_server.serve_ui", return_value=0) as mock_serve:
            code, out, err = self.run_cli(["serve", "--port", "8888"])
            self.assertEqual(0, code)
            mock_serve.assert_called_once_with(
                database=self.db_path,
                host="127.0.0.1",
                port=8888,
                open_browser=True,
            )


if __name__ == "__main__":
    unittest.main()
