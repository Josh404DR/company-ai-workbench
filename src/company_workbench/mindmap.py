"""
AgentOS Living Mind Map & Structured Workflow Pipeline Generator.
Renders an intuitive, hierarchical Left-to-Right workflow pipeline and node-centric dialogue surface.
Addresses scattered connection graph with structured stage levels, focus filters, and workflow steppers.
"""

import html
import json
from pathlib import Path
import subprocess

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


def generate_project_graph_data(project_name: str, root_path: str | Path | None = None) -> tuple[list[dict], list[dict]]:
    """Generate dynamic mind map nodes & edges for any project based on its real directory & git structure."""
    if not root_path:
        return get_agentos_graph_data()

    p = Path(str(root_path).replace("\\", "/"))
    # Handle Docker vs Windows paths
    if not p.exists():
        if str(p).lower().startswith("e:/workspace/"):
            alt = Path("/workspace") / str(p)[len("e:/workspace/"):]
            if alt.exists():
                p = alt
        elif str(p).startswith("/workspace/"):
            alt = Path("E:/Workspace") / str(p)[len("/workspace/"):]
            if alt.exists():
                p = alt

    if not p.exists() or not p.is_dir():
        return get_agentos_graph_data()

    if p.name.lower() in ("agentos-lite", "agentos") or (p / "tools" / "contract_linter").exists():
        return get_agentos_graph_data()

    nodes = []
    edges = []

    # 1. Level 1: 專案治理與契約憲章 (Governance & Memory)
    agents_md = p / "AGENTS.md"
    readme_md = p / "README.md"
    
    mem_nodes = []
    if agents_md.exists():
        mem_nodes.append({
            "id": "mem_governance",
            "label": f"🏛️ {project_name} 核心契約 (AGENTS.md)",
            "group": "memory",
            "layer": "階段一：治理契約",
            "level": 1,
            "summary": "界定 Builder/Verifier 責任邊界、工單狀態流轉與安全不變量 (Invariants)。",
            "files": ["AGENTS.md"],
            "details": "本專案不可違背之最高憲章，所有工單遵循此標準交付。",
            "color": "#8957e5"
        })
    else:
        mem_nodes.append({
            "id": "mem_governance",
            "label": f"🏛️ {project_name} 專案架構契約",
            "group": "memory",
            "layer": "階段一：治理契約",
            "level": 1,
            "summary": "以合約驅動開發 (Contract-Driven)，規範模組邊界與職責邊界。",
            "files": ["README.md" if readme_md.exists() else "."],
            "details": "由專案裝配台統一納管之架構標準。",
            "color": "#8957e5"
        })

    # Specs / State
    doc_files = [f.name for f in p.glob("*.md") if f.name not in ("AGENTS.md",)]
    if doc_files:
        mem_nodes.append({
            "id": "mem_specs",
            "label": f"🧠 專案狀態與設計規格 ({doc_files[0]})",
            "group": "memory",
            "layer": "階段一：治理契約",
            "level": 1,
            "summary": f"收錄 {', '.join(doc_files[:3])} 等專案背景與需求現況。",
            "files": doc_files[:5],
            "details": "現況狀態與技術設計正本。",
            "color": "#8957e5"
        })
    else:
        mem_nodes.append({
            "id": "mem_specs",
            "label": f"🧠 專案狀態與技術規格 (PROJECT_STATE.md)",
            "group": "memory",
            "layer": "階段一：治理契約",
            "level": 1,
            "summary": "維護專案迭代狀態、決策記錄與規格定義。",
            "files": ["PROJECT_STATE.md"],
            "details": "規格與現況狀態追溯。",
            "color": "#8957e5"
        })
    
    docs_dir = p / "docs"
    if docs_dir.exists() and docs_dir.is_dir():
        mem_nodes.append({
            "id": "mem_docs",
            "label": "📖 系統設計與架構手冊 (docs/)",
            "group": "memory",
            "layer": "階段一：治理契約",
            "level": 1,
            "summary": "儲存主題規格文件、流程圖與技術決策記錄。",
            "files": ["docs/"],
            "details": "提供長效期架構參考與決策追溯。",
            "color": "#8957e5"
        })
    else:
        mem_nodes.append({
            "id": "mem_docs",
            "label": "📖 系統架構手冊與文件庫 (docs/)",
            "group": "memory",
            "layer": "階段一：治理契約",
            "level": 1,
            "summary": "收錄架構圖、API 規格與團隊共識指引。",
            "files": ["docs/"],
            "details": "提供系統設計與架構導覽。",
            "color": "#8957e5"
        })

    nodes.extend(mem_nodes)

    # 2. Level 2: 核心功能架構與模組 (Architecture & Modules)
    excluded_dirs = {
        ".git", ".claude", ".agents", ".venv", "venv", "node_modules",
        "__pycache__", "output", "tmp", "logs", "test-results", "scratch",
        "scratch_test", "dist", "build", ".idea", ".vscode", "temp-worktrees"
    }
    subdirs = [d for d in sorted(p.iterdir()) if d.is_dir() and d.name not in excluded_dirs and not d.name.startswith(".") and not d.name.startswith("_")]
    
    arch_nodes = []
    module_labels_map = {
        "modules": "⚙️ modules (核心邏輯模組)",
        "backend_server": "⚡ backend_server (後端服務器)",
        "governance-portal": "🌐 governance-portal (治理中控前端)",
        "coordination": "🤝 coordination (協調調度系統)",
        "prompts": "📝 prompts (AI 提示詞庫)",
        "schemas": "📐 schemas (資料模型與協議)",
        "config": "🔧 config (系統環境配置)",
        "src": "🏛️ src (系統核心源碼庫)",
        "tools": "🛠️ tools (工程輔助工具鏈)",
        "scripts": "📜 scripts (自動化維運腳本)",
        "storage": "💾 storage (持久化儲存層)",
        "prototype": "🎨 prototype (互動原型設計)",
        "webui": "💻 webui (使用者介面)",
        "archive": "📦 archive (歷史歸檔庫)",
        "utils": "🧰 utils (共用工具函數庫)"
    }

    for d in subdirs[:6]:
        slug = d.name.lower().replace("-", "_").replace(" ", "_")
        lbl = module_labels_map.get(d.name, f"📦 {d.name} (核心模組)")
        arch_nodes.append({
            "id": f"arch_{slug}",
            "label": lbl,
            "group": "architecture",
            "layer": "階段二：核心架構",
            "level": 2,
            "summary": f"負責專案 {d.name} 子系統功能實作與服務封裝。",
            "files": [d.name],
            "details": f"子模組目錄：{d.name}",
            "color": "#1f6feb"
        })

    if len(arch_nodes) < 3:
        baseline_arch = [
            ("arch_main", f"🏛️ {project_name} 核心應用層", "主要業務程式碼與應用邏輯入口。"),
            ("arch_logic", f"⚙️ {project_name} 領域邏輯模組", "負責核心計算流程與資料處理管線。"),
            ("arch_schemas", f"📐 資料模型與協議協議 (Schemas)", "定義前後端通信格式與資料約束。"),
        ]
        for aid, albl, asumm in baseline_arch:
            if not any(n["id"] == aid for n in arch_nodes) and len(arch_nodes) < 3:
                arch_nodes.append({
                    "id": aid,
                    "label": albl,
                    "group": "architecture",
                    "layer": "階段二：核心架構",
                    "level": 2,
                    "summary": asumm,
                    "files": ["."],
                    "details": "模組核心封裝。",
                    "color": "#1f6feb"
                })

    nodes.extend(arch_nodes)

    # 3. Level 3: 任務流與排程 (Tasks & Pipelines)
    task_nodes = []
    tasks_md = p / "TASKS.md"
    handoff_md = p / "HANDOFF.md"
    if tasks_md.exists() or handoff_md.exists():
        task_nodes.append({
            "id": "task_pipeline",
            "label": "📋 任務清單與移交進度 (TASKS.md)",
            "group": "logic",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "紀錄當前迭代待辦工單、已完成里程碑與未決問題。",
            "files": [f.name for f in (tasks_md, handoff_md) if f.exists()],
            "details": "敏捷任務看板正本。",
            "color": "#238636"
        })
    else:
        task_nodes.append({
            "id": "task_pipeline",
            "label": "📋 迭代任務看板與排程 (Tasks)",
            "group": "logic",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "追蹤當前階段目標、工作包指派與進度卡點。",
            "files": ["TASKS.md"],
            "details": "任務推進看板。",
            "color": "#238636"
        })

    branch_name = None
    if (p / ".git").exists():
        try:
            r = subprocess.run(["git", "-C", str(p), "branch", "--show-current"], capture_output=True, text=True, timeout=2)
            branch_name = r.stdout.strip()
        except Exception:
            pass
    if branch_name:
        task_nodes.append({
            "id": "task_branch",
            "label": f"🌿 當前工作分支: {branch_name}",
            "group": "path",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": f"隔離開發分支 {branch_name}，追蹤最近提交與變更範圍。",
            "files": [".git"],
            "details": f"Git 分支維度：{branch_name}",
            "color": "#3fb950"
        })
    else:
        task_nodes.append({
            "id": "task_branch",
            "label": "🌿 敏捷工作分支 (Git Workspace)",
            "group": "path",
            "layer": "階段三：任務流水線",
            "level": 3,
            "summary": "工作樹隔離環境，追蹤工單提交與變更範圍。",
            "files": [".git"],
            "details": "分支環境。",
            "color": "#3fb950"
        })

    task_nodes.append({
        "id": "task_active_station",
        "label": f"🔥 {project_name} 當前焦點工位 (Active)",
        "group": "focus",
        "layer": "階段三：任務流水線",
        "level": 3,
        "summary": "【當前工作台裝配中】：任務維度至原子工單維度對話與推進焦點。",
        "files": ["."],
        "details": "在此對話、執行測試或建立原子工單。",
        "color": "#f0883e"
    })
    nodes.extend(task_nodes)

    # 4. Level 4: 執行沙盒與檢驗門禁 (Sandbox & Verification)
    verif_nodes = []
    verif_nodes.append({
        "id": "sandbox_tests",
        "label": "🧪 自動化測試與覆蓋率驗證套件",
        "group": "workbench",
        "layer": "階段四：沙盒與驗證",
        "level": 4,
        "summary": "執行單元測試、整合測試與端對端回歸測試。",
        "files": ["tests/" if (p / "tests").exists() else "."],
        "details": "要求零迴歸 (Zero Regression) 才能提交驗收。",
        "color": "#3fb950"
    })
    verif_nodes.append({
        "id": "sandbox_docker",
        "label": "🐳 Docker 容器沙盒環境",
        "group": "workbench",
        "layer": "階段四：沙盒與驗證",
        "level": 4,
        "summary": "以容器與 Worktree 隔離運行，確保生產環境同構與依賴封裝。",
        "files": ["Dockerfile" if (p / "Dockerfile").exists() else "docker-compose.yml"],
        "details": "沙盒環境隔離試車。",
        "color": "#388bfd"
    })
    nodes.extend(verif_nodes)

    # 5. Level 5: 主幹交付 (Delivery)
    delivery_nodes = [
        {
            "id": "human_acceptance",
            "label": "🛡️ Josh 人工驗收專屬門禁",
            "group": "delivery",
            "layer": "階段五：主幹交付",
            "level": 5,
            "summary": "檢驗 SHA-256 憑證、測試報表與成果驗收，確認無公差後放行合入。",
            "files": ["AGENTS.md"],
            "details": "Fail-Closed 煞車機制，最終人工放行門禁。",
            "color": "#da3633"
        },
        {
            "id": "deliver_main",
            "label": "🚢 Deliver to Mainline (主分支安全交付)",
            "group": "delivery",
            "layer": "階段五：主幹交付",
            "level": 5,
            "summary": f"安全合入主分支並推送至遠端倉庫，完成 {project_name} 本次迭代發布。",
            "files": ["."],
            "details": "已驗收合格工單歸檔上線。",
            "color": "#238636"
        }
    ]
    nodes.extend(delivery_nodes)

    # 建立階層連線
    for m in mem_nodes:
        for a in arch_nodes[:2]:
            edges.append({"from": m["id"], "to": a["id"], "label": "架構約束"})

    for a in arch_nodes[:2]:
        for t in task_nodes:
            edges.append({"from": a["id"], "to": t["id"], "label": "派工執行"})

    for t in task_nodes:
        for v in verif_nodes:
            edges.append({"from": t["id"], "to": v["id"], "label": "進入沙盒驗證", "color": {"color": "#f0883e"}, "width": 2})

    for v in verif_nodes:
        edges.append({"from": v["id"], "to": "human_acceptance", "label": "驗證通過 (PASS)"})
    edges.append({"from": "human_acceptance", "to": "deliver_main", "label": "Josh 核准合入", "color": {"color": "#238636"}, "width": 3})

    return nodes, edges


