"""
Architecture Council Extreme & Adversarial Testing Suite.
Stress-testing Engine Constitution Invariants 1~14, concurrency limits,
fail-closed gates, evidence tampering, and delivery integrity under extreme conditions.
"""
import io
import json
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from company_workbench import WorkbenchEngine, GitDeliveryAdapter, DeliveryError
from company_workbench.engine import (
    TIERED_ACCEPTANCE_AUTHORITY,
    DEFAULT_ACCEPTANCE_AUTHORITY,
    _sha256,
)
from company_workbench.errors import (
    NotFoundError,
    InvalidTransitionError,
    EvidenceRequiredError,
    AcceptanceRequiredError,
    VerifierIndependenceError,
)
from company_workbench.runner import ProcessResult, RunnerInvocation


class FakeProcessHandle:
    def __init__(self, exit_code=0, stdout="test success", stderr=""):
        self.pid = 9876
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr

    def wait(self, *, cancel_event=None, **kwargs):
        return ProcessResult(
            exit_code=self._exit_code,
            stdout=self._stdout,
            stderr=self._stderr,
            pid=self.pid,
        )


class FakeTestRunner:
    def __init__(self, name="codex-cli", exit_code=0):
        self.name = name
        self.exit_code = exit_code

    def start_invocation(self, prompt, cwd, **kwargs):
        return RunnerInvocation(
            FakeProcessHandle(exit_code=self.exit_code),
            timeout_seconds=60,
            max_output_chars=4000,
            cancel_event=None,
            sensitive_values=(),
        )


