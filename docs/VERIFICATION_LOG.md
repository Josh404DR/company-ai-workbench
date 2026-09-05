# Verification Log

## 2026-09-06 — Short Tasks (Auto-Debug Loop) & Long Tasks (Goal Orchestration) with Real Codex CLI

- **Schema upgraded to `SCHEMA_VERSION = 6`**:
  - Added `goals` table (`id`, `project_id`, `title`, `description`, `status CHECK in ('planned','in_progress','achieved','blocked','cancelled')`, `created_at`, `updated_at`).
  - Added `goal_id REFERENCES goals(id)` and `depends_on_ticket_id REFERENCES tickets(id)` to `tickets`.
- **Short Task capability**:
  - Added `run_ticket_auto_debug_loop` to `WorkbenchEngine`: runs managed invocations with automated verification command, catches non-zero exits/test failures, records `DebugEpisode` with fingerprint & diagnostics, appends `auto_debug_attempt_failed` audit event, and dynamically augments the prompt with failure feedback for the next attempt.
- **Long Task capability**:
  - Added Goal orchestration: `create_goal`, `get_goal`, `list_goals`, `link_ticket_to_goal`, `get_next_runnable_ticket_for_goal`.
  - Added `advance_goal`: sequentially selects the next unblocked ticket (status `ready`), executes via `run_ticket_auto_debug_loop`, respects low-risk automated acceptance (`auto-acceptor`), and transitions Goal status to `achieved` upon 100% completion.
  - Preserved Invariant 14 & 4: high-risk tickets cannot be auto-accepted; `advance_goal` safely halts at `none_runnable` until human review (Josh) explicitly accepts the ticket.
- **Real Codex CLI Integration (`gpt-5.5`) on Windows**:
  - Discovered Windows `cmd.exe` batch limitation in `codex.cmd`: `%*` argument expansion strips newlines, truncating multiline prompts.
  - Fixed in `SubprocessExecutor`: automatically resolves npm global batch wrappers (`.cmd`) to direct `node.exe <codex.js>` invocation, preserving full multiline prompts, acceptance criteria, and diagnostic feedback without subprocess pipe deadlocks.
  - Added `default_model` parameter and `CODEX_MODEL` environment variable support to `CodexCliRunner`, defaulting to `gpt-5.5` for ChatGPT account compatibility.
  - Validated real end-to-end execution:
    - Single ticket run with isolated worktree: Codex wrote files, automated verification (`local-command`) passed, ticket auto-accepted, goal marked achieved.
    - Two-stage dependency pipeline: Ticket 1 completed & auto-accepted -> Ticket 2 unblocked, executed & auto-accepted -> Goal 100% achieved.
- **Automated Test Results**:
  - `tests/test_goals_and_auto_debug.py`: 8 tests (goal CRUD, ticket dependencies, immediate pass, debug loop recovery, max attempts exhaustion, goal pipeline orchestration, high-risk human acceptance requirement).
  - Official test suite (`test_engine.py`, `test_governance.py`, `test_runner.py`, `test_worktree.py`, `test_goals_and_auto_debug.py`): **114 tests passed in 11.83s**.


## 2026-09-02 — first engine vertical slice

Builder commands:

```powershell
$env:PYTHONPATH = "src"
py -3.13 -m company_workbench diagnose
py -3.13 -m company_workbench demo
py -3.13 -m unittest discover -s tests -v
py -3.13 -m company_workbench backup $backup
```

Results:

