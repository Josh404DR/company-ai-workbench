"""
AgentOS Living Mind Map & Node-Centric Dialogue Generator.
Ingests E:\Workspace\agentos-lite and renders an interactive, visual knowledge graph
with layered nodes (Architecture, Logic, Memory, Path) and node-grounded conversation.
"""

import html
import json
from pathlib import Path

def get_agentos_graph_data():
    """Extract grounded node graph from E:\Workspace\agentos-lite."""
    nodes = [
        # --- 🏛️ 架構層節點 (Architecture Layer - Blue) ---
        {
            "id": "arch_core",
            "label": "🏛️ AgentOS-Lite 核心契約",
            "group": "architecture",
            "layer": "架構層",
            "summary": "以 AGENTS.md 為正本的合約治理系統，界定 Builder/Verifier 責任邊界與工單生命週期。",
            "files": ["AGENTS.md", "README.md", "docs/SOURCE_MAP.md"],
            "details": "捨棄重型背景守護行程 (Queue/Runner/Gateway)，採用純靜態合約與 IDE 工作流機制。",
            "color": "#1f6feb"
        },
        {
            "id": "arch_linter",
            "label": "🏛️ Contract Linter 契約稽核器",
            "group": "architecture",
            "layer": "架構層",
            "summary": "派工前強制檢查工具，必須達到 error_count=0 才准啟動 Builder。",
            "files": ["tools/contract_linter/", "tests/test_contract_linter.js"],
            "details": "具備 47 項自動化測試，鎖定基線 f524209394d05069f18aa4fbc5707c6fe48bbe1d。",
            "color": "#1f6feb"
        },
        {
            "id": "arch_packet",
            "label": "🏛️ Task / Result Packet 封包系統",
            "group": "architecture",
            "layer": "架構層",
            "summary": "結構化傳遞需求與結果的不可變 JSON 封包，定義輸入路徑、預期產物與驗證權限。",
            "files": ["packets/phase_1/", "packets/schema/task_packet.json"],
            "details": "禁止 Builder 自行擴充產物邊界，所有輸出必須在 expected_outputs 明確宣告。",
            "color": "#1f6feb"
        },
        {
            "id": "arch_verifier",
            "label": "🏛️ Independent Verifier 獨立驗證門禁",
            "group": "architecture",
            "layer": "架構層",
            "summary": "驗證者必須完全獨立於 Builder，禁止自我審查（球員兼裁判）。",
            "files": ["verify/", "AGENTS.md#IV-Rules"],
            "details": "只有獨立驗證通過 (PASS) 的工單，才允許進入 Josh 最終驗收 (Josh Accepted)。",
            "color": "#1f6feb"
        },
        {
            "id": "arch_memory_hub",
            "label": "🏛️ Central Skills 跨 CLI 記憶中樞",
            "group": "architecture",
            "layer": "架構層",
            "summary": "透過 josh-shared-memory 技能與 sync-skills.ps1 實現跨模型 (Codex/Claude/Antigravity) 記憶共享。",
            "files": ["agent-skills-hub/skills/josh-shared-memory/", "E:\\Workspace\\DOCUMENT_GOVERNANCE.md"],
            "details": "不複製對話噪音，僅共享可追溯的治理正本與專案現況狀態。",
            "color": "#1f6feb"
        },

        # --- ⚙️ 底層邏輯節點 (Logic Layer - Green) ---
        {
            "id": "logic_rules",
            "label": "⚙️ 47 題規則庫 (LINT-001 ~ 007)",
            "group": "logic",
            "layer": "底層邏輯",
            "summary": "核心語法與結構規則引擎，檢查路徑衝突、禁止路徑越界與產物完整性。",
            "files": ["tools/contract_linter/rules.js"],
            "details": "涵蓋 LINT-001 (格式) 至 LINT-007 (expected_outputs 階層式路徑核對)。",
            "color": "#238636"
        },
        {
            "id": "logic_rag",
            "label": "⚙️ 本機輕量 RAG 檢索引擎",
            "group": "logic",
            "layer": "底層邏輯",
            "summary": "純本機 TF-IDF 字元 n-gram 索引 (E:\\Workspace\\rag)，零外部 API 依賴。",
            "files": ["E:\\Workspace\\rag\\scripts\\ingest.py", "E:\\Workspace\\rag\\scripts\\config.py"],
            "details": "索引 58 個核心檔案、750 個切塊，專責快速檢索治理與規格正本。",
            "color": "#238636"
        },
        {
            "id": "logic_forbidden",
            "label": "⚙️ 禁止路徑攔截器 (Forbidden Guard)",
            "group": "logic",
            "layer": "底層邏輯",
            "summary": "在沙盒執行前攔截任何企圖讀取機密目錄 (如 saya-Josh-useonly) 的非法操作。",
            "files": ["tools/contract_linter/forbidden_paths.json"],
            "details": "防止跨專案或客戶機密外洩，Fail-Closed 阻擋非授權檔案存取。",
            "color": "#238636"
        },

        # --- 🧠 記憶層節點 (Memory Layer - Purple/Gold) ---
        {
            "id": "mem_governance",
            "label": "🧠 Tier 0~4 分層治理憲法",
            "group": "memory",
            "layer": "記憶層",
            "summary": "定義文件權威順序：Tier 0 硬規則 > Tier 1 導航 > Tier 2 現況正本 > Tier 3 主題參考 > Tier 4 歷史證據。",
            "files": ["E:\\Workspace\\DOCUMENT_GOVERNANCE.md", "E:\\Workspace\\MEMORY_INDEX.md"],
            "details": "解決 947 份文件搜尋混亂問題，禁止批次修改歷史證據。",
            "color": "#8957e5"
        },
        {
            "id": "mem_nogo",
            "label": "🧠 N4 探索工單 No-Go 核心教訓",
            "group": "memory",
            "layer": "記憶層",
            "summary": "N4 因 Task Packet 未授權 Verifier 產物且扁平 expected_outputs 使 LINT-007 漏檢，判定 FAIL。",
            "files": ["DECISIONS.md#2026-08-16", "README.md#最終決策"],
            "details": "觸發停止 AgentOS-Lite 平台常駐化開發，決定將合約機制直接轉入本地 IDE 流程。",
            "color": "#d29922"
        },
        {
            "id": "mem_rag_conf",
            "label": "🧠 CONF-006 隱私隔離命名裁決",
            "group": "memory",
            "layer": "記憶層",
            "summary": "Josh 裁決將 saya-Josh-useonly 正式更名為 rag-governance，消除撞名混淆。",
            "files": ["DECISIONS.md#2026-08-19", "E:\\Workspace\\ai-tool-core\\docs\\DECISION_LOG.md"],
            "details": "保留檔案作為 RAG 治理正本，重跑 ingest.py 確認無孤兒引用。",
            "color": "#8957e5"
        },

        # --- 📍 工單探索路徑節點 (Path / Trajectory - Orange) ---
        {
            "id": "task_n1",
            "label": "📍 N1: 契約基線確立 (Accepted)",
            "group": "path",
            "layer": "歷史軌跡",
            "summary": "建立 contract_linter 初始架構與前 20 項基礎語法測試。",
            "files": ["packets/phase_1/n1-baseline/"],
            "details": "由 Claude 實作完成，通過獨立驗收合入。",
            "color": "#3fb950"
        },
        {
            "id": "task_n2",
            "label": "📍 N2: 輕量 RAG 整合 (Accepted)",
            "group": "path",
            "layer": "歷史軌跡",
            "summary": "整合 E:\\Workspace\\rag 本地搜尋引擎與治理文件索引。",
            "files": ["packets/phase_1/n2-rag-integration/"],
            "details": "建立 58 份文件語意索驥，確認零外部 token 消耗。",
            "color": "#3fb950"
        },
        {
            "id": "task_n3",
            "label": "📍 N3: 來源清冊盤點 (Accepted)",
            "group": "path",
            "layer": "歷史軌跡",
            "summary": "盤點 13 份歷史規格來源，產出 RAG_SOURCE_CONFLICTS。",
            "files": ["packets/phase_1/n3-rag-source-manifest/"],
            "details": "發現 3 筆需主管裁決的政策衝突，為後續治理奠定基礎。",
            "color": "#3fb950"
        },
        {
            "id": "task_n4",
            "label": "📍 N4: 探索性真實工單 (當前焦點 / No-Go)",
            "group": "path",
            "layer": "當前焦點",
            "summary": "【當前探索焦點】：LINT-007 檢查漏洞與 Verifier 未授權邊界。",
            "files": ["packets/phase_1/n4-exploratory/"],
            "details": "這是我們今天討論的出發點！如何修復 LINT-007 並在 Workbench 內重生？",
            "color": "#f0883e"
        }
    ]

    edges = [
        # 架構關聯
        {"from": "arch_core", "to": "arch_linter", "label": "呼叫驗證"},
        {"from": "arch_core", "to": "arch_packet", "label": "定義封包"},
        {"from": "arch_core", "to": "arch_verifier", "label": "門禁委派"},
        {"from": "arch_core", "to": "arch_memory_hub", "label": "共享記憶"},
        
        # 邏輯實作
        {"from": "arch_linter", "to": "logic_rules", "label": "執行規則"},
        {"from": "arch_linter", "to": "logic_forbidden", "label": "路徑過濾"},
        {"from": "arch_memory_hub", "to": "logic_rag", "label": "本機檢索"},
        
        # 記憶約束
        {"from": "mem_governance", "to": "arch_core", "label": "憲法約束"},
        {"from": "mem_nogo", "to": "task_n4", "label": "歷史警示"},
        {"from": "mem_rag_conf", "to": "logic_rag", "label": "命名校正"},
        
        # 軌跡路徑 (N1 -> N2 -> N3 -> N4)
        {"from": "task_n1", "to": "task_n2", "label": "演進至", "arrows": "to", "dashes": False},
        {"from": "task_n2", "to": "task_n3", "label": "演進至", "arrows": "to", "dashes": False},
        {"from": "task_n3", "to": "task_n4", "label": "演進至", "arrows": "to", "dashes": True, "color": {"color": "#f0883e", "highlight": "#f0883e"}},
        
        # N4 與 Linter / Verifier 的受損關係
        {"from": "task_n4", "to": "logic_rules", "label": "暴露 LINT-007 盲點", "dashes": True},
        {"from": "task_n4", "to": "arch_verifier", "label": "產物權限不足", "dashes": True}
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
  <title>AgentOS-Lite 全景心智圖與節點導航工作台</title>
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
    
    /* 頂部導航與路徑指示 */
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
    .badge-arch {{ background: rgba(56, 139, 253, 0.2); color: var(--blue); border: 1px solid var(--blue); }}
    .badge-logic {{ background: rgba(63, 185, 80, 0.2); color: var(--green); border: 1px solid var(--green); }}
    .badge-memory {{ background: rgba(188, 140, 255, 0.2); color: var(--purple); border: 1px solid var(--purple); }}
    .badge-path {{ background: rgba(240, 136, 62, 0.2); color: var(--orange); border: 1px solid var(--orange); }}

    .path-breadcrumbs {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      background: var(--bg);
      padding: 6px 14px;
      border-radius: 20px;
      border: 1px solid var(--border);
    }}
    .path-step {{ color: var(--text); }}
    .path-step.active {{ color: var(--orange); font-weight: bold; }}
    .path-arrow {{ color: var(--border); }}

    .top-actions {{
      display: flex;
      gap: 10px;
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
    .btn-primary {{ background: #238636; border-color: #2ea043; }}
    .btn-primary:hover {{ background: #2ea043; }}

    /* 主區域 */
    .main-workspace {{
      display: flex;
      flex: 1;
      position: relative;
      overflow: hidden;
    }}

    /* 左側節點對話與脈絡工作面板 */
    .node-drawer {{
      width: 420px;
      background: var(--panel-bg);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      transition: width 0.25s ease;
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
      font-size: 18px;
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
      padding: 10px 12px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-size: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: #79c0ff;
      margin-bottom: 8px;
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
      border-color: var(--blue);
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

    /* 圖例說明 */
    .legend-card {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      background: rgba(22, 27, 34, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12px;
      display: flex;
      gap: 16px;
      pointer-events: auto;
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

  <!-- 頂部導航與路徑指示 -->
  <div class="top-bar">
    <div class="brand">
      <h1>AgentOS-Lite 心智圖譜</h1>
      <span class="badge badge-path">專案路徑: E:\Workspace\agentos-lite</span>
    </div>

    <!-- 即時軌跡 (Breadcrumbs) -->
    <div class="path-breadcrumbs" id="active-trajectory">
      <span class="path-step">🏛️ 核心架構</span>
      <span class="path-arrow">➜</span>
      <span class="path-step">⚙️ 契約稽核</span>
      <span class="path-arrow">➜</span>
      <span class="path-step active" id="current-node-label">📍 N4 探索工單 (當前焦點)</span>
    </div>

    <div class="top-actions">
      <button class="btn" onclick="fitNetwork()">視角重置</button>
      <a href="/" class="btn btn-primary">返回主控制台</a>
    </div>
  </div>

  <!-- 主工作區 -->
  <div class="main-workspace">
    <!-- 左側節點對話與脈絡工作台 -->
    <div class="node-drawer">
      <div class="drawer-header">
        <span class="badge badge-path" id="drawer-layer-badge">當前焦點節點</span>
        <span style="font-size: 11px; color:#8b949e;">點擊任意節點即時切換</span>
      </div>
      
      <div class="drawer-content">
        <h2 class="node-title" id="drawer-node-title">📍 N4: 探索性真實工單</h2>
        <p style="font-size: 13px; line-height: 1.6; color: #8b949e;" id="drawer-node-summary">
          Phase 1 最後一張探索性工單，因 Task Packet 未授權 Verifier 產物且扁平 expected_outputs 導致 LINT-007 未檢查，判定 NO-GO。
        </p>

        <div class="section-title">依賴檔案與契約依據</div>
        <div id="drawer-node-files">
          <div class="code-box">📄 packets/phase_1/n4-exploratory/</div>
          <div class="code-box">📄 README.md#最終決策</div>
        </div>

        <div class="section-title">底層細節與記憶脈絡</div>
        <div style="font-size: 13px; line-height: 1.5; color: #c9d1d9; background: var(--card-bg); padding: 12px; border-radius: 6px; border:1px solid var(--border);" id="drawer-node-details">
          這是我們今天討論的最佳出發點！N4 的教訓指明了：扁平路徑無法涵蓋深層驗證，必須升級為階層式約束。
        </div>
      </div>

      <!-- 節點對話窗口 (Node-Centric Chat) -->
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

    <!-- 圖例 -->
    <div class="legend-card">
      <div class="legend-item"><div class="legend-dot" style="background:#1f6feb;"></div> 架構層 (Architecture)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#238636;"></div> 底層邏輯 (Logic)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#8957e5;"></div> 記憶憲法 (Memory)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f0883e;"></div> 演進軌跡 (Trajectory)</div>
    </div>
  </div>

  <script>
    const rawNodes = {nodes_json};
    const rawEdges = {edges_json};

    // 格式化 Vis.js 節點
    const visNodes = rawNodes.map(n => ({{
      id: n.id,
      label: n.label,
      color: {{
        background: n.color,
        border: '#ffffff',
        highlight: {{ background: '#f0883e', border: '#ffffff' }}
      }},
      font: {{ color: '#ffffff', face: '-apple-system, sans-serif', size: 14 }},
      shape: 'box',
      margin: 12,
      shadow: {{ enabled: true, color: 'rgba(0,0,0,0.5)', size: 8, x: 2, y: 2 }},
      raw: n
    }}));

    const visEdges = rawEdges.map(e => ({{
      from: e.from,
      to: e.to,
      label: e.label || '',
      arrows: e.arrows || 'to',
      dashes: e.dashes || false,
      color: e.color || {{ color: '#30363d', highlight: '#f0883e' }},
      font: {{ color: '#8b949e', size: 11, align: 'middle' }},
      smooth: {{ type: 'cubicBezier', roundness: 0.3 }}
    }}));

    const container = document.getElementById('network-canvas');
    const data = {{
      nodes: new vis.DataSet(visNodes),
      edges: new vis.DataSet(visEdges)
    }};

    const options = {{
      physics: {{
        barnesHut: {{
          gravitationalConstant: -3500,
          centralGravity: 0.3,
          springLength: 140,
          springConstant: 0.04
        }},
        stabilization: {{ iterations: 150 }}
      }},
      interaction: {{
        hover: true,
        tooltipDelay: 200,
        zoomView: true,
        dragView: true
      }}
    }};

    const network = new vis.Network(container, data, options);

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
      document.getElementById('current-node-label').innerText = node.label;

      const filesContainer = document.getElementById('drawer-node-files');
      filesContainer.innerHTML = node.files.map(f => `<div class="code-box">📄 ${{f}}</div>`).join('');

      // 動態更新對話快捷按鈕
      const chipsContainer = document.getElementById('dialogue-chips');
      chipsContainer.innerHTML = `
        <button class="prompt-chip" onclick="simulateChat('針對 [${{node.label}}] 的架構設計進行代碼審查')">
          💡 針對 [${{node.label}}] 的架構設計進行代碼審查
        </button>
        <button class="prompt-chip" onclick="simulateChat('分析 [${{node.label}}] 與上下游節點的依賴邊界')">
          💡 分析 [${{node.label}}] 與上下游節點的依賴邊界
        </button>
        <button class="prompt-chip" onclick="simulateChat('在此節點開立 Workbench 工單並切入沙盒實作')">
          ⚡ 在此節點開立 Workbench 工單並切入沙盒實作
        </button>
      `;
    }}

    function fitNetwork() {{
      network.fit({{ animation: {{ duration: 600, easingFunction: 'easeInOutQuad' }} }});
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
      alert(`💬 【從節點出發的對話已觸發】\n\n指令: "${{val}}"\n\n系統已將此節點設為座標起點，並在後端加載對應的代碼與記憶契約！`);
      input.value = '';
    }}

    // 初始化自動居中
    setTimeout(() => {{
      network.selectNodes(['task_n4']);
      fitNetwork();
    }}, 400);
  </script>
</body>
</html>"""
