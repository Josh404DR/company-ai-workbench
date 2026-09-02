from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from .errors import (
    AcceptanceRequiredError,
    EvidenceRequiredError,
    InvalidTransitionError,
    NotFoundError,
    RunnerLaunchError,
)
from .runner import CodexCliRunner, RunnerResult
from .store import SQLiteStore


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def _default_pid_alive_checker(pid: int | None) -> bool | None:
    """Best-effort, read-only liveness probe. Never signals or terminates the target process.

    Returns True/False when the check itself succeeded, or None when liveness could not be
    determined. The result is evidence only; callers must never use it to decide whether to
    act on the process, because a PID can be reused by an unrelated process after the original
    invocation has exited.
    """
    if pid is None:
        return None
    try:
        if os.name == "nt":
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:
        return None


class WorkbenchEngine:
    """Application boundary shared by CLI and future desktop shells."""

    def __init__(self, database_path: str | Path, *, auto_reconcile: bool = False):
        self.store = SQLiteStore(database_path)
        if auto_reconcile:
            self.reconcile_orphan_runs()

    def create_workspace(self, name: str, root_path: str | None = None) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Workspace name is required")
        item = {"id": _id("WS"), "name": name.strip(), "root_path": root_path, "created_at": _now()}
        with self.store.transaction() as db:
            db.execute(
                "INSERT INTO workspaces(id,name,root_path,created_at) VALUES (:id,:name,:root_path,:created_at)", item
            )
        return item

    def create_project(self, workspace_id: str, name: str) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Project name is required")
        item = {"id": _id("PRJ"), "workspace_id": workspace_id, "name": name.strip(), "created_at": _now()}
        try:
            with self.store.transaction() as db:
                db.execute(
                    "INSERT INTO projects(id,workspace_id,name,created_at) VALUES (:id,:workspace_id,:name,:created_at)", item
                )
        except sqlite3.IntegrityError as error:
            raise NotFoundError(f"Workspace not found: {workspace_id}") from error
        return item

    def create_ticket(self, project_id: str, title: str, goal: str, acceptance_criteria: list[str]) -> dict[str, Any]:
        criteria = [value.strip() for value in acceptance_criteria if value.strip()]
        if not title.strip() or not goal.strip() or not criteria:
            raise ValueError("Ticket requires title, goal, and acceptance criteria")
        now = _now()
        item = {
            "id": _id("TKT"), "project_id": project_id, "title": title.strip(), "goal": goal.strip(),
            "acceptance_criteria_json": json.dumps(criteria, ensure_ascii=False), "status": "ready",
            "created_at": now, "updated_at": now,
        }
        try:
            with self.store.transaction() as db:
                db.execute(
                    """INSERT INTO tickets(id,project_id,title,goal,acceptance_criteria_json,status,created_at,updated_at)
                       VALUES (:id,:project_id,:title,:goal,:acceptance_criteria_json,:status,:created_at,:updated_at)""", item
                )
        except sqlite3.IntegrityError as error:
            raise NotFoundError(f"Project not found: {project_id}") from error
        return self.get_ticket(item["id"])

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        with self.store.connect() as db:
            item = _row(db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone())
        if not item:
            raise NotFoundError(f"Ticket not found: {ticket_id}")
        item["acceptance_criteria"] = json.loads(item.pop("acceptance_criteria_json"))
        return item

    def start_run(self, ticket_id: str, runner: str = "fake") -> dict[str, Any]:
        ticket = self.get_ticket(ticket_id)
        if ticket["status"] not in {"ready", "verification"}:
            raise InvalidTransitionError(f"Ticket {ticket_id} cannot start from {ticket['status']}")
        now = _now()
        run = {
            "id": _id("RUN"), "ticket_id": ticket_id, "runner": runner, "status": "running",
            "started_at": now, "created_at": now,
        }
        with self.store.transaction() as db:
            active = db.execute(
                "SELECT 1 FROM runs WHERE ticket_id=? AND status IN ('queued','running')", (ticket_id,)
            ).fetchone()
            if active:
                raise InvalidTransitionError(f"Ticket {ticket_id} already has an active Run")
            db.execute(
                "INSERT INTO runs(id,ticket_id,runner,status,started_at,created_at) VALUES (:id,:ticket_id,:runner,:status,:started_at,:created_at)", run
            )
            db.execute("UPDATE tickets SET status='active', updated_at=? WHERE id=?", (now, ticket_id))
            self._append_event(db, run["id"], "run_started", {"runner": runner})
        return self.get_run(run["id"])

    def start_managed_run(
        self,
        ticket_id: str,
        runner: Any,
        prompt: str,
        *,
        cwd: str | Path,
        runner_name: str = "codex-cli",
        timeout_seconds: float = 300,
        max_output_chars: int = 32_000,
        sensitive_values: Sequence[str] = (),
        cancel_event: threading.Event | None = None,
        model: str | None = None,
        isolate_worktree: bool = False,
        verification_command: str | None = None,
    ) -> dict[str, Any]:
        """Route a Ticket through the verified Runner boundary and record its full lifecycle."""
        ticket = self.get_ticket(ticket_id)
        if ticket["status"] not in {"ready", "verification"}:
            raise InvalidTransitionError(f"Ticket {ticket_id} cannot start from {ticket['status']}")

        run_id = _id("RUN")
        worktree_env = None
        target_cwd = Path(cwd).resolve()

        if isolate_worktree:
            from .worktree import GitWorktreeManager
            wt_manager = GitWorktreeManager(target_cwd)
            worktree_env = wt_manager.create_worktree(run_id)
            target_cwd = worktree_env.worktree_path

        cancel_event = cancel_event if cancel_event is not None else threading.Event()
        invocation_id = _id("INV")
        try:
            invocation = runner.start_invocation(
                prompt,
                cwd=target_cwd,
                timeout_seconds=timeout_seconds,
                max_output_chars=max_output_chars,
                cancel_event=cancel_event,
                sensitive_values=sensitive_values,
                model=model,
            )
        except (ValueError, RunnerLaunchError):
            if worktree_env:
                worktree_env.cleanup()
            raise
        except OSError as error:
            if worktree_env:
                worktree_env.cleanup()
            raise RunnerLaunchError(f"Failed to launch Runner invocation: {error}") from error
        except Exception:
            if worktree_env:
                worktree_env.cleanup()
            raise

        now = _now()
        run = {
            "id": run_id, "ticket_id": ticket_id, "runner": runner_name, "status": "running",
            "started_at": now, "created_at": now, "invocation_id": invocation_id, "pid": invocation.pid,
        }
        try:
            with self.store.transaction() as db:
                active = db.execute(
                    "SELECT 1 FROM runs WHERE ticket_id=? AND status IN ('queued','running')", (ticket_id,)
                ).fetchone()
                if active:
                    raise InvalidTransitionError(f"Ticket {ticket_id} already has an active Run")
                current = db.execute("SELECT status FROM tickets WHERE id=?", (ticket_id,)).fetchone()
                if not current:
                    raise NotFoundError(f"Ticket not found: {ticket_id}")
                if current["status"] not in {"ready", "verification"}:
                    raise InvalidTransitionError(f"Ticket {ticket_id} cannot start from {current['status']}")
                db.execute(
                    """INSERT INTO runs(id,ticket_id,runner,status,started_at,created_at,invocation_id,pid)
                       VALUES (:id,:ticket_id,:runner,:status,:started_at,:created_at,:invocation_id,:pid)""", run
                )
                db.execute("UPDATE tickets SET status='active', updated_at=? WHERE id=?", (now, ticket_id))
                payload = {"runner": runner_name}
                if worktree_env:
                    payload["worktree_path"] = str(worktree_env.worktree_path)
                    payload["branch_name"] = worktree_env.branch_name
                if verification_command:
                    payload["verification_command"] = verification_command
                self._append_event(db, run["id"], "run_started", payload)
        except Exception:
            invocation.cancel()
            invocation.wait()
            if worktree_env:
                worktree_env.cleanup()
            raise

        result = invocation.wait()
        self._finalize_managed_run(
            run["id"],
            result,
            worktree_env=worktree_env,
            verification_command=verification_command,
        )
        return self.get_run(run["id"])

    def _finalize_managed_run(
        self,
        run_id: str,
        result: RunnerResult,
        *,
        worktree_env: Any | None = None,
        verification_command: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        verification_result = None
        if worktree_env and verification_command and result.outcome == "completed":
            verification_result = worktree_env.run_verification(verification_command)

        with self.store.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise NotFoundError(f"Run not found: {run_id}")
            if run["status"] != "running":
                raise InvalidTransitionError(f"Run {run_id} is not awaiting a managed outcome")

            output_payload = {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            if worktree_env:
                try:
                    output_payload["changed_files"] = worktree_env.get_changed_files()
                    output_payload["diff"] = worktree_env.get_diff()
                except Exception:
                    pass

            if verification_result:
                output_payload["verification_result"] = verification_result

            self._append_event(db, run_id, "invocation_output", output_payload)

            if result.outcome == "completed":
                # If auto-verification ran and failed, mark Run failed!
                if verification_result and not verification_result["passed"]:
                    err_msg = f"Automated verification failed (exit {verification_result['exit_code']}): {verification_result['stderr'] or verification_result['stdout']}"
                    db.execute(
                        "UPDATE runs SET status='failed', finished_at=?, error_code='VERIFICATION-FAILED', error_message=? WHERE id=?",
                        (now, err_msg, run_id),
                    )
                    db.execute("UPDATE tickets SET status='ready', updated_at=? WHERE id=?", (now, run["ticket_id"]))
                    self._append_event(db, run_id, "run_failed", {"error_code": "VERIFICATION-FAILED", "message": err_msg})
                else:
                    db.execute("UPDATE runs SET status='completed', finished_at=? WHERE id=?", (now, run_id))
                    db.execute("UPDATE tickets SET status='verification', updated_at=? WHERE id=?", (now, run["ticket_id"]))
                    self._append_event(db, run_id, "run_completed", {})

                    # If auto-verification passed, record verification evidence automatically!
                    if verification_result and verification_result["passed"]:
                        ver_id = _id("VER")
                        v_summary = f"Automated test passed: {verification_command}"
                        v_evidence = f"exit 0 in {verification_result['duration_seconds']}s"
                        db.execute(
                            "INSERT INTO verifications(id,run_id,status,evidence_ref,summary,verifier,created_at) VALUES (?,?,?,?,?,?,?)",
                            (ver_id, run_id, "passed", v_evidence, v_summary, "auto-verifier", now),
                        )
                        self._append_event(db, run_id, "verification_recorded", {
                            "verification_id": ver_id,
                            "status": "passed",
                            "evidence_ref": v_evidence,
                            "automated": True,
                        })

            elif result.outcome == "cancelled":
                message = "Runner invocation cancelled"
                db.execute(
                    "UPDATE runs SET status='cancelled', finished_at=?, error_code=?, error_message=? WHERE id=?",
                    (now, result.error_code, message, run_id),
                )
                db.execute("UPDATE tickets SET status='ready', updated_at=? WHERE id=?", (now, run["ticket_id"]))
                self._append_event(db, run_id, "run_cancelled", {"error_code": result.error_code, "message": message})
            else:
                message = f"Runner invocation failed: {result.error_code}"
                db.execute(
                    "UPDATE runs SET status='failed', finished_at=?, error_code=?, error_message=? WHERE id=?",
                    (now, result.error_code, message, run_id),
                )
                db.execute("UPDATE tickets SET status='ready', updated_at=? WHERE id=?", (now, run["ticket_id"]))
                self._append_event(db, run_id, "run_failed", {"error_code": result.error_code, "message": message})

        return self.get_run(run_id)

    def reconcile_orphan_runs(
        self, *, pid_alive_checker: Callable[[int | None], bool | None] | None = None
    ) -> list[dict[str, Any]]:
        """Fail-close any Run left 'running' from before this Engine session started.

        A Run can only be 'running' because some earlier process claimed it; since no live session
        here ever claimed it, it cannot be legitimately advanced and is marked failed with auditable
        evidence. PID liveness is recorded for diagnostics only and never used to decide whether to
        act on the process: the stored PID may since have been reused by an unrelated process, so it
        is never signalled, terminated, or otherwise touched. Idempotent: rows already reconciled are
        no longer 'running' and are skipped on subsequent calls.
        """
        checker = pid_alive_checker or _default_pid_alive_checker
        now = _now()
        reconciled: list[dict[str, Any]] = []
        with self.store.transaction() as db:
            stale = db.execute("SELECT * FROM runs WHERE status='running'").fetchall()
            for run in stale:
                pid_alive = checker(run["pid"])
                message = (
                    f"Startup reconciliation: no Engine session claims invocation "
                    f"{run['invocation_id']!r} (pid={run['pid']}, pid_alive_at_check={pid_alive}); "
                    "marked failed without any process action."
                )
                db.execute(
                    "UPDATE runs SET status='failed', finished_at=?, error_code='RUNNER-ORPHANED', error_message=? WHERE id=?",
                    (now, message, run["id"]),
                )
                db.execute(
                    "UPDATE tickets SET status='ready', updated_at=? WHERE id=? AND status='active'",
                    (now, run["ticket_id"]),
                )
                self._append_event(
                    db, run["id"], "run_reconciled",
                    {"error_code": "RUNNER-ORPHANED", "pid_alive_at_check": pid_alive},
                )
                reconciled.append(
                    {"run_id": run["id"], "ticket_id": run["ticket_id"], "pid": run["pid"], "pid_alive_at_check": pid_alive}
                )
        return reconciled

    def append_event(self, run_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.store.transaction() as db:
            if not db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
                raise NotFoundError(f"Run not found: {run_id}")
            return self._append_event(db, run_id, kind, payload)

    def _append_event(self, db: sqlite3.Connection, run_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        sequence = int(db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE run_id=?", (run_id,)).fetchone()[0])
        item = {
            "id": _id("EVT"), "run_id": run_id, "sequence": sequence, "kind": kind,
            "payload_json": json.dumps(payload, ensure_ascii=False), "created_at": _now(),
        }
        db.execute(
            "INSERT INTO events(id,run_id,sequence,kind,payload_json,created_at) VALUES (:id,:run_id,:sequence,:kind,:payload_json,:created_at)", item
        )
        return {**item, "payload": payload}

    def record_debug_episode(self, run_id: str, **details: Any) -> dict[str, Any]:
        required = ["symptom", "reproduction", "environment", "error_fingerprint", "root_cause", "accepted_fix", "regression_test"]
        missing = [name for name in required if not str(details.get(name, "")).strip()]
        if missing:
            raise ValueError(f"Debug Episode missing: {', '.join(missing)}")
        item = {
            "id": _id("DBG"), "run_id": run_id,
            **{name: str(details[name]).strip() for name in required},
            "hypotheses_json": json.dumps(details.get("hypotheses", []), ensure_ascii=False),
            "attempted_fixes_json": json.dumps(details.get("attempted_fixes", []), ensure_ascii=False),
            "failed_attempts_json": json.dumps(details.get("failed_attempts", []), ensure_ascii=False),
            "created_at": _now(),
        }
        with self.store.transaction() as db:
            if not db.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
                raise NotFoundError(f"Run not found: {run_id}")
            columns = ",".join(item)
            values = ",".join(f":{name}" for name in item)
            db.execute(f"INSERT INTO debug_episodes({columns}) VALUES ({values})", item)
            self._append_event(db, run_id, "debug_episode_recorded", {"debug_episode_id": item["id"], "fingerprint": item["error_fingerprint"]})
        return item

    def complete_run(self, run_id: str) -> dict[str, Any]:
        now = _now()
        with self.store.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise NotFoundError(f"Run not found: {run_id}")
            if run["status"] != "running":
                raise InvalidTransitionError(f"Run {run_id} cannot complete from {run['status']}")
            db.execute("UPDATE runs SET status='completed', finished_at=? WHERE id=?", (now, run_id))
            db.execute("UPDATE tickets SET status='verification', updated_at=? WHERE id=?", (now, run["ticket_id"]))
            self._append_event(db, run_id, "run_completed", {})
        return self.get_run(run_id)

    def fail_run(self, run_id: str, error_code: str, message: str) -> dict[str, Any]:
        now = _now()
        with self.store.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise NotFoundError(f"Run not found: {run_id}")
            if run["status"] not in {"queued", "running"}:
                raise InvalidTransitionError(f"Run {run_id} cannot fail from {run['status']}")
            db.execute(
                "UPDATE runs SET status='failed', finished_at=?, error_code=?, error_message=? WHERE id=?",
                (now, error_code, message, run_id),
            )
            db.execute("UPDATE tickets SET status='ready', updated_at=? WHERE id=?", (now, run["ticket_id"]))
            self._append_event(db, run_id, "run_failed", {"error_code": error_code, "message": message})
        return self.get_run(run_id)

    def verify_run(self, run_id: str, *, status: str, evidence_ref: str, summary: str, verifier: str) -> dict[str, Any]:
        if status not in {"passed", "failed"}:
            raise ValueError("Verification status must be passed or failed")
        if not evidence_ref.strip() or not summary.strip():
            raise EvidenceRequiredError("Verification requires evidence_ref and summary")
        item = {
            "id": _id("VER"), "run_id": run_id, "status": status, "evidence_ref": evidence_ref.strip(),
            "summary": summary.strip(), "verifier": verifier.strip() or "unknown", "created_at": _now(),
        }
        with self.store.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise NotFoundError(f"Run not found: {run_id}")
            if run["status"] != "completed":
                raise InvalidTransitionError("Verification requires a completed Run")
            db.execute(
                "INSERT INTO verifications(id,run_id,status,evidence_ref,summary,verifier,created_at) VALUES (:id,:run_id,:status,:evidence_ref,:summary,:verifier,:created_at)", item
            )
            self._append_event(db, run_id, "verification_recorded", {"verification_id": item["id"], "status": status, "evidence_ref": evidence_ref})
        return item

    def accept_ticket(self, ticket_id: str, *, accepted_by: str, note: str = "") -> dict[str, Any]:
        if accepted_by != "Josh":
            raise AcceptanceRequiredError("Ticket acceptance requires Josh")
        now = _now()
        with self.store.transaction() as db:
            ticket = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if not ticket:
                raise NotFoundError(f"Ticket not found: {ticket_id}")
            if ticket["status"] == "accepted":
                raise InvalidTransitionError("Ticket is already accepted")
            run = db.execute("SELECT * FROM runs WHERE ticket_id=? ORDER BY rowid DESC LIMIT 1", (ticket_id,)).fetchone()
            if not run or run["status"] != "completed":
                raise AcceptanceRequiredError("Ticket acceptance requires the latest Run to be completed")
            verification = db.execute(
                "SELECT * FROM verifications WHERE run_id=? ORDER BY rowid DESC LIMIT 1", (run["id"],)
            ).fetchone()
            if not verification or verification["status"] != "passed" or not verification["evidence_ref"].strip():
                raise EvidenceRequiredError("Ticket acceptance requires passed Verification evidence")
            acceptance = {
                "id": _id("ACC"), "ticket_id": ticket_id, "run_id": run["id"],
                "verification_id": verification["id"], "accepted_by": accepted_by,
                "note": note, "created_at": now,
            }
            db.execute(
                """INSERT INTO acceptances(id,ticket_id,run_id,verification_id,accepted_by,note,created_at)
                   VALUES (:id,:ticket_id,:run_id,:verification_id,:accepted_by,:note,:created_at)""", acceptance
            )
            db.execute(
                "UPDATE tickets SET status='accepted', accepted_run_id=?, accepted_by=?, updated_at=? WHERE id=?",
                (run["id"], accepted_by, now, ticket_id),
            )
            self._append_event(db, run["id"], "ticket_accepted", {"acceptance_id": acceptance["id"], "accepted_by": accepted_by})
        return self.get_ticket(ticket_id)

    def propose_memory(self, project_id: str, source_run_id: str, *, kind: str, statement: str, scope: str, evidence_ref: str) -> dict[str, Any]:
        if kind not in {"episodic", "semantic", "procedural", "preference", "project"}:
            raise ValueError("Invalid memory kind")
        if not statement.strip() or not scope.strip() or not evidence_ref.strip():
            raise EvidenceRequiredError("Memory Candidate requires statement, scope, and evidence")
        item = {
            "id": _id("MEM"), "project_id": project_id, "source_run_id": source_run_id, "kind": kind,
            "statement": statement.strip(), "scope": scope.strip(), "evidence_ref": evidence_ref.strip(),
            "status": "pending", "created_at": _now(),
        }
        try:
            with self.store.transaction() as db:
                provenance = db.execute(
                    """SELECT tickets.project_id
                       FROM runs JOIN tickets ON tickets.id = runs.ticket_id
                       WHERE runs.id=?""",
                    (source_run_id,),
                ).fetchone()
                if not provenance:
                    raise NotFoundError(f"Source Run not found: {source_run_id}")
                if provenance["project_id"] != project_id:
                    raise InvalidTransitionError("Memory Candidate source Run must belong to the same Project")
                db.execute(
                    """INSERT INTO memory_candidates(id,project_id,source_run_id,kind,statement,scope,evidence_ref,status,created_at)
                       VALUES (:id,:project_id,:source_run_id,:kind,:statement,:scope,:evidence_ref,:status,:created_at)""", item
                )
                self._append_event(db, source_run_id, "memory_candidate_proposed", {"memory_candidate_id": item["id"], "kind": kind, "scope": scope})
        except sqlite3.IntegrityError as error:
            raise NotFoundError("Project or source Run not found") from error
        return item

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self.store.connect() as db:
            item = _row(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
        if not item:
            raise NotFoundError(f"Run not found: {run_id}")
        return item

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM events WHERE run_id=? ORDER BY sequence", (run_id,)).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]

    def list_workspaces(self) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM workspaces ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    def list_projects(self, workspace_id: str) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM projects WHERE workspace_id=? ORDER BY created_at", (workspace_id,)).fetchall()
        return [dict(r) for r in rows]

    def list_tickets(self, project_id: str) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM tickets WHERE project_id=? ORDER BY created_at", (project_id,)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["acceptance_criteria"] = json.loads(item.pop("acceptance_criteria_json"))
            result.append(item)
        return result

    def list_runs(self, ticket_id: str) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM runs WHERE ticket_id=? ORDER BY created_at", (ticket_id,)).fetchall()
        return [dict(r) for r in rows]

    def diagnose(self) -> dict[str, Any]:
        return {
            "database": str(self.store.path.resolve()),
            "database_exists": self.store.path.exists(),
            "integrity": self.store.integrity_check(),
            "schema_version": self.store.schema_version(),
        }
