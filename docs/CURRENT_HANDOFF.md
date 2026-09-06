# Current Handoff

- Stage: **Milestone Fully Implemented, Hardened, and Passed by Independent Multi-Model Architecture Council** (2026-09-06).
- Last reliable stopping point: **122/122 tests PASS** across all 7 test suites (`test_engine.py`, `test_governance.py`, `test_runner.py`, `test_worktree.py`, `test_goals_and_auto_debug.py`, `test_cli_goals.py`, `test_ui_server.py`).
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
  5. **Web UI Upgrade (`prototype/ui_server.py`)**:
     - Goal creation card, dynamic Goal Dashboard with progress percentage and status badges.
     - Linked tickets display `Goal #` and `依賴 #` tags.
     - One-click advance button for active goals.
     - Expanded DebugEpisode failure history on ticket cards.
  6. **Native Multi-Model Runners & Process Hardening on Windows**:
     - Native `ClaudeCliRunner` integrated for Claude Code 2.1.260 (`claude.exe` direct invocation, `--dangerously-skip-permissions`, `--no-session-persistence`, JSON output).
     - Native `CodexCliRunner` with `node.exe <codex.js>` direct resolution bypassing Windows `.cmd` `%*` argument truncation.
     - Hardened node resolution via `_resolve_trusted_node()`, validating system ProgramFiles and preventing workspace/cwd relative binary poisoning.
  7. **Independent Architecture Council Review**:
     - Formally convened with Anthropic Claude Code, OpenAI Codex (`gpt-5.5`), and Antigravity.
     - Codex executed adversarial verification and validated fail-closed boundaries.
     - Formal consensus verdict: **PASS**. Documented in `docs/COUNCIL_REVIEW.md`.
- Next action:
  - Dockerized prototype UI packaging / deployment.
  - Expand delivery adapters (PR/merge).
- Remaining boundary: PySide6 desktop GUI, external GitHub PR integration.