- Diagnosis PASS: SQLite integrity `ok`, schema version `2`.
- Demo PASS: Run completion left Ticket in `verification`; explicit Verification passed; Josh acceptance changed it to `accepted`; Memory Candidate remained `pending`; seven ordered events persisted.
- Unit tests PASS after architecture hardening: 11/11.
- Backup/restore PASS: backup is written to a verified temporary database and atomically replaces the target; it reopened from a second path with integrity `ok` and schema version `2`.
- Two real Windows lifecycle defects were found and fixed before PASS: SQLite connections were not explicitly closed, then the backup destination connection remained locked; migration version commit and idempotent v1 application were also corrected.
- Concurrency review reproduced `database is locked` on the first of eight simultaneous initializations. Root cause: WAL mode was configured before connection cleanup protection and concurrent WAL switching can require an exclusive lock. A regression now starts eight engines simultaneously; it passed in 20 consecutive focused runs after the fix.
- Acceptance audit now rejects repeated acceptance and pins the exact passing Verification ID in schema v2.
- Backup now rejects the source database as its destination and uses verified temporary output plus atomic replacement.

Claude review attempt:

- Claude Code 2.1.258, authenticated through a Claude Pro subscription, was invoked with `--permission-mode plan` and read-only `Read,Glob,Grep` tools.
- It produced no output for about two minutes and was terminated.
- Result: `stalled`, no verdict. This is not Independent Verify evidence.
- A second Claude read-only attempt using a different permission mode also stalled without output and was terminated; it likewise supplies no verdict.

Boundary:

- Fake Agent vertical slice only.
- No real Codex/Claude/OpenCode Runner, Git worktree adapter, PySide6 shell, SQLAlchemy/Alembic integration, RAG, sync, commit, push, PR, merge, deployment, production verification, Independent Verify PASS, or Josh acceptance of the product milestone.

## 2026-09-02 — schema v3 Builder remediation after Independent Verify FAIL

Independent review findings:

- Accepted Verification and Acceptance records remained mutable after Ticket acceptance.
- A Memory Candidate could reference a source Run from another Project.
- A legacy Acceptance without provable passing Verification evidence could be marked migrated.

Builder remediation:

- Schema v3 adds database triggers preventing UPDATE or DELETE of Verification and Acceptance audit records.
- `propose_memory()` verifies the source Run belongs to the requested Project before insert.
- Legacy migration backfills only a passing, evidenced Verification created no later than Acceptance; unresolved records abort migration without recording schema v2 or v3.
- Added regression tests for immutable audit records, cross-Project Memory rejection, successful legacy backfill, and fail-closed unresolved legacy migration.

Fresh Builder evidence:

- Focused legacy migration tests: 5/5 PASS.
- Full unit suite: 18/18 PASS on Python 3.13.
- Python compileall: PASS for `src/` and `tests/`.
- Diagnosis: SQLite integrity `ok`, schema version `3`.
- Complete Fake Agent demo: PASS with Ticket `verification` after Run completion, explicit Verification `passed`, Josh Acceptance `accepted`, Memory Candidate `pending`, and seven persisted events.
- Python 3.13 must run outside the managed sandbox because the sandbox account cannot execute the WindowsApps Python installation; this is an execution-environment boundary, not product test evidence.

Boundary:

- These results remediate the three reported blockers at Builder level.
- Two intermediate read-only verification rounds returned FAIL and exposed additional legacy migration cases; both were remediated before the final review.
- No real Runner, GUI, commit, push, PR, merge, deployment, paid provider call, or Josh product-milestone acceptance occurred.

Fresh Independent Verify:

- Final verdict: `PASS` for the bounded schema v3 remediation scope.
- Independent full suite: 18/18 PASS on Python 3.13.
- v2 adversarial records with failed status, blank evidence, or blank summary: 3/3 rejected; schema versions remained `[1, 2]`.
- v1 records with latest failed Verification, blank summary, or no Verification: 3/3 rejected; schema version remained `[1]`.
- Valid legacy v1 evidence backfilled and reached schema v3.
- Cross-Project and missing-source Memory Candidates failed closed without residual rows.
- Verification UPDATE/DELETE and Acceptance UPDATE/DELETE were all blocked by database triggers.
- The verifier made no repository changes.
- Unverified: real Runner, GUI, deployment, paid provider, Python 3.12, and cross-process high-stress concurrency.

## 2026-09-02 — Codex CLI Runner adapter execution boundary

Claude architecture review:

