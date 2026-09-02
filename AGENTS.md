# Company AI Workbench Agent Entry

本專案是獨立的公司 AI 工作引擎，不是 `ticket-coding-station` 的子目錄或自動替代品。

## Startup order

1. `AGENTS.md`
2. `docs/ENGINE_CONSTITUTION.md`
3. `docs/CURRENT_HANDOFF.md`
4. `docs/VERIFICATION_LOG.md`
5. 視任務需要讀 `docs/LEGACY_REUSE_AUDIT.md`

## Hard boundaries

- Engine owns state transitions and evidence gates; shells must call application services.
- Run completion never means Ticket acceptance.
- Do not silently promote Memory or Skill candidates.
- Do not copy secrets, customer material, provider tokens, or raw credentials into the database, logs, tests, or shared memory.
- Do not modify or migrate `E:\Workspace\ticket-coding-station` without a separate explicit task and fresh dirty-worktree inspection.
- No commit, push, PR, merge, deployment, paid model call, or destructive migration without the corresponding explicit authorization.
- Python 3.13 is the current development runtime because Python 3.12 is absent on this machine; keep source compatible with Python 3.12+.

