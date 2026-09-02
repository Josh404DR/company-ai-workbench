# Company AI Workbench Engine

本機優先、可追溯、可復原的公司 AI 工作引擎。桌面 EXE、CLI、Web 都只是可替換外殼。

目前階段：第一個引擎垂直切片。已涵蓋 Workspace → Project → Ticket → Run → Debug Episode → Verification → Acceptance → Memory Candidate，並刻意使用 Fake Agent，不宣稱已接入真實 AI Runner。

## 快速驗證

```powershell
$env:PYTHONPATH = "src"
py -3.13 -m company_workbench diagnose
py -3.13 -m company_workbench demo
py -3.13 -m unittest discover -s tests -v
```

Python 3.13 是目前開發機可用版本；專案語法與套件邊界維持 Python 3.12+ 相容。

## 不變規則

- Run 完成不等於 Ticket 驗收。
- Verification 必須附證據。
- Ticket 驗收需要最新 Run 完成，且 Verification 通過。
- Event 是 append-only audit trail。
- Acceptance 只能建立一次，並固定引用當時通過的 Verification。
- Memory Candidate 不會自動升級為正式記憶。
- 失敗 Run 與 Debug Episode 必須保留。
- UI 不直接操作資料庫、Git 或 AI CLI。

架構與取捨見 `docs/ENGINE_CONSTITUTION.md` 與 `docs/LEGACY_REUSE_AUDIT.md`。
