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

    def test_ui_renders_and_handles_goals(self):
        # 1. GET / initial load
        status, body, _ = self.request("GET", "/")
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

        # Verify Goal in GET
        status, body, _ = self.request("GET", "/")
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

        # 5. Check updated goal progress in GET
        status, body, _ = self.request("GET", "/")
        self.assertEqual(200, status)
        self.assertIn("完成進度: <strong>100.0%</strong>", body)
        self.assertIn("achieved", body)


if __name__ == "__main__":
    unittest.main()
