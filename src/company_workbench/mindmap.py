"""
AgentOS Living Mind Map & Structured Workflow Pipeline Generator.
Renders an intuitive, hierarchical Left-to-Right workflow pipeline and node-centric dialogue surface.
Addresses scattered connection graph with structured stage levels, focus filters, and workflow steppers.
"""

import html
import json
from pathlib import Path

def get_agentos_graph_data():
    """Extract grounded node graph from E:\Workspace\agentos-lite with explicit Workflow levels."""
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
  <title>AgentOS-Lite 結構化工作流與心智圖譜</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {{
      --bg: #0d1117;
      --panel-bg: #161b22;
      --card-bg: #21262d;
      --border: #30363d;
      --text: #c9d1d9;
      --text-bright: #f0f6fc;
      --blue: #58a6ff;
      --green: #3fb950;
      --purple: #bc8cff;
      --orange: #f0883e;
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
    
    /* 頂部導航 */
    .top-bar {{
      height: 60px;
      background: var(--panel-bg);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      z-index: 10;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand h1 {{
      font-size: 16px;
      color: var(--text-bright);
      font-weight: 600;
    }}
    .badge {{
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 12px;
      font-weight: 600;
    }}
    .badge-path {{ background: rgba(240, 136, 62, 0.2); color: var(--orange); border: 1px solid var(--orange); }}

    /* 工作流階段導航條 (Pipeline Stepper) */
    .workflow-stepper {{
      display: flex;
      align-items: center;
      gap: 4px;
      background: var(--bg);
      padding: 4px 10px;
      border-radius: 24px;
      border: 1px solid var(--border);
    }}
    .step-item {{
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 16px;
      cursor: pointer;
      color: var(--text);
      transition: all 0.15s;
    }}
    .step-item:hover {{
      background: #30363d;
      color: var(--text-bright);
    }}
    .step-item.active {{
      background: rgba(240, 136, 62, 0.25);
      color: var(--orange);
      font-weight: bold;
      border: 1px solid var(--orange);
    }}
    .step-arrow {{
      color: #8b949e;
      font-size: 10px;
    }}

    .top-actions {{
      display: flex;
      gap: 8px;
    }}
    .btn {{
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      border: 1px solid var(--border);
      background: var(--card-bg);
      color: var(--text-bright);
      text-decoration: none;
      transition: all 0.15s;
    }}
    .btn:hover {{ background: #30363d; }}
    .btn.active {{
      background: var(--blue);
      border-color: var(--blue);
      color: #fff;
    }}
    .btn-primary {{ background: #238636; border-color: #2ea043; }}
    .btn-primary:hover {{ background: #2ea043; }}

    /* 主工作區 */
    .main-workspace {{
      display: flex;
      flex: 1;
      position: relative;
      overflow: hidden;
    }}

    /* 左側節點脈絡與對話抽屜 */
    .node-drawer {{
      width: 420px;
      background: var(--panel-bg);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 5;
    }}
    .drawer-header {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .drawer-content {{
      padding: 20px;
      overflow-y: auto;
      flex: 1;
    }}
    .node-title {{
      font-size: 17px;
      color: var(--text-bright);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .section-title {{
      font-size: 12px;
      text-transform: uppercase;
      color: #8b949e;
      font-weight: 700;
      margin-top: 16px;
      margin-bottom: 6px;
      letter-spacing: 0.5px;
    }}
    .code-box {{
      background: var(--bg);
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-size: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: #79c0ff;
      margin-bottom: 6px;
    }}

    /* 節點對話視窗 (Chat Surface) */
    .chat-section {{
      background: var(--bg);
      border-top: 1px solid var(--border);
      padding: 16px 20px;
    }}
    .chat-prompt-chips {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 12px;
    }}
    .prompt-chip {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      color: var(--text-bright);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      cursor: pointer;
      text-align: left;
      transition: all 0.15s;
    }}
    .prompt-chip:hover {{
      background: #30363d;
      border-color: var(--orange);
      transform: translateX(3px);
    }}
    .chat-input-row {{
      display: flex;
      gap: 8px;
    }}
    .chat-input {{
      flex: 1;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 12px;
      color: var(--text-bright);
      font-size: 13px;
    }}
    .chat-input:focus {{
      outline: none;
      border-color: var(--blue);
    }}

    /* 圖形畫布 */
    #network-canvas {{
      flex: 1;
      height: 100%;
      background: radial-gradient(circle, #1a202c 1px, #0d1117 1px);
      background-size: 24px 24px;
    }}

    /* 控制列浮動卡片 */
    .controls-card {{
      position: absolute;
      top: 16px;
      right: 20px;
      background: rgba(22, 27, 34, 0.9);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      gap: 10px;
      z-index: 5;
    }}

    /* 圖例說明 */
    .legend-card {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      background: rgba(22, 27, 34, 0.9);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 16px;
      font-size: 11px;
      display: flex;
      gap: 14px;
      pointer-events: auto;
      z-index: 5;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }}
  </style>
</head>
<body>

  <!-- 頂部導航 -->
  <div class="top-bar">
    <div class="brand">
      <h1>AgentOS 工作流脈絡圖</h1>
    </div>

    <!-- 5 階段結構化工作流導覽條 (Pipeline Stepper) -->
    <div class="workflow-stepper">
      <div class="step-item" onclick="focusStage(1)">1. 治理與憲章</div>
      <span class="step-arrow">➜</span>
      <div class="step-item" onclick="focusStage(2)">2. 契約檢驗門禁</div>
      <span class="step-arrow">➜</span>
      <div class="step-item active" onclick="focusStage(3)">3. 任務封包流水線</div>
      <span class="step-arrow">➜</span>
      <div class="step-item" onclick="focusStage(4)">4. 沙盒與驗證</div>
      <span class="step-arrow">➜</span>
      <div class="step-item" onclick="focusStage(5)">5. 主管交付結案</div>
    </div>

    <div class="top-actions">
      <button class="btn" onclick="fitNetwork()">居中視角</button>
      <a href="/" class="btn btn-primary">返回主控制台</a>
    </div>
  </div>

  <!-- 主工作區 -->
  <div class="main-workspace">
    <!-- 左側節點脈絡抽屜 -->
    <div class="node-drawer">
      <div class="drawer-header">
        <span class="badge badge-path" id="drawer-layer-badge">階段三：任務流水線</span>
        <span style="font-size: 11px; color:#8b949e;">點擊任一節點聚焦</span>
      </div>
      
      <div class="drawer-content">
        <h2 class="node-title" id="drawer-node-title">🔥 N4: 探索真實工單 (當前焦點 / No-Go)</h2>
        <p style="font-size: 13px; line-height: 1.6; color: #8b949e;" id="drawer-node-summary">
          【當前工作流核心卡點】：N4 探索性工單因 Task Packet 未授權 Verifier 產物且扁平 expected_outputs 導致 LINT-007 漏檢，被判定 NO-GO。
        </p>

        <div class="section-title">依賴檔案與契約依據</div>
        <div id="drawer-node-files">
          <div class="code-box">📄 packets/phase_1/n4-exploratory/</div>
          <div class="code-box">📄 README.md#最終決策</div>
        </div>

        <div class="section-title">底層細節與記憶脈絡</div>
        <div style="font-size: 13px; line-height: 1.5; color: #c9d1d9; background: var(--card-bg); padding: 12px; border-radius: 6px; border:1px solid var(--border);" id="drawer-node-details">
          這就是我們的工作流起點！N4 的教訓指明了：扁平路徑無法涵蓋深層驗證，必須升級為階層式約束，並由 Workbench 的 Worktree 沙盒與 Auto-Debug 進行重生修復。
        </div>
      </div>

      <!-- 節點對話視窗 (Chat Surface) -->
      <div class="chat-section">
        <div class="section-title" style="margin-top:0;">從此節點出發討論 (Node Dialogue)</div>
        <div class="chat-prompt-chips" id="dialogue-chips">
          <button class="prompt-chip" onclick="simulateChat('深入分析 N4 為什麼被判定 No-Go？')">
            💡 深入分析 N4 為什麼被判定 No-Go？
          </button>
          <button class="prompt-chip" onclick="simulateChat('如何修復 LINT-007 缺失的階層驗證？')">
            💡 如何修復 LINT-007 缺失的階層驗證？
          </button>
          <button class="prompt-chip" onclick="simulateChat('在 Workbench 開立修復 Ticket，啟動自動除錯迴圈')">
            ⚡ 在 Workbench 開立修復 Ticket，啟動自動除錯迴圈
          </button>
        </div>
        <div class="chat-input-row">
          <input type="text" class="chat-input" id="chat-input-field" placeholder="針對此節點輸入你的問題或指令...">
          <button class="btn btn-primary" onclick="handleSendChat()">發送</button>
        </div>
      </div>
    </div>

    <!-- 視覺化心智圖畫布 -->
    <div id="network-canvas"></div>

    <!-- 視圖控制切換列 -->
    <div class="controls-card">
      <button class="btn active" id="btn-hierarchical" onclick="setMode('hierarchical')">📊 結構化工作流 (由左至右)</button>
      <button class="btn" id="btn-focus" onclick="toggleFocusActivePath()">🎯 僅聚焦當前主線</button>
      <button class="btn" id="btn-free" onclick="setMode('free')">🌐 全景網絡圖</button>
    </div>

    <!-- 圖例 -->
    <div class="legend-card">
      <div class="legend-item"><div class="legend-dot" style="background:#1f6feb;"></div> 架構層</div>
      <div class="legend-item"><div class="legend-dot" style="background:#238636;"></div> 底層邏輯</div>
      <div class="legend-item"><div class="legend-dot" style="background:#8957e5;"></div> 記憶憲法</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f0883e;"></div> 工作流主線</div>
      <div class="legend-item"><div class="legend-dot" style="background:#da3633;"></div> 交付門禁</div>
    </div>
  </div>

  <script>
    const rawNodes = {nodes_json};
    const rawEdges = {edges_json};

    let currentMode = 'hierarchical';
    let isFocusActive = false;

    // 格式化節點，加入 level 階層
    const visNodes = rawNodes.map(n => ({{
      id: n.id,
      label: n.label,
      level: n.level,
      color: {{
        background: n.color,
        border: '#ffffff',
        highlight: {{ background: '#f0883e', border: '#ffffff' }}
      }},
      font: {{ color: '#ffffff', face: '-apple-system, sans-serif', size: 13, bold: true }},
      shape: 'box',
      margin: 10,
      shadow: {{ enabled: true, color: 'rgba(0,0,0,0.5)', size: 6, x: 2, y: 2 }},
      raw: n
    }}));

    const visEdges = rawEdges.map(e => ({{
      from: e.from,
      to: e.to,
      label: e.label || '',
      arrows: 'to',
      width: e.width || 1.5,
      dashes: e.dashes || false,
      color: e.color || {{ color: '#30363d', highlight: '#f0883e' }},
      font: {{ color: '#8b949e', size: 10, align: 'middle' }},
      smooth: {{ type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.2 }}
    }}));

    const container = document.getElementById('network-canvas');
    const dataNodes = new vis.DataSet(visNodes);
    const dataEdges = new vis.DataSet(visEdges);

    function getOptions(mode) {{
      if (mode === 'hierarchical') {{
        return {{
          layout: {{
            hierarchical: {{
              enabled: true,
              direction: 'LR', // 由左至右 Left-to-Right
              sortMethod: 'directed',
              levelSeparation: 240,
              nodeSpacing: 90,
              treeSpacing: 150,
              blockShifting: true,
              edgeMinimization: true,
              parentCentralization: true
            }}
          }},
          physics: {{
            hierarchicalRepulsion: {{
              centralGravity: 0.0,
              springLength: 100,
              springConstant: 0.01,
              nodeDistance: 130,
              damping: 0.09
            }},
            solver: 'hierarchicalRepulsion'
          }},
          interaction: {{ hover: true, zoomView: true, dragView: true }}
        }};
      }} else {{
        return {{
          layout: {{ hierarchical: {{ enabled: false }} }},
          physics: {{
            barnesHut: {{
              gravitationalConstant: -3500,
              centralGravity: 0.3,
              springLength: 140,
              springConstant: 0.04
            }},
            stabilization: {{ iterations: 150 }}
          }},
          interaction: {{ hover: true, zoomView: true, dragView: true }}
        }};
      }}
    }}

    let network = new vis.Network(container, {{ nodes: dataNodes, edges: dataEdges }}, getOptions('hierarchical'));

    // 點擊節點互動
    network.on('click', function(params) {{
      if (params.nodes.length > 0) {{
        const nodeId = params.nodes[0];
        const selected = rawNodes.find(n => n.id === nodeId);
        if (selected) {{
          updateDrawer(selected);
        }}
      }}
    }});

    function updateDrawer(node) {{
      document.getElementById('drawer-node-title').innerText = node.label;
      document.getElementById('drawer-node-summary').innerText = node.summary;
      document.getElementById('drawer-node-details').innerText = node.details;
      document.getElementById('drawer-layer-badge').innerText = node.layer;

      const filesContainer = document.getElementById('drawer-node-files');
      filesContainer.innerHTML = node.files.map(f => `<div class="code-box">📄 ${{f}}</div>`).join('');

      // 動態更新對話快捷按鈕
      const chipsContainer = document.getElementById('dialogue-chips');
      chipsContainer.innerHTML = `
        <button class="prompt-chip" onclick="simulateChat('針對 [${{node.label}}] 進行架構依賴檢查')">
          💡 針對 [${{node.label}}] 進行架構依賴檢查
        </button>
        <button class="prompt-chip" onclick="simulateChat('分析 [${{node.label}}] 在 Workflow 中的上下游阻斷點')">
          💡 分析 [${{node.label}}] 在 Workflow 中的上下游阻斷點
        </button>
        <button class="prompt-chip" onclick="simulateChat('在此節點建立修復 Ticket 並啟動 Worktree 沙盒執行')">
          ⚡ 在此節點建立修復 Ticket 並啟動 Worktree 沙盒執行
        </button>
      `;
    }}

    function setMode(mode) {{
      currentMode = mode;
      document.getElementById('btn-hierarchical').classList.toggle('active', mode === 'hierarchical');
      document.getElementById('btn-free').classList.toggle('active', mode === 'free');
      network.setOptions(getOptions(mode));
      setTimeout(() => network.fit({{ animation: {{ duration: 500 }} }}), 200);
    }}

    function toggleFocusActivePath() {{
      isFocusActive = !isFocusActive;
      document.getElementById('btn-focus').classList.toggle('active', isFocusActive);
      
      const activeIds = ['mem_governance', 'arch_core', 'arch_linter', 'arch_packet', 'task_n4', 'workbench_engine', 'arch_verifier', 'human_acceptance', 'deliver_master'];
      
      dataNodes.forEach(node => {{
        if (isFocusActive) {{
          if (activeIds.includes(node.id)) {{
            dataNodes.update({{ id: node.id, opacity: 1, font: {{ color: '#ffffff' }} }});
          }} else {{
            dataNodes.update({{ id: node.id, opacity: 0.15, font: {{ color: 'rgba(255,255,255,0.2)' }} }});
          }}
        }} else {{
          dataNodes.update({{ id: node.id, opacity: 1, font: {{ color: '#ffffff' }} }});
        }}
      }});
      network.fit();
    }}

    function focusStage(stageLevel) {{
      const matched = rawNodes.filter(n => n.level === stageLevel).map(n => n.id);
      network.selectNodes(matched);
      if (matched.length > 0) {{
        network.focus(matched[0], {{ scale: 1.1, animation: {{ duration: 400 }} }});
        const selected = rawNodes.find(n => n.id === matched[0]);
        if (selected) updateDrawer(selected);
      }}
    }}

    function fitNetwork() {{
      network.fit({{ animation: {{ duration: 500 }} }});
    }}

    function simulateChat(text) {{
      const input = document.getElementById('chat-input-field');
      input.value = text;
      handleSendChat();
    }}

    function handleSendChat() {{
      const input = document.getElementById('chat-input-field');
      const val = input.value.trim();
      if (!val) return;
      alert(`💬 【從節點出發的對話已觸發】\n\n指令: "${{val}}"\n\n系統已將此節點設為工作流起點，並在後端加載對應的代碼與記憶契約！`);
      input.value = '';
    }}

    // 初始化自動居中聚焦在 N4
    setTimeout(() => {{
      network.selectNodes(['task_n4']);
      fitNetwork();
    }}, 400);
  </script>
</body>
</html>"""
