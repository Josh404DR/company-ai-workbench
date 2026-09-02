from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .errors import (
    AcceptanceRequiredError,
    EvidenceRequiredError,
    InvalidTransitionError,
    NotFoundError,
    RunnerLaunchError,
    TicketImportError,
    VerifierIndependenceError,
)
from .runner import CodexCliRunner, RunnerResult, _redact
from .store import SQLiteStore


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


RISK_LEVELS = ("low", "medium", "high")
AUTO_ACCEPTOR = "auto-acceptor"
DEFAULT_MEMORY_TTL_DAYS = 90
MAX_EVIDENCE_BYTES = 1_000_000

# Fail-closed default: every risk tier needs Josh. Opt into delegation explicitly.
DEFAULT_ACCEPTANCE_AUTHORITY: dict[str, tuple[str, ...]] = {
    "low": ("Josh",), "medium": ("Josh",), "high": ("Josh",),
}
# Tiered policy: low-risk Tickets may be closed by the automated acceptor once an
# independent Verification passed; medium/high still require Josh.
TIERED_ACCEPTANCE_AUTHORITY: dict[str, tuple[str, ...]] = {
    "low": ("Josh", AUTO_ACCEPTOR), "medium": ("Josh",), "high": ("Josh",),
}

_PROVIDER_FAMILIES = (
    (re.compile(r"^(codex|openai|gpt|o[0-9])", re.I), "openai"),
    (re.compile(r"^(gemini|google)", re.I), "google"),
    (re.compile(r"^(claude|anthropic)", re.I), "anthropic"),
    (re.compile(r"^(human|josh)$", re.I), "human"),
    (re.compile(r"^(local-command|local)$", re.I), "local-command"),
)


