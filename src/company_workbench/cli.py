from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from .demo import run_demo
from .engine import WorkbenchEngine
from .errors import (
    NotFoundError,
    InvalidTransitionError,
    EvidenceRequiredError,
    AcceptanceRequiredError,
    RunnerLaunchError,
)
from .runner import CodexCliRunner


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
    commands.add_parser("diagnose")
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
    verify_cmd.add_argument("--evidence", required=True, metavar="REF")
    verify_cmd.add_argument("--summary", required=True)
    verify_cmd.add_argument("--verifier", default="cli-user")

    # ── accept ────────────────────────────────────────────────────────────────
    accept_cmd = commands.add_parser("accept")
    accept_cmd.add_argument("ticket_id")
    accept_cmd.add_argument("--by", dest="accepted_by", default="Josh")
    accept_cmd.add_argument("--note", default="")

    # ── reconcile ─────────────────────────────────────────────────────────────
    commands.add_parser("reconcile")

    args = parser.parse_args(argv)

    # ── demo (no engine needed) ───────────────────────────────────────────────
    if args.command == "demo":
        with tempfile.TemporaryDirectory(prefix="company-workbench-demo-") as temp:
            result = run_demo(Path(temp) / "demo.db")
        _out(result)
        return 0

    engine = WorkbenchEngine(args.database)

    # ── utility ───────────────────────────────────────────────────────────────
    if args.command == "diagnose":
        info = engine.diagnose()
        _out(info)
        return 0 if info["integrity"] == "ok" else 1

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
                _out(engine.create_ticket(args.project_id, args.title, args.goal, args.criteria))
            elif args.tkt_action == "show":
                _out(engine.get_ticket(args.ticket_id))
            elif args.tkt_action == "list":
                _out(engine.list_tickets(args.project_id))
        except (NotFoundError, ValueError) as exc:
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
                    )
                    _out(result)

            elif args.run_action == "complete":
                _out(engine.complete_run(args.run_id))
            elif args.run_action == "show":
                _out(engine.get_run(args.run_id))
            elif args.run_action == "events":
                _out(engine.list_events(args.run_id))
            elif args.run_action == "list":
                _out(engine.list_runs(args.ticket_id))
        except (NotFoundError, InvalidTransitionError, RunnerLaunchError, ValueError) as exc:
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
            ))
        except (NotFoundError, EvidenceRequiredError, InvalidTransitionError, ValueError) as exc:
            return _err(str(exc))
        return 0

    # ── accept ────────────────────────────────────────────────────────────────
    if args.command == "accept":
        try:
            _out(engine.accept_ticket(args.ticket_id, accepted_by=args.accepted_by, note=args.note))
        except (NotFoundError, AcceptanceRequiredError, InvalidTransitionError) as exc:
            return _err(str(exc))
        return 0

    return 2


