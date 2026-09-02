from __future__ import annotations

from pathlib import Path

from .engine import WorkbenchEngine


def run_demo(database_path: str | Path) -> dict:
    engine = WorkbenchEngine(database_path)
    workspace = engine.create_workspace("Company AI Workbench", str(Path.cwd()))
    project = engine.create_project(workspace["id"], "Reliable Engine Demo")
    ticket = engine.create_ticket(
        project["id"],
        "修正設定檔解析錯誤",
        "保存完整 Debug 脈絡並以證據驗證修正",
        ["回歸測試通過", "保留根因與修法"],
    )
    run = engine.start_run(ticket["id"], runner="fake")
    engine.append_event(run["id"], "agent_activity", {"activity": "reproduce_failure"})
    debug = engine.record_debug_episode(
        run["id"],
        symptom="找不到設定欄位",
        reproduction="載入舊版設定檔",
        environment="fake-agent / local",
        error_fingerprint="CONFIG-MISSING-FIELD",
        hypotheses=["預設值缺失", "schema rename 未 migration"],
        attempted_fixes=["加入預設值", "加入欄位 migration"],
        failed_attempts=["加入預設值後回歸測試仍失敗"],
        root_cause="舊版欄位名稱未 migration",
        accepted_fix="加入相容 migration",
        regression_test="tests:test_schema_rename_migration",
    )
    engine.complete_run(run["id"])
    before_acceptance = engine.get_ticket(ticket["id"])["status"]
    verification = engine.verify_run(
        run["id"], status="passed", evidence_ref="test://tests:test_schema_rename_migration",
        summary="回歸測試通過", verifier="demo-verifier",
    )
    accepted = engine.accept_ticket(ticket["id"], accepted_by="Josh", note="Demo acceptance")
    memory = engine.propose_memory(
        project["id"], run["id"], kind="semantic",
        statement="遇到 schema rename 時先檢查 migration",
        scope=f"project:{project['id']}", evidence_ref=f"debug:{debug['id']}",
    )
    return {
        "workspace": workspace["id"], "project": project["id"], "ticket": ticket["id"], "run": run["id"],
        "ticket_status_after_run": before_acceptance, "verification": verification["status"],
        "ticket_status_after_acceptance": accepted["status"], "memory_candidate": memory["status"],
        "event_count": len(engine.list_events(run["id"])),
    }