- Orca Run `run_743449d07f1b`, successful Dispatch `ctx_6f503a1cb999`.
- Claude reviewed governance and source read-only, identified cancellation, orphan recovery, output secrecy, error-code separation, and process-identity risks.
- Design decision: PID/invocation identity will use a later schema migration; Event payloads remain redacted audit summaries. `queued` remains unused until a dispatcher exists.

Builder implementation:

- Added allowlisted Codex executable invocation using argv and `shell=False`.
- Added cwd/prompt/timeout/output-limit validation, bounded stdout/stderr, secret redaction, and stable Runner outcome codes.
- Added live cancellation polling with terminate-then-kill fallback and timeout kill handling.

Fresh Builder evidence:

- Runner focused tests: 9/9 PASS.
- Full unit suite: 27/27 PASS on Python 3.13.
- The cancellation test launches only the local Python interpreter as a controlled sleeper; no Codex CLI or provider call occurred.

Boundary:

- Stage is `builder_checked`, not Independent Verify PASS.
- No Engine Run integration, schema v4, PID reuse protection, orphan reconciliation, real Codex smoke, GUI, commit, push, PR, merge, deployment, or paid provider call occurred.

First Independent Verify and remediation:

- Claude Dispatch `ctx_623dbb30591b` returned FAIL after 17 temporary-fixture adversarial tests.
- Blocking findings: path-prefixed executables could satisfy the basename allowlist; redaction missed common AWS/GitHub/Slack and multiline/caller-known secret values; subprocess output was fully buffered in memory before truncation.
- Builder added failing regression tests before fixing executable validation and redaction, changed real subprocess capture to disk-backed temporary files with bounded reads, and added real local-Python cancellation and timeout tests.

Fresh Builder evidence after remediation:

- Runner focused tests: 11/11 PASS.
- Full unit suite: 29/29 PASS on Python 3.13.
- Real local sleeper cancellation and timeout both terminated without invoking Codex or any provider.

Fresh Independent Verify:

- Claude Dispatch `ctx_50673bdc19b4` final verdict: `PASS` for the bounded Runner adapter scope.
- Independent existing tests: runner 11/11 PASS; full suite 29/29 PASS on Python 3.13.14.
- Independent temporary-fixture adversarial tests: 30/30 PASS covering executable impostors, literal argv, process cancellation/timeout and PID exit, disk-backed bounded capture, requested secret shapes, caller-supplied sensitive values, classification, and truncation.
- The verifier made no repository changes and did not invoke real Codex, paid APIs, deployment, or Git mutations.
- Non-blocking residual risks: system `PATH` poisoning is outside the string allowlist boundary; bare secrets without distinctive shapes require explicit `sensitive_values`.
- Still unverified: Engine integration, schema v4, orphan reconciliation, real Codex smoke, GUI, deployment, paid provider, Python 3.12, and cross-process stress.

## 2026-09-02 — schema v4 invocation identity, Engine-to-CodexCliRunner integration, orphan reconciliation

Stage: `independent_verify_pass`.

Scope: implement the four items the prior Runner Adapter Contract explicitly deferred — process
invocation identity in schema, atomic Engine/Runner integration, fail-closed startup orphan
reconciliation without killing on PID reuse, and keeping `queued` unused — with red/green tests, using
only `FakeExecutor`-style test doubles and local Python sleeper subprocesses. No real Codex/provider
call, no commit/push/PR/merge/deployment, no `ticket-coding-station` change.

Implementation:

- `store.py`: `SCHEMA_VERSION = 4`. Migration adds nullable `runs.invocation_id` and `runs.pid` columns
  plus `CREATE UNIQUE INDEX ... ON runs(invocation_id) WHERE invocation_id IS NOT NULL`, following the
  same commit-only-at-the-end-of-`_migrate()` pattern already used for v2/v3, so a data conflict during
  index creation aborts before schema version 4 is ever recorded (fail closed) and legacy v1-v3 rows are
  otherwise untouched (purely additive, nullable columns).
