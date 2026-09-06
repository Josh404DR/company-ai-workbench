# Company AI Workbench (公司級 AI 研發工作台)

> **本機優先 · 不變量治理 · 多模型自動除錯迴圈 · 主分支交付保護**  
> 一個讓團隊與 AI 協同開發時，兼具高速迭代與企業級代碼安全防護的自動化工作台。

---

## ⚡ 快速開始 (3 種開箱即用方式)

### 方式 1：Windows 雙擊啟動 (最推薦)
直接在專案根目錄**雙擊 `start-workbench.bat`**：
- 自動檢測 Python 環境
- 自動啟動 Web UI 控制台
- 自動在瀏覽器開啟：`http://127.0.0.1:8088/`

---

### 方式 2：Python 終端機指令
```bash
# 1. 安裝套件 (開發模式)
pip install -e .

# 2. 一鍵啟動 Web UI 控制台
wb ui

# (選用) 自訂連接埠或遠端綁定
wb ui --host 0.0.0.0 --port 8088 --no-browser
```

---

### 方式 3：Docker 容器化部署
本專案提供完整 Docker 容器化打包，內建 Python 3.13、Node.js 20、Git 與 SQLite3：
```bash
# 背景啟動容器服務
docker compose up -d

# 存取控制台
# 瀏覽器打開 http://localhost:8088/
```

---

## 🖥 視覺化 Web 控制台功能

Web 控制台基於純 Python 標準庫構建，**零外部前端依賴、零 npm build、直讀 SQLite**，即開即用：

1. **長任務目標看板 (Goals Dashboard)**：
   - 支援將龐大目標分解為具備依賴關係的工單鏈。
   - 即時計算總體推進進度（`0.0% ~ 100.0%`）。
   - 提供「一鍵推進下一工單 (Advance)」與「交付此目標至主分支 (Deliver)」。
2. **任務工單看板 (Tickets Board)**：
   - 完整狀態機生命週期：`ready` ➔ `active` ➔ `verification` ➔ `accepted` ➔ `delivered`。
   - **多模型原生執行器**：可切換 **Fake 快速模擬**、**OpenAI Codex CLI** (`gpt-5.5`) 或 **Anthropic Claude Code**。
   - **自動除錯迴圈 (Auto-Debug Loop)**：當 AI 產生語意錯誤或測試失敗時，自動擷取錯誤輸出，提取指紋，並將失敗上下文注入下一次嘗試。
3. **獨立驗證閘門 (Verification Gate)**：
   - 強制執行憲法第 11 條：驗證者與建造者必須彼此獨立。
   - 證據以 SHA-256 內容定址儲存，防篡改。
4. **主分支交付保護 (Delivery Adapter - Invariant 9)**：
   - 嚴格落實**未驗收之工單絕對禁止合併至主分支**。
   - 一鍵將隔離的 `wb-run/<run_id>` 分支安全合併回 `master`，自動生成補丁並打上 `wb-delivery/<run_id>` 里程碑標籤。

---

## 💻 常用 CLI 命令速查

```bash
# ── 系統診斷與備份 ──
wb diagnose                         # 檢查資料庫完整性、證據鏈與孤立 Worktree
wb backup ./backup.db               # 安全熱備份 SQLite 資料庫

# ── 專案與工作區 ──
wb workspace create "研發中心"
wb project create <workspace_id> "核心服務"

# ── 長任務 Goal 管理 ──
wb goal create <project_id> "會員模組重構" --desc "完整長任務目標"
wb goal list <project_id>
wb goal show <goal_id>
wb goal advance <goal_id> --runner codex --verify-cmd "pytest tests/"
wb goal deliver <goal_id> --branch master

# ── 短任務 Ticket 管理 ──
wb ticket create <project_id> "實作登入 API" \
  --goal "支援 JWT 登入" \
  --criteria "pytest tests/ 通過" \
  --criteria "密碼加鹽雜湊" \
  --goal-id <goal_id> \
  --risk low

wb ticket deliver <ticket_id> --branch master

# ── 啟動 Web UI ──
wb ui
```

---

## 🛡 核心治理憲法 (Engine Constitution)

本系統嚴格由 14 條憲法不變量保護，防止 AI 寫壞專案：
- **Invariant 9**：Commit、PR、Merge、部署與 Ticket 驗收是獨立聲明，未通過獨立驗證與驗收之工單嚴禁交付。
- **Invariant 11**：驗證者必須獨立於建造者（例如 Codex 建構的程式碼必須由 local test command 或獨立驗證者審核）。
- **Invariant 14 & 4**：僅 Low 風險工單允許在自動驗證通過後自動驗收；High 風險工單強制停等 Josh 專屬人工簽核。
- **Worktree 隔離**：所有 AI 執行過程皆在獨立 Git Worktree 進行，出錯絕不污染主工作目錄。

詳細使用手冊請參閱：[`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)。

