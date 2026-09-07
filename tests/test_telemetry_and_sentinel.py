import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import HTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "prototype"))

from company_workbench.engine import WorkbenchEngine
from company_workbench.store import SQLiteStore
import company_workbench.ui_server as ui_server


class TelemetryAndSentinelTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_telemetry.db"
        self.store = SQLiteStore(self.db_path)
        self.engine = WorkbenchEngine(self.db_path)
        self.ws = self.engine.create_workspace("Test WS")
        self.prj = self.engine.create_project(self.ws["id"], "Test Project")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_v8_migration(self):
        self.assertEqual(self.store.schema_version(), 8)
        with self.store.connect() as db:
            cols = {row[1] for row in db.execute("PRAGMA table_info(system_errors)")}
            self.assertIn("fingerprint", cols)
            self.assertIn("source", cols)
            self.assertIn("severity", cols)
            self.assertIn("occurrence_count", cols)
            self.assertIn("ticket_id", cols)

    def test_record_error_deduplication(self):
        err1 = self.engine.record_error(
            source="frontend",
            message="TypeError: Cannot read properties of undefined (reading 'id') at 0x1234abcd",
            error_type="TypeError",
            severity="error",
        )
        self.assertEqual(err1["occurrence_count"], 1)
        self.assertEqual(err1["status"], "unresolved")

        # Second record with similar address (should normalize and match fingerprint)
        err2 = self.engine.record_error(
            source="frontend",
            message="TypeError: Cannot read properties of undefined (reading 'id') at 0x5678ef01",
            error_type="TypeError",
            severity="error",
        )
        self.assertEqual(err1["id"], err2["id"])
        self.assertEqual(err2["occurrence_count"], 2)

        # Different error should get a different fingerprint
        err3 = self.engine.record_error(
            source="backend",
            message="DatabaseLockedError: database is locked",
            error_type="OperationalError",
            severity="critical",
        )
        self.assertNotEqual(err1["id"], err3["id"])
        self.assertEqual(err3["occurrence_count"], 1)

    def test_convert_error_to_ticket_and_resolve(self):
        err = self.engine.record_error(
            source="runner",
            message="LINT-007 check failed on packet expected_outputs",
            error_type="LinterError",
            severity="error",
            project_id=self.prj["id"],
        )
        ticket = self.engine.convert_error_to_ticket(err["id"], project_id=self.prj["id"])
        self.assertIsNotNone(ticket["id"])
        self.assertIn("LinterError", ticket["title"])
        self.assertEqual(ticket["status"], "ready")

        updated_err = self.engine.get_error(err["id"])
        self.assertEqual(updated_err["status"], "ticket_created")
        self.assertEqual(updated_err["ticket_id"], ticket["id"])

        resolved = self.engine.resolve_error(err["id"])
        self.assertEqual(resolved["status"], "resolved")

    def test_sentinel_health_check(self):
        # Create a node with exploratory packet without details
        self.engine.create_node(
            project_id=self.prj["id"],
            layer="task",
            title="N4 Exploratory Task",
            summary="Testing exploratory packet",
            files=["packets/phase_1/n4-exploratory/manifest.json"],
        )

        report = self.engine.run_sentinel_health_check(self.prj["id"])
        self.assertGreaterEqual(report["findings_count"], 1)
        finding_types = [f["error_type"] for f in report["findings"]]
        self.assertIn("LINT-007", finding_types)

        # Check that it was recorded in system_errors
        errors = self.engine.list_errors(source="sentinel")
        self.assertGreaterEqual(len(errors), 1)


class TelemetryApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.temp_dir.name) / "workbench_api.db"
        ui_server.DB_PATH = cls.db_path
        if "ui_server" in sys.modules:
            sys.modules["ui_server"].DB_PATH = cls.db_path
        cls.engine = WorkbenchEngine(cls.db_path)
        cls.ws = cls.engine.create_workspace("API WS")
        cls.prj = cls.engine.create_project(cls.ws["id"], "AgentOS-Lite")

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
        if "ui_server" in sys.modules:
            sys.modules["ui_server"].DB_PATH = ui_server.get_default_db_path()

    def _post_json(self, path: str, data: dict) -> tuple[int, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        body = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        conn.request("POST", path, body=body, headers=headers)
        res = conn.getresponse()
        resp_data = json.loads(res.read().decode("utf-8"))
        conn.close()
        return res.status, resp_data

    def _get_json(self, path: str) -> tuple[int, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("GET", path)
        res = conn.getresponse()
        resp_data = json.loads(res.read().decode("utf-8"))
        conn.close()
        return res.status, resp_data

    def test_telemetry_ingestion_and_list_api(self):
        # 1. Ingest an error via POST
        status, res = self._post_json("/api/telemetry/errors", {
            "source": "frontend",
            "error_type": "NetworkError",
            "message": "Failed to fetch /api/chat",
            "severity": "error",
        })
        self.assertEqual(status, 200)
        self.assertEqual(res["status"], "ok")
        err_id = res["error"]["id"]

        # 2. Query via GET
        get_status, get_res = self._get_json("/api/telemetry/errors")
        self.assertEqual(get_status, 200)
        self.assertGreaterEqual(get_res["unresolved_count"], 1)

        # 3. Convert to Ticket via POST
        conv_status, conv_res = self._post_json("/api/telemetry/errors/convert-ticket", {
            "error_id": err_id,
            "project_id": self.prj["id"],
        })
        self.assertEqual(conv_status, 200)
        self.assertEqual(conv_res["status"], "ok")
        self.assertIsNotNone(conv_res["ticket"]["id"])

        # 4. Resolve via POST
        res_status, res_res = self._post_json("/api/telemetry/errors/resolve", {
            "error_id": err_id,
        })
        self.assertEqual(res_status, 200)
        self.assertEqual(res_res["status"], "ok")
        self.assertEqual(res_res["error"]["status"], "resolved")

    def test_sentinel_scan_api(self):
        status, res = self._post_json("/api/sentinel/scan", {"project_id": self.prj["id"]})
        self.assertEqual(status, 200)
        self.assertIn("findings_count", res)
        self.assertIn("scanned_at", res)

    def test_chat_sentinel_report_integration(self):
        status, res = self._post_json("/api/chat", {
            "message": "檢查後台錯誤與巡檢狀況",
            "node_id": "task_n4",
        })
        self.assertEqual(status, 200)
        self.assertEqual(res["action"], "sentinel_report")
        self.assertIn("後台錯誤收集", res["reply"])
