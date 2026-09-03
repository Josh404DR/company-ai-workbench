"""Governance hardening: verifier independence, content-addressed evidence, memory expiry,
run usage/cost, tiered acceptance, ticket import, and worktree lifecycle."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from company_workbench import WorkbenchEngine
from company_workbench.cli import main
from company_workbench.engine import (
    AUTO_ACCEPTOR,
    DEFAULT_MEMORY_TTL_DAYS,
    TIERED_ACCEPTANCE_AUTHORITY,
    _sha256,
    provider_of,
)
from company_workbench.errors import (
    AcceptanceRequiredError,
    EvidenceRequiredError,
    InvalidTransitionError,
    TicketImportError,
    VerifierIndependenceError,
)
from company_workbench.runner import CodexCliRunner, ProcessHandle, ProcessResult, _normalize_usage
from company_workbench.store import SCHEMA_VERSION, SQLiteStore
from company_workbench.worktree import _run_git


class _FakeProcess:
    def __init__(self, result: ProcessResult):
        self.pid = result.pid
        self._result = result

    def wait(self, *, timeout_seconds, cancel_event=None):
        return self._result


class _FakeExecutor:
    def __init__(self, result: ProcessResult):
        self.result = result

    def start(self, argv, *, cwd):
        return _FakeProcess(self.result)


class _FileWritingExecutor:
    """Writes a file into cwd (a worktree) and then runs a trivial real process."""

    def __init__(self, filename: str, content: str):
        self.filename = filename
        self.content = content

    def start(self, argv, *, cwd):
        (cwd / self.filename).write_text(self.content, encoding="utf-8")
        stdout_file = tempfile.TemporaryFile("w+b")
        stderr_file = tempfile.TemporaryFile("w+b")
        proc = subprocess.Popen(
            [sys.executable, "-c", "print('{\"ok\": true}')"], stdout=stdout_file, stderr=stderr_file
        )
        return ProcessHandle(proc, stdout_file, stderr_file)


class GovernanceBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "gov.db"
        self.engine = WorkbenchEngine(self.database)
        self.workspace = self.engine.create_workspace("Gov")
        self.project = self.engine.create_project(self.workspace["id"], "Governance")

    def tearDown(self):
        self.temp.cleanup()

    def completed_run(self, *, runner="fake", risk_level="high", engine=None):
        engine = engine or self.engine
        ticket = engine.create_ticket(self.project["id"], f"T-{runner}-{risk_level}", "goal", ["c1"], risk_level=risk_level)
        run = engine.start_run(ticket["id"], runner=runner)
        engine.complete_run(run["id"])
        return ticket, run

    def verify(self, run_id, *, provider="human", content="evidence body", status="passed", engine=None):
        engine = engine or self.engine
        return engine.verify_run(
            run_id, status=status, evidence_ref="ref", summary="ok", verifier="tester",
            verifier_provider=provider, evidence_content=content,
        )


class VerifierIndependenceTestCase(GovernanceBase):
    def test_provider_families_collapse_labels(self):
        self.assertEqual("openai", provider_of("codex-cli"))
        self.assertEqual("openai", provider_of("gpt-4o"))
        self.assertEqual("google", provider_of("gemini-2.5-flash"))
        self.assertEqual("anthropic", provider_of("claude-code"))
        self.assertEqual("human", provider_of("Josh"))
        self.assertEqual("fake", provider_of("fake"))
        self.assertEqual("", provider_of(None))

    def test_same_family_verifier_is_rejected_for_every_builder(self):
        for runner, same_family in (("codex-cli", "openai"), ("codex-cli", "gpt-4o"), ("gemini", "google"), ("fake", "fake")):
            with self.subTest(runner=runner, verifier=same_family):
                _, run = self.completed_run(runner=runner)
                with self.assertRaises(VerifierIndependenceError):
                    self.verify(run["id"], provider=same_family)
                self.assertEqual([], [v for v in self._verifications(run["id"])])

    def test_empty_verifier_provider_is_rejected(self):
        _, run = self.completed_run(runner="codex-cli")
        with self.assertRaises(VerifierIndependenceError):
            self.verify(run["id"], provider="   ")

    def test_independent_verifier_is_recorded_with_provider(self):
        _, run = self.completed_run(runner="codex-cli")
        for provider in ("human", "anthropic", "google", "local-command"):
            with self.subTest(provider=provider):
                verification = self.verify(run["id"], provider=provider)
                self.assertEqual(provider, verification["verifier_provider"])

    def test_legacy_verification_without_provider_cannot_back_new_acceptance(self):
        ticket, run = self.completed_run(runner="fake")
        with self.engine.store.transaction() as db:
            db.execute(
                "INSERT INTO verifications(id,run_id,status,evidence_ref,summary,verifier,created_at) VALUES (?,?,?,?,?,?,?)",
                ("VER-legacy", run["id"], "passed", "legacy ref", "legacy", "IV", "2026-09-01T00:00:00Z"),
            )
        with self.assertRaises(VerifierIndependenceError):
            self.engine.accept_ticket(ticket["id"], accepted_by="Josh")
        self.assertEqual("verification", self.engine.get_ticket(ticket["id"])["status"])

    def _verifications(self, run_id):
        with self.engine.store.connect() as db:
            return db.execute("SELECT * FROM verifications WHERE run_id=?", (run_id,)).fetchall()


class EvidenceIntegrityTestCase(GovernanceBase):
    def test_verification_pins_sha256_and_artifact_is_retrievable(self):
        _, run = self.completed_run()
        verification = self.verify(run["id"], content="57 passed in 4.7s")
        expected = _sha256(b"57 passed in 4.7s")
        self.assertEqual(expected, verification["evidence_sha256"])
        self.assertEqual(b"57 passed in 4.7s", self.engine.get_evidence(expected))
        event = [e for e in self.engine.list_events(run["id"]) if e["kind"] == "verification_recorded"][-1]
        self.assertEqual(expected, event["payload"]["evidence_sha256"])

    def test_evidence_file_is_hashed(self):
        _, run = self.completed_run()
        evidence = self.root / "pytest.log"
        evidence.write_bytes(b"binary\x00log")
        verification = self.engine.verify_run(
            run["id"], status="passed", evidence_ref="pytest.log", summary="ok", verifier="t",
            verifier_provider="human", evidence_path=evidence,
        )
        self.assertEqual(_sha256(b"binary\x00log"), verification["evidence_sha256"])

    def test_verification_without_evidence_content_is_refused(self):
        _, run = self.completed_run()
        for kwargs in ({}, {"evidence_content": ""}, {"evidence_content": "   "}, {"evidence_path": self.root / "missing.txt"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(EvidenceRequiredError):
                    self.engine.verify_run(
                        run["id"], status="passed", evidence_ref="ref", summary="ok", verifier="t",
                        verifier_provider="human", **kwargs,
                    )

    def test_same_content_is_stored_once(self):
        _, run_a = self.completed_run()
        _, run_b = self.completed_run()
        self.verify(run_a["id"], content="same")
        self.verify(run_b["id"], content="same")
        self.assertEqual(1, self.engine.check_evidence_integrity()["artifacts"])

    def test_evidence_artifacts_are_append_only(self):
        _, run = self.completed_run()
        verification = self.verify(run["id"])
        for statement in (
            "UPDATE evidence_artifacts SET content=X'00' WHERE sha256=?",
            "DELETE FROM evidence_artifacts WHERE sha256=?",
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(sqlite3.DatabaseError):
                    with self.engine.store.connect() as db:
                        db.execute(statement, (verification["evidence_sha256"],))

    def test_tampered_evidence_blocks_acceptance_and_is_reported(self):
        ticket, run = self.completed_run()
        verification = self.verify(run["id"], content="honest output")
        # Simulate an out-of-engine edit by removing the guard trigger first.
        with self.engine.store.connect() as db:
            db.execute("DROP TRIGGER evidence_artifacts_no_update")
            db.execute("UPDATE evidence_artifacts SET content=? WHERE sha256=?", (b"forged", verification["evidence_sha256"]))
            db.commit()
        report = self.engine.check_evidence_integrity()
        self.assertFalse(report["ok"])
        self.assertEqual([verification["evidence_sha256"]], report["mismatched"])
        with self.assertRaises(EvidenceRequiredError):
            self.engine.accept_ticket(ticket["id"], accepted_by="Josh")

    def test_acceptance_event_carries_evidence_hash(self):
        ticket, run = self.completed_run()
        verification = self.verify(run["id"])
        self.engine.accept_ticket(ticket["id"], accepted_by="Josh")
        accepted = [e for e in self.engine.list_events(run["id"]) if e["kind"] == "ticket_accepted"][0]
        self.assertEqual(verification["evidence_sha256"], accepted["payload"]["evidence_sha256"])
        self.assertFalse(accepted["payload"]["automated"])
        self.assertTrue(self.engine.check_evidence_integrity()["ok"])


class MemoryReviewAuthorityTestCase(GovernanceBase):
    # Regression: review_memory() used to hardcode `if reviewed_by != "Josh"` directly, while
    # accept_ticket() went through the configurable acceptance_authority -- inconsistent for no
    # reason, since Invariant 6 only requires "never self-promote", not "must be Josh forever".
    def propose(self, engine, run_id):
        return engine.propose_memory(
            self.project["id"], run_id, kind="procedural", statement="s", scope="p", evidence_ref="e",
        )

    def test_default_requires_josh(self):
        _, run = self.completed_run()
        memory = self.propose(self.engine, run["id"])
        with self.assertRaises(AcceptanceRequiredError):
            self.engine.review_memory(memory["id"], action="approve", reviewed_by="someone-else")
        self.assertEqual("approved", self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh")["status"])

    def test_custom_authority_is_honored(self):
        engine = WorkbenchEngine(self.database, memory_review_authority=("Josh", "lead-editor"))
        _, run = self.completed_run(engine=engine)
        memory = self.propose(engine, run["id"])
        with self.assertRaises(AcceptanceRequiredError):
            engine.review_memory(memory["id"], action="approve", reviewed_by="random-agent")
        approved = engine.review_memory(memory["id"], action="approve", reviewed_by="lead-editor")
        self.assertEqual("lead-editor", approved["reviewed_by"])

    def test_empty_authority_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            WorkbenchEngine(self.database, memory_review_authority=())

    def test_diagnose_reports_memory_review_authority(self):
        engine = WorkbenchEngine(self.database, memory_review_authority=("Josh", "lead-editor"))
        self.assertEqual(["Josh", "lead-editor"], engine.diagnose()["memory_review_authority"])


class MemoryExpiryTestCase(GovernanceBase):
    def propose(self, run_id):
        return self.engine.propose_memory(
            self.project["id"], run_id, kind="procedural", statement="Run tests before claiming done",
            scope="project", evidence_ref=f"run:{run_id}",
        )

    def test_approval_carries_default_expiry_and_provenance(self):
        _, run = self.completed_run()
        memory = self.propose(run["id"])
        approved = self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", source_commit="abc123def456789")
        self.assertEqual("approved", approved["status"])
        self.assertEqual("Josh", approved["reviewed_by"])
        self.assertIsNotNone(approved["approved_at"])
        expires = datetime.fromisoformat(approved["expires_at"])
        approved_at = datetime.fromisoformat(approved["approved_at"])
        self.assertAlmostEqual(DEFAULT_MEMORY_TTL_DAYS, (expires - approved_at).days, delta=1)
        context = self.engine.get_project_active_context(self.project["id"])
        self.assertIn("commit abc123def456", context)
        self.assertIn("expires", context)

    def test_expired_memory_is_excluded_from_context_before_sweep(self):
        _, run = self.completed_run()
        memory = self.propose(run["id"])
        self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=1)
        later = datetime.now(timezone.utc) + timedelta(days=2)
        self.assertIn("Run tests", self.engine.get_project_active_context(self.project["id"]))
        self.assertEqual("", self.engine.get_project_active_context(self.project["id"], now=later))
        self.assertEqual("approved", self.engine.get_memory(memory["id"])["status"])

    def test_sweep_marks_expired_with_event_and_is_idempotent(self):
        _, run = self.completed_run()
        memory = self.propose(run["id"])
        self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=1)
        later = datetime.now(timezone.utc) + timedelta(days=2)
        self.assertEqual([], self.engine.expire_memories())
        swept = self.engine.expire_memories(now=later)
        self.assertEqual([memory["id"]], [item["memory_id"] for item in swept])
        self.assertEqual("expired", self.engine.get_memory(memory["id"])["status"])
        self.assertEqual([], self.engine.expire_memories(now=later))
        kinds = [e["kind"] for e in self.engine.list_events(run["id"])]
        self.assertEqual(1, kinds.count("memory_candidate_expired"))

    def test_expired_memory_can_be_renewed_by_josh_only(self):
        _, run = self.completed_run()
        memory = self.propose(run["id"])
        self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=1)
        self.engine.expire_memories(now=datetime.now(timezone.utc) + timedelta(days=2))
        with self.assertRaises(AcceptanceRequiredError):
            self.engine.review_memory(memory["id"], action="approve", reviewed_by="agent", ttl_days=30)
        renewed = self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=30)
        self.assertEqual("approved", renewed["status"])
        self.assertIn("Run tests", self.engine.get_project_active_context(self.project["id"]))

    def test_expiry_must_be_in_the_future_and_unambiguous(self):
        _, run = self.completed_run()
        memory = self.propose(run["id"])
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", expires_at=past)
        with self.assertRaises(ValueError):
            self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=0)
        with self.assertRaises(ValueError):
            self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=5, expires_at=past)
        self.assertEqual("pending", self.engine.get_memory(memory["id"])["status"])

    def test_diagnose_counts_expired_pending_sweep(self):
        _, run = self.completed_run()
        memory = self.propose(run["id"])
        self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=1)
        with self.engine.store.connect() as db:
            db.execute("UPDATE memory_candidates SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (memory["id"],))
            db.commit()
        self.assertEqual({"approved": 1, "expired_pending_sweep": 1}, self.engine.diagnose()["memory"])


class RunUsageTestCase(GovernanceBase):
    def test_managed_run_records_usage_from_json_output(self):
        stdout = '{"type":"item.completed"}\n{"type":"turn.completed","usage":{"input_tokens":120,"output_tokens":30}}\n'
        engine = WorkbenchEngine(self.database, pricing={"codex-cli": (2.0, 8.0)})
        ticket = engine.create_ticket(self.project["id"], "usage", "goal", ["c"])
        runner = CodexCliRunner(executor=_FakeExecutor(ProcessResult(0, stdout, pid=1)))
        run = engine.start_managed_run(ticket["id"], runner, "work", cwd=self.temp.name, provider_account="acct-A")
        self.assertEqual(120, run["input_tokens"])
        self.assertEqual(30, run["output_tokens"])
        self.assertAlmostEqual((120 * 2.0 + 30 * 8.0) / 1_000_000, run["cost_usd"])
        self.assertEqual("acct-A", run["provider_account"])
        summary = engine.usage_summary()["codex-cli"]
        self.assertEqual(150, summary["input_tokens"] + summary["output_tokens"])
        self.assertEqual(0, summary["runs_without_usage"])

    def test_usage_absent_stays_null_not_zero(self):
        ticket = self.engine.create_ticket(self.project["id"], "no-usage", "goal", ["c"])
        runner = CodexCliRunner(executor=_FakeExecutor(ProcessResult(0, "plain text", pid=1)))
        run = self.engine.start_managed_run(ticket["id"], runner, "work", cwd=self.temp.name)
        self.assertIsNone(run["input_tokens"])
        self.assertIsNone(run["cost_usd"])
        self.assertEqual(1, self.engine.usage_summary()["codex-cli"]["runs_without_usage"])

    def test_gemini_usage_metadata_is_normalized(self):
        self.assertEqual(
            {"input_tokens": 11, "output_tokens": 7},
            _normalize_usage({"promptTokenCount": 11, "candidatesTokenCount": 7, "totalTokenCount": 18}),
        )
        self.assertIsNone(_normalize_usage({"unrelated": True}))
        self.assertIsNone(_normalize_usage(None))

    def test_record_run_usage_validates_and_audits(self):
        _, run = self.completed_run()
        with self.assertRaises(ValueError):
            self.engine.record_run_usage(run["id"], input_tokens=-1)
        updated = self.engine.record_run_usage(run["id"], input_tokens=5, output_tokens=6, cost_usd=0.01, provider_account="acct")
        self.assertEqual((5, 6, 0.01, "acct"), (updated["input_tokens"], updated["output_tokens"], updated["cost_usd"], updated["provider_account"]))
        self.assertIn("usage_recorded", [e["kind"] for e in self.engine.list_events(run["id"])])


class TieredAcceptanceTestCase(GovernanceBase):
    def test_default_authority_requires_josh_for_every_tier(self):
        for risk in ("low", "medium", "high"):
            with self.subTest(risk=risk):
                ticket, run = self.completed_run(risk_level=risk)
                self.verify(run["id"])
                with self.assertRaises(AcceptanceRequiredError):
                    self.engine.accept_ticket(ticket["id"], accepted_by=AUTO_ACCEPTOR)
                self.assertEqual("accepted", self.engine.accept_ticket(ticket["id"], accepted_by="Josh")["status"])

    def test_tiered_authority_delegates_low_only(self):
        engine = WorkbenchEngine(self.database, acceptance_authority=TIERED_ACCEPTANCE_AUTHORITY)
        low, low_run = self.completed_run(risk_level="low", engine=engine)
        self.verify(low_run["id"], engine=engine)
        self.assertEqual(AUTO_ACCEPTOR, engine.accept_ticket(low["id"], accepted_by=AUTO_ACCEPTOR)["accepted_by"])
        for risk in ("medium", "high"):
            with self.subTest(risk=risk):
                ticket, run = self.completed_run(risk_level=risk, engine=engine)
                self.verify(run["id"], engine=engine)
                with self.assertRaises(AcceptanceRequiredError):
                    engine.accept_ticket(ticket["id"], accepted_by=AUTO_ACCEPTOR)

    def test_automation_cannot_be_granted_above_low(self):
        with self.assertRaises(ValueError):
            WorkbenchEngine(self.database, acceptance_authority={"low": ("Josh",), "medium": ("Josh", AUTO_ACCEPTOR), "high": ("Josh",)})
        with self.assertRaises(ValueError):
            WorkbenchEngine(self.database, acceptance_authority={"low": ("Josh",), "medium": ("Josh",)})

    def test_risk_level_is_validated_and_defaults_high(self):
        ticket = self.engine.create_ticket(self.project["id"], "default", "goal", ["c"])
        self.assertEqual("high", ticket["risk_level"])
        with self.assertRaises(ValueError):
            self.engine.create_ticket(self.project["id"], "bad", "goal", ["c"], risk_level="none")

    def test_memory_review_still_requires_josh_under_tiered_authority(self):
        engine = WorkbenchEngine(self.database, acceptance_authority=TIERED_ACCEPTANCE_AUTHORITY)
        _, run = self.completed_run(engine=engine)
        memory = engine.propose_memory(self.project["id"], run["id"], kind="semantic", statement="s", scope="p", evidence_ref="e")
        with self.assertRaises(AcceptanceRequiredError):
            engine.review_memory(memory["id"], action="approve", reviewed_by=AUTO_ACCEPTOR)


class SecondPassAdversarialTestCase(GovernanceBase):
    """Found during a second-model adversarial re-check of this same round (Sonnet 5 reviewing
    Fable 5.1's work); not a cross-provider independent verifier by the engine's own
    provider_of() rules, but real bugs the first pass missed."""

    def test_provider_account_secret_shaped_value_is_redacted_not_stored_raw(self):
        _, run = self.completed_run()
        updated = self.engine.record_run_usage(run["id"], provider_account="sk-live-FAKESECRETVALUE1234567890")
        self.assertNotIn("FAKESECRETVALUE", updated["provider_account"])
        events = self.engine.list_events(run["id"])
        usage_event = [e for e in events if e["kind"] == "usage_recorded"][0]
        self.assertNotIn("FAKESECRETVALUE", json.dumps(usage_event["payload"]))

    def test_provider_account_redacted_on_managed_run_path_too(self):
        engine = WorkbenchEngine(self.database)
        ticket = engine.create_ticket(self.project["id"], "managed", "g", ["c"])
        from company_workbench.runner import CodexCliRunner, ProcessResult

        class _Exec:
            def start(self, argv, *, cwd):
                class _Proc:
                    pid = 1
                    def wait(self, *, timeout_seconds, cancel_event=None):
                        return ProcessResult(0, "ok", pid=1)
                return _Proc()

        runner = CodexCliRunner(executor=_Exec())
        run = engine.start_managed_run(
            ticket["id"], runner, "work", cwd=self.temp.name,
            provider_account="Authorization: Bearer sk-abcdefghijklmnop",
        )
        self.assertNotIn("sk-abcdefghijklmnop", run["provider_account"])

    def test_bool_ttl_days_is_rejected_not_treated_as_one(self):
        _, run = self.completed_run()
        memory = self.engine.propose_memory(
            self.project["id"], run["id"], kind="semantic", statement="s", scope="p", evidence_ref="e",
        )
        with self.assertRaises(ValueError):
            self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=True)
        with self.assertRaises(ValueError):
            self.engine.review_memory(memory["id"], action="approve", reviewed_by="Josh", ttl_days=3.5)
        self.assertEqual("pending", self.engine.get_memory(memory["id"])["status"])


class TicketImportTestCase(GovernanceBase):
    def test_json_import_creates_tickets_with_risk(self):
        source = self.root / "tickets.json"
        source.write_text(json.dumps([
            {"title": "A", "goal": "ga", "acceptance_criteria": ["a1", "a2"], "risk_level": "low"},
            {"title": "B", "goal": "gb", "acceptance_criteria": ["b1"]},
        ]), encoding="utf-8")
        created = self.engine.import_tickets(self.project["id"], source, default_risk_level="medium")
        self.assertEqual([("A", "low", ["a1", "a2"]), ("B", "medium", ["b1"])],
                         [(t["title"], t["risk_level"], t["acceptance_criteria"]) for t in created])

    def test_markdown_import_parses_headings_goal_risk_and_bullets(self):
        source = self.root / "tickets.md"
        source.write_text(
            "# Sprint\n\n## Fix login\nGoal: users can log in\nRisk: low\n- [ ] login test passes\n- no 500s\n\n"
            "## 修正設定\n目標：設定檔可讀\n風險：high\n* 回歸測試通過\n",
            encoding="utf-8",
        )
        created = self.engine.import_tickets(self.project["id"], source)
        self.assertEqual(2, len(created))
        self.assertEqual(("Fix login", "users can log in", "low", ["login test passes", "no 500s"]),
                         (created[0]["title"], created[0]["goal"], created[0]["risk_level"], created[0]["acceptance_criteria"]))
        self.assertEqual(("修正設定", "設定檔可讀", "high", ["回歸測試通過"]),
                         (created[1]["title"], created[1]["goal"], created[1]["risk_level"], created[1]["acceptance_criteria"]))

    def test_import_is_all_or_nothing(self):
        source = self.root / "bad.json"
        source.write_text(json.dumps([
            {"title": "Good", "goal": "g", "acceptance_criteria": ["c"]},
            {"title": "Broken", "goal": "", "acceptance_criteria": []},
        ]), encoding="utf-8")
        with self.assertRaises(TicketImportError):
            self.engine.import_tickets(self.project["id"], source)
        self.assertEqual([], self.engine.list_tickets(self.project["id"]))

    def test_import_rejects_duplicates_inside_file_and_against_project(self):
        self.engine.create_ticket(self.project["id"], "Existing", "g", ["c"])
        dup_inside = self.root / "dup.json"
        dup_inside.write_text(json.dumps([
            {"title": "Same", "goal": "g", "acceptance_criteria": ["c"]},
            {"title": "same", "goal": "g", "acceptance_criteria": ["c"]},
        ]), encoding="utf-8")
        with self.assertRaises(TicketImportError):
            self.engine.import_tickets(self.project["id"], dup_inside)
        clash = self.root / "clash.json"
        clash.write_text(json.dumps([{"title": "existing", "goal": "g", "acceptance_criteria": ["c"]}]), encoding="utf-8")
        with self.assertRaises(TicketImportError):
            self.engine.import_tickets(self.project["id"], clash)
        self.assertEqual(1, len(self.engine.list_tickets(self.project["id"])))

    def test_import_rejects_missing_file_and_empty_source(self):
        with self.assertRaises(TicketImportError):
            self.engine.import_tickets(self.project["id"], self.root / "nope.json")
        empty = self.root / "empty.md"
        empty.write_text("# nothing here\n", encoding="utf-8")
        with self.assertRaises(TicketImportError):
            self.engine.import_tickets(self.project["id"], empty)


class WorktreeLifecycleTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp.name) / "repo"
        self.repo_root.mkdir()
        _run_git(["init", "-b", "main"], cwd=self.repo_root)
        _run_git(["config", "user.name", "Workbench Test"], cwd=self.repo_root)
        _run_git(["config", "user.email", "test@workbench.local"], cwd=self.repo_root)
        (self.repo_root / "README.md").write_text("# repo\n", encoding="utf-8")
        _run_git(["add", "README.md"], cwd=self.repo_root)
        _run_git(["commit", "-q", "-m", "init"], cwd=self.repo_root)
        self.engine = WorkbenchEngine(self.repo_root / ".workbench" / "wb.db")
        ws = self.engine.create_workspace("WS")
        self.project = self.engine.create_project(ws["id"], "P")

    def tearDown(self):
        self.temp.cleanup()

    def _managed(self, engine, ticket, **kwargs):
        runner = CodexCliRunner(executor=_FileWritingExecutor("ai_output.txt", "generated\n"))
        return engine.start_managed_run(ticket["id"], runner, "do it", cwd=self.repo_root, isolate_worktree=True, **kwargs)

    def test_completed_run_commits_output_to_branch_and_removes_directory(self):
        ticket = self.engine.create_ticket(self.project["id"], "T", "g", ["c"])
        run = self._managed(self.engine, ticket)
        self.assertEqual("completed", run["status"])
        worktree_dir = self.repo_root / ".workbench" / "worktrees" / run["id"]
        self.assertFalse(worktree_dir.exists())
        branch = f"wb-run/{run['id']}"
        listing = _run_git(["ls-tree", "--name-only", branch], cwd=self.repo_root)
        self.assertIn("ai_output.txt", listing)
        self.assertFalse((self.repo_root / "ai_output.txt").exists())
        retired = [e for e in self.engine.list_events(run["id"]) if e["kind"] == "worktree_retired"][0]
        self.assertTrue(retired["payload"]["directory_removed"])
        self.assertTrue(retired["payload"]["commit"])
        self.assertEqual([], self.engine.orphan_worktrees(self.repo_root))

    def test_keep_worktree_leaves_directory_but_still_commits(self):
        ticket = self.engine.create_ticket(self.project["id"], "T", "g", ["c"])
        run = self._managed(self.engine, ticket, keep_worktree=True)
        worktree_dir = self.repo_root / ".workbench" / "worktrees" / run["id"]
        self.assertTrue(worktree_dir.exists())
        self.assertIn("ai_output.txt", _run_git(["ls-tree", "--name-only", f"wb-run/{run['id']}"], cwd=self.repo_root))
        self.assertEqual([run["id"]], [o["run_id"] for o in self.engine.orphan_worktrees(self.repo_root)])

    def test_prune_retires_leftover_worktrees_but_not_running_ones(self):
        ticket = self.engine.create_ticket(self.project["id"], "T", "g", ["c"])
        run = self._managed(self.engine, ticket, keep_worktree=True)
        worktree_dir = self.repo_root / ".workbench" / "worktrees" / run["id"]
        (worktree_dir / "late_edit.txt").write_text("after run\n", encoding="utf-8")
        # A directory for a Run this database considers running must be left alone.
        other = self.engine.create_ticket(self.project["id"], "T2", "g", ["c"])
        running = self.engine.start_run(other["id"], runner="fake")
        running_dir = self.repo_root / ".workbench" / "worktrees" / running["id"]
        _run_git(["worktree", "add", "-q", "-b", f"wb-run/{running['id']}", str(running_dir), "HEAD"], cwd=self.repo_root)

        pruned = self.engine.prune_worktrees(self.repo_root)
        self.assertEqual([run["id"]], [p["run_id"] for p in pruned])
        self.assertFalse(worktree_dir.exists())
        self.assertTrue(running_dir.exists())
        self.assertIn("late_edit.txt", _run_git(["ls-tree", "--name-only", f"wb-run/{run['id']}"], cwd=self.repo_root))
        self.assertEqual([], self.engine.prune_worktrees(self.repo_root))

    def test_low_risk_ticket_is_auto_accepted_only_under_tiered_authority(self):
        verify_cmd = f'"{sys.executable}" -c "import pathlib,sys; sys.exit(0 if pathlib.Path(\'ai_output.txt\').exists() else 1)"'
        default_engine = self.engine
        ticket = default_engine.create_ticket(self.project["id"], "low-default", "g", ["c"], risk_level="low")
        run = self._managed(default_engine, ticket, verification_command=verify_cmd)
        self.assertEqual("completed", run["status"])
        self.assertEqual("verification", default_engine.get_ticket(ticket["id"])["status"])

        tiered = WorkbenchEngine(self.repo_root / ".workbench" / "wb.db", acceptance_authority=TIERED_ACCEPTANCE_AUTHORITY)
        low = tiered.create_ticket(self.project["id"], "low-tiered", "g", ["c"], risk_level="low")
        run_low = self._managed(tiered, low, verification_command=verify_cmd)
        after = tiered.get_ticket(low["id"])
        self.assertEqual(("accepted", AUTO_ACCEPTOR), (after["status"], after["accepted_by"]))
        accepted = [e for e in tiered.list_events(run_low["id"]) if e["kind"] == "ticket_accepted"][0]
        self.assertTrue(accepted["payload"]["automated"])
        self.assertTrue(accepted["payload"]["evidence_sha256"])
        self.assertTrue(tiered.check_evidence_integrity()["ok"])

        high = tiered.create_ticket(self.project["id"], "high-tiered", "g", ["c"], risk_level="high")
        self._managed(tiered, high, verification_command=verify_cmd)
        self.assertEqual("verification", tiered.get_ticket(high["id"])["status"])

    def test_auto_verification_evidence_is_content_addressed_and_independent(self):
        verify_cmd = f'"{sys.executable}" -c "print(\'ok\')"'
        ticket = self.engine.create_ticket(self.project["id"], "T", "g", ["c"])
        run = self._managed(self.engine, ticket, verification_command=verify_cmd)
        with self.engine.store.connect() as db:
            verification = db.execute("SELECT * FROM verifications WHERE run_id=?", (run["id"],)).fetchone()
        self.assertEqual("local-command", verification["verifier_provider"])
        stored = json.loads(self.engine.get_evidence(verification["evidence_sha256"]))
        self.assertEqual(0, stored["exit_code"])
        self.assertEqual("accepted", self.engine.accept_ticket(ticket["id"], accepted_by="Josh")["status"])


class MigrationV5TestCase(unittest.TestCase):
    def test_v4_rows_survive_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "v4.db"
            SQLiteStore(database)
            with closing(sqlite3.connect(database)) as db:
                db.execute("DELETE FROM schema_migrations WHERE version=5")
                db.execute("DROP TABLE evidence_artifacts")
                # Rebuild a v4-shaped memory table and insert legacy rows through it.
                db.executescript(
                    """
                    DROP TABLE memory_candidates;
                    CREATE TABLE memory_candidates (
                        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, source_run_id TEXT NOT NULL,
                        kind TEXT NOT NULL, statement TEXT NOT NULL, scope TEXT NOT NULL, evidence_ref TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','disabled')),
                        created_at TEXT NOT NULL
                    );
                    INSERT INTO workspaces VALUES ('WS-1','w',NULL,'2026-09-01T00:00:00Z');
                    INSERT INTO projects VALUES ('PRJ-1','WS-1','p','2026-09-01T00:00:00Z');
                    INSERT INTO tickets(id,project_id,title,goal,acceptance_criteria_json,status,created_at,updated_at)
                        VALUES ('TKT-1','PRJ-1','t','g','["c"]','ready','2026-09-01T00:00:00Z','2026-09-01T00:00:00Z');
                    INSERT INTO runs(id,ticket_id,runner,status,created_at) VALUES ('RUN-1','TKT-1','fake','completed','2026-09-01T00:00:00Z');
                    INSERT INTO memory_candidates VALUES ('MEM-1','PRJ-1','RUN-1','semantic','legacy rule','project','ref','approved','2026-09-01T00:00:00Z');
                    """
                )
                db.commit()
            engine = WorkbenchEngine(database)
            self.assertEqual(SCHEMA_VERSION, engine.store.schema_version())
            self.assertEqual("high", engine.get_ticket("TKT-1")["risk_level"])
            legacy = engine.get_memory("MEM-1")
            self.assertEqual(("approved", None, None), (legacy["status"], legacy["expires_at"], legacy["approved_at"]))
            self.assertIn("legacy", engine.get_project_active_context("PRJ-1"))
            self.assertEqual("ok", engine.diagnose()["integrity"])


class GovernanceCliTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = str(self.root / "cli.db")

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *argv):
        with patch("sys.stdout", new_callable=StringIO) as out, patch("sys.stderr", new_callable=StringIO) as err:
            code = main(["--database", self.db, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_manual_runner_and_log_via_cli(self):
        # Regression for real friction hit dogfooding this CLI: there was no way to record a
        # Run done directly by an interactive session (not a managed subprocess Runner) or to
        # append an audit-trail event to it, short of dropping into raw Python.
        _, out, _ = self.run_cli("workspace", "create", "W")
        ws = json.loads(out)["id"]
        _, out, _ = self.run_cli("project", "create", ws, "P")
        prj = json.loads(out)["id"]
        _, out, _ = self.run_cli("ticket", "create", prj, "T", "--goal", "g", "--criteria", "c")
        tkt = json.loads(out)["id"]

        code, out, _ = self.run_cli("run", "start", tkt, "--manual-runner", "claude-code")
        self.assertEqual(0, code)
        run = json.loads(out)
        self.assertEqual(("claude-code", "running"), (run["runner"], run["status"]))

        code, _, err = self.run_cli("run", "start", tkt, "--fake", "--manual-runner", "claude-code")
        self.assertEqual(1, code)
        self.assertIn("mutually exclusive", err)

        code, out, _ = self.run_cli("run", "log", run["id"], "--note", "did the thing")
        self.assertEqual(0, code)
        event = json.loads(out)
        self.assertEqual(("agent_activity", "did the thing"), (event["kind"], event["payload"]["summary"]))

        code, out, _ = self.run_cli("run", "log", run["id"], "--kind", "checkpoint", "--note", "halfway")
        self.assertEqual(0, code)
        self.assertEqual("checkpoint", json.loads(out)["kind"])

        _, out, _ = self.run_cli("run", "events", run["id"])
        kinds = [e["kind"] for e in json.loads(out)]
        self.assertEqual(["run_started", "agent_activity", "checkpoint"], kinds)

    def test_full_governed_lifecycle_via_cli(self):
        _, out, _ = self.run_cli("workspace", "create", "W")
        ws = json.loads(out)["id"]
        _, out, _ = self.run_cli("project", "create", ws, "P")
        prj = json.loads(out)["id"]

        source = self.root / "tickets.md"
        source.write_text("## Low task\nGoal: g\nRisk: low\n- c1\n## High task\nGoal: g\n- c2\n", encoding="utf-8")
        code, out, _ = self.run_cli("ticket", "import", prj, str(source))
        self.assertEqual(0, code)
        tickets = json.loads(out)
        self.assertEqual(["low", "high"], [t["risk_level"] for t in tickets])

        code, out, err = self.run_cli("ticket", "import", prj, str(source))
        self.assertEqual(1, code)
        self.assertIn("already exist", err)

        tkt = tickets[1]["id"]
        _, out, _ = self.run_cli("run", "start", tkt, "--fake")
        run = json.loads(out)["id"]
        self.run_cli("run", "complete", run)

        code, _, err = self.run_cli(
            "verify", run, "--evidence", "ref", "--evidence-text", "log", "--summary", "s", "--verifier-provider", "fake",
        )
        self.assertEqual(1, code)
        self.assertIn("independent", err)

        evidence = self.root / "pytest.txt"
        evidence.write_text("57 passed", encoding="utf-8")
        code, out, _ = self.run_cli(
            "verify", run, "--evidence", "pytest", "--evidence-file", str(evidence), "--summary", "s", "--verifier-provider", "human",
        )
        self.assertEqual(0, code)
        sha = json.loads(out)["evidence_sha256"]
        code, out, _ = self.run_cli("evidence", "show", sha)
        self.assertEqual((0, "57 passed"), (code, out))
        code, out, _ = self.run_cli("evidence", "check")
        self.assertEqual(0, code)
        self.assertTrue(json.loads(out)["ok"])

        code, _, err = self.run_cli("accept", tkt, "--by", AUTO_ACCEPTOR)
        self.assertEqual(1, code)
        self.assertIn("requires one of: Josh", err)
        code, out, _ = self.run_cli("accept", tkt, "--by", "Josh")
        self.assertEqual(0, code)

        code, out, _ = self.run_cli("run", "usage", run, "--input-tokens", "10", "--output-tokens", "3", "--provider-account", "acct")
        self.assertEqual(0, code)
        self.assertEqual(10, json.loads(out)["input_tokens"])

        _, out, _ = self.run_cli("memory", "propose", prj, run, "--statement", "rule", "--evidence", "e")
        mem = json.loads(out)["id"]
        code, out, _ = self.run_cli("memory", "approve", mem, "--ttl-days", "7", "--commit", "deadbeef")
        self.assertEqual(0, code)
        self.assertEqual("deadbeef", json.loads(out)["source_commit"])
        code, out, _ = self.run_cli("memory", "context", prj)
        self.assertIn("rule", out)
        self.assertIn("expires", out)
        code, out, _ = self.run_cli("memory", "expire")
        self.assertEqual((0, []), (code, json.loads(out)))

        code, out, _ = self.run_cli("diagnose")
        self.assertEqual(0, code)
        report = json.loads(out)
        self.assertEqual({"low": 1, "high": 1}, report["tickets_by_risk"])
        self.assertTrue(report["evidence"]["ok"])
        self.assertIn("fake", report["usage"])
        self.assertEqual(["Josh"], report["acceptance_authority"]["high"])

    def test_worktree_commands_require_repo(self):
        code, _, err = self.run_cli("worktree", "list", "--repo", str(self.root))
        self.assertEqual(1, code)
        self.assertIn("not a git repository", err)


if __name__ == "__main__":
    unittest.main()