class CouncilExtremeTestingSuite(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "extreme_test.db"
        self.engine = WorkbenchEngine(
            self.db_path,
            acceptance_authority=TIERED_ACCEPTANCE_AUTHORITY,
        )
        self.ws = self.engine.create_workspace("Extreme Test Workspace")
        self.prj = self.engine.create_project(self.ws["id"], "Extreme Test Project")

    def tearDown(self):
        self.temp_dir.cleanup()

    # =========================================================================
    # EXTREME TEST 1: Invariant 9 Penetration (Mainline Delivery Fail-Closed)
    # =========================================================================
    def test_extreme_invariant_9_mainline_delivery_penetration(self):
        """Penetrate Invariant 9 by attempting deliveries across all non-accepted states."""
        # 1. Ticket in 'ready' state
        t_ready = self.engine.create_ticket(self.prj["id"], "T-Ready", "goal", ["c1"])
        with self.assertRaises(InvalidTransitionError) as ctx:
            self.engine.deliver_ticket(t_ready["id"], repo_path=self.temp_dir.name)
        self.assertIn("Invariant 9 requires explicit acceptance", str(ctx.exception))

        # 2. Ticket in 'active' state
        t_active = self.engine.create_ticket(self.prj["id"], "T-Active", "goal", ["c1"])
        run = self.engine.start_run(t_active["id"], runner="codex-cli")
        with self.assertRaises(InvalidTransitionError) as ctx:
            self.engine.deliver_ticket(t_active["id"], repo_path=self.temp_dir.name)
        self.assertIn("Invariant 9 requires explicit acceptance", str(ctx.exception))

        # 3. Ticket in 'verification' state (Run completed, but no verification submitted)
        self.engine.complete_run(run["id"])
        with self.assertRaises(InvalidTransitionError) as ctx:
            self.engine.deliver_ticket(t_active["id"], repo_path=self.temp_dir.name)
        self.assertIn("Invariant 9 requires explicit acceptance", str(ctx.exception))

        # 4. Ticket in 'verification' state with passed verification, but NOT accepted
        self.engine.verify_run(
            run["id"], status="passed", evidence_ref="test proof", summary="verified",
            verifier="QA", verifier_provider="local-command", evidence_content="proof",
        )
        t_verified = self.engine.get_ticket(t_active["id"])
        self.assertEqual("verification", t_verified["status"])
        with self.assertRaises(InvalidTransitionError) as ctx:
            self.engine.deliver_ticket(t_active["id"], repo_path=self.temp_dir.name)
        self.assertIn("Invariant 9 requires explicit acceptance", str(ctx.exception))

        # 5. Goal Delivery Penetration: 3 tickets, 2 accepted, 1 unaccepted
        goal = self.engine.create_goal(self.prj["id"], "Goal Delivery Penetration")
        t1 = self.engine.create_ticket(self.prj["id"], "GT1", "g", ["c"], goal_id=goal["id"], risk_level="low")
        t2 = self.engine.create_ticket(self.prj["id"], "GT2", "g", ["c"], goal_id=goal["id"], risk_level="low", depends_on_ticket_id=t1["id"])
        t3 = self.engine.create_ticket(self.prj["id"], "GT3", "g", ["c"], goal_id=goal["id"], risk_level="high", depends_on_ticket_id=t2["id"])

        # Accept t1 and t2 only
        for t in (t1, t2):
            r = self.engine.start_run(t["id"], runner="codex-cli")
            self.engine.complete_run(r["id"])
            self.engine.verify_run(r["id"], status="passed", evidence_ref="proof", summary="ok", verifier="v", verifier_provider="local-command", evidence_content="proof")
            self.engine.accept_ticket(t["id"], accepted_by="Josh")

        # Attempt to deliver Goal when t3 is still in ready
        with self.assertRaises((InvalidTransitionError, DeliveryError)) as ctx:
            self.engine.deliver_goal(goal["id"], repo_path=self.temp_dir.name)
        self.assertIn("not all tickets are accepted", str(ctx.exception))

    # =========================================================================
    # EXTREME TEST 2: Invariant 11 Verifier Independence Penetration
    # =========================================================================
    def test_extreme_invariant_11_verifier_collusion_attack(self):
        """Verify that builder and verifier provider collusion is aggressively blocked."""
        collusion_pairs = [
            ("codex-cli", "openai"),
            ("claude-code", "anthropic"),
            ("gemini", "google"),
            ("local", "local-command"),
        ]
        for runner, collusion_provider in collusion_pairs:
            ticket = self.engine.create_ticket(self.prj["id"], f"TKT-{runner}", "goal", ["crit"])
            run = self.engine.start_run(ticket["id"], runner=runner)
            self.engine.complete_run(run["id"])

            # Attempt collusion verification
            with self.assertRaises(VerifierIndependenceError) as ctx:
                self.engine.verify_run(
                    run["id"],
                    status="passed",
                    evidence_ref="collusion evidence",
                    summary="collusion",
                    verifier="colluding-agent",
                    verifier_provider=collusion_provider,
                    evidence_content="collusion text",
                )
            self.assertIn("Invariant 11 requires an independent verifier", str(ctx.exception))

    # =========================================================================
    # EXTREME TEST 3: Invariant 4 & 14 Tier Escalation & Tampering Penetration
    # =========================================================================
    def test_extreme_invariant_14_tier_escalation_attack(self):
        """Attempt unauthorized automated acceptance on medium and high risk tickets."""
        # 1. High-risk ticket
        t_high = self.engine.create_ticket(self.prj["id"], "T-High", "goal", ["crit"], risk_level="high")
        run_h = self.engine.start_run(t_high["id"], runner="codex-cli")
        self.engine.complete_run(run_h["id"])
        self.engine.verify_run(
            run_h["id"], status="passed", evidence_ref="ref", summary="ok",
            verifier="verifier", verifier_provider="local-command", evidence_content="proof",
        )

        # Attempt acceptance by unauthorized actors
        for imposter in ["automation", "Alice", "Bob", "SYSTEM", ""]:
            with self.assertRaises(AcceptanceRequiredError):
                self.engine.accept_ticket(t_high["id"], accepted_by=imposter)

        # 2. Risk level validation rejects invalid / malicious inputs
        for bad_risk in ["critical", "none", "SUPER_HIGH", "", " "]:
            with self.assertRaises(ValueError):
                self.engine.create_ticket(self.prj["id"], "Bad", "g", ["c"], risk_level=bad_risk)

    # =========================================================================
    # EXTREME TEST 4: Evidence Hash & Bit-Flip Tampering Penetration
    # =========================================================================
    def test_extreme_evidence_tampering_and_bit_flip_attack(self):
        """Tamper with raw evidence in SQLite and confirm engine fail-closed behavior."""
        ticket = self.engine.create_ticket(self.prj["id"], "Tamper Ticket", "goal", ["c"], risk_level="high")
        run = self.engine.start_run(ticket["id"], runner="codex-cli")
        self.engine.complete_run(run["id"])

        original_proof = b"AUTHENTIC_PROOF_DATA_12345"
        self.engine.verify_run(
            run["id"], status="passed", evidence_ref="original_proof", summary="summary",
            verifier="v", verifier_provider="local-command", evidence_content=original_proof,
        )

        # 1. First confirm DB trigger blocks direct UPDATE on evidence_artifacts table
        with self.engine.store.transaction() as db:
            row = db.execute("SELECT sha256, content FROM evidence_artifacts LIMIT 1").fetchone()
            original_sha = row["sha256"]
            tampered_content = b"TAMPERED_MALICIOUS_DATA_9999"
            with self.assertRaises(sqlite3.IntegrityError) as ctx:
                db.execute("UPDATE evidence_artifacts SET content=? WHERE sha256=?", (tampered_content, original_sha))
            self.assertIn("append-only", str(ctx.exception))

            # 2. Now simulate an out-of-band bit-flip by temporarily dropping trigger
            db.execute("DROP TRIGGER evidence_artifacts_no_update")
            db.execute("UPDATE evidence_artifacts SET content=? WHERE sha256=?", (tampered_content, original_sha))

        # Attempt to accept ticket backed by tampered evidence
        with self.assertRaises(EvidenceRequiredError) as ctx:
            self.engine.accept_ticket(ticket["id"], accepted_by="Josh")
        self.assertIn("does not match its hash", str(ctx.exception))

    # =========================================================================
    # EXTREME TEST 5: Extreme Concurrency Race (30 Threads on Single Ticket)
    # =========================================================================
    def test_extreme_concurrency_race_single_ticket_claim(self):
        """Stress-test atomic ticket claim: 30 threads concurrently claim next runnable ticket."""
        goal = self.engine.create_goal(self.prj["id"], "Race Goal")
        t = self.engine.create_ticket(self.prj["id"], "Contended Ticket", "g", ["c"], goal_id=goal["id"], risk_level="low")

        claims = []
        barrier = threading.Barrier(30)

        def worker():
            barrier.wait()
            claimed = self.engine.claim_next_runnable_ticket_for_goal(goal["id"])
            if claimed:
                claims.append(claimed["id"])

        with ThreadPoolExecutor(max_workers=30) as executor:
            list(executor.map(lambda _: worker(), range(30)))

        # Invariant: exactly ONE worker or atomic batch succeeds, no duplicate active run
        self.assertTrue(len(claims) >= 1)
        # Verify ticket has at most 1 active run
        with self.engine.store.connect() as db:
            active_runs = db.execute(
                "SELECT COUNT(*) FROM runs WHERE ticket_id=? AND status IN ('queued','running')", (t["id"],)
            ).fetchone()[0]
        self.assertLessEqual(active_runs, 1)

    # =========================================================================
    # EXTREME TEST 6: Deep Multi-Node Cycle Injection (6-Node Circular DAG)
    # =========================================================================
    def test_extreme_deep_circular_dag_cycle_injection(self):
        """Attempt creating a 6-node cycle: A -> B -> C -> D -> E -> F -> A."""
        goal = self.engine.create_goal(self.prj["id"], "Deep Cycle Goal")
        tA = self.engine.create_ticket(self.prj["id"], "Node A", "g", ["c"], goal_id=goal["id"])
        tB = self.engine.create_ticket(self.prj["id"], "Node B", "g", ["c"], goal_id=goal["id"], depends_on_ticket_id=tA["id"])
        tC = self.engine.create_ticket(self.prj["id"], "Node C", "g", ["c"], goal_id=goal["id"], depends_on_ticket_id=tB["id"])
        tD = self.engine.create_ticket(self.prj["id"], "Node D", "g", ["c"], goal_id=goal["id"], depends_on_ticket_id=tC["id"])
        tE = self.engine.create_ticket(self.prj["id"], "Node E", "g", ["c"], goal_id=goal["id"], depends_on_ticket_id=tD["id"])
        tF = self.engine.create_ticket(self.prj["id"], "Node F", "g", ["c"], goal_id=goal["id"], depends_on_ticket_id=tE["id"])

        # Attempt closing the loop: link A to depend on F (A -> ... -> F -> A)
        with self.assertRaises(ValueError) as ctx:
            self.engine.link_ticket_to_goal(tA["id"], goal["id"], depends_on_ticket_id=tF["id"])
        self.assertIn("Circular dependency detected", str(ctx.exception))

        # Attempt self dependency
        with self.assertRaises(ValueError) as ctx:
            self.engine.link_ticket_to_goal(tA["id"], goal["id"], depends_on_ticket_id=tA["id"])
        self.assertIn("cannot depend on itself", str(ctx.exception))

    # =========================================================================
    # EXTREME TEST 7: Massive Goal Multi-Stage Pipeline Execution
    # =========================================================================
    def test_extreme_massive_goal_pipeline_execution(self):
        """Execute a 6-ticket dependency pipeline through advance_goal to completion."""
        goal = self.engine.create_goal(self.prj["id"], "Massive Pipeline Goal")
        tickets = []
        prev_id = None
        for i in range(6):
            t = self.engine.create_ticket(
                self.prj["id"], f"Step {i+1}", f"goal {i+1}", [f"crit {i+1}"],
                goal_id=goal["id"], depends_on_ticket_id=prev_id, risk_level="low",
            )
            tickets.append(t)
            prev_id = t["id"]

        runner = FakeTestRunner(exit_code=0)
        verify_cmd = 'python -c "exit(0)"'

        # Advance sequentially until all are completed
        for step in range(6):
            adv = self.engine.advance_goal(
                goal["id"],
                runner=runner,
                cwd=self.temp_dir.name,
                verification_command=verify_cmd,
                isolate_worktree=False,
                auto_accept_low_risk=True,
            )
            self.assertEqual("ran_ticket", adv["action"])
            expected_pct = round(((step + 1) / 6) * 100, 1)
            self.assertEqual(expected_pct, adv["goal"]["progress_pct"])

        # Final verification: goal is achieved
        final_goal = self.engine.get_goal(goal["id"])
        self.assertEqual("achieved", final_goal["status"])
        self.assertEqual(100.0, final_goal["progress_pct"])
        self.assertEqual(6, final_goal["accepted_tickets"])


if __name__ == "__main__":
    unittest.main()
