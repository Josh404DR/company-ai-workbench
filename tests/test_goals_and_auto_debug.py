import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from company_workbench import WorkbenchEngine
from company_workbench.engine import TIERED_ACCEPTANCE_AUTHORITY
from company_workbench.errors import NotFoundError
from company_workbench.runner import CodexCliRunner, ProcessResult
from company_workbench.store import SQLiteStore


class FakeManagedProcess:
    def __init__(self, result: ProcessResult):
        self._result = result
        self.pid = result.pid or 1234
        self.wait_calls = []

    def wait(self, *, cancel_event=None, **kwargs):
        was_cancelled = cancel_event is not None and cancel_event.is_set()
        self.wait_calls.append(was_cancelled)
        if was_cancelled:
            return ProcessResult(exit_code=None, cancelled=True, pid=self.pid)
        return self._result


class SequenceExecutor:
    def __init__(self, results: list[ProcessResult]):
        self.results = list(results)
        self.calls = []

    def start(self, argv, *, cwd):
        self.calls.append((tuple(argv), cwd))
        if self.results:
            result = self.results.pop(0)
        else:
            result = ProcessResult(0, "default success", pid=999)
        return FakeManagedProcess(result)


class GoalsAndAutoDebugTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "test.db"
        self.engine = WorkbenchEngine(self.database, acceptance_authority=TIERED_ACCEPTANCE_AUTHORITY)
        self.workspace = self.engine.create_workspace("GoalsWS")
        self.project = self.engine.create_project(self.workspace["id"], "GoalsPRJ")

    def tearDown(self):
        self.temp.cleanup()

    def test_create_and_get_goal(self):
        goal = self.engine.create_goal(self.project["id"], "Release v1.0", "Core features")
        self.assertEqual("Release v1.0", goal["title"])
        self.assertEqual("planned", goal["status"])
        self.assertEqual(0, goal["total_tickets"])
        self.assertEqual(0.0, goal["progress_pct"])

        fetched = self.engine.get_goal(goal["id"])
        self.assertEqual(goal["id"], fetched["id"])
        self.assertEqual("Release v1.0", fetched["title"])

    def test_link_ticket_to_goal_and_dependencies(self):
        goal = self.engine.create_goal(self.project["id"], "Build Pipeline")
        t1 = self.engine.create_ticket(
            self.project["id"], "Setup DB", "create tables", ["tables exist"],
            goal_id=goal["id"],
        )
        t2 = self.engine.create_ticket(
            self.project["id"], "Build API", "serve endpoints", ["routes 200"],
            goal_id=goal["id"],
            depends_on_ticket_id=t1["id"],
        )

        goal_detail = self.engine.get_goal(goal["id"])
        self.assertEqual(2, goal_detail["total_tickets"])
        self.assertEqual(0, goal_detail["accepted_tickets"])

        next_runnable = self.engine.get_next_runnable_ticket_for_goal(goal["id"])
        self.assertIsNotNone(next_runnable)
        self.assertEqual(t1["id"], next_runnable["id"])

    def test_ticket_dependency_advances_only_when_unblocked(self):
        goal = self.engine.create_goal(self.project["id"], "Two-Phase Goal")
        t1 = self.engine.create_ticket(
            self.project["id"], "Phase 1", "do phase 1", ["criteria 1"], goal_id=goal["id"],
        )
        t2 = self.engine.create_ticket(
            self.project["id"], "Phase 2", "do phase 2", ["criteria 2"],
            goal_id=goal["id"], depends_on_ticket_id=t1["id"],
        )

        self.assertEqual(t1["id"], self.engine.get_next_runnable_ticket_for_goal(goal["id"])["id"])

        run1 = self.engine.start_run(t1["id"])
        self.engine.complete_run(run1["id"])
        self.engine.verify_run(
            run1["id"], status="passed", evidence_ref="test://pass", summary="pass",
            verifier="IV", verifier_provider="human", evidence_content="ok",
        )
        self.engine.accept_ticket(t1["id"], accepted_by="Josh")

        next_runnable = self.engine.get_next_runnable_ticket_for_goal(goal["id"])
        self.assertIsNotNone(next_runnable)
        self.assertEqual(t2["id"], next_runnable["id"])

    def test_auto_debug_loop_succeeds_on_first_attempt(self):
        ticket = self.engine.create_ticket(
            self.project["id"], "Fast Ticket", "immediate success", ["criteria"],
            risk_level="low",
        )
        executor = SequenceExecutor([ProcessResult(0, "all good", pid=101)])
        runner = CodexCliRunner(executor=executor)

        cmd = f'"{sys.executable}" -c "exit(0)"'
        res = self.engine.run_ticket_auto_debug_loop(
            ticket_id=ticket["id"],
            runner=runner,
            prompt="write code",
            cwd=self.temp.name,
            verification_command=cmd,
            max_attempts=3,
            isolate_worktree=False,
        )

        self.assertTrue(res["success"])
        self.assertEqual(1, res["attempts"])
        self.assertEqual(0, len(res["debug_episodes"]))
        ticket_after = self.engine.get_ticket(ticket["id"])
        self.assertIn(ticket_after["status"], {"verification", "accepted"})

    def test_auto_debug_loop_recovers_after_initial_failure(self):
        ticket = self.engine.create_ticket(
            self.project["id"], "Debug Ticket", "fix on second try", ["criteria"],
            risk_level="high",
        )
        executor = SequenceExecutor([
            ProcessResult(1, "", "SyntaxError: invalid syntax", pid=201),
            ProcessResult(0, "syntax fixed", "", pid=202),
        ])
        runner = CodexCliRunner(executor=executor)

        cmd = f'"{sys.executable}" -c "exit(0)"'
        res = self.engine.run_ticket_auto_debug_loop(
            ticket_id=ticket["id"],
            runner=runner,
            prompt="implement feature",
            cwd=self.temp.name,
            verification_command=cmd,
            max_attempts=3,
            isolate_worktree=False,
        )

        self.assertTrue(res["success"])
        self.assertEqual(2, res["attempts"])
        self.assertEqual(1, len(res["debug_episodes"]))
        self.assertIn("RUNNER-EXIT-NONZERO", res["debug_episodes"][0]["symptom"])

        second_prompt = executor.calls[1][0]
        full_argv = " ".join(second_prompt)
        self.assertIn("AUTOMATED DEBUG FEEDBACK", full_argv)

    def test_auto_debug_loop_exhausts_max_attempts(self):
        ticket = self.engine.create_ticket(
            self.project["id"], "Stubborn Ticket", "fails every time", ["criteria"],
            risk_level="high",
        )
        executor = SequenceExecutor([
            ProcessResult(1, "", "TypeError: unsupported", pid=301),
            ProcessResult(1, "", "TypeError: unsupported", pid=302),
        ])
        runner = CodexCliRunner(executor=executor)

        cmd = f'"{sys.executable}" -c "exit(0)"'
        res = self.engine.run_ticket_auto_debug_loop(
            ticket_id=ticket["id"],
            runner=runner,
            prompt="implement feature",
            cwd=self.temp.name,
            verification_command=cmd,
            max_attempts=2,
            isolate_worktree=False,
        )

        self.assertFalse(res["success"])
        self.assertEqual(2, res["attempts"])
        self.assertEqual(2, len(res["debug_episodes"]))
        ticket_after = self.engine.get_ticket(ticket["id"])
        self.assertEqual("ready", ticket_after["status"])

    def test_advance_goal_orchestration(self):
        goal = self.engine.create_goal(self.project["id"], "Full Pipeline Goal")
        t1 = self.engine.create_ticket(
            self.project["id"], "Step 1", "first step", ["criteria 1"],
            goal_id=goal["id"], risk_level="low",
        )
        t2 = self.engine.create_ticket(
            self.project["id"], "Step 2", "second step", ["criteria 2"],
            goal_id=goal["id"], depends_on_ticket_id=t1["id"], risk_level="low",
        )

        executor = SequenceExecutor([
            ProcessResult(0, "step 1 done", pid=501),
            ProcessResult(0, "step 2 done", pid=502),
        ])
        runner = CodexCliRunner(executor=executor)
        cmd = f'"{sys.executable}" -c "exit(0)"'

        # Advance 1: should run t1
        adv1 = self.engine.advance_goal(
            goal["id"], runner, self.temp.name,
            verification_command=cmd, isolate_worktree=False,
        )
        self.assertEqual("ran_ticket", adv1["action"])
        self.assertEqual(t1["id"], adv1["ticket_id"])
        self.assertTrue(adv1["loop_result"]["success"])

        # Advance 2: t1 is accepted (low risk auto-accepted), should run t2
        adv2 = self.engine.advance_goal(
            goal["id"], runner, self.temp.name,
            verification_command=cmd, isolate_worktree=False,
        )
        self.assertEqual("ran_ticket", adv2["action"])
        self.assertEqual(t2["id"], adv2["ticket_id"])
        self.assertTrue(adv2["loop_result"]["success"])

        # Verify Goal is now achieved
        goal_after = self.engine.get_goal(goal["id"])
        self.assertEqual("achieved", goal_after["status"])
        self.assertEqual(100.0, goal_after["progress_pct"])

    def test_high_risk_ticket_requires_human_acceptance_in_goal(self):
        goal = self.engine.create_goal(self.project["id"], "Governance Protected Goal")
        ticket = self.engine.create_ticket(
            self.project["id"], "Critical Core Mod", "change core logic", ["all tests pass"],
            goal_id=goal["id"], risk_level="high",
        )
        executor = SequenceExecutor([ProcessResult(0, "core mod done", pid=901)])
        runner = CodexCliRunner(executor=executor)
        cmd = f'"{sys.executable}" -c "exit(0)"'

        adv = self.engine.advance_goal(
            goal["id"], runner, self.temp.name,
            verification_command=cmd, isolate_worktree=False,
        )
        self.assertEqual("ran_ticket", adv["action"])
        self.assertTrue(adv["loop_result"]["success"])

        # Ticket must remain in verification, NOT auto-accepted (Invariant 14 / Invariant 4)
        t_after = self.engine.get_ticket(ticket["id"])
        self.assertEqual("verification", t_after["status"])
        self.assertIsNone(t_after["accepted_by"])

        goal_mid = self.engine.get_goal(goal["id"])
        self.assertEqual("in_progress", goal_mid["status"])
        self.assertEqual(0.0, goal_mid["progress_pct"])

        # Subsequent advance_goal should report none_runnable (blocked by human review)
        adv_blocked = self.engine.advance_goal(
            goal["id"], runner, self.temp.name,
            verification_command=cmd, isolate_worktree=False,
        )
        self.assertEqual("none_runnable", adv_blocked["action"])
        self.assertFalse(adv_blocked["all_accepted"])

        # Human acceptance (Josh)
        self.engine.accept_ticket(ticket["id"], accepted_by="Josh")
        t_accepted = self.engine.get_ticket(ticket["id"])
        self.assertEqual("accepted", t_accepted["status"])

        # Now advance_goal detects all tickets accepted and marks Goal achieved
        adv_final = self.engine.advance_goal(
            goal["id"], runner, self.temp.name,
            verification_command=cmd, isolate_worktree=False,
        )
        self.assertEqual("none_runnable", adv_final["action"])
        self.assertTrue(adv_final["all_accepted"])
        self.assertEqual("achieved", adv_final["goal"]["status"])
        self.assertEqual(100.0, adv_final["goal"]["progress_pct"])

    def test_link_ticket_prevents_cycles_and_cross_goal_dependency(self):
        goal1 = self.engine.create_goal(self.project["id"], "Goal 1")
        goal2 = self.engine.create_goal(self.project["id"], "Goal 2")
        t1 = self.engine.create_ticket(self.project["id"], "T1", "g1", ["c1"], goal_id=goal1["id"])
        t2 = self.engine.create_ticket(self.project["id"], "T2", "g2", ["c2"], goal_id=goal1["id"])
        t3 = self.engine.create_ticket(self.project["id"], "T3", "g3", ["c3"], goal_id=goal2["id"])

        # Cross-goal dependency rejected
        with self.assertRaises(ValueError):
            self.engine.link_ticket_to_goal(t1["id"], goal1["id"], depends_on_ticket_id=t3["id"])

        # Self-dependency rejected
        with self.assertRaises(ValueError):
            self.engine.link_ticket_to_goal(t1["id"], goal1["id"], depends_on_ticket_id=t1["id"])

        # Valid link: t2 depends on t1
        self.engine.link_ticket_to_goal(t2["id"], goal1["id"], depends_on_ticket_id=t1["id"])

        # Circular dependency rejected: t1 cannot depend on t2
        with self.assertRaises(ValueError):
            self.engine.link_ticket_to_goal(t1["id"], goal1["id"], depends_on_ticket_id=t2["id"])

        # 3-node circular dependency rejected: t3 depends on t2 (t1 -> t2 -> t3), so t1 cannot depend on t3
        t3_same_goal = self.engine.create_ticket(self.project["id"], "T3_same", "g3", ["c3"], goal_id=goal1["id"])
        self.engine.link_ticket_to_goal(t3_same_goal["id"], goal1["id"], depends_on_ticket_id=t2["id"])
        with self.assertRaises(ValueError):
            self.engine.link_ticket_to_goal(t1["id"], goal1["id"], depends_on_ticket_id=t3_same_goal["id"])

    def test_advance_goal_honors_auto_accept_low_risk_false(self):
        goal = self.engine.create_goal(self.project["id"], "Manual Review Low Risk Goal")
        ticket = self.engine.create_ticket(
            self.project["id"], "Low Risk Ticket", "low task", ["criteria"],
            goal_id=goal["id"], risk_level="low",
        )
        executor = SequenceExecutor([ProcessResult(0, "completed task", pid=1001)])
        runner = CodexCliRunner(executor=executor)
        cmd = f'"{sys.executable}" -c "exit(0)"'

        adv = self.engine.advance_goal(
            goal["id"], runner, self.temp.name,
            verification_command=cmd, isolate_worktree=False,
            auto_accept_low_risk=False,
        )
        self.assertEqual("ran_ticket", adv["action"])
        self.assertTrue(adv["loop_result"]["success"])

        # When auto_accept_low_risk=False, low risk ticket must NOT be auto-accepted!
        t_after = self.engine.get_ticket(ticket["id"])
        self.assertEqual("verification", t_after["status"])
        self.assertIsNone(t_after["accepted_by"])

    def test_create_ticket_prevents_cycles_and_cross_goal_dependency(self):
        goal1 = self.engine.create_goal(self.project["id"], "Goal 1")
        goal2 = self.engine.create_goal(self.project["id"], "Goal 2")
        t1 = self.engine.create_ticket(self.project["id"], "T1", "g1", ["c1"], goal_id=goal1["id"])

        # Cross-goal dependency rejected on creation
        t_other = self.engine.create_ticket(self.project["id"], "TOther", "go", ["co"], goal_id=goal2["id"])
        with self.assertRaises(ValueError):
            self.engine.create_ticket(
                self.project["id"], "TBadCross", "gb", ["cb"],
                goal_id=goal1["id"], depends_on_ticket_id=t_other["id"],
            )

        # Cross-project dependency rejected on creation
        ws2 = self.engine.create_workspace("WS2")
        p2 = self.engine.create_project(ws2["id"], "P2")
        t_p2 = self.engine.create_ticket(p2["id"], "TP2", "gp2", ["cp2"])
        with self.assertRaises(ValueError):
            self.engine.create_ticket(
                self.project["id"], "TBadProj", "gb", ["cb"],
                goal_id=goal1["id"], depends_on_ticket_id=t_p2["id"],
            )

        # Valid creation with dependency
        t2 = self.engine.create_ticket(
            self.project["id"], "T2", "g2", ["c2"],
            goal_id=goal1["id"], depends_on_ticket_id=t1["id"],
        )
        self.assertEqual(t1["id"], t2["depends_on_ticket_id"])


if __name__ == "__main__":
    unittest.main()
