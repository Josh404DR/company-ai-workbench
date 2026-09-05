# Current Handoff

- Stage: **Short-Task Auto-Debug Loop & Long-Task Goal Orchestration fully implemented and verified with Real Codex CLI (`gpt-5.5`)** (2026-09-06).
- Last reliable stopping point: **114/114 tests PASS** across all 5 test suites (`test_engine.py`, `test_governance.py`, `test_runner.py`, `test_worktree.py`, `test_goals_and_auto_debug.py`); real end-to-end Codex CLI runs verified in isolated worktrees.
- Major milestones completed:
  1. **Schema v6 (Goals & Dependencies)**:
     - Added `goals` table (`id`, `project_id`, `title`, `description`, `status CHECK in ('planned','in_progress','achieved','blocked','cancelled')`, `created_at`, `updated_at`).
     - Added `goal_id` and `depends_on_ticket_id` to `tickets` table.
  2. **Short Tasks (Ticket-internal Auto-Debug Loop)**:
     - `run_ticket_auto_debug_loop`: executes managed runs, automatically captures test failures and stderr/stdout diagnostics, records immutable `DebugEpisode` records with fingerprints, appends audit events, and injects diagnostic feedback into retry attempts.
  3. **Long Tasks (Goal Orchestration)**:
     - `advance_goal`: sequentially advances unblocked tickets under a Goal, checks dependencies, runs the auto-debug loop, tracks dynamic completion progress (`progress_pct`), and marks the Goal `achieved`.
     - Preserved Invariant 14 & 4: automated acceptance strictly limited to low-risk tickets with independent verification (`local-command`); medium and high-risk tickets halt for Josh's explicit review.
  4. **Real Codex CLI Runner (`gpt-5.5`) on Windows**:
     - Resolved the critical Windows batch `%*` limitation in npm's `codex.cmd` where newlines were stripped; `SubprocessExecutor` directly routes to `node.exe <codex.js>`, guaranteeing 100% prompt integrity.
     - Added `default_model` parameter and `CODEX_MODEL` env var support, defaulting to `gpt-5.5` for ChatGPT account compatibility.
     - Verified end-to-end against real Codex CLI with Git worktree isolation:
       - Single ticket auto-completion & auto-acceptance.
       - Multi-ticket sequential dependency pipeline (`Stage 1 -> Stage 2 -> Goal achieved`).
- Next action:
  - Dockerized prototype UI updates for Goal views / pipeline dashboard.
  - Expand delivery adapters (PR/merge).
- Remaining boundary: PySide6 desktop GUI, external GitHub PR integration.

