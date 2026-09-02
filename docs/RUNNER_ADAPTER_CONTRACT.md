# Runner Adapter Contract v0.2

document_owner: Company AI Workbench product and engineering  
authority_level: supporting  
status: builder_checked_pending_independent_verify  
last_verified: 2026-09-02

## Boundary

The first adapter targets local Codex CLI execution. It does not prove a real Codex login, provider call,
paid generation, process recovery under real Codex load, or deployment. Schema v4 invocation identity,
Engine-to-CodexCliRunner integration, and startup orphan reconciliation are now implemented at Builder
level (`builder_checked_pending_independent_verify`), exercised only against `FakeExecutor`-style test
doubles and local Python sleeper subprocesses — never a real Codex process.

## Execution contract

- Invoke an allowlisted Codex executable with an argument sequence and `shell=False`; never compose a shell command string.
- Require an existing working directory, a non-empty NUL-free prompt, a bounded timeout, and bounded captured output.
- Poll cancellation while the child process is running. Terminate first, then kill if it does not exit promptly.
- Classify completed, non-zero exit, timeout, cancellation, and empty-success output with Runner-specific error codes.
- Redact common bearer token, API key, token, password, OpenAI/Google/AWS/GitHub/Slack token shapes, plus caller-supplied sensitive values, before returning output to Engine or Event layers.
- Keep stdout and stderr bounded while retaining both the beginning and end plus an explicit truncation marker.
- `CodexCliRunner.start_invocation()` spawns the process and returns immediately with its PID (via a
  `ProcessExecutor.start()` / `ProcessHandle.wait()` split), so a caller can persist PID/invocation
  identity before ever blocking on completion. `run()` remains the original single blocking call for
  callers that do not need this split.

## Engine integration contract (implemented, schema v4)

- `runs` gained nullable `invocation_id` (a Runner-invocation UUID assigned by the Engine, not the
  Runner) and `pid` columns, plus a partial `UNIQUE(invocation_id) WHERE invocation_id IS NOT NULL`
  index. Process/invocation identity lives only in this schema, never in Event payloads.
- `WorkbenchEngine.start_managed_run()` spawns the invocation first (so the PID is known), then commits
  Run row + invocation identity + Ticket `active` transition + a `run_started` Event in one atomic
  transaction before ever blocking on the invocation's completion. If that transaction loses a race
  (ticket no longer eligible, or a concurrent Run won first), the already-spawned process is cancelled
  and reaped before the error propagates — no Run/Ticket/Event row is left behind either way.
- Redaction happens inside the Runner (`RunnerInvocation.wait()`) before the Engine ever persists an
  Event, so `invocation_output` events always carry already-redacted stdout/stderr.
- Terminal outcomes are finalized in a second atomic transaction: `completed` -> Run `completed` +
  Ticket `verification`; `failed` / `cancelled` -> Run `failed`/`cancelled` + Ticket `ready`, each paired
  with a matching terminal Event (`run_completed` / `run_failed` / `run_cancelled`) carrying the
  Runner's `error_code`. A full formal Debug Episode (root cause, accepted fix) is **not** auto-generated
  for a failed/cancelled managed Run — that requires real analysis and stays a separate,
  explicitly-invoked `record_debug_episode()` call; the redacted `invocation_output` Event is the
  auditable evidence baseline for terminal outcomes at this Builder stage.
- `WorkbenchEngine.reconcile_orphan_runs()` fails closed any Run still `running` at the time it is
  called (intended as a startup step, but not yet auto-wired into any constructor or CLI command — a
  caller must invoke it explicitly): Run -> `failed` with `error_code='RUNNER-ORPHANED'`, Ticket ->
  `ready`, plus a `run_reconciled` Event carrying an optional, best-effort `pid_alive_at_check` flag.
  That flag is diagnostic evidence only; it is never used to decide whether to signal or terminate the
  stored PID, because the PID may have been reused by an unrelated process since the original
  invocation exited. Reconciliation is idempotent: only rows still `running` are touched, so a repeat
  call after a completed pass is a no-op.
- `queued` remains unused: `start_managed_run()` only ever writes `running` directly; no dispatcher
  exists yet.

## Deferred integration contract

- Automatic startup wiring of `reconcile_orphan_runs()` into Engine construction or the CLI is not yet
  decided or implemented; it remains an explicit, caller-invoked method for this bounded slice.
- A real dispatcher that would make `queued` meaningful does not exist yet.
- A real Codex CLI smoke requires separate authorization and must report CLI readiness separately from provider/model execution.
- PySide6 shell, deployment automation, and cross-process high-stress concurrency remain out of scope.

## Residual risks

- A poisoned system `PATH` can redirect a bare executable lookup; deployment/runtime setup must control `PATH` provenance.
- Bare secret values without a distinctive token shape cannot be reliably detected without false positives; callers must supply known values through `sensitive_values`.
- `_default_pid_alive_checker()` is a best-effort, read-only probe (`OpenProcess` with
  `PROCESS_QUERY_LIMITED_INFORMATION` on Windows, `os.kill(pid, 0)` elsewhere); it can return `None` when
  liveness cannot be determined, and its result must never be used to justify acting on the process.

## Usage and worktree retirement (v0.3 builder-level, 2026-09-02)

- `ProcessResult.usage` / `RunnerResult.usage`: optional `{input_tokens, output_tokens}`. `_classify()` accepts a
  provider-shaped mapping (Gemini `usageMetadata`, OpenAI-style `usage`) or scans JSON/JSONL stdout for a `usage`
  object (Codex `exec --json`). Missing usage stays `None`; the Engine persists NULL, never zero.
- `start_managed_run(..., provider_account=, keep_worktree=)`: the account label is stored on the Run row only.
- After the terminal transaction, an isolated worktree is retired: `commit_all()` onto `wb-run/<run>`, directory
  removed unless `keep_worktree`, then a `worktree_retired` Event. A commit failure keeps the directory and records
  `commit_error` so no work product is lost.
- Automated verification evidence is the JSON of the verification result, hashed and stored; its
  `verifier_provider` is `local-command`, which is independent of every model provider by construction.