def provider_of(name: str | None) -> str:
    """Collapse a runner/verifier label onto its provider family for Invariant 11 comparison.

    'codex-cli', 'codex', 'gpt-4o' -> 'openai'; 'gemini-2.5-flash' -> 'google';
    'claude-code' -> 'anthropic'; 'human'/'Josh' -> 'human'; anything else is its own family
    (so 'fake' vs 'fake' is still a collision, which is the safe reading).
    """
    label = (name or "").strip()
    if not label:
        return ""
    for pattern, family in _PROVIDER_FAMILIES:
        if pattern.match(label):
            return family
    return label.lower()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sanitize_label(value: str | None) -> str | None:
    """Run secret-shaped substrings through the same redaction used for Runner stdout/stderr.

    provider_account is a free-text label (e.g. 'acct-A'), not a credential, but nothing stops a
    caller from pasting a real key into it; Invariant 10 forbids secrets in diagnostics, so this is
    the last line of defense before the value ever reaches the database or a diagnose() report.
    """
    if value is None:
        return None
    return _redact(value)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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

    def __init__(
        self,
        database_path: str | Path,
        *,
        auto_reconcile: bool = False,
        acceptance_authority: Mapping[str, Sequence[str]] | None = None,
        pricing: Mapping[str, tuple[float, float]] | None = None,
        memory_ttl_days: int = DEFAULT_MEMORY_TTL_DAYS,
    ):
        """
        acceptance_authority: risk_level -> allowed `accepted_by` identities. Defaults to Josh for
            every tier (DEFAULT_ACCEPTANCE_AUTHORITY); pass TIERED_ACCEPTANCE_AUTHORITY to let the
            automated acceptor close low-risk Tickets.
        pricing: runner-or-model label -> (usd per 1M input tokens, usd per 1M output tokens).
            Without an entry, cost_usd stays NULL; token counts are still recorded.
        memory_ttl_days: default lifetime of an approved memory when the reviewer gives no expiry.
        """
        self.store = SQLiteStore(database_path)
        authority = dict(acceptance_authority or DEFAULT_ACCEPTANCE_AUTHORITY)
        for level in RISK_LEVELS:
            if level not in authority or not tuple(authority[level]):
                raise ValueError(f"acceptance_authority must list at least one acceptor for risk level {level!r}")
            if level != "low" and AUTO_ACCEPTOR in authority[level]:
                raise ValueError("Automated acceptance is only permitted for low-risk Tickets")
        self.acceptance_authority = {level: tuple(authority[level]) for level in RISK_LEVELS}
        self.pricing = dict(pricing or {})
        if memory_ttl_days <= 0:
            raise ValueError("memory_ttl_days must be positive")
        self.memory_ttl_days = memory_ttl_days
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

    def create_ticket(
        self, project_id: str, title: str, goal: str, acceptance_criteria: list[str], *, risk_level: str = "high",
    ) -> dict[str, Any]:
        """risk_level is fixed at creation (default 'high' = Josh-only acceptance). There is
        deliberately no setter: lowering risk after the fact would be an acceptance bypass."""
        item = self._ticket_row(project_id, title, goal, acceptance_criteria, risk_level)
        try:
            with self.store.transaction() as db:
                self._insert_ticket(db, item)
        except sqlite3.IntegrityError as error:
            raise NotFoundError(f"Project not found: {project_id}") from error
        return self.get_ticket(item["id"])

    @staticmethod
    def _ticket_row(project_id: str, title: str, goal: str, acceptance_criteria: list[str], risk_level: str) -> dict[str, Any]:
        criteria = [str(value).strip() for value in acceptance_criteria if str(value).strip()]
        if not title.strip() or not goal.strip() or not criteria:
            raise ValueError("Ticket requires title, goal, and acceptance criteria")
        if risk_level not in RISK_LEVELS:
            raise ValueError(f"Ticket risk_level must be one of {', '.join(RISK_LEVELS)}")
        now = _now()
        return {
            "id": _id("TKT"), "project_id": project_id, "title": title.strip(), "goal": goal.strip(),
            "acceptance_criteria_json": json.dumps(criteria, ensure_ascii=False), "status": "ready",
            "risk_level": risk_level, "created_at": now, "updated_at": now,
        }

    @staticmethod
    def _insert_ticket(db: sqlite3.Connection, item: dict[str, Any]) -> None:
        db.execute(
            """INSERT INTO tickets(id,project_id,title,goal,acceptance_criteria_json,status,risk_level,created_at,updated_at)
               VALUES (:id,:project_id,:title,:goal,:acceptance_criteria_json,:status,:risk_level,:created_at,:updated_at)""", item
        )

    def import_tickets(self, project_id: str, source: str | Path, *, default_risk_level: str = "high") -> list[dict[str, Any]]:
        """Batch-create Tickets from a JSON or Markdown file. All-or-nothing: any invalid entry,
        duplicate title inside the file, or title already present in the Project aborts the import.

        JSON: a list of objects {title, goal, acceptance_criteria: [...], risk_level?}.
        Markdown: one Ticket per `## Heading`; `Goal:` / `Risk:` lines; `- ` bullets are criteria.
        """
        path = Path(source)
        if not path.is_file():
            raise TicketImportError(f"Import source not found: {path}")
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() == ".json":
            specs = self._parse_ticket_json(text)
        else:
            specs = self._parse_ticket_markdown(text)
        if not specs:
            raise TicketImportError("Import source contains no Tickets")
        rows = []
        seen: set[str] = set()
        for index, spec in enumerate(specs, start=1):
            try:
                row = self._ticket_row(
                    project_id, str(spec.get("title", "")), str(spec.get("goal", "")),
                    list(spec.get("acceptance_criteria") or []), str(spec.get("risk_level") or default_risk_level),
                )
            except ValueError as error:
                raise TicketImportError(f"Ticket #{index} invalid: {error}") from error
            key = row["title"].casefold()
            if key in seen:
                raise TicketImportError(f"Duplicate title inside import: {row['title']!r}")
            seen.add(key)
            rows.append(row)
        with self.store.transaction() as db:
            if not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise NotFoundError(f"Project not found: {project_id}")
            existing = {
                str(r[0]).casefold() for r in db.execute("SELECT title FROM tickets WHERE project_id=?", (project_id,))
            }
            clashes = [row["title"] for row in rows if row["title"].casefold() in existing]
            if clashes:
                raise TicketImportError(f"Titles already exist in Project: {', '.join(clashes)}")
            for row in rows:
                self._insert_ticket(db, row)
        return [self.get_ticket(row["id"]) for row in rows]

    @staticmethod
    def _parse_ticket_json(text: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(text)
        except ValueError as error:
            raise TicketImportError(f"Invalid JSON: {error}") from error
        if isinstance(data, dict) and isinstance(data.get("tickets"), list):
            data = data["tickets"]
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise TicketImportError("JSON import must be a list of Ticket objects")
        return data

    @staticmethod
    def _parse_ticket_markdown(text: str) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("## "):
                current = {"title": line[3:].strip(), "goal": "", "acceptance_criteria": [], "risk_level": None}
                specs.append(current)
                continue
            if current is None or not line:
                continue
            lowered = line.lower()
            separator = ":" if ":" in line else "："
            if lowered.startswith(("goal:", "目標:", "目標：")):
                current["goal"] = line.split(separator, 1)[1].strip()
            elif lowered.startswith(("risk:", "風險:", "風險：")):
                current["risk_level"] = line.split(separator, 1)[1].strip().lower()
            elif line.startswith(("- ", "* ")):
                item = line[2:].strip()
                for box in ("[ ]", "[x]", "[X]"):
                    if item.startswith(box):
                        item = item[len(box):].strip()
                current["acceptance_criteria"].append(item)
        return specs

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
        provider_account: str | None = None,
        keep_worktree: bool = False,
    ) -> dict[str, Any]:
        """Route a Ticket through the verified Runner boundary and record its full lifecycle.

        With isolate_worktree, the Run's changes are committed onto its `wb-run/<run>` branch at
        finalization and the worktree directory is removed (unless keep_worktree), so the work
        product survives as auditable git history without leaving directories behind.
        """
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
            provider_account=provider_account,
            runner_label=model or runner_name,
            keep_worktree=keep_worktree,
        )
        return self.get_run(run["id"])

    def _finalize_managed_run(
        self,
        run_id: str,
        result: RunnerResult,
        *,
        worktree_env: Any | None = None,
        verification_command: str | None = None,
        provider_account: str | None = None,
        runner_label: str | None = None,
        keep_worktree: bool = False,
    ) -> dict[str, Any]:
        now = _now()
        verification_result = None
        if worktree_env and verification_command and result.outcome == "completed":
            verification_result = worktree_env.run_verification(verification_command)
        usage = result.usage or {}
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")

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
            if usage:
                output_payload["usage"] = usage

            self._append_event(db, run_id, "invocation_output", output_payload)
            cost = self._cost_for(runner_label or run["runner"], input_tokens, output_tokens)
            db.execute(
                "UPDATE runs SET input_tokens=?, output_tokens=?, cost_usd=?, provider_account=? WHERE id=?",
                (input_tokens, output_tokens, cost, _sanitize_label(provider_account), run_id),
            )

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

                    # If auto-verification passed, record content-addressed verification evidence.
                    # The verifier is the local command, which is independent of every model
                    # provider, so Invariant 11 holds by construction.
                    if verification_result and verification_result["passed"]:
                        v_summary = f"Automated test passed: {verification_command}"
                        v_evidence = f"exit 0 in {verification_result['duration_seconds']}s"
                        evidence_bytes = json.dumps(verification_result, ensure_ascii=False, sort_keys=True).encode("utf-8")
                        verification = self._insert_verification(
                            db, run_id, status="passed", evidence_ref=v_evidence, summary=v_summary,
                            verifier="auto-verifier", verifier_provider="local-command",
                            evidence_content=evidence_bytes, builder_runner=run["runner"], automated=True,
                        )
                        ticket = db.execute("SELECT * FROM tickets WHERE id=?", (run["ticket_id"],)).fetchone()
                        if ticket["risk_level"] == "low" and AUTO_ACCEPTOR in self.acceptance_authority["low"]:
                            self._insert_acceptance(
                                db, ticket, run, verification, accepted_by=AUTO_ACCEPTOR,
                                note=f"Automated low-risk acceptance on {verification['id']}", automated=True,
                            )

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

        if worktree_env:
            self._retire_worktree(run_id, worktree_env, keep_directory=keep_worktree)
        return self.get_run(run_id)

    def _retire_worktree(self, run_id: str, worktree_env: Any, *, keep_directory: bool) -> dict[str, Any]:
        """Preserve the Run's work product on its branch, then drop the directory.

        Runs after the terminal transaction so a persistence failure never loses the files, and
        records its own Event so the branch/commit is discoverable from the audit trail.
        """
        outcome: dict[str, Any] = {"branch_name": worktree_env.branch_name, "commit": None, "directory_removed": False}
        try:
            outcome["commit"] = worktree_env.commit_all(f"workbench: preserve output of {run_id}")
        except Exception as error:
            outcome["commit_error"] = str(error)
        if not keep_directory and "commit_error" not in outcome:
            worktree_env.cleanup()
            outcome["directory_removed"] = not worktree_env.worktree_path.exists()
        with self.store.transaction() as db:
            self._append_event(db, run_id, "worktree_retired", outcome)
        return outcome

    def prune_worktrees(self, repo_root: str | Path) -> list[dict[str, Any]]:
        """Retire every leftover Run worktree whose Run is already terminal (or unknown to this
        database). Work is committed onto the Run branch before the directory goes, so nothing is
        lost; Runs still 'running' are left alone."""
        from .worktree import GitWorktreeManager

        manager = GitWorktreeManager(repo_root)
        pruned: list[dict[str, Any]] = []
        with self.store.connect() as db:
            statuses = {row["id"]: row["status"] for row in db.execute("SELECT id, status FROM runs")}
        for env in manager.list_run_worktrees():
            status = statuses.get(env.run_id)
            if status == "running":
                continue
            entry: dict[str, Any] = {"run_id": env.run_id, "run_status": status, "branch_name": env.branch_name}
            try:
                entry["commit"] = env.commit_all(f"workbench: preserve output of {env.run_id} (prune)")
            except Exception as error:
                entry["commit_error"] = str(error)
                pruned.append(entry)
                continue
            env.cleanup()
            entry["directory_removed"] = not env.worktree_path.exists()
            if status is not None:
                with self.store.transaction() as db:
                    self._append_event(db, env.run_id, "worktree_retired", {**entry, "pruned": True})
            pruned.append(entry)
        return pruned

    def _cost_for(self, label: str | None, input_tokens: int | None, output_tokens: int | None) -> float | None:
        if input_tokens is None and output_tokens is None:
            return None
        price = self.pricing.get(label or "") or self.pricing.get(provider_of(label))
        if not price:
            return None
        per_in, per_out = price
        return round(((input_tokens or 0) * per_in + (output_tokens or 0) * per_out) / 1_000_000, 6)

    def record_run_usage(
        self, run_id: str, *, input_tokens: int | None = None, output_tokens: int | None = None,
        cost_usd: float | None = None, provider_account: str | None = None,
    ) -> dict[str, Any]:
        """Attach token/cost evidence to a Run that the Runner could not report itself."""
        for name, value in (("input_tokens", input_tokens), ("output_tokens", output_tokens)):
            if value is not None and (isinstance(value, bool) or int(value) < 0):
                raise ValueError(f"{name} must be a non-negative integer")
        with self.store.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise NotFoundError(f"Run not found: {run_id}")
            if cost_usd is None:
                cost_usd = self._cost_for(run["runner"], input_tokens, output_tokens)
            clean_account = _sanitize_label(provider_account)
            db.execute(
                "UPDATE runs SET input_tokens=COALESCE(?,input_tokens), output_tokens=COALESCE(?,output_tokens), "
                "cost_usd=COALESCE(?,cost_usd), provider_account=COALESCE(?,provider_account) WHERE id=?",
                (input_tokens, output_tokens, cost_usd, clean_account, run_id),
            )
            self._append_event(db, run_id, "usage_recorded", {
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "cost_usd": cost_usd, "provider_account": clean_account,
            })
        return self.get_run(run_id)

    def usage_summary(self) -> dict[str, Any]:
        """Token and cost totals per runner, from Run rows (never from Event payloads)."""
        with self.store.connect() as db:
            rows = db.execute(
                """SELECT runner, COUNT(*) AS runs,
                          SUM(COALESCE(input_tokens,0)) AS input_tokens,
                          SUM(COALESCE(output_tokens,0)) AS output_tokens,
                          SUM(COALESCE(cost_usd,0.0)) AS cost_usd,
                          SUM(CASE WHEN input_tokens IS NULL AND output_tokens IS NULL THEN 1 ELSE 0 END) AS runs_without_usage
                   FROM runs GROUP BY runner ORDER BY runner"""
            ).fetchall()
        return {row["runner"]: {k: row[k] for k in row.keys() if k != "runner"} for row in rows}

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

    def verify_run(
        self,
        run_id: str,
        *,
        status: str,
        evidence_ref: str,
        summary: str,
        verifier: str,
        verifier_provider: str,
        evidence_content: str | bytes | None = None,
        evidence_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Record a Verification with content-addressed evidence.

        evidence_ref stays a human label; the actual evidence (text/bytes or a file) is stored in
        the append-only evidence_artifacts table under its sha256, which the Verification pins.
        verifier_provider names who/what verified (e.g. 'human', 'anthropic', 'local-command') and
        must differ from the Run's builder provider (Invariant 11).
        """
        if status not in {"passed", "failed"}:
            raise ValueError("Verification status must be passed or failed")
        if not evidence_ref.strip() or not summary.strip():
            raise EvidenceRequiredError("Verification requires evidence_ref and summary")
        if evidence_content is not None and evidence_path is not None:
            raise ValueError("Give evidence_content or evidence_path, not both")
        if evidence_path is not None:
            path = Path(evidence_path)
            if not path.is_file():
                raise EvidenceRequiredError(f"Evidence file not found: {path}")
            content = path.read_bytes()
        elif isinstance(evidence_content, str):
            content = evidence_content.encode("utf-8")
        else:
            content = evidence_content
        if not content or not content.strip():
            raise EvidenceRequiredError("Verification requires evidence content (text, bytes, or a file) so it can be hashed")
        with self.store.transaction() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run:
                raise NotFoundError(f"Run not found: {run_id}")
            if run["status"] != "completed":
                raise InvalidTransitionError("Verification requires a completed Run")
            item = self._insert_verification(
                db, run_id, status=status, evidence_ref=evidence_ref, summary=summary, verifier=verifier,
                verifier_provider=verifier_provider, evidence_content=content, builder_runner=run["runner"],
            )
        return item

    def _insert_verification(
        self, db: sqlite3.Connection, run_id: str, *, status: str, evidence_ref: str, summary: str, verifier: str,
        verifier_provider: str, evidence_content: bytes, builder_runner: str, automated: bool = False,
    ) -> dict[str, Any]:
        provider = verifier_provider.strip()
        if not provider:
            raise VerifierIndependenceError("Verification requires verifier_provider")
        if provider_of(provider) == provider_of(builder_runner):
            raise VerifierIndependenceError(
                f"Verifier provider {provider!r} is the same family as builder runner {builder_runner!r}; "
                "Invariant 11 requires an independent verifier"
            )
        if len(evidence_content) > MAX_EVIDENCE_BYTES:
            raise EvidenceRequiredError(f"Evidence exceeds {MAX_EVIDENCE_BYTES} bytes; attach a digest or excerpt instead")
        sha = self._store_evidence(db, evidence_content)
        item = {
            "id": _id("VER"), "run_id": run_id, "status": status, "evidence_ref": evidence_ref.strip(),
            "summary": summary.strip(), "verifier": verifier.strip() or "unknown", "created_at": _now(),
            "verifier_provider": provider, "evidence_sha256": sha,
        }
        db.execute(
            """INSERT INTO verifications(id,run_id,status,evidence_ref,summary,verifier,created_at,verifier_provider,evidence_sha256)
               VALUES (:id,:run_id,:status,:evidence_ref,:summary,:verifier,:created_at,:verifier_provider,:evidence_sha256)""", item
        )
        self._append_event(db, run_id, "verification_recorded", {
            "verification_id": item["id"], "status": status, "evidence_ref": item["evidence_ref"],
            "evidence_sha256": sha, "verifier_provider": provider, "automated": automated,
        })
        return item

    @staticmethod
    def _store_evidence(db: sqlite3.Connection, content: bytes) -> str:
        sha = _sha256(content)
        db.execute(
            "INSERT OR IGNORE INTO evidence_artifacts(sha256,content,byte_size,created_at) VALUES (?,?,?,?)",
            (sha, content, len(content), _now()),
        )
        return sha

    def get_evidence(self, sha256: str) -> bytes:
        with self.store.connect() as db:
            row = db.execute("SELECT content FROM evidence_artifacts WHERE sha256=?", (sha256,)).fetchone()
        if not row:
            raise NotFoundError(f"Evidence artifact not found: {sha256}")
        return bytes(row["content"])

    def check_evidence_integrity(self) -> dict[str, Any]:
        """Recompute every artifact hash and confirm every hashed Verification still resolves.
        A mismatch means the database was edited outside the engine."""
        mismatched: list[str] = []
        dangling: list[str] = []
        with self.store.connect() as db:
            for row in db.execute("SELECT sha256, content FROM evidence_artifacts"):
                if _sha256(bytes(row["content"])) != row["sha256"]:
                    mismatched.append(row["sha256"])
            for row in db.execute(
                """SELECT v.id FROM verifications v
                   WHERE v.evidence_sha256 IS NOT NULL
                     AND NOT EXISTS (SELECT 1 FROM evidence_artifacts a WHERE a.sha256 = v.evidence_sha256)"""
            ):
                dangling.append(row["id"])
            artifacts = db.execute("SELECT COUNT(*) FROM evidence_artifacts").fetchone()[0]
            unhashed = db.execute("SELECT COUNT(*) FROM verifications WHERE evidence_sha256 IS NULL").fetchone()[0]
        return {
            "artifacts": artifacts, "mismatched": mismatched, "dangling_verifications": dangling,
            "legacy_unhashed_verifications": unhashed, "ok": not mismatched and not dangling,
        }

    def accept_ticket(self, ticket_id: str, *, accepted_by: str, note: str = "") -> dict[str, Any]:
        with self.store.transaction() as db:
            ticket = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if not ticket:
                raise NotFoundError(f"Ticket not found: {ticket_id}")
            if ticket["status"] == "accepted":
                raise InvalidTransitionError("Ticket is already accepted")
            allowed = self.acceptance_authority.get(ticket["risk_level"], ("Josh",))
            if accepted_by not in allowed:
                raise AcceptanceRequiredError(
                    f"Ticket acceptance for risk level {ticket['risk_level']!r} requires one of: {', '.join(allowed)}"
                )
            run = db.execute("SELECT * FROM runs WHERE ticket_id=? ORDER BY rowid DESC LIMIT 1", (ticket_id,)).fetchone()
            if not run or run["status"] != "completed":
                raise AcceptanceRequiredError("Ticket acceptance requires the latest Run to be completed")
            verification = db.execute(
                "SELECT * FROM verifications WHERE run_id=? ORDER BY rowid DESC LIMIT 1", (run["id"],)
            ).fetchone()
            if not verification or verification["status"] != "passed" or not verification["evidence_ref"].strip():
                raise EvidenceRequiredError("Ticket acceptance requires passed Verification evidence")
            self._insert_acceptance(db, ticket, run, verification, accepted_by=accepted_by, note=note, automated=False)
        return self.get_ticket(ticket_id)

    def _insert_acceptance(
        self, db: sqlite3.Connection, ticket: sqlite3.Row, run: sqlite3.Row, verification: Mapping[str, Any], *,
        accepted_by: str, note: str, automated: bool,
    ) -> dict[str, Any]:
        """Shared gate for manual and automated acceptance. Re-checks verifier independence and
        evidence integrity against the pinned Verification so a legacy or tampered row can never
        back a new Acceptance."""
        provider = verification["verifier_provider"]
        if not provider:
            raise VerifierIndependenceError("Pinned Verification has no verifier_provider; re-verify with an independent verifier")
        if provider_of(provider) == provider_of(run["runner"]):
            raise VerifierIndependenceError("Pinned Verification is not independent of the builder provider")
        sha = verification["evidence_sha256"]
        if not sha:
            raise EvidenceRequiredError("Pinned Verification has no hashed evidence; re-verify with evidence content")
        artifact = db.execute("SELECT content FROM evidence_artifacts WHERE sha256=?", (sha,)).fetchone()
        if not artifact or _sha256(bytes(artifact["content"])) != sha:
            raise EvidenceRequiredError("Pinned Verification evidence is missing or does not match its hash")
        now = _now()
        acceptance = {
            "id": _id("ACC"), "ticket_id": ticket["id"], "run_id": run["id"],
            "verification_id": verification["id"], "accepted_by": accepted_by,
            "note": note, "created_at": now,
        }
        db.execute(
            """INSERT INTO acceptances(id,ticket_id,run_id,verification_id,accepted_by,note,created_at)
               VALUES (:id,:ticket_id,:run_id,:verification_id,:accepted_by,:note,:created_at)""", acceptance
        )
        db.execute(
            "UPDATE tickets SET status='accepted', accepted_run_id=?, accepted_by=?, updated_at=? WHERE id=?",
            (run["id"], accepted_by, now, ticket["id"]),
        )
        self._append_event(db, run["id"], "ticket_accepted", {
            "acceptance_id": acceptance["id"], "accepted_by": accepted_by,
            "risk_level": ticket["risk_level"], "evidence_sha256": sha, "automated": automated,
        })
        return acceptance

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

    def get_memory(self, memory_id: str) -> dict[str, Any]:
        with self.store.connect() as db:
            item = _row(db.execute("SELECT * FROM memory_candidates WHERE id=?", (memory_id,)).fetchone())
        if not item:
            raise NotFoundError(f"Memory Candidate not found: {memory_id}")
        return item

    def list_memories(self, project_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            if status:
                rows = db.execute(
                    "SELECT * FROM memory_candidates WHERE project_id=? AND status=? ORDER BY created_at",
                    (project_id, status),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM memory_candidates WHERE project_id=? ORDER BY created_at",
                    (project_id,),
                ).fetchall()
        return [dict(r) for r in rows]

    def review_memory(
        self, memory_id: str, *, action: str, reviewed_by: str, note: str = "",
        expires_at: str | datetime | None = None, ttl_days: int | None = None, source_commit: str | None = None,
    ) -> dict[str, Any]:
        """Approve/reject/disable a candidate. Approval always carries an expiry (explicit
        expires_at, ttl_days, or the engine default) and optionally the commit it was learned
        against, so an approved rule cannot silently outlive the code it describes. Renewing an
        expired memory is an ordinary `approve` with a fresh expiry."""
        if action not in {"approve", "reject", "disable"}:
            raise ValueError("Memory review action must be approve, reject, or disable")
        if reviewed_by != "Josh":
            raise AcceptanceRequiredError("Memory candidate promotion requires Josh")
        if expires_at is not None and ttl_days is not None:
            raise ValueError("Give expires_at or ttl_days, not both")
        if ttl_days is not None and (isinstance(ttl_days, bool) or not isinstance(ttl_days, int)):
            raise ValueError("ttl_days must be an int")

        new_status = {"approve": "approved", "reject": "rejected", "disable": "disabled"}[action]
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="milliseconds")
        expiry: str | None = None
        if action == "approve":
            if isinstance(expires_at, datetime):
                expiry_dt = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
            elif isinstance(expires_at, str):
                expiry_dt = _parse_time(expires_at)
            else:
                days = self.memory_ttl_days if ttl_days is None else ttl_days
                if days <= 0:
                    raise ValueError("ttl_days must be positive")
                expiry_dt = now_dt + timedelta(days=days)
            if expiry_dt <= now_dt:
                raise ValueError("Memory expiry must be in the future")
            expiry = expiry_dt.isoformat(timespec="milliseconds")

        with self.store.transaction() as db:
            mem = db.execute("SELECT * FROM memory_candidates WHERE id=?", (memory_id,)).fetchone()
            if not mem:
                raise NotFoundError(f"Memory Candidate not found: {memory_id}")
            if mem["status"] == new_status:
                raise InvalidTransitionError(f"Memory Candidate is already {new_status}")
            if action == "approve":
                db.execute(
                    "UPDATE memory_candidates SET status=?, approved_at=?, expires_at=?, source_commit=?, reviewed_by=? WHERE id=?",
                    (new_status, now, expiry, (source_commit or "").strip() or None, reviewed_by, memory_id),
                )
            else:
                db.execute(
                    "UPDATE memory_candidates SET status=?, reviewed_by=? WHERE id=?",
                    (new_status, reviewed_by, memory_id),
                )
            self._append_event(db, mem["source_run_id"], "memory_candidate_reviewed", {
                "memory_id": memory_id, "action": action, "status": new_status,
                "reviewed_by": reviewed_by, "note": note, "expires_at": expiry, "source_commit": source_commit,
            })
        return self.get_memory(memory_id)

    def expire_memories(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """Sweep approved memories past their expiry into 'expired' with an audit Event.
        Active-context injection already excludes them by time, so the sweep only makes the
        state explicit; it is idempotent."""
        current = (now or datetime.now(timezone.utc))
        current = current if current.tzinfo else current.replace(tzinfo=timezone.utc)
        stamp = current.isoformat(timespec="milliseconds")
        expired: list[dict[str, Any]] = []
        with self.store.transaction() as db:
            rows = db.execute(
                "SELECT * FROM memory_candidates WHERE status='approved' AND expires_at IS NOT NULL"
            ).fetchall()
            for mem in rows:
                if _parse_time(mem["expires_at"]) > current:
                    continue
                db.execute("UPDATE memory_candidates SET status='expired' WHERE id=?", (mem["id"],))
                self._append_event(db, mem["source_run_id"], "memory_candidate_expired", {
                    "memory_id": mem["id"], "expires_at": mem["expires_at"], "swept_at": stamp,
                })
                expired.append({"memory_id": mem["id"], "expires_at": mem["expires_at"]})
        return expired

    def get_project_active_context(self, project_id: str, *, now: datetime | None = None) -> str:
        """Approved, unexpired memories for a project formatted as instructions. Each line carries
        its age and expiry so the consumer can see how stale a rule is."""
        current = (now or datetime.now(timezone.utc))
        current = current if current.tzinfo else current.replace(tzinfo=timezone.utc)
        memories = [
            m for m in self.list_memories(project_id, status="approved")
            if not m.get("expires_at") or _parse_time(m["expires_at"]) > current
        ]
        if not memories:
            return ""
        lines = ["# Project Memory & Learned Rules (Approved):"]
        for m in memories:
            provenance = []
            if m.get("approved_at"):
                provenance.append(f"approved {m['approved_at'][:10]}")
            else:
                provenance.append("approved: unknown date (legacy)")
            provenance.append(f"expires {m['expires_at'][:10]}" if m.get("expires_at") else "no expiry (legacy)")
            if m.get("source_commit"):
                provenance.append(f"commit {m['source_commit'][:12]}")
            lines.append(
                f"- [{m['kind'].upper()}] {m['statement']} (Scope: {m['scope']}, Ref: {m['evidence_ref']}; {', '.join(provenance)})"
            )
        return "\n".join(lines)

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

    def diagnose(self, *, repo_root: str | Path | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with self.store.connect() as db:
            approved = db.execute("SELECT expires_at FROM memory_candidates WHERE status='approved'").fetchall()
            running = db.execute("SELECT COUNT(*) FROM runs WHERE status='running'").fetchone()[0]
            tickets_by_risk = {
                row["risk_level"]: row["n"]
                for row in db.execute("SELECT risk_level, COUNT(*) AS n FROM tickets GROUP BY risk_level")
            }
        expired_pending_sweep = sum(
            1 for row in approved if row["expires_at"] and _parse_time(row["expires_at"]) <= now
        )
        report: dict[str, Any] = {
            "database": str(self.store.path.resolve()),
            "database_exists": self.store.path.exists(),
            "integrity": self.store.integrity_check(),
            "schema_version": self.store.schema_version(),
            "acceptance_authority": {k: list(v) for k, v in self.acceptance_authority.items()},
            "tickets_by_risk": tickets_by_risk,
            "runs_still_running": running,
            "evidence": self.check_evidence_integrity(),
            "memory": {"approved": len(approved), "expired_pending_sweep": expired_pending_sweep},
            "usage": self.usage_summary(),
        }
        if repo_root is not None:
            report["worktrees"] = self.orphan_worktrees(repo_root)
        return report

    def orphan_worktrees(self, repo_root: str | Path) -> list[dict[str, Any]]:
        """Run worktree directories whose Run is terminal or unknown: candidates for prune_worktrees()."""
        from .worktree import GitWorktreeManager

        try:
            manager = GitWorktreeManager(repo_root)
        except Exception as error:
            return [{"error": str(error)}]
        with self.store.connect() as db:
            statuses = {row["id"]: row["status"] for row in db.execute("SELECT id, status FROM runs")}
        return [
            {"run_id": env.run_id, "run_status": statuses.get(env.run_id), "path": str(env.worktree_path)}
            for env in manager.list_run_worktrees()
            if statuses.get(env.run_id) != "running"
        ]
