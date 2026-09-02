# Engine Constitution v0.2

document_owner: Company AI Workbench product and engineering  
authority_level: canonical_for_engine_v0  
status: proposed_pending_josh_acceptance  
last_verified: 2026-09-02

## Product boundary

The engine owns work state, audit history, evidence gates, memory candidates, and adapter contracts. Desktop, CLI, Web, and API are replaceable shells.

## Invariants

1. Run completion never accepts a Ticket.
2. Verification requires persisted, content-addressed evidence: the evidence body is stored append-only under its sha256 and the Verification pins that hash. A label alone is not evidence.
3. Ticket acceptance requires an acceptance authority for the Ticket's risk level, a completed latest Run, and passing independent Verification whose evidence still matches its hash. The default authority is Josh for every tier. Only the `low` tier may be delegated to the automated acceptor, and only by explicit engine configuration. Risk level is fixed at Ticket creation. The Acceptance record pins the Verification and can only be created once.
4. Events are append-only at the database boundary.
5. Failed and cancelled work remains auditable, including the files a Run produced: a Run worktree is committed to its `wb-run/<run>` branch before its directory is removed.
6. Memory and Skill candidates never self-promote. Approval requires Josh and always carries an expiry; expired memories are never injected and can only be renewed by Josh.
7. Provider-specific behavior stays behind adapters.
8. UI does not directly mutate persistence or invoke tools.
9. Commit, push, PR, merge, deployment, production verification, and Ticket acceptance are distinct claims.
10. Secrets and customer material do not enter shared memory or diagnostics.
11. The verifier must be independent of the builder: a Verification's `verifier_provider` may not belong to the same provider family as the Run's runner (openai / google / anthropic / human / local-command / other). A legacy Verification without a provider cannot back a new Acceptance.
12. Token usage and provider account are first-class Run evidence. Unknown usage is recorded as NULL, never as zero.

## First vertical slice

Workspace → Project → Ticket → Fake Run → Debug Episode → completed Run → Verification → Josh Acceptance → pending Memory Candidate.

## Governance surface (v0.2)

- Ticket: `risk_level` in {low, medium, high}, default high. Batch import from JSON/Markdown is all-or-nothing.
- Verification: `verifier_provider`, `evidence_sha256`; `evidence_artifacts` table is append-only.
- Acceptance authority: `DEFAULT_ACCEPTANCE_AUTHORITY` (Josh everywhere) or `TIERED_ACCEPTANCE_AUTHORITY` (low may be auto-accepted after a passing local verification command).
- Memory: `approved_at`, `expires_at` (default TTL 90 days), `source_commit`, `reviewed_by`; status `expired` exists; `expire_memories()` sweeps with an Event.
- Run: `input_tokens`, `output_tokens`, `cost_usd` (only when a pricing table is configured), `provider_account`.
- Worktree: retired at Run finalization (commit to branch, remove directory, `worktree_retired` Event); `prune_worktrees()` handles leftovers.

## Explicitly deferred

PySide6 UI, real Codex execution, Skill promotion, RAG, vector search, central sync, multi-user RBAC, model-account routing, deployment automation, PR/merge/deploy adapters, and autonomous mutation of formal policy.
