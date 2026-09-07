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
NODE_LAYERS = ("architecture", "logic", "memory", "milestone", "task")
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
# Who may approve/reject/disable a Memory Candidate. Invariant 6 requires "never self-promote",
# not "must literally be the string Josh forever" -- flat (no risk tiers, unlike acceptance).
DEFAULT_MEMORY_REVIEW_AUTHORITY: tuple[str, ...] = ("Josh",)

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
        memory_review_authority: Sequence[str] | None = None,
        pricing: Mapping[str, tuple[float, float]] | None = None,
        memory_ttl_days: int = DEFAULT_MEMORY_TTL_DAYS,
    ):
        """
        acceptance_authority: risk_level -> allowed `accepted_by` identities. Defaults to Josh for
            every tier (DEFAULT_ACCEPTANCE_AUTHORITY); pass TIERED_ACCEPTANCE_AUTHORITY to let the
            automated acceptor close low-risk Tickets.
        memory_review_authority: allowed `reviewed_by` identities for `review_memory()`. Defaults
            to Josh only (DEFAULT_MEMORY_REVIEW_AUTHORITY). Previously this was a bare
            `if reviewed_by != "Josh"` hardcoded in review_memory() itself -- inconsistent with
            acceptance_authority's configurability for no real reason, since Invariant 6 only
            requires "never self-promote", not "must literally be Josh forever".
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
        memory_reviewers = tuple(memory_review_authority) if memory_review_authority is not None else DEFAULT_MEMORY_REVIEW_AUTHORITY
        if not memory_reviewers:
            raise ValueError("memory_review_authority must list at least one reviewer")
        self.memory_review_authority = memory_reviewers
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
        result = dict(item)
        result["is_archived"] = False
        return result

    def create_ticket(
        self,
        project_id: str,
        title: str,
        goal: str,
        acceptance_criteria: list[str],
        *,
        risk_level: str = "high",
        goal_id: str | None = None,
        depends_on_ticket_id: str | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        """risk_level is fixed at creation (default 'high' = Josh-only acceptance). There is
        deliberately no setter: lowering risk after the fact would be an acceptance bypass."""
        item = self._ticket_row(
            project_id,
            title,
            goal,
            acceptance_criteria,
            risk_level,
            goal_id=goal_id,
            depends_on_ticket_id=depends_on_ticket_id,
            node_id=node_id,
        )
        try:
            with self.store.transaction() as db:
                self._validate_goal_and_dependency(
                    db, project_id, item["id"], goal_id, depends_on_ticket_id, node_id=node_id
                )
                self._insert_ticket(db, item)
        except sqlite3.IntegrityError as error:
            raise NotFoundError(f"Project not found: {project_id}") from error
        return self.get_ticket(item["id"])

    @staticmethod
    def _validate_goal_and_dependency(
        db: sqlite3.Connection,
        project_id: str,
        ticket_id: str | None,
        goal_id: str | None,
        depends_on_ticket_id: str | None,
        node_id: str | None = None,
    ) -> None:
        if depends_on_ticket_id and not goal_id:
            raise ValueError("Ticket dependencies require a Goal; goal_id is mandatory when depends_on_ticket_id is specified")

        if goal_id:
            goal = db.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
            if not goal:
                raise NotFoundError(f"Goal not found: {goal_id}")
            if goal["project_id"] != project_id:
                raise ValueError("Ticket and Goal must belong to the same Project")

        if node_id:
            node = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
            if not node:
                raise NotFoundError(f"Node not found: {node_id}")
            if node["project_id"] != project_id:
                raise ValueError("Ticket and Node must belong to the same Project")
            if goal_id and node["goal_id"] and node["goal_id"] != goal_id:
                raise ValueError("Ticket Goal and Node Goal must match")

        if depends_on_ticket_id:
            dep = db.execute("SELECT * FROM tickets WHERE id=?", (depends_on_ticket_id,)).fetchone()
            if not dep:
                raise NotFoundError(f"Dependency Ticket not found: {depends_on_ticket_id}")
            if ticket_id and dep["id"] == ticket_id:
                raise ValueError("Ticket cannot depend on itself")
            if dep["project_id"] != project_id:
                raise ValueError("Dependency Ticket must belong to the same Project")
            if goal_id and dep["goal_id"] != goal_id:
                raise ValueError("Dependency Ticket must belong to the same Goal")

            # Detect dependency cycles (e.g. A -> B -> A)
            if ticket_id:
                visited = {ticket_id, dep["id"]}
                curr_dep_id = dep["depends_on_ticket_id"]
                while curr_dep_id:
                    if curr_dep_id == ticket_id:
                        raise ValueError(f"Circular dependency detected between ticket {ticket_id} and {depends_on_ticket_id}")
                    if curr_dep_id in visited:
                        break
                    visited.add(curr_dep_id)
                    curr_row = db.execute("SELECT depends_on_ticket_id FROM tickets WHERE id=?", (curr_dep_id,)).fetchone()
                    curr_dep_id = curr_row["depends_on_ticket_id"] if curr_row else None

    @staticmethod
    def _ticket_row(
        project_id: str,
        title: str,
        goal: str,
        acceptance_criteria: list[str],
        risk_level: str,
        goal_id: str | None = None,
        depends_on_ticket_id: str | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        criteria = [str(value).strip() for value in acceptance_criteria if str(value).strip()]
        if not title.strip() or not goal.strip() or not criteria:
            raise ValueError("Ticket requires title, goal, and acceptance criteria")
        if risk_level not in RISK_LEVELS:
            raise ValueError(f"Ticket risk_level must be one of {', '.join(RISK_LEVELS)}")
        now = _now()
        return {
            "id": _id("TKT"),
            "project_id": project_id,
            "title": title.strip(),
            "goal": goal.strip(),
            "acceptance_criteria_json": json.dumps(criteria, ensure_ascii=False),
            "status": "ready",
            "risk_level": risk_level,
            "goal_id": goal_id,
            "depends_on_ticket_id": depends_on_ticket_id,
            "node_id": node_id,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def _insert_ticket(db: sqlite3.Connection, item: dict[str, Any]) -> None:
        db.execute(
            """INSERT INTO tickets(id,project_id,title,goal,acceptance_criteria_json,status,risk_level,goal_id,depends_on_ticket_id,node_id,created_at,updated_at)
               VALUES (:id,:project_id,:title,:goal,:acceptance_criteria_json,:status,:risk_level,:goal_id,:depends_on_ticket_id,:node_id,:created_at,:updated_at)""",
            item,
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
        auto_accept: bool = True,
    ) -> dict[str, Any]:
        """Route a Ticket through the verified Runner boundary and record its full lifecycle.

        With isolate_worktree, the Run's changes are committed onto its `wb-run/<run>` branch at
        finalization and the worktree directory is removed (unless keep_worktree), so the work
        product survives as auditable git history without leaving directories behind.
        """
        ticket = self.get_ticket(ticket_id)
        if ticket["status"] != "ready":
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
                if current["status"] != "ready":
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
            cwd=target_cwd,
            provider_account=provider_account,
            runner_label=model or runner_name,
            keep_worktree=keep_worktree,
            auto_accept=auto_accept,
        )
        return self.get_run(run["id"])

    def _finalize_managed_run(
        self,
        run_id: str,
        result: RunnerResult,
        *,
        worktree_env: Any | None = None,
        verification_command: str | None = None,
        cwd: Path | str | None = None,
        provider_account: str | None = None,
        runner_label: str | None = None,
        keep_worktree: bool = False,
        auto_accept: bool = True,
    ) -> dict[str, Any]:
        now = _now()
        verification_result = None
        if verification_command and result.outcome == "completed":
            if worktree_env:
                verification_result = worktree_env.run_verification(verification_command)
            elif cwd:
                from .worktree import WorktreeEnvironment
                dummy = WorktreeEnvironment(run_id, "", Path(cwd), Path(cwd))
                verification_result = dummy.run_verification(verification_command)
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
                        if auto_accept and ticket["risk_level"] == "low" and AUTO_ACCEPTOR in self.acceptance_authority["low"]:
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
        if reviewed_by not in self.memory_review_authority:
            raise AcceptanceRequiredError(
                f"Memory candidate promotion requires one of: {', '.join(self.memory_review_authority)}"
            )
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

    def list_projects(self, workspace_id: str, *, include_archived: bool = False) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            try:
                db.execute("CREATE TABLE IF NOT EXISTS project_archives (project_id TEXT PRIMARY KEY, archived_at TEXT NOT NULL)")
                if include_archived:
                    rows = db.execute(
                        """
                        SELECT p.*, (CASE WHEN a.project_id IS NOT NULL THEN 1 ELSE 0 END) as is_archived
                        FROM projects p
                        LEFT JOIN project_archives a ON p.id = a.project_id
                        WHERE p.workspace_id=?
                        ORDER BY p.created_at
                        """,
                        (workspace_id,),
                    ).fetchall()
                else:
                    rows = db.execute(
                        """
                        SELECT p.*, 0 as is_archived
                        FROM projects p
                        LEFT JOIN project_archives a ON p.id = a.project_id
                        WHERE p.workspace_id=? AND a.project_id IS NULL
                        ORDER BY p.created_at
                        """,
                        (workspace_id,),
                    ).fetchall()
            except sqlite3.OperationalError:
                rows = db.execute("SELECT * FROM projects WHERE workspace_id=? ORDER BY created_at", (workspace_id,)).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["is_archived"] = bool(item.get("is_archived", 0))
            result.append(item)
        return result

    def archive_project(self, project_id: str) -> dict[str, Any]:
        with self.store.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS project_archives (project_id TEXT PRIMARY KEY, archived_at TEXT NOT NULL)")
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Project not found: {project_id}")
            db.execute("INSERT OR REPLACE INTO project_archives (project_id, archived_at) VALUES (?, ?)", (project_id, _now()))
        return self.get_project(project_id)

    def unarchive_project(self, project_id: str) -> dict[str, Any]:
        with self.store.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS project_archives (project_id TEXT PRIMARY KEY, archived_at TEXT NOT NULL)")
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Project not found: {project_id}")
            db.execute("DELETE FROM project_archives WHERE project_id=?", (project_id,))
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> dict[str, Any]:
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Project not found: {project_id}")
            item = dict(row)
            try:
                arch = db.execute("SELECT 1 FROM project_archives WHERE project_id=?", (project_id,)).fetchone()
                item["is_archived"] = bool(arch)
            except sqlite3.OperationalError:
                item["is_archived"] = False
        return item

    def list_tickets(self, project_id: str, *, goal_id: str | None = None) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            if goal_id is not None:
                rows = db.execute(
                    "SELECT * FROM tickets WHERE project_id=? AND goal_id=? ORDER BY created_at",
                    (project_id, goal_id),
                ).fetchall()
            else:
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
            "memory_review_authority": list(self.memory_review_authority),
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

    # -------------------------------------------------------------------------
    # Long Tasks: Goal Orchestration
    # -------------------------------------------------------------------------

    def create_goal(self, project_id: str, title: str, description: str = "") -> dict[str, Any]:
        if not title.strip():
            raise ValueError("Goal requires title")
        now = _now()
        item = {
            "id": _id("GOL"),
            "project_id": project_id,
            "title": title.strip(),
            "description": description.strip(),
            "status": "planned",
            "created_at": now,
            "updated_at": now,
        }
        with self.store.transaction() as db:
            if not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise NotFoundError(f"Project not found: {project_id}")
            db.execute(
                """INSERT INTO goals(id,project_id,title,description,status,created_at,updated_at)
                   VALUES (:id,:project_id,:title,:description,:status,:created_at,:updated_at)""",
                item,
            )
        return self.get_goal(item["id"])

    def get_goal(self, goal_id: str) -> dict[str, Any]:
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Goal not found: {goal_id}")
            goal = dict(row)
            tickets = db.execute(
                "SELECT * FROM tickets WHERE goal_id=? ORDER BY created_at", (goal_id,)
            ).fetchall()
        goal_tickets = []
        for t in tickets:
            item = dict(t)
            item["acceptance_criteria"] = json.loads(item.pop("acceptance_criteria_json"))
            goal_tickets.append(item)
        goal["tickets"] = goal_tickets
        total = len(goal_tickets)
        accepted = sum(1 for t in goal_tickets if t["status"] == "accepted")
        goal["total_tickets"] = total
        goal["accepted_tickets"] = accepted
        goal["progress_pct"] = round((accepted / total * 100.0), 1) if total > 0 else 0.0
        return goal

    def list_goals(self, project_id: str) -> list[dict[str, Any]]:
        with self.store.connect() as db:
            rows = db.execute("SELECT id FROM goals WHERE project_id=? ORDER BY created_at", (project_id,)).fetchall()
        return [self.get_goal(row["id"]) for row in rows]

    def link_ticket_to_goal(
        self,
        ticket_id: str,
        goal_id: str,
        *,
        depends_on_ticket_id: str | None = None,
    ) -> dict[str, Any]:
        with self.store.transaction() as db:
            ticket = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if not ticket:
                raise NotFoundError(f"Ticket not found: {ticket_id}")
            self._validate_goal_and_dependency(
                db, ticket["project_id"], ticket_id, goal_id, depends_on_ticket_id
            )
            now = _now()
            db.execute(
                "UPDATE tickets SET goal_id=?, depends_on_ticket_id=?, updated_at=? WHERE id=?",
                (goal_id, depends_on_ticket_id, now, ticket_id),
            )
        return self.get_ticket(ticket_id)

    # -------------------------------------------------------------------------
    # 5-Layer Hierarchy: Project -> Goal -> Milestone -> Node -> Ticket
    # -------------------------------------------------------------------------

    def create_node(
        self,
        project_id: str,
        title: str,
        summary: str,
        layer: str = "task",
        *,
        goal_id: str | None = None,
        parent_node_id: str | None = None,
        details: str = "",
        files: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("Node requires title")
        if not summary.strip():
            raise ValueError("Node requires summary")
        if layer not in NODE_LAYERS:
            raise ValueError(f"Node layer must be one of {', '.join(NODE_LAYERS)}")

        now = _now()
        item = {
            "id": _id("NOD"),
            "project_id": project_id,
            "goal_id": goal_id,
            "parent_node_id": parent_node_id,
            "layer": layer,
            "title": title.strip(),
            "summary": summary.strip(),
            "details": (details or "").strip(),
            "files_json": json.dumps(files or [], ensure_ascii=False),
            "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
            "created_at": now,
        }

        with self.store.transaction() as db:
            if not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise NotFoundError(f"Project not found: {project_id}")
            if goal_id:
                goal = db.execute("SELECT project_id FROM goals WHERE id=?", (goal_id,)).fetchone()
                if not goal:
                    raise NotFoundError(f"Goal not found: {goal_id}")
                if goal["project_id"] != project_id:
                    raise ValueError("Node Goal must belong to the same Project")
            if parent_node_id:
                parent = db.execute("SELECT project_id FROM nodes WHERE id=?", (parent_node_id,)).fetchone()
                if not parent:
                    raise NotFoundError(f"Parent node not found: {parent_node_id}")
                if parent["project_id"] != project_id:
                    raise ValueError("Parent node must belong to the same Project")

            db.execute(
                """INSERT INTO nodes(id,project_id,goal_id,parent_node_id,layer,title,summary,details,files_json,metadata_json,created_at)
                   VALUES (:id,:project_id,:goal_id,:parent_node_id,:layer,:title,:summary,:details,:files_json,:metadata_json,:created_at)""",
                item,
            )
        return self.get_node(item["id"])

    def get_node(self, node_id: str) -> dict[str, Any]:
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
            if not row:
                raise NotFoundError(f"Node not found: {node_id}")
            node = dict(row)
            files = json.loads(node.pop("files_json") or "[]")
            node["files"] = files
            metadata = json.loads(node.pop("metadata_json") or "{}")
            node["metadata"] = metadata

            tickets = db.execute(
                "SELECT * FROM tickets WHERE node_id=? ORDER BY created_at", (node_id,)
            ).fetchall()
            children = db.execute(
                "SELECT id, title, layer, summary FROM nodes WHERE parent_node_id=? ORDER BY created_at", (node_id,)
            ).fetchall()

        parsed_tickets = []
        for t in tickets:
            item = dict(t)
            item["acceptance_criteria"] = json.loads(item.pop("acceptance_criteria_json"))
            parsed_tickets.append(item)
        node["tickets"] = parsed_tickets
        node["child_nodes"] = [dict(c) for c in children]
        return node

    def list_nodes(
        self,
        project_id: str,
        *,
        layer: str | None = None,
        goal_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT id FROM nodes WHERE project_id=?"
        params: list[Any] = [project_id]
        if layer:
            query += " AND layer=?"
            params.append(layer)
        if goal_id:
            query += " AND goal_id=?"
            params.append(goal_id)
        query += " ORDER BY created_at"

        with self.store.connect() as db:
            rows = db.execute(query, tuple(params)).fetchall()
        return [self.get_node(row["id"]) for row in rows]

    def link_ticket_to_node(self, ticket_id: str, node_id: str) -> dict[str, Any]:
        with self.store.transaction() as db:
            ticket = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if not ticket:
                raise NotFoundError(f"Ticket not found: {ticket_id}")
            node = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
            if not node:
                raise NotFoundError(f"Node not found: {node_id}")
            if node["project_id"] != ticket["project_id"]:
                raise ValueError("Ticket and Node must belong to the same Project")

            now = _now()
            # If node has a goal_id and ticket does not, link to goal_id too
            update_goal = node["goal_id"] if not ticket["goal_id"] else ticket["goal_id"]
            db.execute(
                "UPDATE tickets SET node_id=?, goal_id=?, updated_at=? WHERE id=?",
                (node_id, update_goal, now, ticket_id),
            )
        return self.get_ticket(ticket_id)

    def get_project_hierarchy(self, project_id: str) -> dict[str, Any]:
        """Return the complete 5-layer hierarchy:
        1. 專案結構 (Project Universe)
        2. 長期目標 (Goals)
        3. 中小型任務 (Milestones)
        4. 心智圖譜節點 (Nodes: architecture, logic, memory, task)
        5. 工單維度 (Tickets)
        """
        with self.store.connect() as db:
            project_row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if not project_row:
                raise NotFoundError(f"Project not found: {project_id}")
            project = dict(project_row)

        goals = self.list_goals(project_id)
        all_nodes = self.list_nodes(project_id)

        milestones = [n for n in all_nodes if n["layer"] == "milestone"]
        living_nodes = [n for n in all_nodes if n["layer"] != "milestone"]

        with self.store.connect() as db:
            all_ticket_rows = db.execute(
                "SELECT * FROM tickets WHERE project_id=? ORDER BY created_at", (project_id,)
            ).fetchall()
        tickets = []
        for t in all_ticket_rows:
            item = dict(t)
            item["acceptance_criteria"] = json.loads(item.pop("acceptance_criteria_json"))
            tickets.append(item)

        accepted_tickets = sum(1 for t in tickets if t["status"] == "accepted")
        active_tickets = sum(1 for t in tickets if t["status"] in ("active", "ready", "verification"))

        return {
            "project": project,
            "goals": goals,
            "milestones": milestones,
            "nodes": living_nodes,
            "tickets": tickets,
            "stats": {
                "total_goals": len(goals),
                "total_milestones": len(milestones),
                "total_nodes": len(living_nodes),
                "total_tickets": len(tickets),
                "accepted_tickets": accepted_tickets,
                "active_tickets": active_tickets,
            },
        }

    def sync_agentos_mindmap_nodes(
        self,
        project_id: str,
        *,
        goal_id: str | None = None,
        root_path: str | None = None,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Populate database nodes from grounded project mind map definitions."""
        from .mindmap import generate_project_graph_data

        prj = self.get_project(project_id)
        if not root_path:
            try:
                ws = self.get_workspace(prj["workspace_id"])
                root_path = ws.get("root_path")
            except Exception:
                pass

        nodes_data, _ = generate_project_graph_data(prj["name"], root_path=root_path)
        with self.store.transaction() as db:
            if force_refresh:
                db.execute("DELETE FROM nodes WHERE project_id=?", (project_id,))

            for n in nodes_data:
                existing = db.execute(
                    "SELECT id FROM nodes WHERE project_id=? AND title=?", (project_id, n["label"])
                ).fetchone()
                if existing:
                    continue
                clean_pid = project_id.replace("PRJ-", "")
                node_id = f"NOD-{clean_pid}-{n['id']}"
                now = _now()
                layer_map = {
                    "architecture": "architecture",
                    "logic": "logic",
                    "memory": "memory",
                    "milestone": "milestone",
                    "task": "task",
                    "delivery": "task",
                    "workbench": "task",
                    "path": "task",
                    "focus": "task",
                }
                schema_layer = layer_map.get(n.get("group", "task"), "task")
                db.execute(
                    """INSERT OR IGNORE INTO nodes(id,project_id,goal_id,parent_node_id,layer,title,summary,details,files_json,metadata_json,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        node_id,
                        project_id,
                        goal_id,
                        None,
                        schema_layer,
                        n["label"],
                        n.get("summary", ""),
                        n.get("details", ""),
                        json.dumps(n.get("files", []), ensure_ascii=False),
                        json.dumps({"level": n.get("level", 1), "color": n.get("color", "")}, ensure_ascii=False),
                        now,
                    ),
                )
        return self.list_nodes(project_id)

    def get_next_runnable_ticket_for_goal(self, goal_id: str) -> dict[str, Any] | None:
        """Find the first ready Ticket under this Goal whose dependency (if any) is accepted."""
        goal = self.get_goal(goal_id)
        tickets = goal["tickets"]
        status_map = {t["id"]: t["status"] for t in tickets}
        for ticket in tickets:
            if ticket["status"] != "ready":
                continue
            dep_id = ticket.get("depends_on_ticket_id")
            if dep_id and status_map.get(dep_id) != "accepted":
                continue
            return ticket
        return None

    def claim_next_runnable_ticket_for_goal(self, goal_id: str) -> dict[str, Any] | None:
        """Find the next runnable ticket for a goal, ensuring no active runs exist."""
        with self.store.transaction() as db:
            goal = db.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
            if not goal or goal["status"] in ("achieved", "cancelled"):
                return None
            tickets = db.execute("SELECT * FROM tickets WHERE goal_id=? ORDER BY created_at", (goal_id,)).fetchall()
            status_map = {t["id"]: t["status"] for t in tickets}
            for ticket in tickets:
                if ticket["status"] != "ready":
                    continue
                active_run = db.execute(
                    "SELECT 1 FROM runs WHERE ticket_id=? AND status IN ('queued', 'running')", (ticket["id"],)
                ).fetchone()
                if active_run:
                    continue
                dep_id = ticket["depends_on_ticket_id"]
                if dep_id and status_map.get(dep_id) != "accepted":
                    continue
                return self.get_ticket(ticket["id"])
        return None

    # -------------------------------------------------------------------------
    # Short Tasks: Ticket-internal Auto-Debug Loop
    # -------------------------------------------------------------------------

    def run_ticket_auto_debug_loop(
        self,
        ticket_id: str,
        runner: Any,
        prompt: str,
        cwd: str | Path,
        *,
        verification_command: str,
        max_attempts: int = 3,
        isolate_worktree: bool = True,
        timeout_seconds: float = 300.0,
        model: str | None = None,
        sensitive_values: Sequence[str] = (),
        auto_accept_low_risk: bool = True,
    ) -> dict[str, Any]:
        """Execute a Ticket with an internal auto-debug retry loop.
        If a Run or its verification fails, diagnostics are captured, a DebugEpisode
        is recorded, and the runner is re-prompted with the failure context until
        the verification passes or max_attempts is reached.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        ticket = self.get_ticket(ticket_id)
        current_prompt = prompt
        attempts_recorded = []
        last_run = None

        for attempt in range(1, max_attempts + 1):
            run = self.start_managed_run(
                ticket_id=ticket_id,
                runner=runner,
                prompt=current_prompt,
                cwd=cwd,
                verification_command=verification_command,
                isolate_worktree=isolate_worktree,
                timeout_seconds=timeout_seconds,
                model=model,
                sensitive_values=sensitive_values,
                keep_worktree=False,
                auto_accept=auto_accept_low_risk,
            )
            last_run = run

            # Check if verification passed
            with self.store.connect() as db:
                v = db.execute(
                    "SELECT * FROM verifications WHERE run_id=? AND status='passed' ORDER BY rowid DESC LIMIT 1",
                    (run["id"],),
                ).fetchone()

            if run["status"] == "completed" and v is not None:
                return {
                    "success": True,
                    "attempts": attempt,
                    "latest_run": run,
                    "ticket": self.get_ticket(ticket_id),
                    "debug_episodes": attempts_recorded,
                }

            # Failure: extract failure information
            error_code = run.get("error_code") or "RUN-FAILED"
            error_msg = run.get("error_message") or ""
            events = self.list_events(run["id"])
            output_event = next((e for e in reversed(events) if e["kind"] in ("invocation_output", "run_failed")), None)
            output_payload = output_event["payload"] if output_event else {}
            v_res = output_payload.get("verification_result") or {}
            v_stderr = v_res.get("stderr", "")
            v_stdout = v_res.get("stdout", "")
            stdout = output_payload.get("stdout", "")
            stderr = output_payload.get("stderr", "")
            diag_snippet = v_stderr or v_stdout or stderr or stdout or error_msg

            # Record DebugEpisode for this failed attempt
            fingerprint = f"{error_code}:{hashlib.sha256((diag_snippet or error_code).encode('utf-8')).hexdigest()[:8]}"
            episode = self.record_debug_episode(
                run_id=run["id"],
                symptom=f"Auto-debug attempt {attempt} failed: {error_code}",
                reproduction=verification_command,
                environment=f"runner={runner.name if hasattr(runner, 'name') else 'runner'}, attempt={attempt}/{max_attempts}",
                error_fingerprint=fingerprint,
                root_cause=error_msg or f"Verification exit code {v_res.get('exit_code', 'unknown')}",
                accepted_fix=f"Pending attempt {attempt + 1}" if attempt < max_attempts else "Exhausted attempts",
                regression_test=verification_command,
                hypotheses=[f"Attempt {attempt} failed, applying diagnostic feedback"],
                attempted_fixes=[f"Attempt {attempt} prompt provided"],
                failed_attempts=[{"attempt": attempt, "error": error_code, "diagnostics": diag_snippet[:1000]}],
            )
            attempts_recorded.append(episode)

            with self.store.transaction() as db:
                self._append_event(
                    db,
                    run["id"],
                    "auto_debug_attempt_failed",
                    {"attempt": attempt, "max_attempts": max_attempts, "error_code": error_code},
                )

            if attempt < max_attempts:
                current_prompt = (
                    f"{prompt}\n\n"
                    f"--- AUTOMATED DEBUG FEEDBACK (Attempt {attempt}/{max_attempts}) ---\n"
                    f"Previous run {run['id']} failed with error: {error_code}\n"
                    f"Diagnostics / Verification output:\n{diag_snippet}\n"
                    f"Please fix the implementation so that the verification passes."
                )

        return {
            "success": False,
            "attempts": max_attempts,
            "latest_run": last_run,
            "ticket": self.get_ticket(ticket_id),
            "debug_episodes": attempts_recorded,
        }

    def advance_goal(
        self,
        goal_id: str,
        runner: Any,
        cwd: str | Path,
        *,
        verification_command: str,
        max_attempts_per_ticket: int = 3,
        auto_accept_low_risk: bool = True,
        isolate_worktree: bool = True,
    ) -> dict[str, Any]:
        """Advance a Goal by executing the next unblocked ticket using the auto-debug loop."""
        goal = self.get_goal(goal_id)
        if goal["status"] in ("achieved", "cancelled"):
            return {"goal": goal, "action": "noop", "message": f"Goal is already {goal['status']}"}

        next_ticket = self.claim_next_runnable_ticket_for_goal(goal_id)
        if not next_ticket:
            all_accepted = all(t["status"] == "accepted" for t in goal["tickets"])
            new_status = "achieved" if (all_accepted and len(goal["tickets"]) > 0) else goal["status"]
            if new_status != goal["status"]:
                now = _now()
                with self.store.transaction() as db:
                    db.execute("UPDATE goals SET status=?, updated_at=? WHERE id=?", (new_status, now, goal_id))
                goal = self.get_goal(goal_id)
            return {"goal": goal, "action": "none_runnable", "all_accepted": all_accepted}

        # Update goal status to in_progress if planned
        if goal["status"] == "planned":
            now = _now()
            with self.store.transaction() as db:
                db.execute("UPDATE goals SET status='in_progress', updated_at=? WHERE id=?", (now, goal_id))

        # Run ticket via auto debug loop
        criteria = next_ticket.get("acceptance_criteria") or []
        criteria_text = "\n".join(f"- {c}" for c in criteria)
        ticket_prompt = (
            f"Goal: {goal['title']}\n"
            f"Ticket: {next_ticket['title']}\n"
            f"Requirement: {next_ticket['goal']}\n"
        )
        if criteria_text:
            ticket_prompt += f"Acceptance Criteria:\n{criteria_text}\n"
        loop_result = self.run_ticket_auto_debug_loop(
            ticket_id=next_ticket["id"],
            runner=runner,
            prompt=ticket_prompt,
            cwd=cwd,
            verification_command=verification_command,
            max_attempts=max_attempts_per_ticket,
            isolate_worktree=isolate_worktree,
            auto_accept_low_risk=auto_accept_low_risk,
        )

        # Refresh goal progress
        updated_goal = self.get_goal(goal_id)
        all_done = all(t["status"] == "accepted" for t in updated_goal["tickets"])
        if all_done and len(updated_goal["tickets"]) > 0:
            now = _now()
            with self.store.transaction() as db:
                db.execute("UPDATE goals SET status='achieved', updated_at=? WHERE id=?", (now, goal_id))
            updated_goal = self.get_goal(goal_id)

        return {
            "goal": updated_goal,
            "action": "ran_ticket",
            "ticket_id": next_ticket["id"],
            "loop_result": loop_result,
        }

    # -------------------------------------------------------------------------
    # Delivery Adapters (Invariant 9: Acceptance vs Delivery)
    # -------------------------------------------------------------------------

    def deliver_ticket(
        self,
        ticket_id: str,
        repo_path: str | Path,
        *,
        target_branch: str = "master",
        delivery_adapter: Any | None = None,
        tag: bool = True,
    ) -> dict[str, Any]:
        """Deliver an accepted Ticket's work into the target mainline branch (Invariant 9).
        Enforces:
        1. Ticket must be in 'accepted' status (cannot deliver unaccepted code).
        2. Finds the latest Run for this ticket that produced an auditable wb-run/<run_id> branch.
        3. Merges the run branch into target_branch.
        4. Records a 'delivery_completed' audit event.
        """
        ticket = self.get_ticket(ticket_id)
        if ticket["status"] != "accepted":
            raise InvalidTransitionError(
                f"Ticket {ticket_id} is in status '{ticket['status']}', cannot be delivered. "
                f"Invariant 9 requires explicit acceptance before mainline delivery."
            )

        with self.store.connect() as db:
            run_row = db.execute(
                "SELECT * FROM runs WHERE ticket_id=? AND status='completed' ORDER BY rowid DESC LIMIT 1",
                (ticket_id,),
            ).fetchone()
        if not run_row:
            raise NotFoundError(f"No completed run found for ticket {ticket_id}")

        run_id = run_row["id"]
        from .delivery import GitDeliveryAdapter, DeliveryResult
        adapter = delivery_adapter or GitDeliveryAdapter(repo_path)
        result: DeliveryResult = adapter.merge_run_to_branch(
            run_id,
            target_branch=target_branch,
            commit_message=f"feat({ticket_id}): {ticket['title']}\n\nAccepted by: {ticket.get('accepted_by')}\nRun: {run_id}",
        )

        tag_name = None
        if result.status == "delivered" and tag and result.commit_sha:
            tag_name = f"wb-delivered-{ticket_id.lower()}"
            try:
                adapter.tag_delivery(
                    result.commit_sha,
                    tag_name,
                    message=f"Delivered ticket {ticket_id} from run {run_id}\nTarget branch: {target_branch}",
                )
            except Exception:
                tag_name = None

        payload = {
            "ticket_id": ticket_id,
            "run_id": run_id,
            "target_branch": target_branch,
            "delivery_result": result.to_dict(),
            "tag": tag_name,
        }
        with self.store.transaction() as db:
            self._append_event(db, run_id, "delivery_completed", payload)

        return payload

    def deliver_goal(
        self,
        goal_id: str,
        repo_path: str | Path,
        *,
        target_branch: str = "master",
        delivery_adapter: Any | None = None,
    ) -> dict[str, Any]:
        """Deliver all accepted tickets under a Goal into the target mainline branch (Invariant 9)."""
        goal = self.get_goal(goal_id)
        tickets = goal["tickets"]
        if not tickets:
            raise ValueError(f"Goal {goal_id} contains no tickets")
        if not all(t["status"] == "accepted" for t in tickets):
            raise InvalidTransitionError(
                f"Goal {goal_id} cannot be delivered because not all tickets are accepted."
            )

        results = []
        for ticket in tickets:
            res = self.deliver_ticket(ticket["id"], repo_path, target_branch=target_branch, delivery_adapter=delivery_adapter)
            results.append(res)

        now = _now()
        payload = {
            "goal_id": goal_id,
            "target_branch": target_branch,
            "ticket_deliveries": results,
        }
        with self.store.transaction() as db:
            db.execute("UPDATE goals SET status='achieved', updated_at=? WHERE id=?", (now, goal_id))
            self._append_event(db, results[-1]["run_id"], "goal_delivered", payload)

        return {
            "goal": self.get_goal(goal_id),
            "ticket_deliveries": results,
        }

    # ── Error Telemetry & Sentinel Watchdog ────────────────────────────

    def record_error(
        self,
        source: str,
        message: str,
        *,
        error_type: str | None = None,
        severity: str = "error",
        stack_trace: str | None = None,
        context: dict[str, Any] | None = None,
        fingerprint: str | None = None,
        auto_ticket: bool = False,
        project_id: str | None = None,
        node_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an error in system_errors with deduplication, fingerprinting, and auto-ticket support."""
        if source not in ("frontend", "backend", "runner", "sentinel", "linter"):
            source = "backend"
        if severity not in ("critical", "error", "warning", "info"):
            severity = "error"
        error_type = error_type or "WorkbenchError"
        message_str = (message or "").strip()

        # Compute stable fingerprint if not explicitly supplied
        if not fingerprint:
            norm_msg = re.sub(r"[0-9a-fA-F]{8,}", "<hash>", message_str)
            norm_msg = re.sub(r"\d+", "<n>", norm_msg)
            fp_raw = f"{source}:{error_type}:{norm_msg[:200]}"
            fingerprint = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()[:16]

        now = _now()
        context_json = json.dumps(context or {}, ensure_ascii=False)

        with self.store.transaction() as db:
            existing = db.execute(
                """SELECT * FROM system_errors
                   WHERE fingerprint=? AND status IN ('unresolved', 'triaged', 'ticket_created')
                   ORDER BY rowid DESC LIMIT 1""",
                (fingerprint,),
            ).fetchone()

            if existing:
                err_id = existing["id"]
                new_count = existing["occurrence_count"] + 1
                db.execute(
                    """UPDATE system_errors
                       SET occurrence_count=?, last_seen_at=?, message=?,
                           stack_trace=COALESCE(?, stack_trace), context_json=?
                       WHERE id=?""",
                    (new_count, now, message_str, stack_trace, context_json, err_id),
                )
                err_record = _row(db.execute("SELECT * FROM system_errors WHERE id=?", (err_id,)).fetchone())
            else:
                err_id = _id("ERR")
                err_record = {
                    "id": err_id,
                    "fingerprint": fingerprint,
                    "source": source,
                    "severity": severity,
                    "error_type": error_type,
                    "message": message_str,
                    "stack_trace": stack_trace,
                    "context_json": context_json,
                    "occurrence_count": 1,
                    "status": "unresolved",
                    "ticket_id": None,
                    "created_at": now,
                    "last_seen_at": now,
                }
                db.execute(
                    """INSERT INTO system_errors
                       (id, fingerprint, source, severity, error_type, message, stack_trace,
                        context_json, occurrence_count, status, ticket_id, created_at, last_seen_at)
                       VALUES (:id, :fingerprint, :source, :severity, :error_type, :message, :stack_trace,
                               :context_json, :occurrence_count, :status, :ticket_id, :created_at, :last_seen_at)""",
                    err_record,
                )

        if auto_ticket and not err_record.get("ticket_id"):
            try:
                ticket_info = self.convert_error_to_ticket(err_record["id"], project_id=project_id, node_id=node_id)
                err_record["ticket_id"] = ticket_info["id"]
                err_record["status"] = "ticket_created"
            except Exception:
                pass

        return err_record

    def list_errors(
        self,
        *,
        status: str | None = None,
        source: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List collected errors with filtering and ordering by most recently seen."""
        clauses = []
        params: list[Any] = []
        if status:
            clauses.append("status=?")
            params.append(status)
        if source:
            clauses.append("source=?")
            params.append(source)
        if severity:
            clauses.append("severity=?")
            params.append(severity)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM system_errors {where} ORDER BY last_seen_at DESC LIMIT {int(limit)}"

        with self.store.connect() as db:
            rows = db.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]

    def get_error(self, error_id: str) -> dict[str, Any]:
        """Fetch an individual error record by ID."""
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM system_errors WHERE id=?", (error_id,)).fetchone()
        if not row:
            raise NotFoundError(f"System Error not found: {error_id}")
        return dict(row)

    def resolve_error(self, error_id: str, *, status: str = "resolved") -> dict[str, Any]:
        """Mark an error as resolved or ignored."""
        if status not in ("resolved", "ignored", "triaged"):
            status = "resolved"
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM system_errors WHERE id=?", (error_id,)).fetchone()
            if not row:
                raise NotFoundError(f"System Error not found: {error_id}")
            db.execute("UPDATE system_errors SET status=? WHERE id=?", (status, error_id))
            updated = db.execute("SELECT * FROM system_errors WHERE id=?", (error_id,)).fetchone()
            return dict(updated)

    def convert_error_to_ticket(
        self,
        error_id: str,
        *,
        project_id: str | None = None,
        node_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Convert a system error directly into an atomic fix ticket for auto-debug remediation."""
        err = self.get_error(error_id)
        if not project_id:
            workspaces = self.list_workspaces()
            if workspaces:
                prjs = self.list_projects(workspaces[0]["id"])
                project_id = prjs[0]["id"] if prjs else None
        if not project_id:
            raise ValueError("No project found to associate fix ticket with.")

        tkt_title = title or f"【故障修復】{err['source'].upper()}: {err['error_type']} - {err['message'][:35]}"
        tkt_goal = f"自動修復遙測系統錯誤 [{err['id']}] (指紋 {err['fingerprint']}):\n{err['message']}"
        criteria = [
            f"故障代碼根除，指紋 {err['fingerprint']} 歸零 (error_count=0)",
            "回歸測試通過且無違反 Invariant 1~14 契約",
            "產生獨立 Verifier SHA-256 驗證證據",
        ]

        ticket = self.create_ticket(
            project_id=project_id,
            title=tkt_title,
            goal=tkt_goal,
            acceptance_criteria=criteria,
            risk_level="high",
            node_id=node_id,
        )

        with self.store.transaction() as db:
            db.execute(
                "UPDATE system_errors SET status='ticket_created', ticket_id=? WHERE id=?",
                (ticket["id"], error_id),
            )

        return ticket

    def run_sentinel_health_check(self, project_id: str | None = None) -> dict[str, Any]:
        """Run proactive background health and contract consistency scans across projects and nodes."""
        now = _now()
        findings: list[dict[str, Any]] = []

        workspaces = self.list_workspaces()
        all_projects = []
        if project_id:
            all_projects.append(self.get_project(project_id))
        else:
            for ws in workspaces:
                all_projects.extend(self.list_projects(ws["id"]))

        for prj in all_projects:
            pid = prj["id"]
            nodes = self.list_nodes(pid)
            tickets = self.list_tickets(pid)

            # 1. 檢查 N4 探索工位與階層式產物邊界
            for node in nodes:
                files = node.get("files", [])
                if any("n4-exploratory" in f for f in files):
                    # 檢查是否有未定義階層 expected_outputs
                    if not node.get("details") or "expected_outputs" not in node.get("details", ""):
                        findings.append({
                            "source": "sentinel",
                            "severity": "warning",
                            "error_type": "LINT-007",
                            "message": f"工位 [{node['id']}] {node['title']} 需聲明階層式 expected_outputs 與獨立 Verifier 規範",
                            "node_id": node["id"],
                            "project_id": pid,
                        })

            # 2. 檢查孤立工單或依賴閉環
            ticket_map = {t["id"]: t for t in tickets}
            for tkt in tickets:
                dep_id = tkt.get("depends_on_ticket_id")
                if dep_id and dep_id not in ticket_map:
                    findings.append({
                        "source": "sentinel",
                        "severity": "error",
                        "error_type": "ORPHAN-DEPENDENCY",
                        "message": f"工單 #{tkt['id']} 的前置依賴 #{dep_id} 不存在於當前專案中",
                        "ticket_id": tkt["id"],
                        "project_id": pid,
                    })

        # 將 findings 記錄至 system_errors
        recorded_errors = []
        for f in findings:
            err = self.record_error(
                source=f["source"],
                message=f["message"],
                error_type=f["error_type"],
                severity=f["severity"],
                context={"project_id": f.get("project_id"), "node_id": f.get("node_id"), "ticket_id": f.get("ticket_id")},
                project_id=f.get("project_id"),
                node_id=f.get("node_id"),
            )
            recorded_errors.append(err)

        return {
            "scanned_at": now,
            "findings_count": len(findings),
            "findings": findings,
            "recorded_errors": recorded_errors,
        }

