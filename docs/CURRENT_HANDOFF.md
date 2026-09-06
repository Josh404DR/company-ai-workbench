# Current Handoff

- Stage: **100% User-Ready Milestone Completion & Architecture Council Extreme Adversarial Verification** (2026-09-06).
- Last reliable stopping point: **135/135 tests PASS** across all 9 test suites (`test_engine.py`, `test_governance.py`, `test_runner.py`, `test_worktree.py`, `test_goals_and_auto_debug.py`, `test_cli_goals.py`, `test_ui_server.py`, `test_delivery.py`, `test_extreme_council.py`).
- Major milestones completed:
  1. **Schema v6 (Goals & Dependencies)**:
     - Added `goals` table (`id`, `project_id`, `title`, `description`, `status CHECK in ('planned','in_progress','achieved','blocked','cancelled')`, `created_at`, `updated_at`).
     - Added `goal_id` and `depends_on_ticket_id` to `tickets` table.
     - Centralized `_validate_goal_and_dependency()` enforcing same-project, same-goal, cycle detection (`A -> B -> A`, `A -> B -> C -> A`), and rejecting un-goaled dependencies across both `create_ticket()` and `link_ticket_to_goal()`.
  2. **Short Tasks (Ticket-internal Auto-Debug Loop)**:
     - `run_ticket_auto_debug_loop`: executes managed runs, automatically captures test failures and stderr/stdout diagnostics, records immutable `DebugEpisode` records with fingerprints, appends audit events, and injects diagnostic feedback into retry attempts.
  3. **Long Tasks (Goal Orchestration)**:
     - `advance_goal`: sequentially advances unblocked tickets under a Goal, checks dependencies, runs the auto-debug loop, tracks dynamic completion progress (`progress_pct`), and marks the Goal `achieved`.
     - Atomic ticket selection via `claim_next_runnable_ticket_for_goal()`.
     - Preserved Invariant 14 & 4: automated acceptance strictly limited to low-risk tickets with independent verification (`local-command`); medium and high-risk tickets halt for Josh's explicit review.
  4. **CLI Subcommands**:
     - Added `wb goal create`, `wb goal list`, `wb goal show`, `wb goal link`, `wb goal advance`.
     - Added `--goal-id` and `--depends-on` options to `wb ticket create`.
     - Added `wb ticket deliver` and `wb goal deliver` commands.
     - Added `wb ui` and `wb serve` commands with host, port, and auto-browser launching.
     - Registered `wb` command in `pyproject.toml` scripts for direct terminal access.
  5. **Web UI & Direct User Usability**:
     - Upgraded `src/company_workbench/ui_server.py` as official first-class UI module with `WORKBENCH_DB` env support.
     - Zero-friction project creation, goal creation, ticket creation, runner selection (Fake / Codex / Claude), auto-debug episodes view, SHA-256 evidence verification gate, Josh acceptance, and 1-click delivery.
     - One-click launcher `start-workbench.bat` for Windows users (double-click to auto-launch server and browser).
     - One-click launcher `start-workbench.sh` for Linux/macOS users.
     - Comprehensive `README.md` and `docs/USER_GUIDE.md` for end-users.
  6. **Native Multi-Model Runners & Process Hardening on Windows**:
     - Native `ClaudeCliRunner` integrated for Claude Code 2.1.260 (`claude.exe` direct invocation, `--dangerously-skip-permissions`, `--no-session-persistence`, JSON output).
     - Native `CodexCliRunner` with `node.exe <codex.js>` direct resolution bypassing Windows `.cmd` `%*` argument truncation.
     - Hardened node resolution via `_resolve_trusted_node()`, validating system ProgramFiles and preventing workspace/cwd relative binary poisoning.
  7. **Independent Architecture Council Review**:
     - Formally convened with Anthropic Claude Code, OpenAI Codex (`gpt-5.5`), and Antigravity.
     - Codex executed adversarial verification and validated fail-closed boundaries.
     - Formal consensus verdict: **PASS**. Documented in `docs/COUNCIL_REVIEW.md`.
  8. **Phase 5: Delivery Adapters (Invariant 9 Strict Enforcement)**:
     - Implemented `GitDeliveryAdapter` (`src/company_workbench/delivery.py`) with `merge_run_to_branch()`, `generate_patch()`, and `tag_delivery()`.
     - Enforces Invariant 9: Tickets must have `status == 'accepted'` with independent verification evidence before any merge to mainline or patch generation can occur.
     - Engine methods `deliver_ticket` and `deliver_goal` merge isolated run branches (`wb-run/<run_id>`) into mainline (`master`), generate patches, tag delivery milestones (`wb-delivery/<run_id>`), and append immutable audit log events (`delivery_completed`, `goal_delivered`).
  9. **Phase 6: Production Packaging & Containerization**:
     - Multi-stage hardened `Dockerfile` (Python 3.13-slim, Node.js 20, Git, SQLite3, pre-installed wheel).
     - Production `docker-compose.yml` with container healthchecks, volume persistence (`/data`), and host workspace mounting (`/workspace`).
     - `.dockerignore` configured to eliminate cache leaks and isolate runtime dependencies.

- Current Boundary & Hand-off Note:
  - All core phases (1 through 6) of Company AI Workbench are fully delivered, hardened, verified with 100% test coverage (128/128 PASS), and ready for direct end-user operation.
  - Out of scope / future extension: Desktop native PySide6 GUI and GitHub Enterprise cloud webhook integration.