- `runner.py`: added `ProcessHandle` (spawned process, PID available immediately, `wait()` runs the
  existing poll/cancel/timeout loop and bounded disk-backed capture) and `SubprocessExecutor.start()`;
  `SubprocessExecutor.execute()` is now `start().wait()` with unchanged external behavior. Added
  `CodexCliRunner.start_invocation()` (validates inputs, spawns via `executor.start()`, returns a
  `RunnerInvocation` exposing `.pid` before blocking) and `RunnerInvocation.wait()`/`.cancel()`. Both
  `run()` and `RunnerInvocation.wait()` share one `_classify()` helper — the original `run()` outcome
  logic (cancelled/timeout/non-zero/empty-output/completed) is unchanged and reused, not duplicated.
- `errors.py`: added `RunnerLaunchError` (`WB-502-RUNNER-LAUNCH`) for spawn-time `OSError` (e.g. a
  missing executable), kept distinct from `ValueError` input-validation failures.
- `engine.py`: added `WorkbenchEngine.start_managed_run()` — spawns via `runner.start_invocation()`
  first (so PID is known), then commits Run row (with `invocation_id`/`pid`) + Ticket `active` +
  `run_started` Event in one transaction that re-validates both "no concurrent active Run" and current
  Ticket status; on any failure of that transaction the already-spawned process is cancelled and reaped
  before the error propagates, leaving zero Run/Ticket/Event rows. `_finalize_managed_run()` then
  commits the terminal outcome (`completed`/`failed`/`cancelled`) for Run + Ticket + a redacted
  `invocation_output` Event + a matching terminal Event, all in one transaction. Added
  `reconcile_orphan_runs()` (fails closed any Run still `status='running'`, records an optional
  best-effort `pid_alive_at_check` as evidence only, never signals/kills the PID, and is idempotent
  because it only ever touches rows still `running`) and `_default_pid_alive_checker()` (Windows:
  `OpenProcess` with `PROCESS_QUERY_LIMITED_INFORMATION`, read-only; POSIX: `os.kill(pid, 0)`).
  Event payloads for `run_started`/`invocation_output`/terminal events carry no `pid` or
  `invocation_id` key — that identity lives only in the `runs` row, per the schema-not-payload
  requirement.

Tests added (red before green in each case: assertion written and observed failing against the
pre-change code/behavior, then made to pass):

- `tests/test_runner.py`: `test_start_invocation_exposes_pid_before_wait_and_classifies_on_wait`,
  `test_start_invocation_validates_before_spawning`, `test_start_invocation_cancel_reports_cancelled_outcome`,
  `test_start_invocation_redacts_and_bounds_like_run`,
  `test_process_handle_start_then_wait_cancels_real_subprocess` (real local Python sleeper).
- `tests/test_engine.py`: `ManagedRunEngineTestCase` (completion, failure, redaction-before-persistence,
  launch-failure-leaves-no-partial-state, a real-subprocess cancellation test that polls the DB until the
  Run is visibly `running` with a real PID before cancelling mid-flight, a simple-rejection test, and a
  genuine two-thread race test forcing real transactional overlap); `OrphanReconciliationTestCase`
  (marks-failed-with-evidence, idempotency, multiple-stale-runs-in-one-pass, a real subprocess proving
  the OS process survives reconciliation untouched, and two direct tests of
  `_default_pid_alive_checker`); `SchemaV4MigrationTestCase` (fresh DB reaches v4 with the new columns, a
  v1-through-v3 legacy DB migrates to v4 preserving existing rows, `queued` stays unused by
  `start_managed_run`). Updated the pre-existing `StoreConcurrencyTestCase` and one
  `StoreMigrationTestCase` assertion from schema version `3` to `4` (the only two pre-existing
  assertions that needed to change; no other legacy behavior was altered).

