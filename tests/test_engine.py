import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier
from typing import Any

from company_workbench import WorkbenchEngine
from company_workbench.demo import run_demo
from company_workbench.engine import _default_pid_alive_checker
from company_workbench.errors import (
    AcceptanceRequiredError,
    EvidenceRequiredError,
    InvalidTransitionError,
    RunnerLaunchError,
)
from company_workbench.runner import CodexCliRunner, ProcessResult, SubprocessExecutor
from company_workbench.store import SQLiteStore


class EngineTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "test.db"
        self.engine = WorkbenchEngine(self.database)
        self.workspace = self.engine.create_workspace("Test")
        self.project = self.engine.create_project(self.workspace["id"], "Engine")
        self.ticket = self.engine.create_ticket(self.project["id"], "Work", "Prove flow", ["Evidence exists"])

    def tearDown(self):
        self.temp.cleanup()

    def test_run_completion_does_not_accept_ticket(self):
        run = self.engine.start_run(self.ticket["id"])
        self.engine.complete_run(run["id"])
        self.assertEqual("verification", self.engine.get_ticket(self.ticket["id"])["status"])
        self.assertIsNone(self.engine.get_ticket(self.ticket["id"])["accepted_by"])

    def test_acceptance_requires_completed_latest_run_and_evidence(self):
        with self.assertRaises(AcceptanceRequiredError):
            self.engine.accept_ticket(self.ticket["id"], accepted_by="Josh")
        run = self.engine.start_run(self.ticket["id"])
        self.engine.complete_run(run["id"])
        with self.assertRaises(EvidenceRequiredError):
            self.engine.accept_ticket(self.ticket["id"], accepted_by="Josh")
        self.engine.verify_run(run["id"], status="passed", evidence_ref="test://pass", summary="passed", verifier="IV")
        with self.assertRaises(AcceptanceRequiredError):
            self.engine.accept_ticket(self.ticket["id"], accepted_by="Agent")
        accepted = self.engine.accept_ticket(self.ticket["id"], accepted_by="Josh")
        self.assertEqual("accepted", accepted["status"])
        with self.assertRaises(InvalidTransitionError):
            self.engine.accept_ticket(self.ticket["id"], accepted_by="Josh")
        with self.engine.store.connect() as db:
            acceptance = db.execute("SELECT * FROM acceptances WHERE ticket_id=?", (self.ticket["id"],)).fetchone()
        self.assertIsNotNone(acceptance["verification_id"])

    def test_verification_requires_evidence(self):
        run = self.engine.start_run(self.ticket["id"])
        self.engine.complete_run(run["id"])
        with self.assertRaises(EvidenceRequiredError):
            self.engine.verify_run(run["id"], status="passed", evidence_ref="", summary="passed", verifier="IV")

    def test_failed_run_keeps_events_and_returns_ticket_to_ready(self):
        run = self.engine.start_run(self.ticket["id"])
        self.engine.append_event(run["id"], "agent_activity", {"step": "before_failure"})
        failed = self.engine.fail_run(run["id"], "FAKE-FAIL", "controlled failure")
        self.assertEqual("failed", failed["status"])
        self.assertEqual("ready", self.engine.get_ticket(self.ticket["id"])["status"])
        self.assertEqual(["run_started", "agent_activity", "run_failed"], [event["kind"] for event in self.engine.list_events(run["id"])])

    def test_only_one_active_run(self):
        self.engine.start_run(self.ticket["id"])
        with self.assertRaises(InvalidTransitionError):
            self.engine.start_run(self.ticket["id"])

    def test_events_are_append_only_at_database_boundary(self):
        run = self.engine.start_run(self.ticket["id"])
        event = self.engine.list_events(run["id"])[0]
        with self.assertRaises(sqlite3.DatabaseError):
            with self.engine.store.connect() as db:
                db.execute("UPDATE events SET kind='tampered' WHERE id=?", (event["id"],))

    def test_accepted_verification_and_acceptance_are_immutable(self):
        run = self.engine.start_run(self.ticket["id"])
        self.engine.complete_run(run["id"])
        verification = self.engine.verify_run(
            run["id"], status="passed", evidence_ref="test://proof", summary="passed", verifier="IV"
        )
        self.engine.accept_ticket(self.ticket["id"], accepted_by="Josh")
        with self.assertRaises(sqlite3.DatabaseError):
            with self.engine.store.connect() as db:
                db.execute("UPDATE verifications SET status='failed' WHERE id=?", (verification["id"],))
        with self.assertRaises(sqlite3.DatabaseError):
            with self.engine.store.connect() as db:
                db.execute("DELETE FROM acceptances WHERE ticket_id=?", (self.ticket["id"],))

    def test_memory_starts_pending(self):
        run = self.engine.start_run(self.ticket["id"])
        self.engine.complete_run(run["id"])
        memory = self.engine.propose_memory(
            self.project["id"], run["id"], kind="semantic", statement="Lesson",
            scope=f"project:{self.project['id']}", evidence_ref=f"run:{run['id']}",
        )
        self.assertEqual("pending", memory["status"])

    def test_memory_source_run_must_belong_to_same_project(self):
        other_project = self.engine.create_project(self.workspace["id"], "Other")
        run = self.engine.start_run(self.ticket["id"])
        self.engine.complete_run(run["id"])
        with self.assertRaises(InvalidTransitionError):
            self.engine.propose_memory(
                other_project["id"], run["id"], kind="semantic", statement="Cross-project contamination",
                scope=f"project:{other_project['id']}", evidence_ref=f"run:{run['id']}",
            )

    def test_backup_can_be_opened_and_has_same_ticket(self):
        backup = Path(self.temp.name) / "backup.db"
        self.engine.store.backup_to(backup)
        restored = WorkbenchEngine(backup)
        self.assertEqual("ok", restored.diagnose()["integrity"])
        self.assertEqual(self.ticket["id"], restored.get_ticket(self.ticket["id"])["id"])

    def test_backup_rejects_source_database_as_target(self):
        with self.assertRaises(ValueError):
            self.engine.store.backup_to(self.database)


