## Pull Request Summary

<!-- Provide a concise description of the purpose of this PR and what problem it solves -->

### Target Goal / Issue
- **Goal / Issue ID**: #
- **Risk Level**: [ ] Low (Automated acceptance eligible) | [ ] Medium (Requires Josh approval) | [ ] High (Requires Josh approval)

---

## Changes Made

- 
- 
- 

---

## Constitution Invariants Checklist

Please confirm compliance with the 14 Engine Constitution Invariants:

- [ ] **Invariant 1 & 3 (Acceptance Separation)**: No run completion self-accepts; acceptance strictly requires a passing independent Verification record.
- [ ] **Invariant 4 & 14 (Tiered Acceptance Authority)**: Risk level is evaluated. High/Medium risk changes require human review (Josh); automated acceptance is limited to `low` risk.
- [ ] **Invariant 5 (Isolated Worktree)**: Changes were developed and tested within an isolated git worktree/branch.
- [ ] **Invariant 9 (Mainline Delivery Gate)**: No unaccepted or unverified code reaches the `master` mainline. Delivery merges only accepted tickets/goals.
- [ ] **Invariant 11 (Verifier Independence)**: Verifier is independent of the builder (no same-provider collusion e.g. openai-openai, anthropic-anthropic).
- [ ] **Invariant 12 (Content-Addressed Evidence)**: Test evidence is stored append-only and pinned by SHA-256 hash.

---

## Verification & Testing Evidence

```bash
# Paste local test execution command and output here:
python -m pytest tests -v
```

- **Tests Passing**: 135/135 tests PASS
- **Evidence SHA-256**: `[Paste hash if applicable]`

---

## Reviewer Checklist

- [ ] CI pipeline (`test-and-verify` & `invariant-gate`) passed 100% GREEN.
- [ ] Code follows local-first and fail-closed security design.
- [ ] Architecture Council / Human Reviewer approved.
