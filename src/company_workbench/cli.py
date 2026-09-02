from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .demo import run_demo
from .engine import RISK_LEVELS, TIERED_ACCEPTANCE_AUTHORITY, WorkbenchEngine
from .errors import (
    NotFoundError,
    InvalidTransitionError,
    EvidenceRequiredError,
    AcceptanceRequiredError,
    RunnerLaunchError,
    TicketImportError,
    VerifierIndependenceError,
    WorktreeError,
)
from .runner import CodexCliRunner

_GOVERNANCE_ERRORS = (
    NotFoundError, InvalidTransitionError, EvidenceRequiredError, AcceptanceRequiredError,
    VerifierIndependenceError, TicketImportError, WorktreeError, ValueError,
)


def _repo_root_if_git(path: Path) -> Path | None:
    return path if (path / ".git").exists() else None


def _current_commit(path: Path) -> str | None:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=False)
    except OSError:
        return None
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def _default_database() -> Path:
    return Path.cwd() / ".workbench" / "workbench.db"


def _out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _err(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wb", description="Company AI Workbench CLI")
    parser.add_argument("--database", type=Path, default=_default_database(), metavar="PATH")
    commands = parser.add_subparsers(dest="command", required=True)

    # ── legacy / utility ─────────────────────────────────────────────────────
    diag_cmd = commands.add_parser("diagnose")
    diag_cmd.add_argument("--repo", type=Path, default=None, metavar="DIR",
                          help="Git repo root to scan for leftover Run worktrees (default: cwd if it is a repo)")
    commands.add_parser("demo")
    backup_cmd = commands.add_parser("backup")
    backup_cmd.add_argument("target", type=Path)

    # ── workspace ─────────────────────────────────────────────────────────────
    ws_cmd = commands.add_parser("workspace")
    ws_sub = ws_cmd.add_subparsers(dest="ws_action", required=True)
    ws_create = ws_sub.add_parser("create")
    ws_create.add_argument("name")
    ws_create.add_argument("--path", dest="root_path", default=None, metavar="DIR")
    ws_sub.add_parser("list")

    # ── project ───────────────────────────────────────────────────────────────
    proj_cmd = commands.add_parser("project")
    proj_sub = proj_cmd.add_subparsers(dest="proj_action", required=True)
    proj_create = proj_sub.add_parser("create")
    proj_create.add_argument("workspace_id")
    proj_create.add_argument("name")
    proj_list = proj_sub.add_parser("list")
    proj_list.add_argument("workspace_id")

    # ── ticket ────────────────────────────────────────────────────────────────
    tkt_cmd = commands.add_parser("ticket")
    tkt_sub = tkt_cmd.add_subparsers(dest="tkt_action", required=True)
    tkt_create = tkt_sub.add_parser("create")
    tkt_create.add_argument("project_id")
    tkt_create.add_argument("title")
    tkt_create.add_argument("--goal", required=True)
    tkt_create.add_argument("--criteria", action="append", dest="criteria", required=True, metavar="TEXT")
    tkt_create.add_argument("--risk", dest="risk_level", choices=RISK_LEVELS, default="high",
                            help="Acceptance tier; fixed at creation (default: high = Josh only)")
    tkt_import = tkt_sub.add_parser("import", help="Batch-create Tickets from a JSON or Markdown file (all-or-nothing)")
    tkt_import.add_argument("project_id")
    tkt_import.add_argument("file", type=Path)
    tkt_import.add_argument("--default-risk", dest="default_risk", choices=RISK_LEVELS, default="high")
    tkt_show = tkt_sub.add_parser("show")
    tkt_show.add_argument("ticket_id")
    tkt_list = tkt_sub.add_parser("list")
    tkt_list.add_argument("project_id")

    # ── run ───────────────────────────────────────────────────────────────────
    run_cmd = commands.add_parser("run")
    run_sub = run_cmd.add_subparsers(dest="run_action", required=True)
    run_start = run_sub.add_parser("start")
    run_start.add_argument("ticket_id")
    prompt_grp = run_start.add_mutually_exclusive_group()
    prompt_grp.add_argument("--prompt", metavar="TEXT")
    prompt_grp.add_argument("--prompt-file", type=Path, metavar="FILE")
    run_start.add_argument("--fake", action="store_true", help="Use fake runner (no real AI call)")
    run_start.add_argument("--runner", choices=["gemini", "codex"], default="gemini",
                           help="Runner to execute prompt with (default: gemini)")
    run_start.add_argument("--model", default=None, metavar="MODEL",
                           help="Model override (e.g. gemini-2.5-flash or gpt-4o)")
    run_start.add_argument("--timeout", type=float, default=300, metavar="SECONDS")
    run_start.add_argument("--worktree", action="store_true", help="Run inside an isolated temporary Git worktree")
    run_start.add_argument("--verify-cmd", default=None, metavar="CMD",
                           help="Automated test/check command to run inside worktree after AI finishes (e.g. 'pytest tests/')")
    run_start.add_argument("--provider-account", default=None, metavar="LABEL",
                           help="Which provider account/quota this Run consumed (label only, never a secret)")
    run_start.add_argument("--keep-worktree", action="store_true",
                           help="Leave the Run worktree directory in place after committing its output to the Run branch")
    run_start.add_argument("--auto-accept-low-risk", action="store_true",
                           help="Let the automated acceptor close LOW-risk Tickets when the --verify-cmd passes")
    run_usage = run_sub.add_parser("usage", help="Attach token/cost evidence to a Run")
    run_usage.add_argument("run_id")
    run_usage.add_argument("--input-tokens", type=int, default=None)
    run_usage.add_argument("--output-tokens", type=int, default=None)
    run_usage.add_argument("--cost-usd", type=float, default=None)
    run_usage.add_argument("--provider-account", default=None, metavar="LABEL")
    run_complete = run_sub.add_parser("complete")
    run_complete.add_argument("run_id")
    run_show = run_sub.add_parser("show")
    run_show.add_argument("run_id")
    run_events = run_sub.add_parser("events")
    run_events.add_argument("run_id")
    run_list = run_sub.add_parser("list")
    run_list.add_argument("ticket_id")

    # ── verify ────────────────────────────────────────────────────────────────
    verify_cmd = commands.add_parser("verify")
    verify_cmd.add_argument("run_id")
    verify_cmd.add_argument("--status", choices=["passed", "failed"], default="passed")
    verify_cmd.add_argument("--evidence", required=True, metavar="REF", help="Human-readable label for the evidence")
    evidence_grp = verify_cmd.add_mutually_exclusive_group(required=True)
    evidence_grp.add_argument("--evidence-text", metavar="TEXT", help="Evidence body to hash and store")
    evidence_grp.add_argument("--evidence-file", type=Path, metavar="FILE", help="Evidence file to hash and store")
    verify_cmd.add_argument("--summary", required=True)
    verify_cmd.add_argument("--verifier", default="cli-user")
    verify_cmd.add_argument("--verifier-provider", required=True, metavar="PROVIDER",
                            help="Who verified: human, anthropic, google, openai, local-command ... must differ from the builder")

    # ── evidence ──────────────────────────────────────────────────────────────
    ev_cmd = commands.add_parser("evidence")
    ev_sub = ev_cmd.add_subparsers(dest="ev_action", required=True)
    ev_show = ev_sub.add_parser("show")
    ev_show.add_argument("sha256")
    ev_sub.add_parser("check")

    # ── worktree ──────────────────────────────────────────────────────────────
    wt_cmd = commands.add_parser("worktree")
    wt_sub = wt_cmd.add_subparsers(dest="wt_action", required=True)
    wt_list = wt_sub.add_parser("list")
    wt_list.add_argument("--repo", type=Path, default=None, metavar="DIR")
    wt_prune = wt_sub.add_parser("prune", help="Commit leftover Run worktrees to their branches and remove the directories")
    wt_prune.add_argument("--repo", type=Path, default=None, metavar="DIR")

    # ── accept ────────────────────────────────────────────────────────────────
    accept_cmd = commands.add_parser("accept")
    accept_cmd.add_argument("ticket_id")
    accept_cmd.add_argument("--by", dest="accepted_by", default="Josh")
    accept_cmd.add_argument("--note", default="")

    # ── memory ────────────────────────────────────────────────────────────────
    mem_parser = commands.add_parser("memory")
    mem_sub = mem_parser.add_subparsers(dest="mem_action", required=True)
    mem_prop = mem_sub.add_parser("propose")
    mem_prop.add_argument("project_id")
    mem_prop.add_argument("source_run_id")
    mem_prop.add_argument("--kind", choices=["episodic", "semantic", "procedural", "preference", "project"], default="procedural")
    mem_prop.add_argument("--statement", required=True)
    mem_prop.add_argument("--scope", default="project")
    mem_prop.add_argument("--evidence", required=True)

    mem_list = mem_sub.add_parser("list")
    mem_list.add_argument("project_id")
    mem_list.add_argument("--status", choices=["pending", "approved", "rejected", "disabled"], default=None)

    mem_app = mem_sub.add_parser("approve")
    mem_app.add_argument("memory_id")
    mem_app.add_argument("--by", dest="reviewed_by", default="Josh")
    mem_app.add_argument("--note", default="")
    mem_app.add_argument("--ttl-days", type=int, default=None, help="Lifetime in days (default: engine TTL, 90)")
    mem_app.add_argument("--expires-at", default=None, metavar="ISO8601")
    mem_app.add_argument("--commit", dest="source_commit", default=None, metavar="SHA",
                         help="Commit the rule was learned against (default: git HEAD of cwd when available)")

    mem_expire = mem_sub.add_parser("expire", help="Sweep approved memories past their expiry")
    mem_ctx = mem_sub.add_parser("context", help="Print the approved, unexpired memory block for a project")
    mem_ctx.add_argument("project_id")

    mem_rej = mem_sub.add_parser("reject")
    mem_rej.add_argument("memory_id")
    mem_rej.add_argument("--by", dest="reviewed_by", default="Josh")
    mem_rej.add_argument("--note", default="")

    # ── reconcile ─────────────────────────────────────────────────────────────
    commands.add_parser("reconcile")

    args = parser.parse_args(argv)

    # ── demo (no engine needed) ───────────────────────────────────────────────
    if args.command == "demo":
        with tempfile.TemporaryDirectory(prefix="company-workbench-demo-") as temp:
            result = run_demo(Path(temp) / "demo.db")
        _out(result)
        return 0

    authority = TIERED_ACCEPTANCE_AUTHORITY if getattr(args, "auto_accept_low_risk", False) else None
    engine = WorkbenchEngine(args.database, acceptance_authority=authority)

    # ── utility ───────────────────────────────────────────────────────────────
    if args.command == "diagnose":
        repo = args.repo or _repo_root_if_git(Path.cwd())
        info = engine.diagnose(repo_root=repo)
        _out(info)
        return 0 if info["integrity"] == "ok" and info["evidence"]["ok"] else 1

    if args.command == "backup":
        target = engine.store.backup_to(args.target)
        restored = WorkbenchEngine(target).diagnose()
        _out({"backup": str(target.resolve()), "restore_check": restored})
        return 0 if restored["integrity"] == "ok" else 1

    if args.command == "reconcile":
        orphans = engine.reconcile_orphan_runs()
        _out({"reconciled": len(orphans), "runs": orphans})
        return 0

    # ── workspace ─────────────────────────────────────────────────────────────
    if args.command == "workspace":
        if args.ws_action == "create":
            _out(engine.create_workspace(args.name, root_path=args.root_path))
        elif args.ws_action == "list":
            _out(engine.list_workspaces())
        return 0

    # ── project ───────────────────────────────────────────────────────────────
    if args.command == "project":
        try:
            if args.proj_action == "create":
                _out(engine.create_project(args.workspace_id, args.name))
            elif args.proj_action == "list":
                _out(engine.list_projects(args.workspace_id))
        except NotFoundError as exc:
            return _err(str(exc))
        return 0

    # ── ticket ────────────────────────────────────────────────────────────────
    if args.command == "ticket":
        try:
            if args.tkt_action == "create":
                _out(engine.create_ticket(args.project_id, args.title, args.goal, args.criteria, risk_level=args.risk_level))
            elif args.tkt_action == "import":
                _out(engine.import_tickets(args.project_id, args.file, default_risk_level=args.default_risk))
            elif args.tkt_action == "show":
                _out(engine.get_ticket(args.ticket_id))
            elif args.tkt_action == "list":
                _out(engine.list_tickets(args.project_id))
        except _GOVERNANCE_ERRORS as exc:
            return _err(str(exc))
        return 0

    # ── run ───────────────────────────────────────────────────────────────────
    if args.command == "run":
        try:
            if args.run_action == "start":
                if args.fake:
                    _out(engine.start_run(args.ticket_id, runner="fake"))
                else:
                    # Resolve prompt
                    if args.prompt_file:
                        prompt = args.prompt_file.read_text(encoding="utf-8")
                    elif args.prompt:
                        prompt = args.prompt
                    else:
                        return _err("--prompt or --prompt-file is required for a real run (or use --fake)")
                    runner_name = args.runner
                    if args.runner == "gemini":
                        from .gemini_runner import GeminiRunner
                        runner = GeminiRunner(model=args.model or "gemini-2.5-flash")
                    else:
                        runner = CodexCliRunner()
                    cwd = Path.cwd()
                    print(f"Starting managed run for ticket {args.ticket_id} (runner: {runner_name}) ...", file=sys.stderr)
                    result = engine.start_managed_run(
                        args.ticket_id, runner, prompt,
                        cwd=cwd,
                        runner_name=runner_name,
                        timeout_seconds=args.timeout,
                        model=args.model,
                        isolate_worktree=args.worktree,
                        verification_command=args.verify_cmd,
                        provider_account=args.provider_account,
                        keep_worktree=args.keep_worktree,
                    )
                    _out(result)

            elif args.run_action == "usage":
                _out(engine.record_run_usage(
                    args.run_id, input_tokens=args.input_tokens, output_tokens=args.output_tokens,
                    cost_usd=args.cost_usd, provider_account=args.provider_account,
                ))
            elif args.run_action == "complete":
                _out(engine.complete_run(args.run_id))
            elif args.run_action == "show":
                _out(engine.get_run(args.run_id))
            elif args.run_action == "events":
                _out(engine.list_events(args.run_id))
            elif args.run_action == "list":
                _out(engine.list_runs(args.ticket_id))
        except (*_GOVERNANCE_ERRORS, RunnerLaunchError) as exc:
            return _err(str(exc))
        return 0

    # ── verify ────────────────────────────────────────────────────────────────
    if args.command == "verify":
        try:
            _out(engine.verify_run(
                args.run_id,
                status=args.status,
                evidence_ref=args.evidence,
                summary=args.summary,
                verifier=args.verifier,
                verifier_provider=args.verifier_provider,
                evidence_content=args.evidence_text,
                evidence_path=args.evidence_file,
            ))
        except _GOVERNANCE_ERRORS as exc:
            return _err(str(exc))
        return 0

    # ── evidence ──────────────────────────────────────────────────────────────
    if args.command == "evidence":
        try:
            if args.ev_action == "show":
                sys.stdout.write(engine.get_evidence(args.sha256).decode("utf-8", errors="replace"))
            elif args.ev_action == "check":
                report = engine.check_evidence_integrity()
                _out(report)
                return 0 if report["ok"] else 1
        except _GOVERNANCE_ERRORS as exc:
            return _err(str(exc))
        return 0

    # ── worktree ──────────────────────────────────────────────────────────────
    if args.command == "worktree":
        repo = args.repo or _repo_root_if_git(Path.cwd())
        if repo is None:
            return _err("not inside a git repository; pass --repo DIR")
        try:
            if args.wt_action == "list":
                found = engine.orphan_worktrees(repo)
                if found and "error" in found[0]:
                    return _err(found[0]["error"])
                _out(found)
            elif args.wt_action == "prune":
                _out(engine.prune_worktrees(repo))
        except _GOVERNANCE_ERRORS as exc:
            return _err(str(exc))
        return 0

    # ── accept ────────────────────────────────────────────────────────────────

    if args.command == "accept":
        try:
            _out(engine.accept_ticket(args.ticket_id, accepted_by=args.accepted_by, note=args.note))
        except _GOVERNANCE_ERRORS as exc:
            return _err(str(exc))
        return 0

    # ── memory ────────────────────────────────────────────────────────────────
    if args.command == "memory":
        try:
            if args.mem_action == "propose":
                _out(engine.propose_memory(
                    args.project_id,
                    args.source_run_id,
                    kind=args.kind,
                    statement=args.statement,
                    scope=args.scope,
                    evidence_ref=args.evidence,
                ))
            elif args.mem_action == "list":
                _out(engine.list_memories(args.project_id, status=args.status))
            elif args.mem_action == "approve":
                commit = args.source_commit or _current_commit(Path.cwd())
                _out(engine.review_memory(
                    args.memory_id, action="approve", reviewed_by=args.reviewed_by, note=args.note,
                    ttl_days=args.ttl_days, expires_at=args.expires_at, source_commit=commit,
                ))
            elif args.mem_action == "reject":
                _out(engine.review_memory(args.memory_id, action="reject", reviewed_by=args.reviewed_by, note=args.note))
            elif args.mem_action == "expire":
                _out(engine.expire_memories())
            elif args.mem_action == "context":
                sys.stdout.write(engine.get_project_active_context(args.project_id) + "\n")
        except _GOVERNANCE_ERRORS as exc:
            return _err(str(exc))
        return 0

    return 2




