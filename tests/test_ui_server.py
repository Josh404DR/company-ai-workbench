import http.client
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import HTTPServer
from pathlib import Path
from urllib.parse import urlencode

# Ensure prototype and src are in path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "prototype"))

import ui_server
from company_workbench.engine import WorkbenchEngine


class UiServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "workbench.db"
        # Monkeypatch DB_PATH in ui_server
        ui_server.DB_PATH = cls.db_path
        cls.engine = WorkbenchEngine(cls.db_path)
        cls.ws = cls.engine.create_workspace("UI Test WS")
        cls.prj = cls.engine.create_project(cls.ws["id"], "UI Test PRJ")

        # Start HTTPServer on ephemeral port
        cls.server = HTTPServer(("127.0.0.1", 0), ui_server.PrototypeHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()
        ui_server.DB_PATH = ui_server.get_default_db_path()

    def request(self, method: str, path: str, data: dict | None = None) -> tuple[int, str, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {}
        body = None
        if data is not None:
            body = urlencode(data)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        resp_body = res.read().decode("utf-8")
        resp_headers = dict(res.getheaders())
        conn.close()
        return res.status, resp_body, resp_headers

    def request_json(self, path: str, data: dict) -> tuple[int, dict]:
        import json
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        body = json.dumps(data)
        headers = {"Content-Type": "application/json"}
        conn.request("POST", path, body=body, headers=headers)
        res = conn.getresponse()
        resp_data = json.loads(res.read().decode("utf-8"))
        conn.close()
        return res.status, resp_data

    def test_ui_renders_and_handles_goals(self):
        # 1. GET /classic initial load
        status, body, _ = self.request("GET", "/classic")
        self.assertEqual(200, status)
        self.assertIn("長任務目標看板 (Goals)", body)
        self.assertIn("目前沒有長任務 Goal", body)

        # 2. POST /goal/create
        status, _, headers = self.request("POST", "/goal/create", {
            "project_id": self.prj["id"],
            "title": "UI Goal 1",
            "description": "Created via UI test",
        })
        self.assertEqual(303, status)
        self.assertIn("Location", headers)

        # Verify Goal in GET /classic
        status, body, _ = self.request("GET", "/classic")
        self.assertEqual(200, status)
        self.assertIn("UI Goal 1", body)

        goals = self.engine.list_goals(self.prj["id"])
        self.assertEqual(1, len(goals))
        goal_id = goals[0]["id"]

        # 3. POST /ticket/create linked to Goal
        status, _, headers = self.request("POST", "/ticket/create", {
            "project_id": self.prj["id"],
            "title": "Sub Ticket 1",
            "goal": "do work",
            "criteria": "criteria 1",
            "goal_id": goal_id,
            "risk_level": "low",
        })
        self.assertEqual(303, status)

        # 4. POST /goal/advance
        status, _, headers = self.request("POST", "/goal/advance", {
            "goal_id": goal_id,
        })
        self.assertEqual(303, status)

        # 5. Check updated goal progress in GET /classic
        status, body, _ = self.request("GET", "/classic")
        self.assertEqual(200, status)
        self.assertIn("完成進度: <strong>100.0%</strong>", body)
        self.assertIn("achieved", body)

        # 6. POST /project/create
        status, _, headers = self.request("POST", "/project/create", {
            "workspace_id": self.ws["id"],
            "name": "Another Project",
        })
        self.assertEqual(303, status)
        prjs = self.engine.list_projects(self.ws["id"])
        self.assertEqual(2, len(prjs))

        # 7. Check /classic redirect message handling
        status, body, _ = self.request("GET", "/classic?msg=TestSuccess")
        self.assertEqual(200, status)
        self.assertIn("TestSuccess", body)

    def test_ui_mindmap_and_nodes_sync(self):
        # 1. GET / renders precision cockpit by default
        status, body, _ = self.request("GET", "/")
        self.assertEqual(200, status)
        self.assertIn("日產精工裝配駕駛艙", body)
        self.assertIn("Tier 0~4 分層治理憲法", body)

        # 2. POST /nodes/sync-agentos populates SQLite nodes
        status, _, headers = self.request("POST", "/nodes/sync-agentos", {
            "project_id": self.prj["id"],
        })
        self.assertEqual(303, status)
        nodes = self.engine.list_nodes(self.prj["id"])
        self.assertGreaterEqual(len(nodes), 10)
        target_node = next(n for n in nodes if "Contract Linter" in n["title"])

        # 3. POST /ticket/create linked to node
        status, _, _ = self.request("POST", "/ticket/create", {
            "project_id": self.prj["id"],
            "title": "驗證 LINT 門禁",
            "goal": "核對 expected_outputs",
            "criteria": "error_count 歸零",
            "node_id": target_node["id"],
            "risk_level": "high",
        })
        self.assertEqual(303, status)

        # 4. GET /classic displays ticket with node badge
        status, body, _ = self.request("GET", "/classic")
        self.assertEqual(200, status)
        self.assertIn(f"Node #{target_node['id']}", body)
        self.assertIn("驗證 LINT 門禁", body)

    def test_ui_precision_cockpit_and_api_chat(self):
        # 1. Test chat sandbox verification
        status, data = self.request_json("/api/chat", {
            "message": "⚡ 啟動沙盒測試",
            "node_id": "task_n4",
        })
        self.assertEqual(200, status)
        self.assertEqual("verified", data["action"])
        self.assertIn("極限試車沙盒驗證通過", data["reply"])
        self.assertIn("SHA-256", data["reply"])

        # 2. Test chat create ticket
        status, data = self.request_json("/api/chat", {
            "message": "🛠️ 在此工位開立工單",
            "node_id": "task_n4",
        })
        self.assertEqual(200, status)
        self.assertEqual("ticket_created", data["action"])
        self.assertIn("日產精工工單已建立", data["reply"])

        # 3. Test chat diagnose
        status, data = self.request_json("/api/chat", {
            "message": "🔍 診斷此工位阻斷點",
            "node_id": "task_n4",
        })
        self.assertEqual(200, status)
        self.assertEqual("diagnosed", data["action"])
        self.assertIn("工位精密診斷報告", data["reply"])


class ProjectSwitcherTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "workbench.db"
        ui_server.DB_PATH = cls.db_path
        cls.engine = WorkbenchEngine(cls.db_path)
        cls.ws = cls.engine.create_workspace("Switcher WS")
        cls.prj = cls.engine.create_project(cls.ws["id"], "Switcher Main PRJ")

        cls.server = HTTPServer(("127.0.0.1", 0), ui_server.PrototypeHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()
        ui_server.DB_PATH = ui_server.get_default_db_path()

    def request(self, method: str, path: str, data: dict | None = None) -> tuple[int, str, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        headers = {}
        body = None
        if data is not None:
            body = urlencode(data)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()
        resp_body = res.read().decode("utf-8")
        resp_headers = dict(res.getheaders())
        conn.close()
        return res.status, resp_body, resp_headers

    def request_json(self, path: str, data: dict) -> tuple[int, dict]:
        import json
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        body = json.dumps(data)
        headers = {"Content-Type": "application/json"}
        conn.request("POST", path, body=body, headers=headers)
        res = conn.getresponse()
        resp_data = json.loads(res.read().decode("utf-8"))
        conn.close()
        return res.status, resp_data

    def test_project_switcher_and_all_tickets_api(self):
        # 1. Verify GET / renders project switcher and ticket scope buttons
        status, body, _ = self.request("GET", "/")
        self.assertEqual(200, status)
        self.assertIn("project-dropdown-menu", body)
        self.assertIn("ladder-project-title", body)
        self.assertIn("switchTicketsScope('all')", body)

        # 2. Test JSON POST /api/project/create
        status, data = self.request_json("/api/project/create", {
            "name": "Switcher Test Project",
            "workspace_id": self.ws["id"],
        })
        self.assertEqual(200, status)
        self.assertEqual("ok", data.get("status"))
        new_prj_id = data.get("project_id")
        self.assertIsNotNone(new_prj_id)
        self.assertTrue(any(p["id"] == new_prj_id for p in data.get("projects", [])))

        # 3. Create a ticket in the new project
        self.engine.create_ticket(
            project_id=new_prj_id,
            title="Ticket in Project 2",
            goal="Test ticket in second project",
            acceptance_criteria=["Done"],
        )

        # 4. Test GET /api/state?project_id=all
        status, body, _ = self.request("GET", "/api/state?project_id=all")
        self.assertEqual(200, status)
        import json
        state_all = json.loads(body)
        self.assertIn("all_projects", state_all)
        self.assertGreaterEqual(len(state_all["all_projects"]), 2)
        ticket_titles = [t["title"] for t in state_all.get("tickets", [])]
        self.assertIn("Ticket in Project 2", ticket_titles)
        # Verify project_name is attached in cross-project tickets
        target_t = next(t for t in state_all.get("tickets", []) if t["title"] == "Ticket in Project 2")
        self.assertEqual("Switcher Test Project", target_t.get("project_name"))

        # 5. Test GET /api/state?project_id=<new_prj_id> (filtered)
        status, body, _ = self.request("GET", f"/api/state?project_id={new_prj_id}")
        self.assertEqual(200, status)
        state_filtered = json.loads(body)
        self.assertEqual(new_prj_id, state_filtered.get("current_project_id"))
        self.assertEqual(1, len(state_filtered.get("tickets", [])))
        self.assertEqual("Ticket in Project 2", state_filtered["tickets"][0]["title"])


if __name__ == "__main__":
    unittest.main()