class DemoTestCase(unittest.TestCase):
    def test_complete_demo(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_demo(Path(temp) / "demo.db")
        self.assertEqual("verification", result["ticket_status_after_run"])
        self.assertEqual("passed", result["verification"])
        self.assertEqual("accepted", result["ticket_status_after_acceptance"])
        self.assertEqual("pending", result["memory_candidate"])
        self.assertGreaterEqual(result["event_count"], 6)


class StoreConcurrencyTestCase(unittest.TestCase):
    def test_concurrent_first_open_does_not_lock_or_leak_database(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "concurrent.db"
            barrier = Barrier(8)

            def open_engine():
                barrier.wait()
                return WorkbenchEngine(database).diagnose()

            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: open_engine(), range(8)))

            self.assertTrue(all(result["integrity"] == "ok" for result in results))
            self.assertTrue(all(result["schema_version"] == 4 for result in results))


class StoreMigrationTestCase(unittest.TestCase):
    @staticmethod
    def create_legacy_v1_database(path: Path, *, with_passing_verification: bool) -> None:
        with closing(sqlite3.connect(path)) as db:
            db.executescript(
                """
                CREATE TABLE schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                INSERT INTO schema_migrations(version, applied_at) VALUES (1, '2026-09-01T00:00:00Z');
                CREATE TABLE runs (
                    id TEXT PRIMARY KEY
                );
                CREATE TABLE verifications (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    status TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    verifier TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE acceptances (
                    id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    accepted_by TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                INSERT INTO runs(id) VALUES ('RUN-legacy');
                """
            )
            if with_passing_verification:
                db.execute(
                    """INSERT INTO verifications(
                           id,run_id,status,evidence_ref,summary,verifier,created_at
                       ) VALUES (?,?,?,?,?,?,?)""",
                    (
                        "VER-legacy", "RUN-legacy", "passed", "test://legacy-proof",
                        "legacy pass", "IV", "2026-09-01T00:01:00Z",
                    ),
                )
            db.execute(
                """INSERT INTO acceptances(id,ticket_id,run_id,accepted_by,note,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (
                    "ACC-legacy", "TKT-legacy", "RUN-legacy", "Josh", "legacy",
                    "2026-09-01T00:02:00Z",
                ),
            )
            db.commit()

    @staticmethod
    def create_legacy_v2_database(
        path: Path, *, verification_status: str, evidence_ref: str, summary: str
    ) -> None:
        with closing(sqlite3.connect(path)) as db:
            db.executescript(
                """
                CREATE TABLE schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                INSERT INTO schema_migrations(version, applied_at) VALUES (1, '2026-09-01T00:00:00Z');
                INSERT INTO schema_migrations(version, applied_at) VALUES (2, '2026-09-01T00:03:00Z');
                CREATE TABLE runs (id TEXT PRIMARY KEY);
                CREATE TABLE verifications (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    status TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    verifier TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE acceptances (
                    id TEXT PRIMARY KEY,
                    ticket_id TEXT NOT NULL,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    verification_id TEXT REFERENCES verifications(id),
                    accepted_by TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                INSERT INTO runs(id) VALUES ('RUN-legacy');
                """
            )
            db.execute(
                """INSERT INTO verifications(
                       id,run_id,status,evidence_ref,summary,verifier,created_at
                   ) VALUES (?,?,?,?,?,?,?)""",
                (
                    "VER-pinned", "RUN-legacy", verification_status, evidence_ref,
                    summary, "IV", "2026-09-01T00:01:00Z",
                ),
            )
            db.execute(
                """INSERT INTO acceptances(
                       id,ticket_id,run_id,verification_id,accepted_by,note,created_at
                   ) VALUES (?,?,?,?,?,?,?)""",
                (
                    "ACC-legacy", "TKT-legacy", "RUN-legacy", "VER-pinned",
                    "Josh", "legacy", "2026-09-01T00:02:00Z",
                ),
            )
            db.commit()

    def test_v1_acceptance_backfills_passing_verification_before_v3(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "legacy.db"
            self.create_legacy_v1_database(database, with_passing_verification=True)

            store = SQLiteStore(database)

            self.assertEqual(4, store.schema_version())
            with store.connect() as db:
                acceptance = db.execute(
                    "SELECT verification_id FROM acceptances WHERE id='ACC-legacy'"
                ).fetchone()
            self.assertEqual("VER-legacy", acceptance["verification_id"])

    def test_v1_acceptance_without_proof_refuses_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "legacy.db"
            self.create_legacy_v1_database(database, with_passing_verification=False)

            with self.assertRaisesRegex(sqlite3.DatabaseError, "lack passing Verification evidence"):
                SQLiteStore(database)

            with closing(sqlite3.connect(database)) as db:
                versions = [row[0] for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")]
            self.assertEqual([1], versions)

    def test_v1_acceptance_refuses_when_latest_verification_failed(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "legacy.db"
            self.create_legacy_v1_database(database, with_passing_verification=True)
            with closing(sqlite3.connect(database)) as db:
                db.execute(
                    """INSERT INTO verifications(
                           id,run_id,status,evidence_ref,summary,verifier,created_at
                       ) VALUES (?,?,?,?,?,?,?)""",
                    (
                        "VER-latest-failed", "RUN-legacy", "failed", "test://failed",
                        "latest verification failed", "IV", "2026-09-01T00:01:30Z",
                    ),
                )
                db.commit()

            with self.assertRaisesRegex(sqlite3.DatabaseError, "lack passing Verification evidence"):
                SQLiteStore(database)

            with closing(sqlite3.connect(database)) as db:
                versions = [row[0] for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")]
            self.assertEqual([1], versions)

    def test_v1_acceptance_refuses_blank_verification_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "legacy.db"
            self.create_legacy_v1_database(database, with_passing_verification=False)
            with closing(sqlite3.connect(database)) as db:
                db.execute(
                    """INSERT INTO verifications(
                           id,run_id,status,evidence_ref,summary,verifier,created_at
                       ) VALUES (?,?,?,?,?,?,?)""",
                    (
                        "VER-blank-summary", "RUN-legacy", "passed", "test://legacy-proof",
                        "   ", "IV", "2026-09-01T00:01:00Z",
                    ),
                )
                db.commit()

            with self.assertRaisesRegex(sqlite3.DatabaseError, "lack passing Verification evidence"):
                SQLiteStore(database)

    def test_v2_acceptance_refuses_invalid_pinned_verification(self):
        cases = (
            ("failed", "test://failed", "failed verification"),
            ("passed", "   ", "missing evidence"),
            ("passed", "test://proof", "   "),
        )
        for status, evidence_ref, summary in cases:
            with self.subTest(status=status, evidence_ref=evidence_ref, summary=summary):
                with tempfile.TemporaryDirectory() as temp:
                    database = Path(temp) / "legacy-v2.db"
                    self.create_legacy_v2_database(
                        database,
                        verification_status=status,
                        evidence_ref=evidence_ref,
                        summary=summary,
                    )

                    with self.assertRaisesRegex(sqlite3.DatabaseError, "lack valid pinned Verification evidence"):
                        SQLiteStore(database)

                    with closing(sqlite3.connect(database)) as db:
                        versions = [
                            row[0] for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")
                        ]
                    self.assertEqual([1, 2], versions)


class FakeManagedProcess:
    """A start()/wait() double that never touches a real OS process."""

    def __init__(self, result: ProcessResult):
        self.pid = result.pid
        self._result = result
        self.wait_calls: list[bool] = []

    def wait(self, *, timeout_seconds, cancel_event=None):
        was_cancelled = cancel_event is not None and cancel_event.is_set()
        self.wait_calls.append(was_cancelled)
        if was_cancelled:
            return ProcessResult(exit_code=None, cancelled=True, pid=self.pid)
        return self._result


class FakeManagedExecutor:
    def __init__(self, result: ProcessResult):
        self.result = result
        self.calls = []

    def start(self, argv, *, cwd):
        self.calls.append((tuple(argv), cwd))
        return FakeManagedProcess(self.result)


class FailingSpawnExecutor:
    """Simulates a missing/unreachable Codex executable at spawn time."""

    def start(self, argv, *, cwd):
        raise FileNotFoundError("codex executable not found")


class LocalSleeperExecutor:
    """Routes CodexCliRunner's fixed argv to a real local Python sleeper, never a real Codex process."""

    def __init__(self, sleep_seconds: float = 5.0):
        self._real = SubprocessExecutor()
        self.sleep_seconds = sleep_seconds

    def start(self, argv, *, cwd):
        return self._real.start((sys.executable, "-c", f"import time; time.sleep({self.sleep_seconds})"), cwd=cwd)


class ManagedRunEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "test.db"
        self.engine = WorkbenchEngine(self.database)
        self.workspace = self.engine.create_workspace("Test")
        self.project = self.engine.create_project(self.workspace["id"], "Engine")
        self.ticket = self.engine.create_ticket(self.project["id"], "Work", "Prove flow", ["Evidence exists"])

    def tearDown(self):
        self.temp.cleanup()

    def test_managed_run_persists_invocation_identity_and_completes(self):
        executor = FakeManagedExecutor(ProcessResult(0, '{"ok":true}', pid=4321))
        runner = CodexCliRunner(executor=executor)
        run = self.engine.start_managed_run(self.ticket["id"], runner, "do work", cwd=self.temp.name)
        self.assertEqual("completed", run["status"])
        self.assertEqual(4321, run["pid"])
        self.assertTrue(run["invocation_id"])
        self.assertEqual("verification", self.engine.get_ticket(self.ticket["id"])["status"])
        events = self.engine.list_events(run["id"])
        self.assertEqual(["run_started", "invocation_output", "run_completed"], [event["kind"] for event in events])
        for event in events:
            self.assertNotIn("pid", event["payload"])
            self.assertNotIn("invocation_id", event["payload"])

    def test_managed_run_failure_returns_ticket_to_ready_with_evidence(self):
        executor = FakeManagedExecutor(ProcessResult(1, "", "boom", pid=55))
        runner = CodexCliRunner(executor=executor)
        run = self.engine.start_managed_run(self.ticket["id"], runner, "do work", cwd=self.temp.name)
        self.assertEqual("failed", run["status"])
        self.assertEqual("RUNNER-EXIT-NONZERO", run["error_code"])
        self.assertEqual("ready", self.engine.get_ticket(self.ticket["id"])["status"])
        self.assertEqual(
            ["run_started", "invocation_output", "run_failed"],
            [event["kind"] for event in self.engine.list_events(run["id"])],
        )

    def test_managed_run_redacts_before_persisting_events(self):
        raw = "Authorization: Bearer secret123"
        executor = FakeManagedExecutor(ProcessResult(1, raw, raw, pid=9))
        runner = CodexCliRunner(executor=executor)
        run = self.engine.start_managed_run(self.ticket["id"], runner, "do work", cwd=self.temp.name)
        events = self.engine.list_events(run["id"])
        output_event = next(event for event in events if event["kind"] == "invocation_output")
        self.assertNotIn("secret123", output_event["payload"]["stdout"])
        self.assertNotIn("secret123", output_event["payload"]["stderr"])
        with self.engine.store.connect() as db:
            rows = db.execute("SELECT payload_json FROM events WHERE run_id=?", (run["id"],)).fetchall()
        self.assertTrue(all("secret123" not in row["payload_json"] for row in rows))

    def test_managed_run_launch_failure_leaves_no_partial_state(self):
        runner = CodexCliRunner(executor=FailingSpawnExecutor())
        with self.assertRaises(RunnerLaunchError):
            self.engine.start_managed_run(self.ticket["id"], runner, "work", cwd=self.temp.name)
        with self.engine.store.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM runs WHERE ticket_id=?", (self.ticket["id"],)).fetchone()[0]
        self.assertEqual(0, count)
        ticket = self.engine.get_ticket(self.ticket["id"])
        self.assertEqual("ready", ticket["status"])

    def _wait_for_running_row(self, *, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.engine.store.connect() as db:
                row = db.execute(
                    "SELECT * FROM runs WHERE ticket_id=? ORDER BY rowid DESC LIMIT 1", (self.ticket["id"],)
                ).fetchone()
            if row and row["status"] == "running" and row["pid"]:
                return row
            time.sleep(0.05)
        self.fail("Run never became visible as running with a pid")

    def test_managed_run_cancelled_mid_flight_via_real_local_sleeper(self):
        runner = CodexCliRunner(executor=LocalSleeperExecutor(sleep_seconds=5))
        cancel_event = threading.Event()
        outcome: dict = {}

        def worker():
            outcome["run"] = self.engine.start_managed_run(
                self.ticket["id"], runner, "do work", cwd=self.temp.name,
                timeout_seconds=30, cancel_event=cancel_event,
            )

        thread = threading.Thread(target=worker)
        thread.start()
        running_row = self._wait_for_running_row()
        self.assertTrue(running_row["pid"] > 0)

        cancel_event.set()
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive())

        run = self.engine.get_run(outcome["run"]["id"])
        self.assertEqual("cancelled", run["status"])
        self.assertEqual("RUNNER-CANCELLED", run["error_code"])
        self.assertEqual("ready", self.engine.get_ticket(self.ticket["id"])["status"])
        self.assertEqual(
            ["run_started", "invocation_output", "run_cancelled"],
            [event["kind"] for event in self.engine.list_events(run["id"])],
        )

    def test_managed_run_rejects_second_call_once_ticket_is_already_active(self):
        blocking_cancel = threading.Event()
        first_runner = CodexCliRunner(executor=LocalSleeperExecutor(sleep_seconds=5))

        def worker():
            self.engine.start_managed_run(
                self.ticket["id"], first_runner, "first", cwd=self.temp.name,
                timeout_seconds=30, cancel_event=blocking_cancel,
            )

        first_thread = threading.Thread(target=worker)
        first_thread.start()
        try:
            self._wait_for_running_row()

            second_executor = FakeManagedExecutor(ProcessResult(0, '{"ok":true}', pid=999))
            second_runner = CodexCliRunner(executor=second_executor)
            with self.assertRaises(InvalidTransitionError):
                self.engine.start_managed_run(self.ticket["id"], second_runner, "second", cwd=self.temp.name)

            # Ticket is already visibly 'active', so the second call is rejected before it ever
            # spawns a process -- no orphan process, no partial row.
            self.assertEqual([], second_executor.calls)
            with self.engine.store.connect() as db:
                count = db.execute(
                    "SELECT COUNT(*) FROM runs WHERE ticket_id=? AND pid=999", (self.ticket["id"],)
                ).fetchone()[0]
            self.assertEqual(0, count)
        finally:
            blocking_cancel.set()
            first_thread.join(timeout=10)

    def test_managed_run_race_on_still_ready_ticket_cancels_loser_spawned_process(self):
        """Both calls read the Ticket as 'ready' before either commits; only one may win the Run slot.

        The loser has already spawned its process by the time the transactional check loses the
        race, so it must be explicitly cancelled and reaped -- it cannot simply be abandoned.
        """
        barrier = threading.Barrier(2, timeout=5)

        class SlowFakeManagedProcess(FakeManagedProcess):
            """Holds the winner's Run visibly 'running' long enough for the loser's transactional
            check to genuinely overlap with it, instead of racing against an already-finalized Run."""

            def wait(self, *, timeout_seconds, cancel_event=None):
                if cancel_event is None or not cancel_event.is_set():
                    time.sleep(0.3)
                return super().wait(timeout_seconds=timeout_seconds, cancel_event=cancel_event)

        class BarrierGatedExecutor:
            def __init__(self, result):
                self.result = result
                self.processes: list[FakeManagedProcess] = []

            def start(self, argv, *, cwd):
                barrier.wait()
                process = SlowFakeManagedProcess(self.result)
                self.processes.append(process)
                return process

        executor_a = BarrierGatedExecutor(ProcessResult(0, '{"ok":true}', pid=111))
        executor_b = BarrierGatedExecutor(ProcessResult(0, '{"ok":true}', pid=222))
        runner_a = CodexCliRunner(executor=executor_a)
        runner_b = CodexCliRunner(executor=executor_b)
        results: dict[str, Any] = {}
        errors: dict[str, Exception] = {}

        def attempt(name, runner, prompt):
            try:
                results[name] = self.engine.start_managed_run(self.ticket["id"], runner, prompt, cwd=self.temp.name)
            except Exception as error:  # noqa: BLE001 - captured for assertion, not swallowed
                errors[name] = error

        thread_a = threading.Thread(target=attempt, args=("a", runner_a, "first"))
        thread_b = threading.Thread(target=attempt, args=("b", runner_b, "second"))
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=10)
        thread_b.join(timeout=10)

        self.assertEqual(1, len(results), f"expected exactly one winner, got results={results} errors={errors}")
        self.assertEqual(1, len(errors))
        (loser_name, error) = next(iter(errors.items()))
        self.assertIsInstance(error, InvalidTransitionError)

        loser_executor = executor_a if loser_name == "a" else executor_b
        self.assertEqual(1, len(loser_executor.processes))
        self.assertEqual([True], loser_executor.processes[0].wait_calls, "loser's process was not cancelled")

        winner_name = "b" if loser_name == "a" else "a"
        winner_executor = executor_a if winner_name == "a" else executor_b
        self.assertEqual([False], winner_executor.processes[0].wait_calls)

        with self.engine.store.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM runs WHERE ticket_id=?", (self.ticket["id"],)).fetchone()[0]
        self.assertEqual(1, count)


class OrphanReconciliationTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "test.db"
        self.engine = WorkbenchEngine(self.database)
        self.workspace = self.engine.create_workspace("Test")
        self.project = self.engine.create_project(self.workspace["id"], "Engine")
        self.ticket = self.engine.create_ticket(self.project["id"], "Work", "Prove flow", ["Evidence exists"])

    def tearDown(self):
        self.temp.cleanup()

    def _insert_running_run(self, *, pid, invocation_id="INV-orphan", run_id="RUN-orphan"):
        now = "2026-09-01T00:00:00.000Z"
        with self.engine.store.transaction() as db:
            db.execute(
                """INSERT INTO runs(id,ticket_id,runner,status,started_at,created_at,invocation_id,pid)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (run_id, self.ticket["id"], "codex-cli", "running", now, now, invocation_id, pid),
            )
            db.execute("UPDATE tickets SET status='active', updated_at=? WHERE id=?", (now, self.ticket["id"]))

    def test_reconciliation_marks_stale_running_run_failed_with_evidence(self):
        self._insert_running_run(pid=4_000_000)
        reconciled = self.engine.reconcile_orphan_runs(pid_alive_checker=lambda pid: False)
        self.assertEqual(1, len(reconciled))
        run = self.engine.get_run("RUN-orphan")
        self.assertEqual("failed", run["status"])
        self.assertEqual("RUNNER-ORPHANED", run["error_code"])
        self.assertEqual("ready", self.engine.get_ticket(self.ticket["id"])["status"])
        events = self.engine.list_events("RUN-orphan")
        self.assertIn("run_reconciled", [event["kind"] for event in events])
        reconciled_event = next(event for event in events if event["kind"] == "run_reconciled")
        self.assertEqual(False, reconciled_event["payload"]["pid_alive_at_check"])

    def test_reconciliation_is_idempotent(self):
        self._insert_running_run(pid=4_000_000)
        first = self.engine.reconcile_orphan_runs(pid_alive_checker=lambda pid: False)
        second = self.engine.reconcile_orphan_runs(pid_alive_checker=lambda pid: False)
        self.assertEqual(1, len(first))
        self.assertEqual(0, len(second))
        self.assertEqual("failed", self.engine.get_run("RUN-orphan")["status"])

    def test_reconciliation_handles_multiple_stale_runs_in_one_pass(self):
        other_ticket = self.engine.create_ticket(self.project["id"], "Other", "Prove flow", ["Evidence exists"])
        self._insert_running_run(pid=4_000_001, invocation_id="INV-a", run_id="RUN-a")
        with self.engine.store.transaction() as db:
            db.execute(
                """INSERT INTO runs(id,ticket_id,runner,status,started_at,created_at,invocation_id,pid)
                   VALUES (?,?,?,?,?,?,?,?)""",
                ("RUN-b", other_ticket["id"], "codex-cli", "running", "2026-09-01T00:00:00.000Z",
                 "2026-09-01T00:00:00.000Z", "INV-b", 4_000_002),
            )
            db.execute(
                "UPDATE tickets SET status='active', updated_at=? WHERE id=?",
                ("2026-09-01T00:00:00.000Z", other_ticket["id"]),
            )
        reconciled = self.engine.reconcile_orphan_runs(pid_alive_checker=lambda pid: False)
        self.assertEqual({"RUN-a", "RUN-b"}, {item["run_id"] for item in reconciled})
        self.assertEqual("failed", self.engine.get_run("RUN-a")["status"])
        self.assertEqual("failed", self.engine.get_run("RUN-b")["status"])

    def test_reconciliation_never_kills_a_real_alive_process_even_when_pid_matches(self):
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"])
        try:
            self._insert_running_run(pid=sleeper.pid)
            reconciled = self.engine.reconcile_orphan_runs()
            self.assertEqual(1, len(reconciled))
            self.assertTrue(reconciled[0]["pid_alive_at_check"])
            run = self.engine.get_run("RUN-orphan")
            self.assertEqual("failed", run["status"])
            self.assertIsNone(sleeper.poll(), "Reconciliation must never terminate the OS process")
        finally:
            sleeper.terminate()
            sleeper.wait(timeout=5)

    def test_default_pid_alive_checker_returns_false_for_nonexistent_pid_without_raising(self):
        self.assertFalse(_default_pid_alive_checker(999_999_999))

    def test_default_pid_alive_checker_returns_none_for_no_pid(self):
        self.assertIsNone(_default_pid_alive_checker(None))


class SchemaV4MigrationTestCase(unittest.TestCase):
    def test_fresh_database_reaches_v4_with_invocation_columns(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteStore(Path(temp) / "fresh.db")
            self.assertEqual(4, store.schema_version())
            with store.connect() as db:
                columns = {row[1] for row in db.execute("PRAGMA table_info(runs)")}
            self.assertIn("invocation_id", columns)
            self.assertIn("pid", columns)

    def test_v3_database_migrates_to_v4_preserving_existing_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "v3.db"
            store = SQLiteStore(database)
            engine = WorkbenchEngine(database)
            workspace = engine.create_workspace("W")
            project = engine.create_project(workspace["id"], "P")
            ticket = engine.create_ticket(project["id"], "T", "Goal", ["Criterion"])
            run = engine.start_run(ticket["id"])
            self.assertIsNone(run["invocation_id"])
            self.assertIsNone(run["pid"])
            self.assertEqual(4, store.schema_version())

    def test_queued_status_remains_unused_by_managed_run(self):
        with tempfile.TemporaryDirectory() as temp:
            engine = WorkbenchEngine(Path(temp) / "q.db")
            workspace = engine.create_workspace("W")
            project = engine.create_project(workspace["id"], "P")
            ticket = engine.create_ticket(project["id"], "T", "Goal", ["Criterion"])
            executor = FakeManagedExecutor(ProcessResult(0, '{"ok":true}', pid=1))
            runner = CodexCliRunner(executor=executor)
            run = engine.start_managed_run(ticket["id"], runner, "work", cwd=temp)
            self.assertNotEqual("queued", run["status"])
            with engine.store.connect() as db:
                statuses = {row[0] for row in db.execute("SELECT DISTINCT status FROM runs")}
            self.assertNotIn("queued", statuses)


class CliAndQueryTestCase(unittest.TestCase):
    def test_list_queries_and_auto_reconcile_at_startup(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "query.db"
            engine = WorkbenchEngine(db_path)
            ws = engine.create_workspace("TestWS")
            prj = engine.create_project(ws["id"], "TestPRJ")
            tkt = engine.create_ticket(prj["id"], "Title", "Goal", ["Crit1", "Crit2"])
            run = engine.start_run(tkt["id"])

            self.assertEqual(1, len(engine.list_workspaces()))
            self.assertEqual("TestWS", engine.list_workspaces()[0]["name"])
            self.assertEqual(1, len(engine.list_projects(ws["id"])))
            self.assertEqual(1, len(engine.list_tickets(prj["id"])))
            self.assertEqual(["Crit1", "Crit2"], engine.list_tickets(prj["id"])[0]["acceptance_criteria"])
            self.assertEqual(1, len(engine.list_runs(tkt["id"])))

            # Re-opening engine with auto_reconcile=True auto-reconciles orphan 'running' run
            engine2 = WorkbenchEngine(db_path, auto_reconcile=True)
            updated_run = engine2.get_run(run["id"])
            self.assertEqual("failed", updated_run["status"])
            self.assertEqual("RUNNER-ORPHANED", updated_run["error_code"])
            self.assertEqual("ready", engine2.get_ticket(tkt["id"])["status"])

    def test_cli_full_lifecycle(self):
        from io import StringIO
        from unittest.mock import patch
        from company_workbench.cli import main

        with tempfile.TemporaryDirectory() as temp:
            db_path = str(Path(temp) / "cli.db")
            # 1. Create workspace
            with patch("sys.stdout", new_callable=StringIO) as out:
                code = main(["--database", db_path, "workspace", "create", "W1"])
                self.assertEqual(0, code)
                ws = json.loads(out.getvalue())
                ws_id = ws["id"]

            # 2. Create project
            with patch("sys.stdout", new_callable=StringIO) as out:
                code = main(["--database", db_path, "project", "create", ws_id, "P1"])
                self.assertEqual(0, code)
                prj = json.loads(out.getvalue())
                prj_id = prj["id"]

            # 3. Create ticket
            with patch("sys.stdout", new_callable=StringIO) as out:
                code = main([
                    "--database", db_path, "ticket", "create", prj_id, "T1",
                    "--goal", "Build MVP", "--criteria", "Passes tests"
                ])
                self.assertEqual(0, code)
                tkt = json.loads(out.getvalue())
                tkt_id = tkt["id"]

            # 4. Run start with fake
            with patch("sys.stdout", new_callable=StringIO) as out:
                code = main(["--database", db_path, "run", "start", tkt_id, "--fake"])
                self.assertEqual(0, code)
                run = json.loads(out.getvalue())
                run_id = run["id"]

            # Complete the fake run via CLI to reach verification
            with patch("sys.stdout", new_callable=StringIO) as out:
                code = main(["--database", db_path, "run", "complete", run_id])
                self.assertEqual(0, code)

            # 5. Verify run
            with patch("sys.stdout", new_callable=StringIO) as out:
                code = main([
                    "--database", db_path, "verify", run_id,
                    "--evidence", "tests pass", "--summary", "Verified all acceptance criteria"
                ])
                self.assertEqual(0, code)

            # 6. Accept ticket
            with patch("sys.stdout", new_callable=StringIO) as out:
                code = main(["--database", db_path, "accept", tkt_id, "--by", "Josh"])
                self.assertEqual(0, code)
                accepted = json.loads(out.getvalue())
                self.assertEqual("accepted", accepted["status"])
                self.assertEqual("Josh", accepted["accepted_by"])


if __name__ == "__main__":
    unittest.main()
