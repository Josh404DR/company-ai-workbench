"""
AgentOS Living Mind Map & Structured Workflow Pipeline Generator.
Renders an intuitive, hierarchical Left-to-Right workflow pipeline and node-centric dialogue surface.
Addresses scattered connection graph with structured stage levels, focus filters, and workflow steppers.
"""

import html
import json
from pathlib import Path

def get_agentos_graph_data():
    r"""Extract grounded node graph from E:\Workspace\agentos-lite with explicit Workflow levels."""
    nodes = [
        # --- Level 1: 階段一：專案輸入與治理憲法 (Governance & Project Ingestion) ---
        {
            "id": "mem_governance",
            "label": "🧠 Tier 0~4 分層治理憲法",
            "group": "memory",
            "layer": "階段一：治理憲法",
            "level": 1,
            "summary": "定義文件權威順序：Tier 0 硬規則 > Tier 1 導航 > Tier 2 現況正本 > Tier 3 主題參考 > Tier 4 歷史證據。",
            "files": ["E:\\Workspace\\DOCUMENT_GOVERNANCE.md", "E:\\Workspace\\MEMORY_INDEX.md"],
            "details": "解決 947 份文件搜尋混亂問題，作為整個工作流不可違背的最高憲章。",
            "color": "#8957e5"
        },
        {
            "id": "arch_core",
            "label": "🏛️ AgentOS-Lite 核心契約",
            "group": "architecture",
            "layer": "階段一：治理憲法",
            "level": 1,
            "summary": "以 AGENTS.md 為正本的合約治理系統，界定 Builder/Verifier 責任邊界與工單生命週期。",
            "files": ["AGENTS.md", "README.md", "docs/SOURCE_MAP.md"],
            "details": "捨棄重型背景守護行程 (Queue/Runner/Gateway)，採用純靜態合約與 IDE 工作流機制。",
            "color": "#1f6feb"
        },
        {
            "id": "arch_memory_hub",
            "label": "🏛️ Central Skills 跨 CLI 記憶中樞",
            "group": "architecture",
            "layer": "階段一：治理憲法",
            "level": 1,
            "summary": "透過 josh-shared-memory 技能與 sync-skills.ps1 實現跨模型 (Codex/Claude/Antigravity) 記憶共享。",
            "files": ["agent-skills-hub/skills/josh-shared-memory/", "E:\\Workspace\\DOCUMENT_GOVERNANCE.md"],
            "details": "不複製對話噪音，僅共享可追溯的治理正本與專案現況狀態。",
            "color": "#1f6feb"
        },

        # --- Level 2: 階段二：契約檢驗門禁 (Contract Linter Gate) ---
        {
            "id": "arch_linter",
            "label": "🏛️ Contract Linter 契約稽核器",
            "group": "architecture",
            "layer": "階段二：契約檢驗",
            "level": 2,
            "summary": "派工前強制檢查工具，必須達到 error_count=0 才准啟動 Builder。",
            "files": ["tools/contract_linter/", "tests/test_contract_linter.js"],
            "details": "具備 47 項自動化測試，鎖定基線 f524209394d05069f18aa4fbc5707c6fe48bbe1d。",
            "color": "#1f6feb"
        },
        {
            "id": "logic_rules",
            "label": "⚙️ 47 題規則庫 (LINT-001 ~ 007)",
            "group": "logic",
            "layer": "階段二：契約檢驗",
            "level": 2,
            "summary": "核心語法與結構規則引擎，檢查路徑衝突、禁止路徑越界與產物完整性。",
            "files": ["tools/contract_linter/rules.js"],
            "details": "涵蓋 LINT-001 (格式) 至 LINT-007 (expected_outputs 階層式路徑核對)。",
            "color": "#238636"
        },
        {
            "id": "logic_forbidden",
            "label": "⚙️ 禁止路徑攔截器 (Forbidden Guard)",
            "group": "logic",
            "layer": "階段二：契約檢驗",
            "level": 2,
            "summary": "在沙盒執行前攔截任何企圖讀取機密目錄 (如 saya-Josh-useonly) 的非法操作。",
            "files": ["tools/contract_linter/forbidden_paths.json"],
            "details": "防止跨專案或客戶機密外洩，Fail-Closed 阻擋非授權檔案存取。",
            "color": "#238636"
        },

        # --- Level 3: 階段三：任務流水線 (Task Packet Workflow Pipeline) ---
        {
            "id": "arch_packet",
            "label": "🏛️ Task Packet 封包派工",
            "group": "architecture",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "結構化傳遞需求與結果的不可變 JSON 封包，定義輸入路徑、預期產物與驗證權限。",
            "files": ["packets/phase_1/", "packets/schema/task_packet.json"],
            "details": "禁止 Builder 自行擴充產物邊界，所有輸出必須在 expected_outputs 明確宣告。",
            "color": "#1f6feb"
        },
        {
            "id": "task_n1",
            "label": "📍 N1: 契約基線確立 (Passed)",
            "group": "path",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "建立 contract_linter 初始架構與前 20 項基礎語法測試。",
            "files": ["packets/phase_1/n1-baseline/"],
            "details": "通過獨立驗收合入。",
            "color": "#3fb950"
        },
        {
            "id": "task_n2",
            "label": "📍 N2: 輕量 RAG 整合 (Passed)",
            "group": "path",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "整合 E:\\Workspace\\rag 本地搜尋引擎與治理文件索引。",
            "files": ["packets/phase_1/n2-rag-integration/"],
            "details": "建立 58 份文件語意索驥，確認零外部 token 消耗。",
            "color": "#3fb950"
        },
        {
            "id": "task_n3",
            "label": "📍 N3: 來源清冊盤點 (Passed)",
            "group": "path",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "盤點 13 份歷史規格來源，產出 RAG_SOURCE_CONFLICTS。",
            "files": ["packets/phase_1/n3-rag-source-manifest/"],
            "details": "發現 3 筆需主管裁決的政策衝突，為後續治理奠定基礎。",
            "color": "#3fb950"
        },
        {
            "id": "task_n4",
            "label": "🔥 N4: 探索真實工單 (當前焦點 / No-Go)",
            "group": "focus",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "【當前工作流核心卡點】：LINT-007 檢查漏洞與 Verifier 未授權邊界。",
            "files": ["packets/phase_1/n4-exploratory/"],
            "details": "這是我們今天討論的起點！如何修復 LINT-007 並在 Workbench 內重獲新生？",
            "color": "#f0883e"
        },

        # --- Level 4: 階段四：執行沙盒與獨立驗證 (Sandbox & Verification) ---
        {
            "id": "workbench_engine",
            "label": "⚡ Workbench 沙盒與 Auto-Debug 迴圈",
            "group": "workbench",
            "layer": "階段四：執行與驗證",
            "level": 4,
            "summary": "以 Git Worktree 隔離運行，捕獲失敗日誌自動重試除錯，修復 N4 暴露的漏洞。",
            "files": ["src/company_workbench/engine.py"],
            "details": "Invariants 14 條憲法保障，未通過獨立驗證絕不放行。",
            "color": "#f0883e"
        },
        {
            "id": "arch_verifier",
            "label": "🏛️ Independent Verifier 獨立驗證門禁",
            "group": "architecture",
            "layer": "階段四：執行與驗證",
            "level": 4,
            "summary": "驗證者必須完全獨立於 Builder，產出 SHA-256 數位證據。",
            "files": ["verify/", "AGENTS.md#IV-Rules"],
            "details": "嚴格檢查 expected_outputs，禁止未授權產物偷渡。",
            "color": "#1f6feb"
        },
        {
            "id": "mem_nogo",
            "label": "🧠 N4 No-Go 核心教訓約束",
            "group": "memory",
            "layer": "階段四：執行與驗證",
            "level": 4,
            "summary": "N4 因 Task Packet 未授權 Verifier 產物且扁平 expected_outputs 導致 LINT-007 漏檢，判定 FAIL。",
            "files": ["DECISIONS.md#2026-08-16", "README.md#最終決策"],
            "details": "要求未來工單必須具備階層式產物宣告與明確 Verifier 授權。",
            "color": "#d29922"
        },

        # --- Level 5: 階段五：主管審批與主幹交付 (Acceptance & Master Delivery) ---
        {
            "id": "human_acceptance",
            "label": "👤 Josh 人工最終驗收 (Accept Gate)",
            "group": "delivery",
            "layer": "階段五：主幹交付",
            "level": 5,
            "summary": "高風險任務必須由 Josh 親自審查 SHA-256 數位證據後手動點擊核准。",
            "files": ["docs/COUNCIL_REVIEW.md#Invariant-14"],
            "details": "系統 Fail-Closed 踩死煞車，未經簽核絕對無法合入主幹。",
            "color": "#da3633"
        },
        {
            "id": "deliver_master",
            "label": "🚢 Deliver to Master (主幹安全交付)",
            "group": "delivery",
            "layer": "階段五：主幹交付",
            "level": 5,
            "summary": "乾淨 Merge 回 master 主分支，建立 wb-delivery 標籤並推送 GitHub。",
            "files": ["src/company_workbench/delivery.py"],
            "details": "只有已驗收通過的工單才具備交付資格，交付後自動通知 CI/CD。",
            "color": "#238636"
        }
    ]

    edges = [
        # Level 1 -> Level 2
        {"from": "mem_governance", "to": "arch_core", "label": "約束憲法"},
        {"from": "arch_core", "to": "arch_linter", "label": "啟動稽核"},
        {"from": "arch_linter", "to": "logic_rules", "label": "加載47題規則"},
        {"from": "arch_linter", "to": "logic_forbidden", "label": "禁止路徑"},

        # Level 2 -> Level 3
        {"from": "arch_linter", "to": "arch_packet", "label": "檢查通過(error=0)"},
        {"from": "arch_packet", "to": "task_n1", "label": "派工 N1"},
        {"from": "task_n1", "to": "task_n2", "label": "推進至 N2"},
        {"from": "task_n2", "to": "task_n3", "label": "推進至 N3"},
        {"from": "task_n3", "to": "task_n4", "label": "推進至 N4(焦點)", "color": {"color": "#f0883e"}, "width": 3},

        # Level 3 -> Level 4
        {"from": "task_n4", "to": "workbench_engine", "label": "導入沙盒重構", "color": {"color": "#f0883e"}, "width": 3},
        {"from": "workbench_engine", "to": "arch_verifier", "label": "提交獨立驗證"},
        {"from": "mem_nogo", "to": "arch_verifier", "label": "卡控授權邊界"},

        # Level 4 -> Level 5
        {"from": "arch_verifier", "to": "human_acceptance", "label": "驗證通過(PASS)"},
        {"from": "human_acceptance", "to": "deliver_master", "label": "Josh 核准合入", "color": {"color": "#238636"}, "width": 3}
    ]

    return nodes, edges


