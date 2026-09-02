# Current Handoff

- Stage: **Governance hardening v0.2 is `builder_checked_pending_independent_verify`** (Claude Builder, 2026-09-02). Everything through Phase 3 remains `independent_verify_pass`.
- Last reliable stopping point: 97/97 tests PASS (30 subtests) on Python 3.13 via
  `PYTHONPATH=src uv run --no-project --python 3.13 --with pytest python -m pytest -q`; `compileall` PASS; `diagnose` PASS on the real database (schema v5, evidence ok, 0 orphan worktrees).
- What this round added (schema v5, all additive; memory_candidates rebuilt for the new status set):
  1. Invariant 11 verifier independence: `verify_run(..., verifier_provider=)` rejects same-family verifier/builder; acceptance re-checks the pinned Verification.
  2. Content-addressed evidence: `evidence_content` / `evidence_path` hashed into append-only `evidence_artifacts`; acceptance refuses missing or mismatched evidence; `wb evidence show|check`.
  3. Memory expiry: approval carries `expires_at` (default 90 days), `source_commit`, `reviewed_by`; expired memories never injected; `wb memory expire|context`.
  4. Run usage: `input_tokens`, `output_tokens`, `cost_usd` (needs a pricing table), `provider_account`; `wb run usage`; `diagnose` shows per-runner totals.
  5. Tiered acceptance: Ticket `risk_level` (default high, fixed at creation); `TIERED_ACCEPTANCE_AUTHORITY` lets the automated acceptor close low-risk Tickets after a passing `--verify-cmd`; CLI flag `--auto-accept-low-risk`.
  6. Ticket import: `wb ticket import PROJECT FILE` (JSON or Markdown), all-or-nothing, duplicate-safe.
  7. Worktree lifecycle: Run worktrees are committed to `wb-run/<run>` and removed at finalization; `wb worktree list|prune`. Leftover `RUN-6ae9f4c6` was pruned (commit `7c9ffea` on its branch).
- Real database notes:
  - `.workbench/backups/pre-v5-20260902.db` was taken through the CLI, so it is already at schema v5 (the CLI migrates on open). The migration was additive; the two legacy Verifications keep NULL provider/hash and can no longer back a new Acceptance (existing Acceptances untouched).
  - Both real Runs have `runs_without_usage=1`: usage is only captured for Runs started after this change.
- Next action:
  - Independent verification of this round (a verifier that is not Claude, per the spirit of Invariant 11).
  - Dogfood: run real Tickets through `wb ticket import` -> `wb run start --worktree --verify-cmd` -> `wb verify` -> `wb accept` for two weeks before expanding Runners or building delivery adapters.
- Source boundary: `ticket-coding-station` was not modified. Nothing was committed or pushed.
- Remaining boundary: real Codex CLI execution (upstream quota until 9/22), PySide6 GUI, deployment, PR/merge/deploy adapters.
