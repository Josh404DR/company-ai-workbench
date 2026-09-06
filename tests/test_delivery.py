import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from company_workbench import WorkbenchEngine
from company_workbench.delivery import GitDeliveryAdapter, DeliveryError
from company_workbench.engine import InvalidTransitionError


class DeliveryTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name) / "repo"
        self.repo_dir.mkdir()

        # Initialize real git repository
        self._git(["init", "-b", "master"])
        self._git(["config", "user.name", "Test Deliverer"])
        self._git(["config", "user.email", "deliver@test.local"])
        self._git(["config", "commit.gpgsign", "false"])

        # Create initial commit on master
        readme = self.repo_dir / "README.md"
        readme.write_text("# Test Repo\n", encoding="utf-8")
        self._git(["add", "README.md"])
        self._git(["commit", "-m", "initial commit"])

        # Setup workbench engine
        self.db_path = Path(self.temp_dir.name) / "workbench.db"
        self.engine = WorkbenchEngine(self.db_path)
        self.ws = self.engine.create_workspace("Deliver WS")
        self.project = self.engine.create_project(self.ws["id"], "Deliver Project")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _git(self, args):
        res = subprocess.run(
            ["git"] + args,
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if res.returncode != 0:
            raise RuntimeError(f"Git failed: {res.stderr}")
        return res

    def _create_run_branch(self, run_id, filename, content):
        self._git(["checkout", "-b", f"wb-run/{run_id}"])
        file_path = self.repo_dir / filename
        file_path.write_text(content, encoding="utf-8")
        self._git(["add", filename])
        self._git(["commit", "-m", f"work on {run_id}"])
        self._git(["checkout", "master"])

    def test_deliver_unaccepted_ticket_rejected_by_invariant_9(self):
        ticket = self.engine.create_ticket(self.project["id"], "T1", "goal", ["criteria"])
        # Ticket is in 'ready', not 'accepted'
        with self.assertRaises(InvalidTransitionError) as ctx:
            self.engine.deliver_ticket(ticket["id"], self.repo_dir)
        self.assertIn("Invariant 9 requires explicit acceptance", str(ctx.exception))

    def test_deliver_accepted_ticket_merges_and_tags(self):
        ticket = self.engine.create_ticket(
            self.project["id"], "Feature 1", "add feature", ["criteria"],
            risk_level="low",
        )
        # Create run and run branch
        run = self.engine.start_run(ticket["id"], runner="codex-cli")
        self.engine.complete_run(run["id"])
        self._create_run_branch(run["id"], "feature1.txt", "feature 1 implementation\n")

        # Verify and accept
        v = self.engine.verify_run(
            run["id"], status="passed", evidence_ref="cmd://test", summary="all passed",
            verifier="verifier", verifier_provider="local-command",
            evidence_content=b"test-evidence",
        )
        self.engine.accept_ticket(ticket["id"], accepted_by="Josh")

        # Now deliver ticket
        deliv = self.engine.deliver_ticket(ticket["id"], self.repo_dir, target_branch="master")
        self.assertEqual(ticket["id"], deliv["ticket_id"])
        self.assertEqual("delivered", deliv["delivery_result"]["status"])
        self.assertIn("feature1.txt", deliv["delivery_result"]["files_changed"])

        # Check master has the file
        self._git(["checkout", "master"])
        f1 = self.repo_dir / "feature1.txt"
        self.assertTrue(f1.exists())
        self.assertEqual("feature 1 implementation\n", f1.read_text(encoding="utf-8"))

        # Verify delivery event recorded
        events = self.engine.list_events(run["id"])
        deliv_events = [e for e in events if e["kind"] == "delivery_completed"]
        self.assertEqual(1, len(deliv_events))
        self.assertEqual("master", deliv_events[0]["payload"]["target_branch"])

    def test_generate_patch(self):
        run_id = "RUN-patch-test"
        self._create_run_branch(run_id, "patch_mod.txt", "patch contents\n")
        adapter = GitDeliveryAdapter(self.repo_dir)
        patch_file = adapter.generate_patch(run_id, base_branch="master")
        self.assertTrue(patch_file.exists())
        content = patch_file.read_text(encoding="utf-8")
        self.assertIn("+patch contents", content)

    def test_deliver_goal_orchestration(self):
        goal = self.engine.create_goal(self.project["id"], "Multi-ticket Goal")
        t1 = self.engine.create_ticket(self.project["id"], "Step 1", "g1", ["c1"], goal_id=goal["id"])
        t2 = self.engine.create_ticket(self.project["id"], "Step 2", "g2", ["c2"], goal_id=goal["id"], depends_on_ticket_id=t1["id"])

        # Setup runs and branches for both
        r1 = self.engine.start_run(t1["id"], runner="codex-cli")
        self.engine.complete_run(r1["id"])
        self._create_run_branch(r1["id"], "step1.txt", "step 1 done\n")
        v1 = self.engine.verify_run(r1["id"], status="passed", evidence_ref="cmd://1", summary="p", verifier="v", verifier_provider="local-command", evidence_content=b"1")
        self.engine.accept_ticket(t1["id"], accepted_by="Josh")

        r2 = self.engine.start_run(t2["id"], runner="codex-cli")
        self.engine.complete_run(r2["id"])
        self._create_run_branch(r2["id"], "step2.txt", "step 2 done\n")
        v2 = self.engine.verify_run(r2["id"], status="passed", evidence_ref="cmd://2", summary="p", verifier="v", verifier_provider="local-command", evidence_content=b"2")
        self.engine.accept_ticket(t2["id"], accepted_by="Josh")

        # Deliver goal
        goal_deliv = self.engine.deliver_goal(goal["id"], self.repo_dir, target_branch="master")
        self.assertEqual("achieved", goal_deliv["goal"]["status"])
        self.assertEqual(2, len(goal_deliv["ticket_deliveries"]))

        # Check master has both files
        self._git(["checkout", "master"])
        self.assertTrue((self.repo_dir / "step1.txt").exists())
        self.assertTrue((self.repo_dir / "step2.txt").exists())


if __name__ == "__main__":
    unittest.main()