def render_agentos_mindmap_html(project_id=None):
    nodes, edges = None, None
    prj_name = "AgentOS Lite"
    if project_id and project_id != "all":
        try:
            from .ui_server import get_engine
            eng = get_engine()
            prj = eng.get_project(project_id)
            if prj:
                prj_name = prj["name"]
            ws = eng.get_workspace(prj["workspace_id"]) if prj.get("workspace_id") else None
            root_p = ws.get("root_path") if ws else None
            nodes, edges = generate_project_graph_data(prj["name"], root_path=root_p)
        except Exception:
            pass
    if not nodes or not edges:
        nodes, edges = get_agentos_graph_data()
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)

    init_active_node = next(
        (n for n in nodes if "active_station" in n["id"] or "焦點工位" in n["label"] or "task_n4" in n["id"] or n.get("level") == 3),
        nodes[0] if nodes else {"id": "task_n4", "label": "N4 沙盒重構工位", "layer": "階段三：任務流水線", "summary": "", "details": ""}
    )
    init_node_id = init_active_node["id"]
    init_node_label = init_active_node["label"]
    init_node_layer = init_active_node.get("layer", "階段三：任務流水線")
    init_node_desc = (init_active_node.get("summary", "") + (" " + init_active_node.get("details", "") if init_active_node.get("details") else "")).strip()
    if not init_node_desc:
        init_node_desc = "覆蓋任務維度至原子工單維度，提供本工位沙盒試車、規格審計與修復推進。"
    init_node_short = init_node_label.split(" ")[1] if " " in init_node_label else init_node_label

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

    /* 專案下拉切換選單 (Project Dropdown Switcher) */
    .project-dropdown-wrapper {{
      position: relative;
      display: inline-block;
    }}
    .project-switcher-btn {{
      background: transparent;
      border: 1px dashed var(--border-bright);
      color: var(--text-bright);
      font-size: 11.5px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s;
    }}
    .project-switcher-btn:hover {{
      background: var(--hover-bg);
      border-color: var(--blue);
      color: #79c0ff;
    }}
    .project-dropdown-menu {{
      display: none;
      position: absolute;
      top: calc(100% + 6px);
      left: 0;
      min-width: 230px;
      background: var(--card-bg);
      border: 1px solid var(--border-bright);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.7);
      z-index: 1000;
      padding: 6px 0;
      text-align: left;
    }}
    .project-dropdown-menu.show {{
      display: block;
    }}
    .dropdown-header {{
      font-size: 10px;
      text-transform: uppercase;
      font-weight: 800;
      color: var(--text-muted);
      padding: 6px 12px;
      letter-spacing: 0.5px;
    }}
    .dropdown-item {{
      padding: 7px 12px;
      font-size: 12px;
      color: var(--text);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.15s;
    }}
    .dropdown-item:hover {{
      background: var(--hover-bg);
      color: var(--text-bright);
    }}
    .dropdown-item.active {{
      color: #388bfd;
      font-weight: 700;
      background: rgba(56, 139, 253, 0.12);
    }}
    .dropdown-divider {{
      height: 1px;
      background: var(--border);
      margin: 4px 0;
    }}
    .dropdown-action {{
      padding: 7px 12px;
      font-size: 11.5px;
      color: #7ee787;
      cursor: pointer;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }}
    .dropdown-action:hover {{
      background: rgba(63, 185, 80, 0.15);
      color: #fff;
    }}
    .btn-item-action {{
      opacity: 0.35;
      font-size: 11px;
      padding: 1px 4px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .dropdown-item:hover .btn-item-action {{
      opacity: 0.85;
    }}
    .btn-item-action:hover {{
      opacity: 1 !important;
      background: rgba(255, 255, 255, 0.15);
      transform: scale(1.15);
    }}

    /* 專案建立/導入彈窗 (New/Import Project Modal) */
    .modal-backdrop {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(4, 8, 16, 0.82);
      backdrop-filter: blur(6px);
      z-index: 10000;
      align-items: center;
      justify-content: center;
    }}
    .modal-backdrop.show {{
      display: flex;
    }}
    .modal-dialog {{
      background: #161b22;
      border: 1px solid var(--border-bright);
      border-radius: 12px;
      width: 640px;
      max-width: 94vw;
      max-height: 88vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.85);
      animation: modalFadeIn 0.18s ease-out;
      overflow: hidden;
    }}
    @keyframes modalFadeIn {{
      from {{ transform: scale(0.96); opacity: 0; }}
      to {{ transform: scale(1); opacity: 1; }}
    }}
    .modal-header {{
      padding: 14px 18px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(255, 255, 255, 0.02);
    }}
    .modal-header h3 {{
      margin: 0;
      font-size: 14.5px;
      font-weight: 700;
      color: var(--text-bright);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .modal-close-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 18px;
      cursor: pointer;
      line-height: 1;
      padding: 4px 8px;
      border-radius: 4px;
      transition: all 0.15s;
    }}
    .modal-close-btn:hover {{
      color: var(--text-bright);
      background: rgba(255, 255, 255, 0.1);
    }}
    .modal-tabs {{
      display: flex;
      border-bottom: 1px solid var(--border);
      background: #0d1117;
    }}
    .modal-tab-btn {{
      flex: 1;
      padding: 10px 14px;
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-muted);
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }}
    .modal-tab-btn:hover {{
      color: var(--text-bright);
      background: rgba(255, 255, 255, 0.02);
    }}
    .modal-tab-btn.active {{
      color: #58a6ff;
      border-bottom-color: #58a6ff;
      background: rgba(56, 139, 253, 0.06);
    }}
    .modal-body {{
      padding: 18px;
      overflow-y: auto;
      flex: 1;
    }}
    .modal-tab-content {{
      display: none;
    }}
    .modal-tab-content.active {{
      display: block;
    }}
    .form-group {{
      margin-bottom: 14px;
    }}
    .form-group label {{
      display: block;
      font-size: 11.5px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 6px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .form-input {{
      width: 100%;
      box-sizing: border-box;
      background: #0d1117;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 12.5px;
      color: var(--text-bright);
      outline: none;
      transition: all 0.15s;
    }}
    .form-input:focus {{
      border-color: #58a6ff;
      box-shadow: 0 0 0 3px rgba(56, 139, 253, 0.2);
    }}
    .candidate-scroll {{
      max-height: 180px;
      overflow-y: auto;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: #0d1117;
      margin-bottom: 12px;
    }}
    .candidate-card {{
      padding: 8px 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.12s;
    }}
    .candidate-card:hover {{
      background: rgba(56, 139, 253, 0.08);
    }}
    .candidate-card.selected {{
      background: rgba(56, 139, 253, 0.18);
      border-left: 3px solid #58a6ff;
    }}
    .candidate-card.imported {{
      opacity: 0.55;
    }}
    .modal-footer {{
      padding: 12px 18px;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      background: rgba(255, 255, 255, 0.02);
    }}
    .btn-secondary {{
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }}
    .btn-secondary:hover {{
      background: var(--hover-bg);
      color: var(--text-bright);
    }}
    .btn-primary {{
      background: #238636;
      border: 1px solid rgba(255,255,255,0.1);
      color: #fff;
      padding: 6px 16px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .btn-primary:hover {{
      background: #2ea043;
    }}
    .btn-primary:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}

    .account-badge-group {{
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }}
    .account-badge-card {{
      flex: 1;
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: #0d1117;
      font-size: 11.5px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
      user-select: none;
    }}
    .account-badge-card:hover {{
      border-color: var(--border-bright);
      background: rgba(255, 255, 255, 0.04);
    }}
    .account-badge-card.active {{
      border-color: #388bfd;
      background: rgba(56, 139, 253, 0.15);
      color: var(--text-bright);
      font-weight: 700;
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

    /* ================================================================ */
    /* 模式 D: 後台錯誤收集與哨兵抽屜 (Error Telemetry Drawer) */
    /* ================================================================ */
    .error-drawer {{
      position: fixed;
      top: 0;
      right: -530px;
      width: 500px;
      height: 100vh;
      background: rgba(17, 22, 32, 0.96);
      backdrop-filter: blur(16px);
      border-left: 2px solid var(--border-bright);
      box-shadow: -10px 0 30px rgba(0, 0, 0, 0.7);
      z-index: 1000;
      transition: right 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
    }}
    .error-drawer.open {{
      right: 0;
    }}
    .err-drawer-header {{
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-bg);
    }}
    .err-drawer-header h3 {{
      margin: 0;
      font-size: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-bright);
    }}
    .err-drawer-stats {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      padding: 12px 20px;
      background: rgba(0,0,0,0.25);
      border-bottom: 1px solid var(--border);
    }}
    .err-stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      text-align: center;
    }}
    .err-stat-num {{
      font-size: 18px;
      font-weight: 800;
      color: #f85149;
    }}
    .err-stat-label {{
      font-size: 10.5px;
      color: var(--text-muted);
    }}
    .err-drawer-body {{
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .err-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-left: 4px solid #f85149;
      border-radius: 8px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      position: relative;
    }}
    .err-card.warning {{
      border-left-color: #f0883e;
    }}
    .err-card-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .err-badge-src {{
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      background: rgba(248, 81, 73, 0.2);
      color: #f85149;
      border: 1px solid rgba(248, 81, 73, 0.4);
    }}
    .err-badge-src.sentinel {{
      background: rgba(240, 136, 62, 0.2);
      color: #f0883e;
      border-color: rgba(240, 136, 62, 0.4);
    }}
    .err-badge-src.frontend {{
      background: rgba(56, 139, 253, 0.2);
      color: #388bfd;
      border-color: rgba(56, 139, 253, 0.4);
    }}
    .err-badge-src.backend {{
      background: rgba(163, 113, 247, 0.2);
      color: #a371f7;
      border-color: rgba(163, 113, 247, 0.4);
    }}
    .err-count-pill {{
      font-size: 11px;
      font-weight: 700;
      background: rgba(255,255,255,0.08);
      padding: 2px 8px;
      border-radius: 10px;
      color: var(--text-muted);
    }}
    .err-msg {{
      font-size: 12.5px;
      color: var(--text-bright);
      line-height: 1.4;
      font-weight: 500;
      word-break: break-word;
    }}
    .err-details-toggle {{
      font-size: 11px;
      color: var(--text-muted);
      cursor: pointer;
    }}
    .err-stack-box {{
      margin-top: 6px;
      font-family: monospace;
      font-size: 11px;
      background: #090d13;
      padding: 8px;
      border-radius: 4px;
      color: #8b99ab;
      max-height: 120px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }}
    .err-actions {{
      display: flex;
      gap: 8px;
      margin-top: 6px;
    }}
    .btn-err-action {{
      font-size: 11.5px;
      padding: 4px 10px;
      border-radius: 6px;
      border: 1px solid var(--border);
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s;
    }}
    .btn-err-ticket {{
      background: rgba(56, 139, 253, 0.15);
      border-color: var(--blue);
      color: #79c0ff;
    }}
    .btn-err-ticket:hover {{
      background: var(--blue);
      color: #fff;
    }}
    .btn-err-resolve {{
      background: rgba(63, 185, 80, 0.15);
      border-color: var(--green);
      color: #7ee787;
    }}
    .btn-err-resolve:hover {{
      background: var(--green);
      color: #fff;
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
      <div class="ladder-step" data-dim="project" title="專案結構維度 (點擊切換專案)">
        <span class="dim-icon">🏢</span>
        <span class="dim-name">專案</span>
        <div class="project-dropdown-wrapper">
          <button class="project-switcher-btn" id="project-switcher-btn" onclick="toggleProjectDropdown(event)">
            <span class="dim-val" id="ladder-project-title">載入中...</span>
            <span class="arrow-down" style="font-size:9px; opacity:0.8;">▾</span>
          </button>
          <div class="project-dropdown-menu" id="project-dropdown-menu">
            <div class="dropdown-header">切換所屬專案</div>
            <div class="dropdown-item" id="opt-prj-all" onclick="selectProject('all')">
              <span>🌐 全部專案 (跨專案總表)</span>
            </div>
            <div class="dropdown-divider"></div>
            <div id="project-list-items"></div>
            <div id="archived-projects-wrapper" style="display:none; border-top:1px dashed var(--border); margin-top:4px; padding-top:4px;">
              <div class="dropdown-header" style="cursor:pointer; display:flex; justify-content:space-between; align-items:center; user-select:none;" onclick="toggleArchivedSection(event)">
                <span>📦 已歸檔專案 (<span id="archived-count-badge">0</span>)</span>
                <span id="archived-toggle-icon" style="font-size:9px;">▾</span>
              </div>
              <div id="archived-project-list" style="display:none; max-height:160px; overflow-y:auto; padding:2px 0;"></div>
            </div>
            <div class="dropdown-divider"></div>
            <div class="dropdown-action" onclick="openNewProjectModal()">
              <span>➕ 建立 / 導入新專案...</span>
            </div>
          </div>
        </div>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step" data-dim="goal" title="長期目標維度">
        <span class="dim-icon">🎯</span>
        <span class="dim-name">目標</span>
        <span class="dim-val" id="ladder-goal-title">{html.escape(prj_name)} 核心架構演進</span>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step" data-dim="task" title="中小型任務維度">
        <span class="dim-icon">📦</span>
        <span class="dim-name">任務</span>
        <span class="dim-val" id="ladder-task-title">{html.escape(init_node_label)}</span>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step active" data-dim="node" title="工位節點維度">
        <span class="dim-icon">📍</span>
        <span class="dim-name">節點</span>
        <span class="dim-val" id="ladder-node-title">{html.escape(init_node_short)}</span>
      </div>
      <span class="ladder-sep">›</span>
      <div class="ladder-step" data-dim="ticket" title="原子工單維度">
        <span class="dim-icon">⚛️</span>
        <span class="dim-name">原子</span>
        <span class="dim-val" id="ladder-ticket-title">(待開立工單)</span>
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
      <button class="mode-tab" id="tab-errors" onclick="toggleErrorDrawer()" style="background: rgba(248, 81, 73, 0.12); border-color: rgba(248, 81, 73, 0.4); color: #f85149;">
        🛡️ 後台錯誤 (<span id="unresolved-err-badge">0</span>)
      </button>
    </div>
  </header>

  <!-- 模式 D: 後台錯誤收集與哨兵抽屜 (Error Telemetry Drawer) -->
  <div class="error-drawer" id="error-drawer">
    <div class="err-drawer-header">
      <h3>🛡️ 後台錯誤收集與哨兵中心</h3>
      <div style="display:flex; gap:8px; align-items:center;">
        <button class="btn-err-action" onclick="triggerSentinelScan()" style="background:rgba(240,136,62,0.2); border-color:#f0883e; color:#f0883e;">🔍 立即執行哨兵巡檢</button>
        <button class="close-btn" onclick="toggleErrorDrawer()">✕</button>
      </div>
    </div>
    <div class="err-drawer-stats">
      <div class="err-stat-card">
        <div class="err-stat-num" id="stat-unresolved-count">0</div>
        <div class="err-stat-label">待處理異常</div>
      </div>
      <div class="err-stat-card">
        <div class="err-stat-num" id="stat-total-count" style="color:var(--text-bright);">0</div>
        <div class="err-stat-label">歷史累積錯誤</div>
      </div>
      <div class="err-stat-card">
        <div class="err-stat-num" id="stat-sentinel-status" style="color:#3fb950; font-size:14px; margin-top:2px;">PASS</div>
        <div class="err-stat-label">背景哨兵防護</div>
      </div>
    </div>
    <div class="err-drawer-list" id="error-list-container">
      <div style="text-align:center; padding:32px 16px; color:var(--text-muted); font-size:12px;">
        正在取得系統哨兵異常記錄...
      </div>
    </div>
  </div>

  <!-- 主容器 (支援 Flex 水平並排 雙座分屏) -->
  <main class="main-container" id="main-container">
    
    <!-- === 模式 A: ORCA 精工工作台 (Orca Workbench) === -->
    <div class="workbench-view" id="workbench-view">
      
      <!-- 左側：可對話視窗 (Conversational AI Station) -->
      <section class="chat-console">
        <div class="console-header">
          <div class="station-badge">
            <span class="pulse-dot"></span>
            <span id="active-station-label">🎯 當前工位：{html.escape(init_node_label)} [{html.escape(init_node_layer)}]</span>
          </div>
          <div class="console-meta">
            <span class="tag tag-runner">⚡ Codex Runner</span>
            <span class="tag tag-gov">Tier 0 憲章</span>
          </div>
        </div>

        <!-- 對話訊息串 (Dialogue Stream) -->
        <div class="chat-stream" id="chat-stream">
          <!-- 系統歡迎與當前工位卡片 -->
          <div class="chat-card chat-assistant" id="assistant-welcome-card">
            <div class="card-avatar">🐋</div>
            <div class="card-body">
              <div class="card-header">
                <strong>Orca 工作台助理</strong>
                <span class="card-time">10:00:00</span>
              </div>
              <div class="card-text" id="chat-welcome-text">
                已鎖定工位 <code>{html.escape(init_node_label)}</code> [{html.escape(init_node_layer)}]。<br>
                已加載 <strong>{html.escape(prj_name)}</strong> 專案架構（共 {len(nodes)} 個架構節點與門禁基線）。<br>
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
              <span class="badge-phase" id="task-phase-badge">{html.escape(init_node_layer)}</span>
              <h2 id="task-title-heading">{html.escape(init_node_label)}</h2>
            </div>
            <div class="task-card-status">
              <span class="status-pill status-ready" id="task-status-pill">● 待裝配 (READY)</span>
            </div>
          </div>
          <p class="task-desc" id="task-desc-text">
            {html.escape(init_node_desc)}
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
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; background:rgba(0,0,0,0.28); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                <div style="font-size:12px; font-weight:700; color:var(--text-bright);">
                  <span id="tickets-view-title">當前專案工單</span> (<span id="tickets-count-badge">0</span>)
                </div>
                <div style="display:flex; gap:6px;">
                  <button class="f-btn active" id="btn-scope-current" onclick="switchTicketsScope('current')">📍 當前專案</button>
                  <button class="f-btn" id="btn-scope-all" onclick="switchTicketsScope('all')">🌐 跨專案全視角</button>
                </div>
              </div>
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
          <button class="f-btn" id="btn-resync-mindmap" onclick="resyncCurrentMindmap()" title="從本機工作區即時重新掃描專案架構並刷新心智圖">🔄 重新掃描架構</button>
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

  <!-- 專案建立 / 導入彈窗 Modal (New & Import Project Modal) -->
  <div class="modal-backdrop" id="modal-new-project">
    <div class="modal-dialog">
      <div class="modal-header">
        <h3><span>➕</span> 建立 / 導入專案 (New &amp; Import Project)</h3>
        <button class="modal-close-btn" onclick="closeNewProjectModal()">✕</button>
      </div>
      <div class="modal-tabs">
        <button class="modal-tab-btn active" id="tab-btn-local" onclick="switchNewProjectTab('local')">
          <span>📁</span> 本機專案資料夾
        </button>
        <button class="modal-tab-btn" id="tab-btn-github" onclick="switchNewProjectTab('github')">
          <span>🌐</span> GitHub Pull / Fork
        </button>
        <button class="modal-tab-btn" id="tab-btn-blank" onclick="switchNewProjectTab('blank')">
          <span>⚡</span> 空白專案
        </button>
      </div>
      <div class="modal-body">
        <!-- Tab 1: 本機專案資料夾 -->
        <div class="modal-tab-content active" id="tab-content-local">
          <div style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
            直接抓取本機現有專案目錄導入裝配台，自動解析 Git 分支並掛載日產精工心智工位：
          </div>
          <div class="form-group">
            <label>快速選取本機目錄 (Discovered Local Folders):</label>
            <div class="candidate-scroll" id="local-candidate-list">
              <div style="padding:16px; text-align:center; color:var(--text-muted); font-size:12px;">正在掃描工作區目錄...</div>
            </div>
          </div>
          <div class="form-group">
            <label>資料夾絕對路徑 (Folder Path):</label>
            <input type="text" class="form-input" id="input-local-path" placeholder="/workspace/scc-system-control 或 E:\Workspace\..." />
          </div>
          <div class="form-group">
            <label>自訂專案名稱 (Project Name):</label>
            <input type="text" class="form-input" id="input-local-name" placeholder="例如：scc-system-control" />
          </div>
          <div style="margin-top:10px;">
            <label style="font-size:12px; color:var(--text); cursor:pointer; display:flex; align-items:center; gap:6px;">
              <input type="checkbox" id="check-local-sync-nodes" checked />
              自動導入 Tier 0~4 五階精工架構節點 (Architecture / Logic / Task)
            </label>
          </div>
        </div>

        <!-- Tab 2: GitHub Pull / Fork -->
        <div class="modal-tab-content" id="tab-content-github">
          <div style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
            從 GitHub 遠端拉取或 Fork 倉庫至本機工作區，並即刻初始化專案裝配節點：
          </div>
          <div class="form-group">
            <label>GitHub 倉庫網址或 owner/repo (GitHub Repository):</label>
            <input type="text" class="form-input" id="input-gh-repo" placeholder="例如：https://github.com/sayaJosh/scc-sys 或 sayaJosh/scc-sys" oninput="autoFillGithubInputs()" />
          </div>
          <div class="form-group">
            <label>導入動作模式 (Action Mode):</label>
            <div style="display:flex; gap:16px; font-size:12px; margin-top:4px;">
              <label style="cursor:pointer; display:flex; align-items:center; gap:4px;">
                <input type="radio" name="gh-action" value="clone" checked />
                📥 直接 Clone / Pull 到本機
              </label>
              <label style="cursor:pointer; display:flex; align-items:center; gap:4px;">
                <input type="radio" name="gh-action" value="fork" />
                🍴 Fork 到我的帳號並 Clone
              </label>
            </div>
          </div>
          <div class="form-group">
            <label>GitHub 操作身份 (GitHub Account):</label>
            <div class="account-badge-group">
              <label class="account-badge-card active" id="badge-acc-josh404">
                <input type="radio" name="gh-account" value="Josh404DR" checked onchange="switchGhAccount('Josh404DR')" />
                <span>👤 Josh404DR (主帳號)</span>
              </label>
              <label class="account-badge-card" id="badge-acc-sayajosh">
                <input type="radio" name="gh-account" value="sayaJosh" onchange="switchGhAccount('sayaJosh')" />
                <span>👤 sayaJosh</span>
              </label>
              <label class="account-badge-card" id="badge-acc-custom">
                <input type="radio" name="gh-account" value="custom" onchange="switchGhAccount('custom')" />
                <span>➕ 自訂 Token</span>
              </label>
            </div>
          </div>
          <div class="form-group" id="group-gh-token" style="display:none;">
            <label>Personal Access Token (PAT):</label>
            <input type="password" class="form-input" id="input-gh-token" placeholder="ghp_... 或 github_pat_..." />
          </div>
          <div class="form-group">
            <label>本機存放目錄名稱 (Target Folder):</label>
            <input type="text" class="form-input" id="input-gh-folder" placeholder="例如：scc-sys" />
          </div>
          <div class="form-group">
            <label>專案名稱 (Project Name):</label>
            <input type="text" class="form-input" id="input-gh-name" placeholder="例如：scc-sys" />
          </div>
          <div class="form-group">
            <label>指定拉取分支 (Branch, 選填):</label>
            <input type="text" class="form-input" id="input-gh-branch" placeholder="留空預設主分支 (master / main)" />
          </div>
          <div style="margin-top:10px;">
            <label style="font-size:12px; color:var(--text); cursor:pointer; display:flex; align-items:center; gap:6px;">
              <input type="checkbox" id="check-gh-sync-nodes" checked />
              自動導入 Tier 0~4 五階精工架構節點
            </label>
          </div>
        </div>

        <!-- Tab 3: 空白專案 -->
        <div class="modal-tab-content" id="tab-content-blank">
          <div style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
            在系統資料庫中直接建立一個全新獨立的空白專案：
          </div>
          <div class="form-group">
            <label>專案名稱 (Project Name):</label>
            <input type="text" class="form-input" id="input-blank-name" placeholder="例如：my-new-service" />
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" onclick="closeNewProjectModal()">取消</button>
        <button class="btn-primary" id="btn-submit-import" onclick="executeCurrentProjectImport()">🚀 立即導入本機專案目錄</button>
      </div>
    </div>
  </div>

  <!-- JavaScript 核心控制邏輯 -->
  <script>
    let RAW_NODES = {nodes_json};
    let RAW_EDGES = {edges_json};
    const DEFAULT_EDGES = {edges_json};

    let currentNodeId = "task_n4";
    let activeViewMode = "workbench";
    let network = null;
    let visNodes = null;
    let visEdges = null;

    function switchGhAccount(acc) {{
      ["josh404", "sayajosh", "custom"].forEach(k => {{
        const el = document.getElementById("badge-acc-" + k);
        if (el) el.classList.toggle("active", (k === "josh404" && acc === "Josh404DR") || (k === "sayajosh" && acc === "sayaJosh") || (k === "custom" && acc === "custom"));
      }});
      const tokenGroup = document.getElementById("group-gh-token");
      if (tokenGroup) tokenGroup.style.display = (acc === "custom") ? "block" : "none";
    }}

    function switchActiveStation(nodeObj) {{
      if (!nodeObj) return;
      currentNodeId = nodeObj.id;
      const lbl = nodeObj.label || nodeObj.title || "未知工位";
      const layer = nodeObj.layer || "任務維度";
      const summary = nodeObj.summary || "";
      const details = nodeObj.details || "";

      const activeSt = document.getElementById("active-station-label");
      if (activeSt) activeSt.textContent = `🎯 當前工位：${{lbl}} [${{layer}}]`;

      const ladderNode = document.getElementById("ladder-node-title");
      if (ladderNode) ladderNode.textContent = lbl.split(" ")[1] || lbl;

      const taskHeading = document.getElementById("task-title-heading");
      if (taskHeading) taskHeading.textContent = lbl;

      const phaseBadge = document.getElementById("task-phase-badge");
      if (phaseBadge) phaseBadge.textContent = layer;

      const taskDesc = document.getElementById("task-desc-text");
      if (taskDesc) taskDesc.textContent = summary + (details ? (" " + details) : "");

      // 動態更新助理歡迎卡片與工位鎖定說明
      const welcomeCard = document.getElementById("chat-welcome-text");
      if (welcomeCard) {{
        const prjName = (cachedAllProjects.find(p => p.id === currentProjectId) || {{}}).name || (document.getElementById("ladder-project-title") ? document.getElementById("ladder-project-title").textContent.trim() : "當前專案");
        const count = (RAW_NODES && RAW_NODES.length) || 16;
        welcomeCard.innerHTML = `已鎖定工位 <code>${{escapeHtml(lbl)}}</code> [${{escapeHtml(layer)}}]。<br>` +
          `已加載 <strong>${{escapeHtml(prjName)}}</strong> 專案架構（共 ${{count}} 個架構節點與門禁基線）。<br>` +
          `本工作台覆蓋<strong>任務維度到原子維度</strong>，你可以直接下達指令，或點擊下方一鍵裝配工令：`;
      }}

      // 天眼畫布自動定位 (Auto-Locate and Focus to Selected Station Node)
      if (network && visNodes && nodeObj && nodeObj.id) {{
        try {{
          network.selectNodes([nodeObj.id]);
          network.focus(nodeObj.id, {{
            scale: 1.15,
            animation: {{
              duration: 500,
              easingFunction: "easeInOutQuad"
            }}
          }});
        }} catch (err) {{}}
      }}
    }}

    function formatDbNodesToVis(dbNodes) {{
      if (!dbNodes || dbNodes.length === 0) return {{ nodes: [], edges: [] }};
      
      const layerLevelMap = {{
        "memory": 1,
        "architecture": 1,
        "logic": 2,
        "milestone": 3,
        "task": 4,
        "delivery": 5
      }};

      const formatted = dbNodes.map(n => {{
        const meta = n.metadata || {{}};
        const lvl = meta.level || layerLevelMap[n.layer] || 3;
        const clr = meta.color || (lvl === 1 ? '#8957e5' : (lvl === 2 ? '#1f6feb' : (lvl === 3 ? '#238636' : (lvl === 4 ? '#f0883e' : '#3fb950'))));
        return {{
          id: n.id,
          label: n.title,
          level: lvl,
          color: {{
            background: clr,
            border: n.id === currentNodeId ? "#f0883e" : "#30363d",
            highlight: {{ background: clr, border: "#f0883e" }}
          }},
          shape: "box",
          margin: 10,
          font: {{ color: "#ffffff", size: 12, face: "system-ui" }},
          borderWidth: n.id === currentNodeId ? 3 : 1,
          shadow: n.id === currentNodeId ? {{ enabled: true, color: "rgba(240, 136, 62, 0.4)", size: 10 }} : false,
          rawData: {{
            id: n.id,
            label: n.title,
            layer: n.layer,
            level: lvl,
            summary: n.summary || "",
            details: n.details || "",
            files: n.files || [],
            color: clr
          }}
        }};
      }});

      const idMap = {{}};
      dbNodes.forEach(n => {{
        idMap[n.id] = n.id;
        const parts = n.id.split("-");
        if (parts.length > 2) {{
          idMap[parts.slice(2).join("-")] = n.id;
        }}
      }});

      let edges = [];
      DEFAULT_EDGES.forEach(e => {{
        const fromId = idMap[e.from] || (dbNodes.find(n => n.id.endsWith(e.from)) || {{}}).id;
        const toId = idMap[e.to] || (dbNodes.find(n => n.id.endsWith(e.to)) || {{}}).id;
        if (fromId && toId && fromId !== toId) {{
          edges.push({{
            ...e,
            from: fromId,
            to: toId,
            arrows: "to",
            color: e.color || {{ color: "#30363d", highlight: "#f0883e" }},
            smooth: {{ type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 }}
          }});
        }}
      }});

      if (edges.length === 0 && formatted.length > 1) {{
        const lvlNodes = {{ 1: [], 2: [], 3: [], 4: [], 5: [] }};
        formatted.forEach(n => {{
          const l = n.level || 3;
          if (!lvlNodes[l]) lvlNodes[l] = [];
          lvlNodes[l].push(n);
        }});
        // Level 1 -> Level 2
        (lvlNodes[1] || []).forEach(n1 => {{
          (lvlNodes[2] || []).slice(0, 3).forEach(n2 => {{
            edges.push({{
              from: n1.id,
              to: n2.id,
              arrows: "to",
              color: {{ color: "#30363d", highlight: "#f0883e" }},
              smooth: {{ type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 }}
            }});
          }});
        }});
        // Level 2 -> Level 3
        (lvlNodes[2] || []).slice(0, 3).forEach(n2 => {{
          (lvlNodes[3] || []).forEach(n3 => {{
            edges.push({{
              from: n2.id,
              to: n3.id,
              arrows: "to",
              color: {{ color: "#30363d", highlight: "#f0883e" }},
              smooth: {{ type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 }}
            }});
          }});
        }});
        // Level 3 -> Level 4
        (lvlNodes[3] || []).forEach(n3 => {{
          (lvlNodes[4] || []).forEach(n4 => {{
            edges.push({{
              from: n3.id,
              to: n4.id,
              arrows: "to",
              color: {{ color: "#f0883e" }},
              width: 2,
              smooth: {{ type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 }}
            }});
          }});
        }});
        // Level 4 -> Level 5 (acceptance)
        (lvlNodes[4] || []).forEach(n4 => {{
          const acceptance = (lvlNodes[5] || []).find(n => n.id.includes("acceptance") || n.label.includes("驗收")) || (lvlNodes[5] || [])[0];
          if (acceptance) {{
            edges.push({{
              from: n4.id,
              to: acceptance.id,
              arrows: "to",
              color: {{ color: "#3fb950" }},
              smooth: {{ type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 }}
            }});
          }}
        }});
        // Within Level 5: acceptance -> deliver
        const acc = (lvlNodes[5] || []).find(n => n.id.includes("acceptance") || n.label.includes("驗收"));
        const del = (lvlNodes[5] || []).find(n => n.id.includes("deliver") || n.label.includes("交付") || n.label.includes("main"));
        if (acc && del && acc.id !== del.id) {{
          edges.push({{
            from: acc.id,
            to: del.id,
            arrows: "to",
            color: {{ color: "#238636" }},
            width: 3,
            smooth: {{ type: "cubicBezier", forceDirection: "horizontal", roundness: 0.4 }}
          }});
        }}
      }}

      return {{ nodes: formatted, edges: edges }};
    }}

    // 1. 初始化
    document.addEventListener("DOMContentLoaded", function() {{
      const urlParams = new URLSearchParams(window.location.search);
      const initialPrj = urlParams.get("project_id") || localStorage.getItem("workbench_active_project_id");
      initVisNetwork();
      loadDatabaseState(initialPrj);
      loadErrors();
      setInterval(loadErrors, 10000);
      
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
        switchActiveStation(nodeObj);
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

    let currentProjectId = null;
    let cachedAllProjects = [];
    let cachedTickets = [];
    let ticketsScope = "current";

    // 專案切換下拉選單 (Project Dropdown)
    function toggleProjectDropdown(e) {{
      if (e) e.stopPropagation();
      const menu = document.getElementById("project-dropdown-menu");
      if (menu) menu.classList.toggle("show");
    }}

    window.addEventListener("click", function(e) {{
      const menu = document.getElementById("project-dropdown-menu");
      if (menu && !e.target.closest(".project-dropdown-wrapper")) {{
        menu.classList.remove("show");
      }}
    }});

    function selectProject(prjId, autoSwitchView = true) {{
      currentProjectId = prjId;
      const menu = document.getElementById("project-dropdown-menu");
      if (menu) menu.classList.remove("show");

      if (prjId === "all") {{
        ticketsScope = "all";
        const btnCur = document.getElementById("btn-scope-current");
        const btnAll = document.getElementById("btn-scope-all");
        if (btnCur && btnAll) {{
          btnAll.classList.add("active");
          btnCur.classList.remove("active");
        }}
      }}

      appendTerminalLine(`[PROJECT-SWITCH] Switched active project context to: ${{prjId}}`, "term-warn");
      loadDatabaseState(prjId);
      if (autoSwitchView && activeViewMode === "workbench") {{
        switchViewMode("split");
      }}
    }}

    async function resyncCurrentMindmap() {{
      if (!currentProjectId || currentProjectId === "all") {{
        alert("請先選取具體專案以執行架構掃描");
        return;
      }}
      appendTerminalLine(`[MINDMAP-SYNC] 正在即時重新掃描專案 ${{currentProjectId}} 之實體目錄與架構...`, "term-warn");
      try {{
        const resp = await fetch("/api/project/resync-mindmap", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ project_id: currentProjectId }})
        }});
        const data = await resp.json();
        if (data.status === "ok") {{
          appendTerminalLine(`[MINDMAP-SYNC] ${{data.message}}`, "term-success");
          loadDatabaseState(currentProjectId);
        }} else {{
          appendTerminalLine(`[MINDMAP-SYNC-ERROR] ${{data.message}}`, "term-warn");
        }}
      }} catch (err) {{
        appendTerminalLine(`[MINDMAP-SYNC-ERROR] 通訊失敗: ${{err.message}}`, "term-dim");
      }}
    }}

    let currentNewProjectTab = "local";
    let cachedCandidates = [];

    function openNewProjectModal() {{
      const menu = document.getElementById("project-dropdown-menu");
      if (menu) menu.classList.remove("show");

      const modal = document.getElementById("modal-new-project");
      if (modal) modal.classList.add("show");

      switchNewProjectTab("local");
      loadLocalCandidates();
    }}

    function closeNewProjectModal() {{
      const modal = document.getElementById("modal-new-project");
      if (modal) modal.classList.remove("show");
    }}

    function switchNewProjectTab(tab) {{
      currentNewProjectTab = tab;
      ["local", "github", "blank"].forEach(t => {{
        const btn = document.getElementById(`tab-btn-${{t}}`);
        const content = document.getElementById(`tab-content-${{t}}`);
        if (btn) btn.classList.toggle("active", t === tab);
        if (content) content.classList.toggle("active", t === tab);
      }});
      const submitBtn = document.getElementById("btn-submit-import");
      if (submitBtn) {{
        if (tab === "local") submitBtn.textContent = "🚀 導入本機專案目錄";
        else if (tab === "github") submitBtn.textContent = "🌐 從 GitHub 拉取並建立專案";
        else submitBtn.textContent = "⚡ 建立空白專案";
      }}
    }}

    async function loadLocalCandidates() {{
      const container = document.getElementById("local-candidate-list");
      if (!container) return;
      try {{
        const resp = await fetch("/api/project/candidates");
        const data = await resp.json();
        cachedCandidates = data.candidates || [];
        if (cachedCandidates.length === 0) {{
          container.innerHTML = '<div style="padding:16px; text-align:center; color:var(--text-muted); font-size:12px;">未掃描到本機工作區目錄，可於下方手動填寫路徑。</div>';
          return;
        }}
        container.innerHTML = cachedCandidates.map(c => `
          <div class="candidate-card ${{c.imported ? 'imported' : ''}}" onclick="selectCandidate('${{escapeHtml(c.path)}}', '${{escapeHtml(c.name)}}')">
            <div style="flex:1; overflow:hidden;">
              <div style="font-weight:700; color:var(--text-bright); font-size:12px; display:flex; align-items:center; gap:6px;">
                <span>📁 ${{escapeHtml(c.name)}}</span>
                ${{c.is_git ? `<span class="badge" style="background:rgba(56,139,253,0.15); color:#79c0ff; font-size:10px; padding:1px 5px; border-radius:3px;">git: ${{escapeHtml(c.branch || 'HEAD')}}</span>` : ''}}
                ${{c.imported ? '<span class="badge" style="background:rgba(63,185,80,0.15); color:#3fb950; font-size:10px; padding:1px 5px; border-radius:3px;">已在裝配台</span>' : ''}}
              </div>
              <div style="font-size:10.5px; color:var(--text-muted); font-family:monospace; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                ${{escapeHtml(c.path)}} ${{c.remote ? `&middot; <span style="color:#8b949e;">${{escapeHtml(c.remote)}}</span>` : ''}}
              </div>
            </div>
            <button class="btn-secondary" style="font-size:11px; padding:2px 8px; margin-left:8px;" onclick="event.stopPropagation(); selectCandidate('${{escapeHtml(c.path)}}', '${{escapeHtml(c.name)}}')">選取</button>
          </div>
        `).join("");

        // 自動選取第一個尚未導入的候選目錄
        const firstAvail = cachedCandidates.find(c => !c.imported);
        if (firstAvail) {{
          selectCandidate(firstAvail.path, firstAvail.name);
        }}
      }} catch(err) {{
        container.innerHTML = `<div style="padding:16px; text-align:center; color:var(--text-muted); font-size:12px;">載入失敗: ${{err}}</div>`;
      }}
    }}

    function selectCandidate(path, name) {{
      const pathInput = document.getElementById("input-local-path");
      const nameInput = document.getElementById("input-local-name");
      if (pathInput) pathInput.value = path;
      if (nameInput) nameInput.value = name;

      document.querySelectorAll(".candidate-card").forEach(el => {{
        el.classList.remove("selected");
        if (el.textContent.includes(name)) el.classList.add("selected");
      }});
    }}

    function autoFillGithubInputs() {{
      const repoInput = document.getElementById("input-gh-repo");
      const folderInput = document.getElementById("input-gh-folder");
      const nameInput = document.getElementById("input-gh-name");
      if (!repoInput) return;
      const val = repoInput.value.trim();
      if (!val) return;
      let repoName = val.replace(/\/+$/, "").split("/").pop();
      if (repoName.endsWith(".git")) repoName = repoName.slice(0, -4);
      if (folderInput && !folderInput.value) folderInput.value = repoName;
      if (nameInput && !nameInput.value) nameInput.value = repoName;
    }}

    async function executeCurrentProjectImport() {{
      const submitBtn = document.getElementById("btn-submit-import");
      if (submitBtn) submitBtn.disabled = true;

      try {{
        if (currentNewProjectTab === "local") {{
          const path = document.getElementById("input-local-path").value.trim();
          const name = document.getElementById("input-local-name").value.trim();
          const syncNodes = document.getElementById("check-local-sync-nodes").checked;
          if (!path) {{
            alert("請輸入或選取本機目錄路徑");
            return;
          }}
          appendTerminalLine(`[IMPORT-LOCAL] Importing local directory: "${{path}}"...`, "term-info");
          const resp = await fetch("/api/project/import-local", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ path: path, name: name, sync_nodes: syncNodes }})
          }});
          const data = await resp.json();
          if (data.status === "ok") {{
            appendTerminalLine(`[IMPORT-SUCCESS] ${{data.message}}`, "term-success");
            closeNewProjectModal();
            selectProject(data.project.id);
          }} else {{
            alert(data.message || "導入失敗");
            appendTerminalLine(`[IMPORT-ERROR] ${{data.message}}`, "term-warn");
          }}

        }} else if (currentNewProjectTab === "github") {{
          const repo = document.getElementById("input-gh-repo").value.trim();
          const actionRadio = document.querySelector('input[name="gh-action"]:checked');
          const action = actionRadio ? actionRadio.value : "clone";
          const accRadio = document.querySelector('input[name="gh-account"]:checked');
          const account = accRadio ? accRadio.value : "Josh404DR";
          const token = document.getElementById("input-gh-token") ? document.getElementById("input-gh-token").value.trim() : "";
          const folder = document.getElementById("input-gh-folder").value.trim();
          const name = document.getElementById("input-gh-name").value.trim();
          const branch = document.getElementById("input-gh-branch").value.trim();
          const syncNodes = document.getElementById("check-gh-sync-nodes").checked;
          if (!repo) {{
            alert("請輸入 GitHub 倉庫網址或 owner/repo");
            return;
          }}
          appendTerminalLine(`[IMPORT-GITHUB] Pulling from GitHub: "${{repo}}" (${{action}}, 帳號: ${{account}})...`, "term-info");
          const resp = await fetch("/api/project/import-github", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              repo: repo,
              action: action,
              account: account,
              token: token,
              target_folder: folder,
              project_name: name,
              branch: branch,
              sync_nodes: syncNodes
            }})
          }});
          const data = await resp.json();
          if (data.status === "ok") {{
            appendTerminalLine(`[IMPORT-SUCCESS] ${{data.message}}`, "term-success");
            closeNewProjectModal();
            selectProject(data.project.id);
          }} else {{
            alert(data.message || "GitHub 導入失敗");
            appendTerminalLine(`[IMPORT-ERROR] ${{data.message}}`, "term-warn");
          }}

        }} else if (currentNewProjectTab === "blank") {{
          const name = document.getElementById("input-blank-name").value.trim();
          if (!name) {{
            alert("請輸入專案名稱");
            return;
          }}
          appendTerminalLine(`[PROJECT-CREATE] Creating blank project: "${{name}}"...`, "term-info");
          const resp = await fetch("/api/project/create", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ name: name }})
          }});
          const data = await resp.json();
          if (data.status === "ok") {{
            appendTerminalLine(`[PROJECT-CREATE] Blank project created: ${{data.project.name}} (${{data.project.id}})`, "term-success");
            closeNewProjectModal();
            selectProject(data.project.id);
          }} else {{
            alert(data.message || "建立失敗");
            appendTerminalLine(`[PROJECT-CREATE-ERROR] ${{data.message}}`, "term-warn");
          }}
        }}
      }} catch(err) {{
        appendTerminalLine(`[IMPORT-ERROR] ${{err}}`, "term-dim");
      }} finally {{
        if (submitBtn) submitBtn.disabled = false;
      }}
    }}

    async function archiveProject(prjId, prjName) {{
      if (!confirm(`確定要歸檔專案「${{prjName}}」嗎？\n歸檔後會移至「已歸檔專案」清單，隨時可一鍵還原。`)) return;
      appendTerminalLine(`[PROJECT-ARCHIVE] Archiving project: "${{prjName}}"...`, "term-info");
      try {{
        const resp = await fetch("/api/project/archive", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ project_id: prjId }})
        }});
        const data = await resp.json();
        if (data.status === "ok") {{
          appendTerminalLine(`[PROJECT-ARCHIVED] Project "${{prjName}}" archived.`, "term-success");
          if (currentProjectId === prjId) {{
            currentProjectId = "all";
          }}
          loadDatabaseState(currentProjectId);
        }} else {{
          appendTerminalLine(`[PROJECT-ARCHIVE-ERROR] ${{data.message}}`, "term-warn");
        }}
      }} catch(err) {{
        appendTerminalLine(`[PROJECT-ARCHIVE-ERROR] ${{err}}`, "term-dim");
      }}
    }}

    async function unarchiveProject(prjId, prjName) {{
      appendTerminalLine(`[PROJECT-UNARCHIVE] Restoring project: "${{prjName}}"...`, "term-info");
      try {{
        const resp = await fetch("/api/project/unarchive", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ project_id: prjId }})
        }});
        const data = await resp.json();
        if (data.status === "ok") {{
          appendTerminalLine(`[PROJECT-RESTORED] Project "${{prjName}}" restored to active.`, "term-success");
          loadDatabaseState(prjId);
        }} else {{
          appendTerminalLine(`[PROJECT-UNARCHIVE-ERROR] ${{data.message}}`, "term-warn");
        }}
      }} catch(err) {{
        appendTerminalLine(`[PROJECT-UNARCHIVE-ERROR] ${{err}}`, "term-dim");
      }}
    }}

    function toggleArchivedSection(e) {{
      if (e) e.stopPropagation();
      const list = document.getElementById("archived-project-list");
      const icon = document.getElementById("archived-toggle-icon");
      if (list) {{
        const isHidden = (list.style.display === "none" || !list.style.display);
        list.style.display = isHidden ? "block" : "none";
        if (icon) icon.textContent = isHidden ? "▴" : "▾";
      }}
    }}

    function switchTicketsScope(scope) {{
      ticketsScope = scope;
      const btnCur = document.getElementById("btn-scope-current");
      const btnAll = document.getElementById("btn-scope-all");
      if (btnCur && btnAll) {{
        if (scope === "all") {{
          btnAll.classList.add("active");
          btnCur.classList.remove("active");
        }} else {{
          btnCur.classList.add("active");
          btnAll.classList.remove("active");
        }}
      }}
      renderTicketsTable();
    }}

    function renderTicketsTable() {{
      const container = document.getElementById("tickets-table-container");
      if (!container) return;

      const titleEl = document.getElementById("tickets-view-title");
      const badgeEl = document.getElementById("tickets-count-badge");

      let filteredTickets = cachedTickets;
      if (ticketsScope === "current" && currentProjectId && currentProjectId !== "all") {{
        filteredTickets = cachedTickets.filter(t => t.project_id === currentProjectId);
      }}

      const isAllScope = (ticketsScope === "all" || currentProjectId === "all");
      if (titleEl) titleEl.textContent = isAllScope ? "跨專案全部工單 (全視角)" : "當前專案工單";
      if (badgeEl) badgeEl.textContent = filteredTickets.length;

      if (!filteredTickets || filteredTickets.length === 0) {{
        container.innerHTML = `<div style="color:var(--text-muted); padding:16px; text-align:center;">
          ${{isAllScope ? "所有專案中目前無工單記錄。" : "此專案目前無工單記錄。可在左側對話框下達「在此開立工單」立案。"}}
        </div>`;
        return;
      }}

      let tableHtml = `
        <table style="width:100%; border-collapse:collapse; font-size:11.5px;">
          <thead>
            <tr style="border-bottom:1px solid var(--border); color:var(--text-muted); text-align:left;">
              <th style="padding:6px;">標號</th>
              ${{isAllScope ? '<th style="padding:6px;">所屬專案</th>' : ''}}
              <th style="padding:6px;">標題</th>
              <th style="padding:6px;">風險</th>
              <th style="padding:6px;">狀態</th>
              <th style="padding:6px;">工位</th>
            </tr>
          </thead>
          <tbody>
      `;

      filteredTickets.forEach(t => {{
        const statusColor = t.status === "accepted" ? "#3fb950" : (t.status === "verification" ? "#a371f7" : (t.status === "active" ? "#f0883e" : "#8b99ab"));
        const prjCol = isAllScope ? `<td style="padding:6px;"><span class="badge" style="background:rgba(56,139,253,0.15); color:#79c0ff; border:1px solid rgba(56,139,253,0.3); font-size:10.5px; padding:2px 6px; border-radius:4px;">🏢 ${{escapeHtml(t.project_name || t.project_id)}}</span></td>` : '';
        tableHtml += `
          <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:6px; font-weight:700;">#${{t.id}}</td>
            ${{prjCol}}
            <td style="padding:6px; color:var(--text-bright); font-weight:500;">${{escapeHtml(t.title)}}</td>
            <td style="padding:6px; color:#f85149; font-weight:700;">${{t.risk_level.toUpperCase()}}</td>
            <td style="padding:6px;"><span style="color:${{statusColor}}; font-weight:700;">${{t.status.toUpperCase()}}</span></td>
            <td style="padding:6px; font-family:monospace; color:#79c0ff;">${{t.node_id || 'task_n4'}}</td>
          </tr>
        `;
      }});

      tableHtml += '</tbody></table>';
      container.innerHTML = tableHtml;
    }}

    // 6. 載入資料庫現況 (Load DB State)
    async function loadDatabaseState(targetProjectId) {{
      try {{
        const pId = targetProjectId || currentProjectId || "";
        const url = pId ? `/api/state?project_id=${{encodeURIComponent(pId)}}` : "/api/state";
        const resp = await fetch(url);
        const data = await resp.json();
        
        cachedAllProjects = data.all_projects || [];
        const cachedArchivedProjects = data.archived_projects || [];
        cachedTickets = data.tickets || [];
        
        const prevProjectId = currentProjectId;
        currentProjectId = (data.project && data.project.id) || targetProjectId || "all";

        // 本地儲存與網址同步 (Persistence & URL Query)
        if (currentProjectId && currentProjectId !== "all") {{
          localStorage.setItem("workbench_active_project_id", currentProjectId);
          const curUrl = new URL(window.location.href);
          if (curUrl.searchParams.get("project_id") !== currentProjectId) {{
            curUrl.searchParams.set("project_id", currentProjectId);
            window.history.replaceState({{ project_id: currentProjectId }}, "", curUrl.toString());
          }}
        }}

        // 渲染專案切換標題與階梯麵包屑
        const curPrjName = (data.project && data.project.name) || "專案";
        const prjTitle = document.getElementById("ladder-project-title");
        if (prjTitle) {{
          prjTitle.textContent = curPrjName;
        }}
        const goalTitle = document.getElementById("ladder-goal-title");
        if (goalTitle) {{
          goalTitle.textContent = (data.goals && data.goals.length > 0) ? data.goals[0].title : `${{curPrjName}} 核心架構演進`;
        }}
        const tktTitle = document.getElementById("ladder-ticket-title");
        if (tktTitle) {{
          tktTitle.textContent = (data.tickets && data.tickets.length > 0) ? (`#TKT-${{data.tickets[0].id}} [${{data.tickets[0].title}}]`) : "(待開立工單)";
        }}
        const tktPill = document.getElementById("task-status-pill");
        if (tktPill) {{
          tktPill.textContent = (data.tickets && data.tickets.length > 0) ? (`● ${{data.tickets[0].status.toUpperCase()}}`) : "● 待裝配 (READY)";
        }}

        // 動態重組可視化圖譜節點 (Vis-Network) 與工位更新
        if (data.nodes && data.nodes.length > 0) {{
          const graph = formatDbNodesToVis(data.nodes);
          RAW_NODES = graph.nodes.map(fn => fn.rawData);
          RAW_EDGES = graph.edges;
          if (visNodes && visEdges && network) {{
            visNodes.clear();
            visNodes.add(graph.nodes);
            visEdges.clear();
            visEdges.add(graph.edges);
            network.fit();
          }}
          const activeNode = RAW_NODES.find(n => n.id.includes("active_station") || n.label.includes("焦點工位") || n.id.includes("task_n4") || n.label.includes("N4") || n.level === 3) || RAW_NODES[0];
          if (activeNode) {{
            switchActiveStation(activeNode);
            const taskTitle = document.getElementById("ladder-task-title");
            if (taskTitle) {{
              taskTitle.textContent = (data.tickets && data.tickets.length > 0) ? data.tickets[0].title : activeNode.label;
            }}
          }}
        }} else if (!data.nodes || data.nodes.length === 0) {{
          RAW_NODES = [];
          RAW_EDGES = [];
          if (visNodes && visEdges && network) {{
            visNodes.clear();
            visEdges.clear();
          }}
          switchActiveStation({{
            id: "empty",
            label: (data.project && data.project.name) ? `${{data.project.name}} (空白沙盒)` : "尚未初始化架構節點",
            layer: "空白專案",
            summary: "此專案目前無心智圖節點架構。",
            details: "您可在右上方點擊「➕ 建立 / 導入新專案」導入現有資料夾，或於左側對話框下達「在此開立工單」立案。"
          }});
        }}

        // 專案切換對話提示
        if (prevProjectId && prevProjectId !== currentProjectId && data.project) {{
          const stream = document.getElementById("chat-stream");
          if (stream) {{
            const switchHtml = `
              <div style="margin: 10px 0; padding: 10px 14px; background: rgba(56, 139, 253, 0.1); border: 1px solid rgba(56, 139, 253, 0.3); border-radius: 8px; font-size: 12px; color: var(--text-bright);">
                <div style="font-weight: 700; display: flex; align-items: center; gap: 6px;">
                  <span>🏢 工作台已切換至專案：${{escapeHtml(data.project.name)}}</span>
                  <span class="badge" style="background:#1f6feb; color:#fff; font-size:10px; padding:1px 5px; border-radius:3px;">${{escapeHtml(data.project.id)}}</span>
                </div>
                <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; font-family: monospace;">
                  工作區目錄：${{escapeHtml(data.workspace ? (data.workspace.root_path || '') : '沙盒隔離目錄')}} &middot; 節點數：${{data.nodes ? data.nodes.length : 0}} 個 &middot; 工單數：${{data.tickets ? data.tickets.length : 0}} 張
                </div>
              </div>
            `;
            stream.insertAdjacentHTML("beforeend", switchHtml);
            stream.scrollTop = stream.scrollHeight;
          }}
        }}

        // 渲染活躍專案下拉選單清單
        const pContainer = document.getElementById("project-list-items");
        if (pContainer) {{
          pContainer.innerHTML = cachedAllProjects.map(p => `
            <div class="dropdown-item ${{p.id === currentProjectId ? 'active' : ''}}" onclick="selectProject('${{p.id}}')">
              <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:180px;">🏢 ${{escapeHtml(p.name)}}</span>
              <div style="display:flex; align-items:center; gap:6px;">
                ${{p.id === currentProjectId ? '<span style="color:#388bfd; font-weight:800;">✓</span>' : ''}}
                <span class="btn-item-action" title="封存/歸檔此專案" onclick="event.stopPropagation(); archiveProject('${{p.id}}', '${{escapeHtml(p.name)}}')">📦</span>
              </div>
            </div>
          `).join("");
        }}

        // 渲染已歸檔專案清單
        const archWrapper = document.getElementById("archived-projects-wrapper");
        const archList = document.getElementById("archived-project-list");
        const archBadge = document.getElementById("archived-count-badge");
        if (archWrapper && archList) {{
          if (cachedArchivedProjects.length > 0) {{
            archWrapper.style.display = "block";
            if (archBadge) archBadge.textContent = cachedArchivedProjects.length;
            archList.innerHTML = cachedArchivedProjects.map(p => `
              <div class="dropdown-item ${{p.id === currentProjectId ? 'active' : ''}}" style="opacity:0.8; font-size:11px;" onclick="selectProject('${{p.id}}')">
                <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:170px; color:var(--text-muted);">📁 ${{escapeHtml(p.name)}}</span>
                <span class="btn-item-action" title="還原此專案至活躍狀態" onclick="event.stopPropagation(); unarchiveProject('${{p.id}}', '${{escapeHtml(p.name)}}')">↺</span>
              </div>
            `).join("");
          }} else {{
            archWrapper.style.display = "none";
          }}
        }}
        const optAll = document.getElementById("opt-prj-all");
        if (optAll) {{
          optAll.classList.toggle("active", currentProjectId === "all");
        }}

        // 渲染工單清單表格
        renderTicketsTable();

      }} catch (err) {{
        console.warn("無法取得 /api/state:", err);
      }}
    }}

    function escapeHtml(str) {{
      if (!str) return "";
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }}

    // 7. 全域錯誤遙測與哨兵中心 (Global Error Telemetry & Sentinel Center)
    function toggleErrorDrawer() {{
      const drawer = document.getElementById("error-drawer");
      if (drawer) {{
        drawer.classList.toggle("open");
        if (drawer.classList.contains("open")) {{
          loadErrors();
        }}
      }}
    }}

    function reportClientError(source, errorType, message, stack, context) {{
      try {{
        fetch("/api/telemetry/errors", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            source: source || "frontend",
            error_type: errorType || "ClientError",
            message: String(message || "Unknown error"),
            stack_trace: stack || "",
            context: Object.assign({{
              url: window.location.href,
              station: currentNodeId,
              user_agent: navigator.userAgent
            }}, context || {{}})
          }})
        }}).then(r => r.json()).then(data => {{
          loadErrors();
        }}).catch(e => {{}});
      }} catch(err) {{}}
    }}

    window.addEventListener("error", function(e) {{
      reportClientError("frontend", e.error ? e.error.name : "Error", e.message, e.error ? e.error.stack : (e.filename + ":" + e.lineno));
    }});

    window.addEventListener("unhandledrejection", function(e) {{
      const reason = e.reason;
      const msg = reason ? (reason.message || String(reason)) : "Unhandled Promise Rejection";
      const stack = reason ? reason.stack : "";
      reportClientError("frontend", "UnhandledRejection", msg, stack);
    }});

    async function loadErrors() {{
      try {{
        const resp = await fetch("/api/telemetry/errors");
        const data = await resp.json();
        
        const badge = document.getElementById("unresolved-err-badge");
        const statUnresolved = document.getElementById("stat-unresolved-count");
        const statTotal = document.getElementById("stat-total-occurrences");
        const statSentinel = document.getElementById("stat-sentinel-status");
        const listContainer = document.getElementById("err-drawer-list");

        const unresCount = data.unresolved_count || 0;
        if (badge) badge.textContent = unresCount;
        if (statUnresolved) statUnresolved.textContent = unresCount;

        const errBtn = document.getElementById("tab-errors");
        if (errBtn) {{
          if (unresCount > 0) {{
            errBtn.style.background = "rgba(248, 81, 73, 0.25)";
            errBtn.style.borderColor = "#f85149";
            errBtn.style.color = "#ff7b72";
            errBtn.style.animation = "pulse 2s infinite";
          }} else {{
            errBtn.style.background = "rgba(255, 255, 255, 0.05)";
            errBtn.style.borderColor = "var(--border)";
            errBtn.style.color = "var(--text-muted)";
            errBtn.style.animation = "none";
          }}
        }}

        let totalOccur = 0;
        let sentinelHasIssue = false;
        (data.errors || []).forEach(e => {{
          totalOccur += (e.occurrence_count || 1);
          if (e.source === "sentinel" && e.status === "unresolved") sentinelHasIssue = true;
        }});
        if (statTotal) statTotal.textContent = totalOccur;
        if (statSentinel) {{
          if (sentinelHasIssue) {{
            statSentinel.textContent = "WARN";
            statSentinel.style.color = "#f0883e";
          }} else {{
            statSentinel.textContent = "PASS";
            statSentinel.style.color = "#3fb950";
          }}
        }}

        if (!listContainer) return;
        if (!data.errors || data.errors.length === 0) {{
          listContainer.innerHTML = `
            <div style="text-align:center; padding:40px 20px; color:var(--text-muted);">
              <div style="font-size:36px; margin-bottom:12px;">🟢</div>
              <strong style="color:var(--text-bright);">後台無任何異常紀錄</strong>
              <p style="font-size:12px; margin-top:6px;">前端操作、API 呼叫與背景哨兵均處於最佳狀態。</p>
            </div>
          `;
          return;
        }}

        let cardsHtml = "";
        data.errors.forEach(e => {{
          const isResolved = e.status === "resolved";
          const srcClass = e.source || "backend";
          const sevClass = e.severity || "error";
          const cardOpacity = isResolved ? "opacity:0.55;" : "";
          
          let stackHtml = "";
          if (e.stack_trace) {{
            stackHtml = `
              <details style="margin-top:4px;">
                <summary class="err-details-toggle">檢視呼叫棧追蹤 (Stack Trace)</summary>
                <div class="err-stack-box">${{escapeHtml(e.stack_trace)}}</div>
              </details>
            `;
          }}

          let actionButtons = "";
          if (!isResolved) {{
            if (!e.ticket_id) {{
              actionButtons += `<button class="btn-err-action btn-err-ticket" onclick="convertErrorToTicket('${{e.id}}')">🛠️ 一鍵轉修復工單</button>`;
            }} else {{
              actionButtons += `<span style="font-size:11px; color:#79c0ff; font-weight:600; padding:4px 0;">⤷ 已轉工單 #${{e.ticket_id}}</span>`;
            }}
            actionButtons += `<button class="btn-err-action btn-err-resolve" onclick="resolveError('${{e.id}}')">✓ 標記已解決</button>`;
          }} else {{
            actionButtons = `<span style="font-size:11.5px; color:#3fb950; font-weight:700;">✓ 已解決 (Resolved)</span>`;
          }}

          cardsHtml += `
            <div class="err-card ${{sevClass}}" style="${{cardOpacity}}">
              <div class="err-card-top">
                <div style="display:flex; gap:6px; align-items:center;">
                  <span class="err-badge-src ${{srcClass}}">${{e.source.toUpperCase()}}</span>
                  <span style="font-weight:700; font-size:12px; color:var(--text-bright);">${{escapeHtml(e.error_type)}}</span>
                </div>
                <span class="err-count-pill" title="重複發生次數">×${{e.occurrence_count}}</span>
              </div>
              <div class="err-msg">${{escapeHtml(e.message)}}</div>
              <div style="font-size:10.5px; color:var(--text-muted); display:flex; justify-content:space-between;">
                <span>指紋: <code>${{e.fingerprint}}</code></span>
                <span>${{e.last_seen_at.substring(11, 19)}}</span>
              </div>
              ${{stackHtml}}
              <div class="err-actions">
                ${{actionButtons}}
              </div>
            </div>
          `;
        }});

        listContainer.innerHTML = cardsHtml;
      }} catch (err) {{
        console.warn("無法取得 /api/telemetry/errors:", err);
      }}
    }}

    async function triggerSentinelScan() {{
      appendTerminalLine("[SENTINEL] Triggering proactive background sentinel scan...", "term-warn");
      try {{
        const resp = await fetch("/api/sentinel/scan", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{}})
        }});
        const data = await resp.json();
        appendTerminalLine(`[SENTINEL] Scan complete. Found ${{data.findings_count}} findings.`, data.findings_count > 0 ? "term-warn" : "term-success");
        loadErrors();
      }} catch (err) {{
        appendTerminalLine(`[SENTINEL-ERROR] ${{err}}`, "term-dim");
      }}
    }}

    async function convertErrorToTicket(errId) {{
      appendTerminalLine(`[AUTO-TRIAGE] Converting error ${{errId}} to atomic ticket...`, "term-info");
      try {{
        const resp = await fetch("/api/telemetry/errors/convert-ticket", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ error_id: errId, node_id: currentNodeId }})
        }});
        const res = await resp.json();
        if (res.status === "ok") {{
          appendTerminalLine(`[AUTO-TRIAGE] Ticket #${{res.ticket.id}} created: "${{res.ticket.title}}"`, "term-success");
          loadErrors();
          loadDatabaseState();
          toggleErrorDrawer();
          switchInspTab("tickets");
        }} else {{
          appendTerminalLine(`[AUTO-TRIAGE-ERROR] ${{res.message}}`, "term-warn");
        }}
      }} catch(err) {{
        appendTerminalLine(`[AUTO-TRIAGE-ERROR] ${{err}}`, "term-dim");
      }}
    }}

    async function resolveError(errId) {{
      try {{
        await fetch("/api/telemetry/errors/resolve", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ error_id: errId, status: "resolved" }})
        }});
        loadErrors();
      }} catch(err) {{}}
    }}
  </script>
</body>
</html>"""
