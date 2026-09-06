# Company AI Workbench 使用者完整操作指南 (User Guide)

歡迎使用 **Company AI Workbench**！本指南將帶領您快速熟悉整個系統的運作方式、網頁操作介面、CLI 命令列工具，以及背後的安全防護機制。

---

## 目錄
1. [系統簡介與核心防線](#1-系統簡介與核心防線)
2. [快速啟動工作台](#2-快速啟動工作台)
3. [端到端實戰操作教學 (Web UI)](#3-端到端實戰操作教學-web-ui)
4. [多模型 AI 執行器配置](#4-多模型-ai-執行器配置)
5. [CLI 指令集操作教學](#5-cli-指令集操作教學)
6. [常見問題與疑難排解 (FAQ)](#6-常見問題與疑難排解-faq)

---

## 1. 系統簡介與核心防線

Company AI Workbench 是一套為團隊打造的**本機優先 (Local-first)**、**高安全性**的 AI 協同研發系統。

### 為什麼我的主分支不會被 AI 搞壞？
在一般使用 AI 寫程式的場景中，AI 常常會直接修改工作目錄，甚至未經測試就推送到主分支。Company AI Workbench 具備四道不可逾越的「治理防線」：

1. **Git Worktree 完全隔離**：AI 撰寫代碼與執行測試都在獨立的暫存 Worktree 進行，即便 AI 執行出錯甚至刪除檔案，主工作區永遠不受影響。
2. **自動除錯迴圈 (Auto-Debug Loop)**：當測試失敗時，系統自動捕捉錯誤日誌並附帶指紋重試，在隔離沙盒內完成修正。
3. **獨立驗證者約束 (Invariant 11)**：撰寫代碼的 AI（如 Codex）絕對不能自己給自己發放及格證書，必須通過獨立的測試命令（如 pytest）或人類驗證。
4. **主分支交付保護 (Invariant 9)**：未經正式簽核驗收（Accepted）的工單，系統從根本架構上直接拒絕合併至主分支或生成補丁。

---

## 2. 快速啟動工作台

您可以透過以下任一方式啟動控制台：

### 方式 A：Windows 雙擊啟動 (最簡便)
專案根目錄下已為您準備好 `start-workbench.bat`：
- 直接**滑鼠雙擊 `start-workbench.bat`**。
- 系統將自動尋找 Python 環境並開啟瀏覽器至 `http://127.0.0.1:8088/`。

### 方式 B：終端機 CLI 啟動
在終端機中：
```bash
# 確保已安裝環境
pip install -e .

# 啟動控制台 (預設綁定 127.0.0.1:8088 並自動開啟瀏覽器)
wb ui
```

### 方式 C：Docker 容器化一鍵部署
若您偏好容器化隔離：
```bash
docker compose up -d
```
瀏覽器造訪 `http://localhost:8088/` 即可進入控制台。

---

## 3. 端到端實戰操作教學 (Web UI)

### 步驟 1：建立專案與長任務目標 (Goal)
1. 進入控制台頂部「新增專案 (Project)」卡片，輸入專案名稱（例如：`電商金流整合`）。
2. 在「建立長任務目標 (Goal)」卡片中：
   - 選擇所屬專案。
   - 輸入目標標題（例如：`LinePay 與 綠界金流串接`）。
   - 點擊「建立長任務 Goal」。
3. 建立後，下方「長任務目標看板 (Goals)」將即時顯示該目標，目前進度為 `0.0%`。

### 步驟 2：開立任務工單 (Tickets) 與設定依賴順序
1. 前往「開立 Ticket (工單任務)」表單：
   - **Ticket 標題**：例如 `實作 LinePay 簽章驗證演算法`
   - **所屬長任務**：選擇剛才建立的 Goal
   - **前置依賴工單**：若為第一張工單則選「(無 - 無前置依賴)」；後續工單可指定必須等哪一張工單完成後才能開始
   - **風險等級**：
     - `Low`：單元測試通過後，系統允許自動驗收（極致自動化）。
     - `High`：涉及核心邏輯或資料庫改動，測試通過後強制停等專屬管理員（Josh）人工簽核。
   - **目標說明與驗收條件**：清楚寫明要求（例如：`pytest tests/test_linepay.py 100% 通過`）。
2. 點擊「建立 Ticket」。

### 步驟 3：啟動 Managed Run (Auto-Debug Loop)
1. 在工單看板中找到處於 `READY` 狀態的工單。
2. 選擇執行器：
   - **Fake 模擬 (自動測試)**：用於功能體驗與快速驗收演示。
   - **OpenAI Codex CLI**：調用 OpenAI 原生 CLI (`gpt-5.5`) 進行代碼編寫。
   - **Anthropic Claude Code**：調用 Claude Code 原生 CLI 進行工程研發。
3. 點擊「啟動 Managed Run」或在目標卡片點擊「一鍵推進下一工單 (Advance)」。
4. 系統將在背景建立獨立 Worktree，執行代碼變更與自動驗證。

### 步驟 4：獨立驗證與審查簽核 (Verification & Acceptance)
1. Run 執行完成後，工單進入 `VERIFICATION` 狀態。
2. 檢查測試輸出與證據，點擊「提交 SHA-256 驗證證據」。
3. 驗證通過後，對於 High 風險工單，點擊「Josh 正式簽核驗收 (Accept)」。
4. 工單狀態變更為 `ACCEPTED`，Goal 完成進度條將即時更新增加！

### 步驟 5：交付至主分支 (Deliver to Master)
1. 當工單或整體 Goal 已驗收完成時，卡片上會亮起綠色「**交付至主分支 (Deliver)**」按鈕。
2. 點擊後，系統會：
   - 自動將該次任務分支（`wb-run/<run_id>`）合併至主分支 `master`。
   - 自動產生補丁檔案與交付標籤（Tag: `wb-delivery/<run_id>`）。
   - 記錄不可篡改的交付審計事件。

---

## 4. 多模型 AI 執行器配置

### OpenAI Codex CLI (`gpt-5.5`)
- 確認本機已安裝 Node.js 18+ 與 Codex CLI：
  ```bash
  npm install -g @openai/codex
  ```
- 設定環境變數：
  ```powershell
  $env:OPENAI_API_KEY = "sk-..."
  ```

### Anthropic Claude Code
- 確認本機已安裝 Claude Code：
  ```bash
  npm install -g @anthropic-ai/claude-code
  ```
- 設定環境變數：
  ```powershell
  $env:ANTHROPIC_API_KEY = "sk-ant-..."
  ```

---

## 5. CLI 指令集操作教學

除了網頁介面，您也可以透過終端機 `wb` 命令完整控制所有流程：

### 診斷與系統自檢
```bash
wb diagnose
```

### 建立與推進長任務 Goal
```bash
# 建立 Goal
wb goal create PRJ-xxx "新架構重構" --desc "逐步分解長任務"

# 查看 Goal 詳細進度
wb goal show GOL-xxx

# 一鍵推進 Goal
wb goal advance GOL-xxx --runner codex --verify-cmd "pytest tests/"

# 交付已達成之 Goal 至 master
wb goal deliver GOL-xxx --branch master
```

### 建立與交付工單 Ticket
```bash
# 建立 Ticket
wb ticket create PRJ-xxx "重構認證模組" \
  --goal "全面改用 JWT" \
  --criteria "單元測試全部通過" \
  --goal-id GOL-xxx \
  --risk low

# 交付 Ticket 至 master
wb ticket deliver TKT-xxx --branch master
```

---

## 6. 常見問題與疑難排解 (FAQ)

**Q1: 為什麼點擊「交付至主分支」會提示失敗？**  
A: 這是系統憲法第 9 條的強制保護。工單必須處於 `accepted` 狀態且附帶有效之獨立驗證證據。如果工單尚未驗收，系統將嚴格阻絕合併。

**Q2: 網頁上的資料存放在哪裡？**  
A: 預設存放在目前目錄下的 `.workbench/workbench.db`（SQLite 單一檔案）。您也可以隨時使用 `wb backup ./my_backup.db` 進行安全備份。

**Q3: 如何自訂 Web 控制台的連接埠？**  
A: 執行 `wb ui --port 9000` 或在環境變數中設定 `PORT=9000`。