Investigation note (test defect found and fixed, not a product defect): the first version of the
two-thread race test intermittently reported two Run rows for one Ticket. Timestamped tracing of
`BEGIN IMMEDIATE`/commit across both threads showed the Engine's atomic transaction was correct the
whole time: the fake process resolved effectively instantly, so one thread's full managed run
(persist-running, then finalize-completed) could complete and legitimately return the Ticket to
`verification` before the other thread's transaction ever acquired the write lock — making its
subsequent, separate Run legitimately valid, not a race violation. The test was corrected to hold the
winning fake process visibly `running` for a fixed short delay so the loser's check genuinely overlaps
it; it then deterministically reproduced "loser is cancelled and reaped, exactly one Run row persists"
across 25 consecutive runs. No engine code was changed by this investigation.

Fresh Builder evidence (Python 3.13.14, `PYTHONPATH=src`):

```powershell
py -3.13 -m compileall src tests
py -3.13 -m unittest tests.test_runner -v
py -3.13 -m unittest tests.test_engine -v
py -3.13 -m unittest discover -s tests -v
py -3.13 -m company_workbench diagnose
py -3.13 -m company_workbench demo
```

- `compileall`: PASS for `src/` and `tests/`.
- Runner focused tests: 16/16 PASS.
- Engine focused tests: 34/34 PASS.
- Full suite: 50/50 PASS; re-run 15 consecutive times with no flakiness (after the race-test fix above),
  plus the two-thread race test specifically re-run 25 consecutive times with no flakiness.
- `diagnose`: integrity `ok`, schema version `4`, exit code `0`.
- Fake demo: PASS, unchanged shape from the schema v3 evidence (`ticket_status_after_run=verification`,
  `verification=passed`, `ticket_status_after_acceptance=accepted`, `memory_candidate=pending`,
  `event_count=7`) — the demo still uses the original `start_run`/`complete_run` path, not
  `start_managed_run`, so this is a pure regression check that schema v4 does not disturb the v1-v3
  vertical slice.
- No real `codex` executable was ever invoked; all managed-run and reconciliation tests use either
  `FakeExecutor`-style doubles or a real local `python -c "import time; time.sleep(...)"` subprocess
  standing in for a Codex process. No file outside `E:\Workspace\company-ai-workbench` was modified. No
  git commit, push, PR, merge, or deployment occurred.

Boundary:

- This is Builder-level evidence only: `builder_checked_pending_independent_verify`. No Independent
  Verify dispatch ran against this scope.
- Not exercised: real Codex CLI, GUI, deployment, paid provider, Python 3.12, high-volume cross-process
  stress beyond the two-thread race test above, and automatic startup wiring of
  `reconcile_orphan_runs()` (it exists as an explicit method only; nothing calls it from `__init__` or
  the CLI yet).
- A full formal Debug Episode is intentionally not auto-generated for failed/cancelled managed Runs
  (that requires real root-cause analysis and stays a separate, explicitly-invoked
  `record_debug_episode()` call); the redacted `invocation_output` Event is the auditable evidence
  baseline for terminal outcomes at this stage. This is a documented design boundary, not an oversight
  — see `docs/RUNNER_ADAPTER_CONTRACT.md` v0.2.

Fresh Independent Verify:

- Antigravity Dispatch `conv_4f60bdf1`, 2026-09-02. Final verdict: `PASS` for the bounded schema v4 /
  Engine integration / orphan reconciliation scope.
- Independent test suite: compileall PASS; runner 16/16 PASS; engine 34/34 PASS; full 50/50 PASS on
  Python 3.13.14.
- Adversarial probes (7/7 PASS): `invocation_id` partial-unique-index enforcement (duplicate non-null
  rejected, two NULLs accepted); spawn failure leaves zero Run/Ticket/Event rows (`RunnerLaunchError`
  surfaces, Ticket stays `ready`); orphan idempotency (second call is a no-op); PID non-termination
  (live sleeper process survives `reconcile_orphan_runs()` untouched); `queued` never written by
  `start_managed_run()`; Event payload secrecy (no `pid`/`invocation_id` key in any payload, only
  boolean `pid_alive_at_check` in `run_reconciled`); two-thread race (exactly one Run persists, loser
  fail-closed).
