# Ticket Coding Station reuse audit — 2026-09-02

## Current evidence boundary

- Source inspected read-only from `E:\Workspace\ticket-coding-station`.
- Branch observed: `fix/acceptance-governance-hardening`.
- The source worktree contains many modified and untracked files; none were changed or copied wholesale.
- Last recorded local evidence included server 94/94 and web 7/7, but this new engine audit did not rerun those suites.

## Reuse as product/domain concepts

- Ticket and Run are separate entities.
- Run completion projects Ticket to verification, never acceptance.
- Event history is ordered and append-oriented.
- Plan, Checkpoint, Attention, Artifact, Verification, Acceptance, Conversation, and Provider Account are useful vocabulary.
- Evidence-bearing Checkpoint and explicit Josh acceptance gates are load-bearing rules.
- Every real coding Run should remain isolated from the source checkout.
- Provider Account remains metadata-only until real selection/routing exists.

## Reimplement behind engine boundaries

- Persistence: replace several JSON files with one transactional SQLite database.
- State transitions: move from Express route/store coupling into application services with database transactions.
- Runner execution: preserve adapter concept but do not bring Node PTY details into the domain.
- Conversation: retain later as a shell/application workflow, not the first engine slice.
- Progress: retain Commitment → Activity → Checkpoint Evidence semantics after core lifecycle stabilizes.

## Do not bring into the first engine slice

- React/Vite UI state.
- Express/CORS/HTTP routing.
- WebSocket terminal transport.
- `node-pty` and embedded browser terminal behavior.
- Docker as a requirement for starting the desktop engine.
- Existing JSON file layout and backward compatibility endpoints.
- Automatic provider account routing claims.

## Decision

Create an independent Python engine repository. Treat Ticket Coding Station as a validated source of domain lessons, not as a codebase to mechanically port. No deletion, migration, or deprecation of the existing station is authorized by this audit.

