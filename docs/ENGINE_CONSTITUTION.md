# Engine Constitution v0.1

document_owner: Company AI Workbench product and engineering  
authority_level: canonical_for_engine_v0  
status: proposed_pending_josh_acceptance  
last_verified: 2026-09-02

## Product boundary

The engine owns work state, audit history, evidence gates, memory candidates, and adapter contracts. Desktop, CLI, Web, and API are replaceable shells.

## Invariants

1. Run completion never accepts a Ticket.
2. Verification requires persisted evidence.
3. Ticket acceptance requires Josh, a completed latest Run, and passing Verification evidence; the Acceptance record pins that Verification and can only be created once.
4. Events are append-only at the database boundary.
5. Failed and cancelled work remains auditable.
6. Memory and Skill candidates never self-promote.
7. Provider-specific behavior stays behind adapters.
8. UI does not directly mutate persistence or invoke tools.
9. Commit, push, PR, merge, deployment, production verification, and Ticket acceptance are distinct claims.
10. Secrets and customer material do not enter shared memory or diagnostics.

## First vertical slice

Workspace → Project → Ticket → Fake Run → Debug Episode → completed Run → Verification → Josh Acceptance → pending Memory Candidate.

## Explicitly deferred

PySide6 UI, real Runner execution, Skill promotion, RAG, vector search, central sync, multi-user RBAC, model-account routing, deployment automation, and autonomous mutation of formal policy.
