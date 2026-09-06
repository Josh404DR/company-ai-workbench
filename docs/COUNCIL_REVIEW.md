# Architecture Council Review Verdict & Consensus Report

**Date**: 2026-09-06  
**Session**: Milestone Architecture & Security Council (Short/Long Tasks, CLI, UI, Windows Isolation)  
**Council Reviewers**:
- **Anthropic Family**: Claude Code (Claude 3.7 Sonnet / claude.exe native runner)
- **OpenAI Family**: OpenAI Codex CLI (`gpt-5.5` Senior Principal Reviewer)
- **Google DeepMind Family**: Antigravity Assistant (Autonomous Coordinator)

---

## 1. Executive Summary & Verdict

### Final Consensus Verdict: **PASS (with non-blocking hardening recommendations)**

The Architecture Council performed an independent, cross-model governance and security audit of the `company-ai-workbench` Milestone:
- **Schema v6**: Long-task `goals` and ticket dependency DAGs (`goal_id`, `depends_on_ticket_id`).
- **Short Tasks**: `run_ticket_auto_debug_loop` in `WorkbenchEngine`, capturing diagnostics into immutable `DebugEpisode` records and feeding failure traces into subsequent retry attempts.
- **Long Tasks**: `advance_goal` in `WorkbenchEngine`, managing sequential ticket execution, progress tracking, and automated acceptance.
- **CLI Commands**: `wb goal create/list/show/link/advance` and `--goal-id` / `--depends-on` on `wb ticket create`.
- **Web UI Upgrade**: Goal progress dashboard, dependency links, one-click advance, and auto-debug episode inspection.
- **Runner Upgrades**: Native `ClaudeCliRunner` on Windows and hardened Node resolution in `SubprocessExecutor`.

Across adversarial probes, dependency edge validations, process isolation checks, and the full 122-test automated suite (`122/122 PASS`), the Council confirmed that **Engine Constitution Invariants 1, 3, 4, 5, 11, and 14 remain strictly inviolate**.

---

## 2. Invariant-by-Invariant Evaluation

| Constitution Invariant | Requirement | Status | Council Verification Findings |
|---|---|---|---|
| **Invariant 1 & 3** | Run completion never accepts a Ticket; acceptance strictly requires passing independent verification. | **PASS** | `_finalize_managed_run` marks run completed into `verification` status; acceptance is never granted without an independent verification record. |
| **Invariant 4 & 14** | Automated acceptance is strictly limited to `low` risk tickets. `medium` and `high` risk tickets MUST halt for human review (Josh). | **PASS** | Engine construction strictly rejects `AUTO_ACCEPTOR` on non-low tiers. Adversarial test probe confirmed `medium` and `high` tickets remain in `verification` with `accepted_by=None` even when `advance_goal(..., auto_accept_low_risk=True)` is called. |
| **Invariant 5** | Isolated Git worktrees committed to `wb-run/<run>` branches. | **PASS** | Worktree branches survive directory teardown, providing auditable git commit history for all short and long runs. |
| **Invariant 11** | Verifier must be independent of builder (openai / anthropic / google / local-command / human). | **PASS** | Auto-verifier runs local-command verifications (`exit 0`), which are provider-independent by construction. |

---

## 3. Findings, Council Critiques & Implemented Remediations

During initial council rounds, the external Reviewer (`gpt-5.5`) identified four critical architectural gaps, all of which were remediated and verified in the current codebase:

### Finding 1: Dependency & Goal Boundary Validation (Remediated)
- **Issue**: `link_ticket_to_goal` checked only self-dependency. Furthermore, `create_ticket(..., goal_id=..., depends_on_ticket_id=...)` bypassed checks altogether.
- **Remediation**: Centralized `_validate_goal_and_dependency()` called by **both** `create_ticket()` and `link_ticket_to_goal()`:
  - Rejects `depends_on_ticket_id` if `goal_id` is missing (dependencies must be Goal-scoped).
  - Enforces same-project and same-goal constraints.
  - Prohibits self-dependency.
  - Implements depth cycle detection preventing circular dependency graphs (e.g. `A -> B -> A` and `A -> B -> C -> A`).
- **Tests Added**: `test_create_ticket_prevents_cycles_and_cross_goal_dependency`, `test_link_ticket_prevents_cycles_and_cross_goal_dependency` (including 3-node cycle tests).

### Finding 2: Concurrency & Duplicate-Run Race in Goal Advancement (Remediated)
- **Issue**: Concurrent callers to `advance_goal` could pick the same `ready` ticket outside a transaction. If a ticket completed into `verification`, a second caller could launch another run because `start_managed_run` previously allowed starting from `verification`.
- **Remediation**:
  - Implemented `claim_next_runnable_ticket_for_goal()` executing atomic eligibility check inside `store.transaction()`, ensuring no active runs exist (`queued`/`running`).
  - Restricted `start_managed_run` strictly to `status == 'ready'`, preventing duplicate runs from starting on tickets in `verification`.

### Finding 3: `auto_accept_low_risk` Parameter Alignment (Remediated)
- **Issue**: Parameter was declared on `advance_goal` but not forwarded down to `_finalize_managed_run`.
- **Remediation**: Threaded `auto_accept` through `advance_goal` -> `run_ticket_auto_debug_loop` -> `start_managed_run` -> `_finalize_managed_run`. Setting `auto_accept_low_risk=False` preserves manual review for low-risk tickets.
- **Tests Added**: `test_advance_goal_honors_auto_accept_low_risk_false`.

### Finding 4: Windows Process Execution & Node Resolution Hardening (Remediated)
- **Issue**: Using raw `shutil.which("node")` risked picking up a malicious `node.exe` if placed in the working directory.
- **Remediation**: Added `_resolve_trusted_node(cwd)`:
  - Checks explicit `WORKBENCH_NODE_PATH` environment variable.
  - Checks standard system installation paths (`C:\Program Files\nodejs\node.exe` and `C:\Program Files (x86)\nodejs\node.exe`).
  - Validates any fallback `PATH` binary is absolute and strictly **outside** `cwd`.

---

## 4. Test Verification Matrix

All 7 test suites pass cleanly:
```
tests.test_cli_goals                  ... OK (6 tests)
tests.test_engine                     ... OK (35 tests)
tests.test_goals_and_auto_debug       ... OK (11 tests)
tests.test_governance                 ... OK (22 tests)
tests.test_runner                     ... OK (20 tests)
tests.test_ui_server                  ... OK (2 tests)
tests.test_worktree                   ... OK (26 tests)
----------------------------------------------------------------------
Ran 122 tests in 13.060s — 100% PASS (OK)
```

---

## 5. Non-Blocking Future Hardening Recommendations

1. **Ticket Claim State**: Transition tickets to an explicit intermediate `dispatching` state upon selection in `claim_next_runnable_ticket_for_goal` to avoid redundant process spawning under high concurrency.
2. **Path Hardening for Multi-User Deployment**: Require explicit `WORKBENCH_NODE_PATH` in multi-tenant production configurations.