def render_agentos_mindmap_html():
    nodes, edges = get_agentos_graph_data()
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Company AI Workbench · Orca 精工工作台</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {{
      --bg: #090d13;
      --panel-bg: #111620;
      --card-bg: #171f2d;
      --hover-bg: #1f2a3c;
      --border: #233044;
      --border-bright: #374b6b;
      --text: #c5d1de;
      --text-bright: #f0f6fc;
      --text-muted: #8b99ab;
      --blue: #388bfd;
      --blue-glow: rgba(56, 139, 253, 0.15);
      --green: #3fb950;
      --green-glow: rgba(63, 185, 80, 0.15);
      --purple: #a371f7;
      --orange: #f0883e;
      --orange-glow: rgba(240, 136, 62, 0.15);
      --gold: #d29922;
      --red: #f85149;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}

    /* 頂部雙座導航條 */
    .top-bar {{
      height: 60px;
      background: var(--panel-bg);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      z-index: 20;
      flex-shrink: 0;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .logo-icon {{
      font-size: 22px;
      filter: drop-shadow(0 0 6px rgba(56, 139, 253, 0.5));
    }}
    .brand h1 {{
      font-size: 15px;
      color: var(--text-bright);
      font-weight: 700;
      letter-spacing: 0.3px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .badge-sub {{
      font-size: 10px;
      padding: 2px 7px;
      border-radius: 12px;
      font-weight: 600;
      background: rgba(56, 139, 253, 0.18);
      color: var(--blue);
      border: 1px solid var(--blue);
    }}

    /* 五階維度梯子導航 (Dimension Ladder) */
    .dimension-ladder {{
      display: flex;
      align-items: center;
      gap: 4px;
      background: var(--bg);
      padding: 4px 12px;
      border-radius: 20px;
      border: 1px solid var(--border);
    }}
    .ladder-step {{
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 11.5px;
      padding: 3px 8px;
      border-radius: 12px;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.15s;
    }}
    .ladder-step:hover {{
      background: var(--card-bg);
      color: var(--text-bright);
    }}
    .ladder-step.active {{
      background: var(--orange-glow);
      color: var(--orange);
      font-weight: 700;
      border: 1px solid var(--orange);
    }}
    .dim-name {{
      font-size: 10px;
      opacity: 0.7;
    }}
    .dim-val {{
      font-weight: 600;
    }}
    .ladder-sep {{
      color: #48566a;
      font-size: 12px;
      user-select: none;
    }}

    /* 模式切換標籤頁 (View Mode Switcher) */
    .view-mode-tabs {{
      display: flex;
      gap: 6px;
      background: var(--bg);
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    .mode-tab {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .mode-tab:hover {{
      color: var(--text-bright);
      background: var(--card-bg);
    }}
    .mode-tab.active {{
      background: var(--blue);
      color: #fff;
      box-shadow: 0 0 10px rgba(56, 139, 253, 0.4);
    }}

    /* 主工作區容器 */
    .main-container {{
      flex: 1;
      display: flex;
      position: relative;
      overflow: hidden;
    }}

    /* ================================================================ */
    /* 模式 A: ORCA 精工工作台 (Workbench View) */
    /* ================================================================ */
    .workbench-view {{
      display: flex;
      width: 100%;
      height: 100%;
      transition: all 0.25s ease-in-out;
    }}
    
    /* 左側：可對話視窗 (Conversational AI Station) */
    .chat-console {{
      flex: 1;
      min-width: 420px;
      max-width: 580px;
      background: var(--panel-bg);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      height: 100%;
      position: relative;
    }}
    .console-header {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-bg);
    }}
    .station-badge {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 700;
      color: var(--text-bright);
    }}
    .pulse-dot {{
      width: 8px;
      height: 8px;
      background: var(--green);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--green);
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0% {{ transform: scale(0.95); opacity: 0.7; }}
      50% {{ transform: scale(1.15); opacity: 1; }}
      100% {{ transform: scale(0.95); opacity: 0.7; }}
    }}
    .console-meta {{
      display: flex;
      gap: 6px;
    }}
    .tag {{
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
    }}
    .tag-runner {{ background: rgba(56, 139, 253, 0.2); color: var(--blue); border: 1px solid var(--blue); }}
    .tag-gov {{ background: rgba(163, 113, 247, 0.2); color: var(--purple); border: 1px solid var(--purple); }}

    /* 對話訊息串 */
    .chat-stream {{
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: var(--bg);
    }}
    .chat-card {{
      display: flex;
      gap: 12px;
      max-width: 96%;
      animation: fadeIn 0.2s ease-in-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .card-avatar {{
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: var(--card-bg);
      border: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
    }}
    .card-body {{
      flex: 1;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 14px;
      font-size: 13px;
      line-height: 1.55;
    }}
    .chat-user {{
      align-self: flex-end;
      flex-direction: row-reverse;
    }}
    .chat-user .card-body {{
      background: #193863;
      border-color: #2b548b;
      color: #fff;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      font-size: 11px;
      color: var(--text-muted);
    }}
    .card-text code {{
      background: rgba(0,0,0,0.3);
      padding: 2px 5px;
      border-radius: 4px;
      font-family: monospace;
      color: #79c0ff;
    }}

    /* 一鍵工令裝配工具列 */
    .quick-action-bar {{
      padding: 10px 14px;
      background: var(--panel-bg);
      border-top: 1px solid var(--border);
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .q-btn {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 11px;
      font-weight: 600;
      padding: 6px 10px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .q-btn:hover {{
      background: var(--hover-bg);
      border-color: var(--blue);
      color: var(--text-bright);
      transform: translateY(-1px);
    }}
    .q-btn-accent {{
      background: rgba(240, 136, 62, 0.15);
      border-color: var(--orange);
      color: var(--orange);
    }}
    .q-btn-accent:hover {{
      background: var(--orange);
      color: #fff;
    }}

    /* 輸入框 */
    .console-input-box {{
      padding: 12px 14px;
      background: var(--card-bg);
      border-top: 1px solid var(--border);
      display: flex;
      gap: 10px;
      align-items: flex-end;
    }}
    .console-input-box textarea {{
      flex: 1;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 12px;
      color: var(--text-bright);
      font-size: 13px;
      resize: none;
      height: 48px;
      line-height: 1.4;
    }}
    .console-input-box textarea:focus {{
      outline: none;
      border-color: var(--blue);
      box-shadow: 0 0 0 2px var(--blue-glow);
    }}
    .console-input-box button {{
      background: var(--blue);
      color: #fff;
      border: none;
      padding: 0 16px;
      height: 48px;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .console-input-box button:hover {{
      background: #2376e5;
    }}

    /* 右側：任務維度到原子維度工作區 (Task to Atomic Dimension Panel) */
    .dimension-workplace {{
      flex: 1.2;
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--bg);
      overflow-y: auto;
      padding: 16px 20px;
      gap: 16px;
    }}

    /* 任務與目標層級卡片 */
    .task-overview-card {{
      background: var(--panel-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      position: relative;
    }}
    .task-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 8px;
    }}
    .badge-phase {{
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 12px;
      background: rgba(163, 113, 247, 0.18);
      color: var(--purple);
      border: 1px solid var(--purple);
      display: inline-block;
      margin-bottom: 6px;
    }}
    .task-card-header h2 {{
      font-size: 17px;
      color: var(--text-bright);
      font-weight: 700;
    }}
    .status-pill {{
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 12px;
      font-weight: 700;
    }}
    .status-ready {{ background: rgba(63, 185, 80, 0.2); color: var(--green); border: 1px solid var(--green); }}
    .status-active {{ background: rgba(240, 136, 62, 0.2); color: var(--orange); border: 1px solid var(--orange); }}
    .task-desc {{
      font-size: 13px;
      line-height: 1.5;
      color: var(--text);
      margin-bottom: 14px;
    }}
    .task-metrics {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 12px;
      background: var(--card-bg);
      padding: 10px 14px;
      border-radius: 6px;
      border: 1px solid var(--border);
    }}
    .metric-item {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .m-label {{
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
    }}
    .m-val {{
      font-size: 12.5px;
      font-weight: 700;
      color: var(--text-bright);
    }}
    .progress-bar-wrap {{
      height: 6px;
      background: #233044;
      border-radius: 3px;
      overflow: hidden;
      margin: 4px 0;
    }}
    .progress-bar-fill {{
      height: 100%;
      background: var(--blue);
      border-radius: 3px;
    }}

    /* 原子步驟檢驗鏈 (Atomic Stepper) */
    .atomic-stepper-card {{
      background: var(--panel-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 16px;
    }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
      font-weight: 700;
      color: var(--text-bright);
      margin-bottom: 12px;
    }}
    .step-counter {{
      font-size: 11px;
      color: var(--orange);
      font-weight: 600;
    }}
    .stepper-list {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .step-row {{
      display: flex;
      align-items: center;
      gap: 12px;
      background: var(--card-bg);
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--border);
      transition: all 0.15s;
    }}
    .step-row:hover {{
      border-color: var(--border-bright);
      background: var(--hover-bg);
    }}
    .step-check {{
      width: 22px;
      height: 22px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 800;
      flex-shrink: 0;
    }}
    .step-done .step-check {{ background: var(--green); color: #fff; }}
    .step-active .step-check {{ background: var(--orange); color: #fff; animation: pulse 1.5s infinite; }}
    .step-pending .step-check {{ background: #233044; color: #8b99ab; }}
    .step-info {{
      flex: 1;
    }}
    .step-title {{
      font-size: 12.5px;
      font-weight: 600;
      color: var(--text-bright);
    }}
    .step-meta {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    /* 即時終端與產物監控台 */
    .inspector-card {{
      background: var(--panel-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      flex: 1;
      min-height: 260px;
    }}
    .inspector-tabs {{
      display: flex;
      background: var(--card-bg);
      border-bottom: 1px solid var(--border);
      padding: 0 8px;
    }}
    .insp-tab {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 600;
      padding: 10px 14px;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.15s;
    }}
    .insp-tab:hover {{
      color: var(--text-bright);
    }}
    .insp-tab.active {{
      color: var(--blue);
      border-bottom-color: var(--blue);
    }}
    .inspector-body {{
      flex: 1;
      background: #06090e;
      overflow-y: auto;
      padding: 12px;
      position: relative;
    }}
    .tab-pane {{
      display: none;
      height: 100%;
    }}
    .tab-pane.active {{
      display: block;
    }}
    .terminal-view {{
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 12px;
      line-height: 1.6;
      color: #7ee787;
    }}
    .term-line {{ margin-bottom: 3px; }}
    .term-dim {{ color: #48566a; }}
    .term-info {{ color: #79c0ff; }}
    .term-success {{ color: #7ee787; }}
    .term-warn {{ color: #e3b341; }}
    .diff-view {{
      font-family: monospace;
      font-size: 12px;
      line-height: 1.5;
      color: #c9d1d9;
      white-space: pre-wrap;
    }}
    .evidence-box {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      font-size: 12.5px;
    }}
    .ev-row {{
      display: flex;
      gap: 8px;
    }}
    .ev-k {{ color: var(--text-muted); font-weight: 600; width: 140px; }}
    .ev-v {{ color: var(--text-bright); }}
    .code-highlight {{
      font-family: monospace;
      background: rgba(56, 139, 253, 0.15);
      padding: 2px 6px;
      border-radius: 4px;
      color: #79c0ff;
    }}

    /* ================================================================ */
    /* 模式 B: 全維度可視化天眼 (Full Dimension Universe View) */
    /* ================================================================ */
    .universe-view {{
      display: none;
      width: 100%;
      height: 100%;
      position: relative;
    }}
    .universe-toolbar {{
      position: absolute;
      top: 14px;
      left: 18px;
      right: 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(17, 22, 32, 0.88);
      backdrop-filter: blur(10px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 14px;
      z-index: 10;
    }}
    .filter-group {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .filter-label {{
      font-size: 11.5px;
      font-weight: 700;
      color: var(--text-muted);
      margin-right: 4px;
    }}
    .f-btn {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .f-btn:hover {{
      background: var(--hover-bg);
      color: var(--text-bright);
    }}
    .f-btn.active {{
      background: var(--blue);
      border-color: var(--blue);
      color: #fff;
    }}
    #network-canvas {{
      width: 100%;
      height: 100%;
      background: radial-gradient(circle, #182232 1px, #090d13 1px);
      background-size: 26px 26px;
    }}

    /* 懸浮檢驗卡片 (Flyout Card) */
    .node-flyout-card {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      width: 380px;
      background: rgba(23, 31, 45, 0.94);
      backdrop-filter: blur(12px);
      border: 1px solid var(--blue);
      border-radius: 10px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      z-index: 15;
    }}
    .flyout-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }}
    .flyout-header h3 {{
      font-size: 15px;
      color: var(--text-bright);
      font-weight: 700;
    }}
    .close-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 18px;
      cursor: pointer;
    }}
    .flyout-meta {{
      font-size: 11px;
      color: var(--orange);
      font-weight: 600;
      margin-bottom: 8px;
    }}
    .flyout-desc {{
      font-size: 12.5px;
      line-height: 1.5;
      color: var(--text);
      margin-bottom: 12px;
    }}
    .flyout-section {{
      font-size: 10px;
      text-transform: uppercase;
      font-weight: 800;
      color: var(--text-muted);
      margin-bottom: 4px;
    }}
    .flyout-files {{
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 14px;
    }}
    .flyout-file-badge {{
      font-family: monospace;
      font-size: 11px;
      background: rgba(0,0,0,0.3);
      padding: 3px 6px;
      border-radius: 4px;
      color: #79c0ff;
    }}
    .flyout-footer button {{
      width: 100%;
      background: var(--blue);
      color: #fff;
      border: none;
      padding: 10px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .flyout-footer button:hover {{
      background: #2376e5;
    }}

    /* ================================================================ */
    /* 模式 C: 雙座分屏模式 (Split Mode) */
    /* ================================================================ */
    .split-view-active .workbench-view {{
      width: 55%;
      border-right: 1px solid var(--border);
    }}
    .split-view-active .universe-view {{
      display: block;
      width: 45%;
    }}
  </style>
</head>
<body>

  <!-- 頂部雙座導航與五階維度階梯 (Top Bar & 5-Layer Dimension Tracker) -->
  <header class="top-bar">
    <div class="brand">
      <span class="logo-icon">🐋</span>
      <div class="brand-text">
        <h1>Company AI Workbench · 日產精工裝配駕駛艙 <span class="badge-sub">Orca 精工工作台</span></h1>
      </div>
    </div>

    <!-- 五階維度階梯導航 (5-Layer Dimension Breadcrumbs) -->
    <nav class="dimension-ladder" id="dimension-ladder">
      <div class="ladder-step" data-dim="project" title="專案結構維度">
        <span class="dim-icon">🏢</span>
        <span class="dim-name">專案</span>
        <span class="dim-val">AgentOS-Lite</span>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step" data-dim="goal" title="長期目標維度">
        <span class="dim-icon">🎯</span>
        <span class="dim-name">目標</span>
        <span class="dim-val" id="ladder-goal-title">核心架構重構</span>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step" data-dim="task" title="中小型任務維度">
        <span class="dim-icon">📦</span>
        <span class="dim-name">任務</span>
        <span class="dim-val" id="ladder-task-title">Phase 1 契約門禁</span>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step active" data-dim="node" title="工位節點維度">
        <span class="dim-icon">📍</span>
        <span class="dim-name">節點</span>
        <span class="dim-val" id="ladder-node-title">N4 沙盒重構</span>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step" data-dim="ticket" title="原子工單維度">
        <span class="dim-icon">⚛️</span>
        <span class="dim-name">原子</span>
        <span class="dim-val" id="ladder-ticket-title">#TKT-104 [沙盒極限試車]</span>
      </div>
    </nav>

    <!-- 模式切換按鈕 (View Modes: Workbench / Split / Universe) -->
    <div class="view-mode-tabs">
      <button class="mode-tab active" id="tab-workbench" onclick="switchViewMode('workbench')">
        🛠️ 工作台 (Orca)
      </button>
      <button class="mode-tab" id="tab-split" onclick="switchViewMode('split')">
        🔲 雙座分屏
      </button>
      <button class="mode-tab" id="tab-universe" onclick="switchViewMode('universe')">
        🌌 全維度可視化
      </button>
    </div>
  </header>

  <!-- 主工作台容器 (Main Container) -->
  <main class="main-container" id="main-container">
    
    <!-- === 模式 A: ORCA 精工工作台 (Orca Workbench) === -->
    <div class="workbench-view" id="workbench-view">
      
      <!-- 左側：可對話視窗 (Conversational AI Station) -->
      <section class="chat-console">
        <div class="console-header">
          <div class="station-badge">
            <span class="pulse-dot"></span>
            <span id="active-station-label">🎯 當前工位：N4 沙盒重構工位 [階段四：執行與驗證]</span>
          </div>
          <div class="console-meta">
            <span class="tag tag-runner">⚡ Codex Runner</span>
            <span class="tag tag-gov">Tier 0 憲章</span>
          </div>
        </div>

        <!-- 對話訊息串 (Dialogue Stream) -->
        <div class="chat-stream" id="chat-stream">
          <!-- 系統歡迎與當前工位卡片 -->
          <div class="chat-card chat-assistant">
            <div class="card-avatar">🐋</div>
            <div class="card-body">
              <div class="card-header">
                <strong>Orca 工作台助理</strong>
                <span class="card-time">10:00:00</span>
              </div>
              <div class="card-text">
                已鎖定工位 <code>task_n4 (N4 沙盒重構工位)</code>。<br>
                已加載 <strong>Contract Linter 47 題規則庫</strong> 與 <strong>Invariant 14 門禁基線</strong>。<br>
                本工作台覆蓋<strong>任務維度到原子維度</strong>，你可以直接下達指令，或點擊下方一鍵裝配工令：
              </div>
            </div>
          </div>
        </div>

        <!-- 一鍵工令裝配工具列 (Quick Action Bar) -->
        <div class="quick-action-bar">
          <button class="q-btn" onclick="sendQuickCommand('啟動沙盒測試')">🧪 啟動沙盒測試</button>
          <button class="q-btn" onclick="sendQuickCommand('在此開立工單')">🛠️ 在此開立工單</button>
          <button class="q-btn" onclick="sendQuickCommand('診斷當前卡點')">🔍 診斷當前卡點</button>
          <button class="q-btn" onclick="sendQuickCommand('推進原子步驟')">⚡ 推進原子步驟</button>
          <button class="q-btn q-btn-accent" onclick="sendQuickCommand('提交 Josh 驗收')">🚢 提交 Josh 驗收</button>
        </div>

        <!-- 對話輸入框 (Interactive Input Box) -->
        <div class="console-input-box">
          <textarea id="chat-input" placeholder="對工位下達指令... (例如：執行沙盒測試、開立修復工單、分析卡點，Enter 送出)" rows="2"></textarea>
          <button id="send-btn" onclick="handleSendMessage()">送出 ↵</button>
        </div>
      </section>

      <!-- 右側：任務維度到原子維度工作區 (Task to Atomic Dimension Panel) -->
      <section class="dimension-workplace">
        
        <!-- 任務與目標層級卡片 (Task Dimension Overview) -->
        <div class="task-overview-card">
          <div class="task-card-header">
            <div>
              <span class="badge-phase" id="task-phase-badge">階段四：執行與驗證</span>
              <h2 id="task-title-heading">N4 沙盒重構與 Verifier 獨立隔離門禁</h2>
            </div>
            <div class="task-card-status">
              <span class="status-pill status-ready" id="task-status-pill">● 待裝配 (READY)</span>
            </div>
          </div>
          <p class="task-desc" id="task-desc-text">
            透過臨時 Git Worktree 隔離環境重構 N4 產物邊界，要求 Contract Linter 達到 error_count=0 且符合 Invariant 14 數位憑證要求。
          </p>
          <div class="task-metrics">
            <div class="metric-item">
              <span class="m-label">目標完成度</span>
              <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width: 75%;"></div></div>
              <span class="m-val">75%</span>
            </div>
            <div class="metric-item">
              <span class="m-label">風控等級</span>
              <span class="m-val" style="color: #f85149;">HIGH (Josh 專屬簽核)</span>
            </div>
            <div class="metric-item">
              <span class="m-label">獨立驗證</span>
              <span class="m-val" style="color: #3fb950;">ENFORCED (無公差)</span>
            </div>
          </div>
        </div>

        <!-- 原子步驟檢驗鏈 (Atomic Checklist & Stepper) -->
        <div class="atomic-stepper-card">
          <div class="section-heading">
            <span>⚛️ 原子維度執行鏈 (Atomic Action Stepper)</span>
            <span class="step-counter" id="step-counter">步驟 3 / 5</span>
          </div>
          <div class="stepper-list" id="stepper-list">
            <div class="step-row step-done" id="step-1">
              <span class="step-check">✓</span>
              <div class="step-info">
                <div class="step-title">步驟 1：Contract Linter 靜態語法與路徑核對 (47 題規則庫)</div>
                <div class="step-meta">規則 LINT-001 ~ LINT-007 檢驗 · error_count=0 (PASS)</div>
              </div>
            </div>
            <div class="step-row step-done" id="step-2">
              <span class="step-check">✓</span>
              <div class="step-info">
                <div class="step-title">步驟 2：建立隔離 Worktree 沙盒環境</div>
                <div class="step-meta">目錄 <code>/tmp/wt-n4-isolate</code> · SHA <code>f524209</code></div>
              </div>
            </div>
            <div class="step-row step-active" id="step-3">
              <span class="step-check">▶</span>
              <div class="step-info">
                <div class="step-title">步驟 3：自動化測試與覆蓋率檢驗 (Pytest / Node)</div>
                <div class="step-meta">執行 <code>pytest tests/test_hierarchy.py -q</code> · 144/144 通過</div>
              </div>
            </div>
            <div class="step-row step-pending" id="step-4">
              <span class="step-check">○</span>
              <div class="step-info">
                <div class="step-title">步驟 4：獨立 Verifier 數位憑證簽署 (SHA-256)</div>
                <div class="step-meta">簽章機構 <code>Josh-Automated-Gate</code> · Invariant 11 門禁</div>
              </div>
            </div>
            <div class="step-row step-pending" id="step-5">
              <span class="step-check">🔒</span>
              <div class="step-info">
                <div class="step-title">步驟 5：Josh 人工專屬驗收 ➔ 合入 Master 主幹</div>
                <div class="step-meta">審查數位憑證 · Invariant 14 簽核 · Push GitHub mainline</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 即時原子終端與數位憑證監控 (Live Terminal & Evidence Inspector) -->
        <div class="inspector-card">
          <div class="inspector-tabs">
            <button class="insp-tab active" id="tab-btn-terminal" onclick="switchInspTab('terminal')">📟 即時終端 (Terminal)</button>
            <button class="insp-tab" id="tab-btn-diff" onclick="switchInspTab('diff')">📄 代碼變更 (Git Diff)</button>
            <button class="insp-tab" id="tab-btn-evidence" onclick="switchInspTab('evidence')">🛡️ 數位證據 (SHA-256)</button>
            <button class="insp-tab" id="tab-btn-tickets" onclick="switchInspTab('tickets')">📋 原子工單庫 (Tickets)</button>
          </div>
          <div class="inspector-body">
            <!-- 終端分頁 -->
            <div class="tab-pane active" id="pane-terminal">
              <div class="terminal-view" id="terminal-view">
                <div class="term-line term-dim">[10:00:01] Initializing Orca Workbench Daemon v0.1.0...</div>
                <div class="term-line term-info">[10:00:02] Connected to SQLite database: /app/.workbench/workbench.db</div>
                <div class="term-line term-success">[10:00:03] Container company-ai-workbench-local: HEALTHY</div>
                <div class="term-line term-warn">[10:00:04] Current active node: task_n4 (N4 沙盒重構工位)</div>
                <div class="term-line term-dim">[10:00:05] Ready for interactive dispatch and atomic execution.</div>
              </div>
            </div>
            <!-- Diff 分頁 -->
            <div class="tab-pane" id="pane-diff">
              <pre class="diff-view" id="diff-view">
diff --git a/tools/contract_linter/rules.js b/tools/contract_linter/rules.js
--- a/tools/contract_linter/rules.js
+++ b/tools/contract_linter/rules.js
@@ -104,7 +104,7 @@
-  const forbidden = ["saya-Josh-useonly", "private/"];
+  const forbidden = ["saya-Josh-useonly", "private/", "secrets/"];
+  // Enforce zero-tolerance forbidden directory isolation
+  // Expected outputs verified with hierarchical checking
              </pre>
            </div>
            <!-- 數位憑證分頁 -->
            <div class="tab-pane" id="pane-evidence">
              <div class="evidence-box" id="evidence-box">
                <div class="ev-row"><span class="ev-k">工單標號：</span><span class="ev-v">#TKT-104</span></div>
                <div class="ev-row"><span class="ev-k">工位節點：</span><span class="ev-v">task_n4</span></div>
                <div class="ev-row"><span class="ev-k">數位雜湊 (SHA-256)：</span><span class="ev-v code-highlight" id="ev-sha">3a9f8c12b0e77d24a1599876e4c3d2b1f0e9a8b7c6d5e4f3a2b1c0d9e8f7a6b5</span></div>
                <div class="ev-row"><span class="ev-k">驗證者身份：</span><span class="ev-v">Josh-Automated-Gate (human-delegated)</span></div>
                <div class="ev-row"><span class="ev-k">合規門禁：</span><span class="ev-v" style="color:#3fb950;">Invariant 11 (Verifier Independence: PASS)</span></div>
              </div>
            </div>
            <!-- 工單清單分頁 -->
            <div class="tab-pane" id="pane-tickets">
              <div id="tickets-table-container" style="font-size:12px; color:var(--text);">
                正在載入本地資料庫工單清冊...
              </div>
            </div>
          </div>
        </div>

      </section>
    </div>

    <!-- === 模式 B: 全維度可視化天眼 (Full Dimension Universe View) === -->
    <div class="universe-view" id="universe-view">
      <!-- 畫布工具列 -->
      <div class="universe-toolbar">
        <div class="filter-group">
          <span class="filter-label">維度篩選：</span>
          <button class="f-btn active" onclick="filterUniverse('all', this)">全部維度 (All Dimensions)</button>
          <button class="f-btn" onclick="filterUniverse(1, this)">維度 1：治理憲法</button>
          <button class="f-btn" onclick="filterUniverse(2, this)">維度 2：檢驗門禁</button>
          <button class="f-btn" onclick="filterUniverse(3, this)">維度 3：任務流水線</button>
          <button class="f-btn" onclick="filterUniverse(4, this)">維度 4：執行與驗證</button>
          <button class="f-btn" onclick="filterUniverse(5, this)">維度 5：主幹交付</button>
        </div>
        <div class="universe-actions">
          <button class="f-btn" onclick="resetUniverseView()">⟲ 重設視角</button>
        </div>
      </div>

      <!-- Vis-Network 畫布容器 -->
      <div id="network-canvas"></div>

      <!-- 節點懸浮檢驗卡片 (點擊節點後彈出，附帶「進入此節點工作台」按鈕) -->
      <div class="node-flyout-card" id="node-flyout-card" style="display:none;">
        <div class="flyout-header">
          <h3 id="flyout-title">節點標題</h3>
          <button class="close-btn" onclick="closeFlyout()">×</button>
        </div>
        <div class="flyout-body">
          <div class="flyout-meta" id="flyout-meta">階段三：任務流水線 · Level 3</div>
          <p class="flyout-desc" id="flyout-desc">節點描述細節...</p>
          <div class="flyout-section">相關文件 / 規則</div>
          <div class="flyout-files" id="flyout-files"></div>
        </div>
        <div class="flyout-footer">
          <button id="flyout-open-btn" onclick="openNodeInWorkbench()">
            🚀 進入此節點工作台 (Open in Workbench)
          </button>
        </div>
      </div>
    </div>

  </main>

  <!-- JavaScript 核心控制邏輯 -->
  <script>
    const RAW_NODES = {nodes_json};
    const RAW_EDGES = {edges_json};

    let currentNodeId = "task_n4";
    let activeViewMode = "workbench";
    let network = null;
    let visNodes = null;
    let visEdges = null;

    // 1. 初始化
    document.addEventListener("DOMContentLoaded", function() {{
      initVisNetwork();
      loadDatabaseState();
      
      const chatInput = document.getElementById("chat-input");
      if (chatInput) {{
        chatInput.addEventListener("keydown", function(e) {{
          if (e.key === "Enter" && !e.shiftKey) {{
            e.preventDefault();
            handleSendMessage();
          }}
        }});
      }}
    }});

    // 2. 視圖模式切換 (Workbench / Split / Universe)
    function switchViewMode(mode) {{
      activeViewMode = mode;
      
      const tabWb = document.getElementById("tab-workbench");
      const tabSplit = document.getElementById("tab-split");
      const tabUniv = document.getElementById("tab-universe");
      const mainContainer = document.getElementById("main-container");
      const wbView = document.getElementById("workbench-view");
      const univView = document.getElementById("universe-view");

      tabWb.classList.remove("active");
      tabSplit.classList.remove("active");
      tabUniv.classList.remove("active");
      mainContainer.classList.remove("split-view-active");

      if (mode === "workbench") {{
        tabWb.classList.add("active");
        wbView.style.display = "flex";
        univView.style.display = "none";
      }} else if (mode === "universe") {{
        tabUniv.classList.add("active");
        wbView.style.display = "none";
        univView.style.display = "block";
        if (network) network.fit();
      }} else if (mode === "split") {{
        tabSplit.classList.add("active");
        mainContainer.classList.add("split-view-active");
        wbView.style.display = "flex";
        univView.style.display = "block";
        if (network) network.fit();
      }}
    }}

    // 3. 檢驗監控台分頁切換 (Terminal / Diff / Evidence / Tickets)
    function switchInspTab(tabName) {{
      const tabs = ["terminal", "diff", "evidence", "tickets"];
      tabs.forEach(t => {{
        const btn = document.getElementById("tab-btn-" + t);
        const pane = document.getElementById("pane-" + t);
        if (btn) btn.classList.remove("active");
        if (pane) pane.classList.remove("active");
      }});
      const targetBtn = document.getElementById("tab-btn-" + tabName);
      const targetPane = document.getElementById("pane-" + tabName);
      if (targetBtn) targetBtn.classList.add("active");
      if (targetPane) targetPane.classList.add("active");
    }}

    // 4. 對話視窗訊息發送 (Interactive Conversational Engine)
    async function handleSendMessage() {{
      const input = document.getElementById("chat-input");
      const msg = input.value.trim();
      if (!msg) return;
      input.value = "";
      await executeChatDispatch(msg);
    }}

    function sendQuickCommand(cmd) {{
      executeChatDispatch(cmd);
    }}

    async function executeChatDispatch(msg) {{
      const stream = document.getElementById("chat-stream");
      const now = new Date().toTimeString().split(" ")[0];

      // 加入使用者訊息氣泡
      const userHtml = `
        <div class="chat-card chat-user">
          <div class="card-avatar">👤</div>
          <div class="card-body">
            <div class="card-header">
              <strong>Josh</strong>
              <span class="card-time">${{now}}</span>
            </div>
            <div class="card-text">${{escapeHtml(msg)}}</div>
          </div>
        </div>
      `;
      stream.insertAdjacentHTML("beforeend", userHtml);
      stream.scrollTop = stream.scrollHeight;

      // 加入即時終端指令行
      appendTerminalLine(`[USER-CMD] >> ${{msg}}`, "term-info");

      try {{
        const resp = await fetch("/api/chat", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ message: msg, node_id: currentNodeId }})
        }});
        const data = await resp.json();

        // 格式化助理回覆
        let replyFormatted = escapeHtml(data.reply || "")
          .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
          .replace(/`(.*?)`/g, '<code>$1</code>')
          .replace(/\\n/g, '<br>');

        const assistantHtml = `
          <div class="chat-card chat-assistant">
            <div class="card-avatar">🐋</div>
            <div class="card-body">
              <div class="card-header">
                <strong>Orca 工作台助理</strong>
                <span class="card-time">${{new Date().toTimeString().split(" ")[0]}}</span>
              </div>
              <div class="card-text">${{replyFormatted}}</div>
            </div>
          </div>
        `;
        stream.insertAdjacentHTML("beforeend", assistantHtml);
        stream.scrollTop = stream.scrollHeight;

        // 終端輸出串接
        if (data.terminal_output && Array.isArray(data.terminal_output)) {{
          data.terminal_output.forEach(line => {{
            const colorClass = line.includes("PASS") ? "term-success" : (line.includes(">>") ? "term-info" : "term-dim");
            appendTerminalLine(line, colorClass);
          }});
        }}

        // 更新原子步驟鏈
        if (data.atomic_step) {{
          updateAtomicStep(data.atomic_step.step, data.atomic_step.status);
        }}

        // 更新數位雜湊憑證
        if (data.evidence_sha) {{
          const shaEl = document.getElementById("ev-sha");
          if (shaEl) shaEl.textContent = data.evidence_sha;
        }}

        // 重新整理資料庫工單
        loadDatabaseState();

      }} catch (err) {{
        appendTerminalLine(`[ERROR] Communication failure: ${{err.message}}`, "term-warn");
      }}
    }}

    function appendTerminalLine(text, colorClass = "term-dim") {{
      const term = document.getElementById("terminal-view");
      if (!term) return;
      const line = document.createElement("div");
      line.className = `term-line ${{colorClass}}`;
      line.textContent = text;
      term.appendChild(line);
      term.scrollTop = term.scrollHeight;
    }}

    function updateAtomicStep(stepNum, status) {{
      for (let i = 1; i <= 5; i++) {{
        const el = document.getElementById("step-" + i);
        if (!el) continue;
        if (i < stepNum) {{
          el.className = "step-row step-done";
          el.querySelector(".step-check").textContent = "✓";
        }} else if (i === stepNum) {{
          el.className = status === "pass" ? "step-row step-done" : "step-row step-active";
          el.querySelector(".step-check").textContent = status === "pass" ? "✓" : "▶";
        }} else {{
          el.className = "step-row step-pending";
          el.querySelector(".step-check").textContent = i === 5 ? "🔒" : "○";
        }}
      }}
      const counter = document.getElementById("step-counter");
      if (counter) counter.textContent = `步驟 ${{Math.min(stepNum, 5)}} / 5`;
    }}

    // 5. 初始化全維度可視化圖譜 (Vis-Network Universe)
    function initVisNetwork() {{
      const container = document.getElementById("network-canvas");
      if (!container) return;

      const formattedNodes = RAW_NODES.map(n => {{
        return {{
          id: n.id,
          label: n.label,
          level: n.level,
          color: {{
            background: n.color || "#1f6feb",
            border: n.id === currentNodeId ? "#f0883e" : "#30363d",
            highlight: {{ background: n.color || "#1f6feb", border: "#f0883e" }}
          }},
          shape: "box",
          margin: 10,
          font: {{ color: "#ffffff", size: 12, face: "system-ui" }},
          borderWidth: n.id === currentNodeId ? 3 : 1,
          shadow: n.id === currentNodeId ? {{ enabled: true, color: "rgba(240, 136, 62, 0.4)", size: 10 }} : false,
          rawData: n
        }};
      }});

      visNodes = new vis.DataSet(formattedNodes);
      visEdges = new vis.DataSet(RAW_EDGES.map(e => ({{
        ...e,
        arrows: "to",
        color: e.color || {{ color: "#30363d", highlight: "#f0883e" }},
        smooth: {{ type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 }}
      }})));

      const options = {{
        layout: {{
          hierarchical: {{
            direction: "LR",
            sortMethod: "directed",
            levelSeparation: 220,
            nodeSpacing: 100
          }}
        }},
        physics: {{ enabled: false }},
        interaction: {{ hover: true, tooltipDelay: 100 }}
      }};

      network = new vis.Network(container, {{ nodes: visNodes, edges: visEdges }}, options);

      // 點擊節點事件
      network.on("click", function(params) {{
        if (params.nodes.length > 0) {{
          const clickedId = params.nodes[0];
          showFlyout(clickedId);
        }} else {{
          closeFlyout();
        }}
      }});
    }}

    function showFlyout(nodeId) {{
      const nodeObj = RAW_NODES.find(n => n.id === nodeId);
      if (!nodeObj) return;

      currentNodeId = nodeId;
      const flyout = document.getElementById("node-flyout-card");
      document.getElementById("flyout-title").textContent = nodeObj.label;
      document.getElementById("flyout-meta").textContent = `${{nodeObj.layer}} · 維度 ${{nodeObj.level}}`;
      document.getElementById("flyout-desc").textContent = nodeObj.summary + " " + (nodeObj.details || "");
      
      const filesContainer = document.getElementById("flyout-files");
      filesContainer.innerHTML = (nodeObj.files || []).map(f => `<span class="flyout-file-badge">${{escapeHtml(f)}}</span>`).join("");
      
      flyout.style.display = "block";
    }}

    function closeFlyout() {{
      const flyout = document.getElementById("node-flyout-card");
      if (flyout) flyout.style.display = "none";
    }}

    function openNodeInWorkbench() {{
      const nodeObj = RAW_NODES.find(n => n.id === currentNodeId);
      if (nodeObj) {{
        // 更新工作台標題與指示
        document.getElementById("active-station-label").textContent = `🎯 當前工位：${{nodeObj.label}} [${{nodeObj.layer}}]`;
        document.getElementById("ladder-node-title").textContent = nodeObj.label.split(" ")[1] || nodeObj.label;
        document.getElementById("task-title-heading").textContent = nodeObj.label;
        document.getElementById("task-phase-badge").textContent = nodeObj.layer;
        document.getElementById("task-desc-text").textContent = nodeObj.summary + " " + (nodeObj.details || "");
        
        appendTerminalLine(`[STATION-SWITCH] Switched active station to: ${{nodeObj.id}} (${{nodeObj.label}})`, "term-warn");
      }}
      closeFlyout();
      switchViewMode("workbench");
    }}

    function filterUniverse(level, btnEl) {{
      const btns = document.querySelectorAll(".filter-group .f-btn");
      btns.forEach(b => b.classList.remove("active"));
      if (btnEl) btnEl.classList.add("active");

      if (level === "all") {{
        visNodes.forEach(n => visNodes.update({{ id: n.id, hidden: false }}));
      }} else {{
        visNodes.forEach(n => {{
          const isMatch = (n.rawData && n.rawData.level === level);
          visNodes.update({{ id: n.id, hidden: !isMatch }});
        }});
      }}
      if (network) network.fit();
    }}

    function resetUniverseView() {{
      if (network) {{
        network.fit();
      }}
    }}

    // 6. 載入資料庫現況 (Load DB State)
    async function loadDatabaseState() {{
      try {{
        const resp = await fetch("/api/state");
        const data = await resp.json();
        
        // 渲染工單清單表格
        const container = document.getElementById("tickets-table-container");
        if (!container) return;

        if (!data.tickets || data.tickets.length === 0) {{
          container.innerHTML = '<div style="color:var(--text-muted);">目前無工單記錄。可在左側直接點擊「在此開立工單」立案。</div>';
          return;
        }}

        let tableHtml = `
          <table style="width:100%; border-collapse:collapse; font-size:11.5px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border); color:var(--text-muted); text-align:left;">
                <th style="padding:6px;">標號</th>
                <th style="padding:6px;">標題</th>
                <th style="padding:6px;">風險</th>
                <th style="padding:6px;">狀態</th>
                <th style="padding:6px;">工位</th>
              </tr>
            </thead>
            <tbody>
        `;

        data.tickets.forEach(t => {{
          const statusColor = t.status === "accepted" ? "#3fb950" : (t.status === "verification" ? "#a371f7" : (t.status === "active" ? "#f0883e" : "#8b99ab"));
          tableHtml += `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
              <td style="padding:6px; font-weight:700;">#${{t.id}}</td>
              <td style="padding:6px; color:var(--text-bright);">${{escapeHtml(t.title)}}</td>
              <td style="padding:6px; color:#f85149;">${{t.risk_level.toUpperCase()}}</td>
              <td style="padding:6px;"><span style="color:${{statusColor}}; font-weight:700;">${{t.status.toUpperCase()}}</span></td>
              <td style="padding:6px; font-family:monospace; color:#79c0ff;">${{t.node_id || 'task_n4'}}</td>
            </tr>
          `;
        }});

        tableHtml += '</tbody></table>';
        container.innerHTML = tableHtml;

      }} catch (err) {{
        console.warn("無法取得 /api/state:", err);
      }}
    }}

    function escapeHtml(str) {{
      if (!str) return "";
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }}
  </script>
</body>
</html>"""