- Constitution invariant check PASS: INV1 (Run completion never accepts); INV2 (Verification requires
  persisted evidence); INV4 (append-only Events enforced by DB triggers); INV8 (no direct
  `sqlite3.connect` outside `engine.py`/`store.py`).
- Non-blocking findings (documented design choices, not defects): `reconcile_orphan_runs()` is not
  auto-wired into `__init__` or any CLI command; Debug Episode is not auto-generated for
  failed/cancelled managed Runs; `_default_pid_alive_checker` is best-effort on Windows.
- The verifier made no repository changes. No real Codex executable, paid API, Git mutation, or
  deployment was invoked.
- Still unverified: real Codex CLI smoke, Python 3.12, PySide6 GUI, deployment, high-volume
  cross-process stress, automatic startup wiring of `reconcile_orphan_runs()`.

---

## 2026-09-02 Phase 2 Hardening, Worktree Isolation & Auto-Verification Independent Verify

Scope:
- `.env` secret protection in `.gitignore`.
- Command injection hardening in `worktree.py` (`shell=False`, `shlex.split(posix=False)`).
- `GeminiRunner` integration with `RunnerInvocation` handle and `start_managed_run`.
- Worktree cleanup on launch failure across all exception paths (`ValueError`, `RunnerLaunchError`, `OSError`, `Exception`).
- Automated Worktree Verification Execution (`--verify-cmd` pass/fail gates).
- Constitution invariants 1, 2, 4, 8, 10.

Evidence:
- Antigravity Dispatch `0933af45-d781-4506-94f0-a2212d9f9511` (Claude Independent Verifier), 2026-09-02.
- Test Suite: 57/57 unit tests PASS (Python 3.13.14), `compileall` PASS, `diagnose` PASS.
- Adversarial probes:
  - Command injection probe: string tokens with `;` / `&&` safely parsed without shell execution.
  - Secret protection probe: `.env`, `.env.*`, `*.env` untracked in git status.
  - Worktree cleanup probe on launch failure: temporary directories purged immediately.
- Final Verdict: `PASS`.

---

## 2026-09-02 Phase 3 Memory Promotion & Review Independent Verify

Scope:
- `Engine.propose_memory()`: Initial `pending` status, metadata validation, cross-project protection.
- `Engine.review_memory()`: Enforces Invariant 6 ("never self-promote"), requires `reviewed_by='Josh'`.
- `Engine.get_project_active_context()`: Safe injection containing ONLY `approved` memories.
- CLI commands: `wb memory propose`, `wb memory list`, `wb memory approve`, `wb memory reject`.
- Constitution Invariants 6 and 10.

Evidence:
- Antigravity Dispatch `636ad098-fe85-4bc9-bc7e-1c1e1521e82d` (Claude Independent Verifier), 2026-09-02.
- Test Suite: 57/57 unit tests PASS (Python 3.13.14), `compileall` PASS, `diagnose` PASS.
- Adversarial probes:
  - Non-Josh approval attempts (`"AI"`, `"admin"`, `""`) rejected with `AcceptanceRequiredError`.
  - Re-approving already approved memory rejected with `InvalidTransitionError`.
  - Context leakage probe: `pending`, `rejected`, and `disabled` memories confirmed blocked from active context.
- Final Verdict: `PASS`.




---

## 2026-09-02 Governance Hardening v0.2 (Builder-level, NOT independently verified)

Status: `builder_checked_pending_independent_verify`. The Builder was Claude (Fable 5.1) in this session; by the
spirit of Invariant 11 the independent verifier for this round should not be Claude.

Scope:
- Schema v5: `tickets.risk_level`, `runs.{input_tokens,output_tokens,cost_usd,provider_account}`,
  `verifications.{verifier_provider,evidence_sha256}`, append-only `evidence_artifacts`, `memory_candidates` rebuilt
  with `approved_at/expires_at/source_commit/reviewed_by` and status `expired`.
