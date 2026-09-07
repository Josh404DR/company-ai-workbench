from __future__ import annotations

import pytest
from pathlib import Path
from company_workbench.engine import WorkbenchEngine
from company_workbench.errors import NotFoundError


def test_schema_v7_applied(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = WorkbenchEngine(db_path)
    assert engine.store.schema_version() >= 7


def test_create_and_get_node(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = WorkbenchEngine(db_path)
    ws = engine.create_workspace("Test Workspace")
    prj = engine.create_project(ws["id"], "AgentOS-Lite")

    node = engine.create_node(
        prj["id"],
        title="Tier 0~4 分層治理憲法",
        summary="定義文件權威順序",
        layer="memory",
        details="解決 947 份文件搜尋混亂問題",
        files=["E:\\Workspace\\DOCUMENT_GOVERNANCE.md"],
        metadata={"level": 1, "color": "#8957e5"},
    )

    assert node["id"].startswith("NOD-")
    assert node["title"] == "Tier 0~4 分層治理憲法"
    assert node["layer"] == "memory"
    assert node["files"] == ["E:\\Workspace\\DOCUMENT_GOVERNANCE.md"]
    assert node["metadata"]["level"] == 1
    assert node["tickets"] == []
    assert node["child_nodes"] == []

    fetched = engine.get_node(node["id"])
    assert fetched["id"] == node["id"]
    assert fetched["title"] == node["title"]


def test_parent_child_nodes(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = WorkbenchEngine(db_path)
    ws = engine.create_workspace("Test Workspace")
    prj = engine.create_project(ws["id"], "AgentOS-Lite")

    parent = engine.create_node(
        prj["id"],
        title="Contract Linter 契約稽核器",
        summary="派工前強制檢查工具",
        layer="architecture",
    )

    child1 = engine.create_node(
        prj["id"],
        title="47 題規則庫 (LINT-001 ~ 007)",
        summary="核心語法與結構規則引擎",
        layer="logic",
        parent_node_id=parent["id"],
    )

    child2 = engine.create_node(
        prj["id"],
        title="禁止路徑攔截器",
        summary="攔截機密路徑越界",
        layer="logic",
        parent_node_id=parent["id"],
    )

    fetched_parent = engine.get_node(parent["id"])
    assert len(fetched_parent["child_nodes"]) == 2
    child_ids = [c["id"] for c in fetched_parent["child_nodes"]]
    assert child1["id"] in child_ids
    assert child2["id"] in child_ids


def test_ticket_linked_to_node(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = WorkbenchEngine(db_path)
    ws = engine.create_workspace("Test Workspace")
    prj = engine.create_project(ws["id"], "AgentOS-Lite")

    node = engine.create_node(
        prj["id"],
        title="N4 任務封包重構",
        summary="重構扁平 expected_outputs 為階層結構",
        layer="task",
    )

    t1 = engine.create_ticket(
        prj["id"],
        title="修正 LINT-007 階層式檢查",
        goal="解決 N4 漏檢問題",
        acceptance_criteria=["測試通過", "error_count 歸零"],
        node_id=node["id"],
    )
    assert t1["node_id"] == node["id"]

    updated_node = engine.get_node(node["id"])
    assert len(updated_node["tickets"]) == 1
    assert updated_node["tickets"][0]["id"] == t1["id"]

    t2 = engine.create_ticket(
        prj["id"],
        title="補充 Verifier 授權宣告",
        goal="符合 Invariant 11 門禁",
        acceptance_criteria=["宣告獨立驗證者"],
    )
    assert t2["node_id"] is None

    linked_t2 = engine.link_ticket_to_node(t2["id"], node["id"])
    assert linked_t2["node_id"] == node["id"]

    updated_node = engine.get_node(node["id"])
    assert len(updated_node["tickets"]) == 2


def test_node_validation_fails_closed(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = WorkbenchEngine(db_path)
    ws = engine.create_workspace("WS1")
    prj1 = engine.create_project(ws["id"], "Prj1")
    prj2 = engine.create_project(ws["id"], "Prj2")

    node1 = engine.create_node(prj1["id"], "Node 1", "Summary 1", layer="architecture")

    with pytest.raises(ValueError, match="same Project"):
        engine.create_ticket(
            prj2["id"],
            title="Cross Project Ticket",
            goal="Test",
            acceptance_criteria=["Criteria"],
            node_id=node1["id"],
        )

    with pytest.raises(NotFoundError):
        engine.create_ticket(
            prj1["id"],
            title="Ghost Node Ticket",
            goal="Test",
            acceptance_criteria=["Criteria"],
            node_id="NOD-nonexistent",
        )

    with pytest.raises(ValueError, match="Node layer must be one of"):
        engine.create_node(prj1["id"], "Invalid Layer", "Summary", layer="spaceship")


def test_5_layer_project_hierarchy(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = WorkbenchEngine(db_path)
    ws = engine.create_workspace("Company Workspace")
    prj = engine.create_project(ws["id"], "AgentOS-Lite V2")

    goal = engine.create_goal(prj["id"], "完成 N1~N4 契約沙盒遷移", "目標全綠")

    milestone = engine.create_node(
        prj["id"],
        title="M1: 靜態門禁全數接管",
        summary="Contract Linter 與 47 題規則",
        layer="milestone",
        goal_id=goal["id"],
    )

    n_arch = engine.create_node(prj["id"], "架構層", "契約核心", layer="architecture")
    n_logic = engine.create_node(prj["id"], "邏輯層", "47 條規則", layer="logic")
    n_mem = engine.create_node(prj["id"], "記憶層", "決策紀錄", layer="memory")

    engine.create_ticket(
        prj["id"],
        title="工單 1: 驗證 LINT-001",
        goal="無語法錯誤",
        acceptance_criteria=["pass"],
        goal_id=goal["id"],
        node_id=n_logic["id"],
    )

    hierarchy = engine.get_project_hierarchy(prj["id"])

    assert hierarchy["project"]["name"] == "AgentOS-Lite V2"
    assert len(hierarchy["goals"]) == 1
    assert len(hierarchy["milestones"]) == 1
    assert len(hierarchy["nodes"]) == 3
    assert len(hierarchy["tickets"]) == 1
    assert hierarchy["stats"]["total_goals"] == 1
    assert hierarchy["stats"]["total_milestones"] == 1
    assert hierarchy["stats"]["total_nodes"] == 3
    assert hierarchy["stats"]["total_tickets"] == 1


def test_sync_agentos_mindmap_nodes(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = WorkbenchEngine(db_path)
    ws = engine.create_workspace("AgentOS WS")
    prj = engine.create_project(ws["id"], "AgentOS Project")

    nodes = engine.sync_agentos_mindmap_nodes(prj["id"])
    assert len(nodes) >= 10

    titles = [n["title"] for n in nodes]
    assert any("Tier 0~4 分層治理憲法" in t for t in titles)
    assert any("Contract Linter" in t for t in titles)
    assert any("47 題規則庫" in t for t in titles)
    assert any("N4" in t for t in titles)
    assert any("Josh 人工最終驗收" in t for t in titles)