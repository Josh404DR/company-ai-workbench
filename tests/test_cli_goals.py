import io
import json
import os
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
        self.assertEqual(t2["id"], adv2["ticket_id"])
        self.assertEqual("achieved", adv2["goal"]["status"])
        self.assertEqual(100.0, adv2["goal"]["progress_pct"])


if __name__ == "__main__":
    unittest.main()