- Engine: `provider_of()`, `verify_run` content-addressed + independence gate, `_insert_acceptance` re-check,
  acceptance authority per risk tier, `import_tickets`, `review_memory` expiry, `expire_memories`,
  `get_project_active_context` time filter, `record_run_usage`, `usage_summary`, `_retire_worktree`,
  `prune_worktrees`, `orphan_worktrees`, extended `diagnose`.
- Runner: usage extraction/normalization; Gemini `usageMetadata` captured.
- Worktree: `commit_all`, `list_run_worktrees`; missing `Any` import fixed.
- CLI: `ticket --risk`, `ticket import`, `run --provider-account/--keep-worktree/--auto-accept-low-risk`, `run usage`,
  `verify --evidence-text|--evidence-file --verifier-provider`, `evidence show|check`, `worktree list|prune`,
  `memory approve --ttl-days/--expires-at/--commit`, `memory expire|context`, `diagnose --repo`.
- Prototype UI `/verify` updated to the new signature.

Builder evidence (Python 3.13 via uv, `PYTHONPATH=src`):
- 97/97 PASS, 30 subtests (57 pre-existing + 40 new in `tests/test_governance.py`).
- `compileall src tests` PASS.
- Real database: backup taken, `diagnose` integrity ok, schema 5, evidence ok, `worktree prune` retired
  `RUN-6ae9f4c6` (commit `7c9ffeac` on `wb-run/RUN-6ae9f4c6`, directory removed).
- Adversarial tests included: same-family verifier for codex/gemini/fake builders, legacy Verification without
  provider blocked at acceptance, evidence tampering (trigger dropped, blob edited) blocked at acceptance and
  reported by `check_evidence_integrity`, automated acceptor refused above `low`, memory renewal by non-Josh refused,
  import duplicates inside file and against project, prune leaves `running` worktrees alone.

Known limits:
- Codex usage parsing is best-effort against `exec --json`; unverified against a real Codex process.
- `cost_usd` requires a caller-supplied pricing table; no prices are hard-coded.
- Backup `pre-v5-20260902.db` is post-migration (CLI migrates on open).

---

## 2026-09-02 Second-Pass Adversarial Review of Governance Hardening v0.2 (Sonnet 5)

Status: still `builder_checked_pending_independent_verify` overall. This pass was run by Claude Sonnet 5
against Claude Fable 5.1's build in the same session. By the engine's own `provider_of()` rules both
collapse to the `anthropic` family, so **this does not satisfy Invariant 11's independence bar** and is
not a substitute for a cross-provider verifier. It is a genuine second read that found real bugs.

Findings and fixes:
1. `provider_account` was stored and returned raw with no redaction. A secret-shaped value
   (`sk-live-...`, `Authorization: Bearer ...`) pasted into `--provider-account` would sit in the `runs`
   table and in `usage_recorded` Event payloads unredacted — a live Invariant 10 violation surface, not
   just a hypothetical one. Fixed: both write paths (`_finalize_managed_run`, `record_run_usage`) now run
   the value through the same secret-pattern redaction Runner stdout/stderr already uses
   (`_sanitize_label`, reusing `runner._redact`).
2. `review_memory(..., ttl_days=True)` was silently accepted as `ttl_days=1` because `bool` is a subtype
   of `int` in Python. Fixed: `ttl_days` now explicitly rejects non-`int` and `bool` values.

Also probed and confirmed correct (no fix needed): zero-token usage distinguishable from unknown,
whitespace-only evidence content refused, verifier-independence collision is case-insensitive, two
different unknown-provider labels correctly collide under the fail-closed default, negative `ttl_days`
already rejected, automated acceptance above `low` tier already refused at Engine construction, ticket
import already rejects non-dict JSON entries.

Evidence: `tests/test_governance.py::SecondPassAdversarialTestCase` (3 new tests) plus the ad hoc probe
script that surfaced the findings above. Full suite: 100/100 PASS (30 subtests), Python 3.13 via
`PYTHONPATH=src uv run --no-project --python 3.13 --with pytest python -m pytest -q`.

Still open: a true cross-provider independent verify has not happened for this round.
