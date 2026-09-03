"""
Throwaway UI Prototype for Company AI Workbench.
Pure Python standard library (http.server), zero external dependencies, zero npm build.
"""
from __future__ import annotations

import html
import json
import sys
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from company_workbench.engine import WorkbenchEngine
from company_workbench.errors import (
    NotFoundError,
    InvalidTransitionError,
    EvidenceRequiredError,
    AcceptanceRequiredError,
)

DB_PATH = Path.cwd() / ".workbench" / "workbench.db"
PORT = 8088


def get_engine() -> WorkbenchEngine:
    return WorkbenchEngine(DB_PATH)


def render_html(body: str, message: str = "", error: str = "") -> str:
    msg_box = f'<div style="background:#e6ffed;border:1px solid #34d058;padding:10px;margin-bottom:15px;border-radius:4px;color:#22863a;">{html.escape(message)}</div>' if message else ''
    err_box = f'<div style="background:#ffeef0;border:1px solid #d73a49;padding:10px;margin-bottom:15px;border-radius:4px;color:#cb2431;">{html.escape(error)}</div>' if error else ''
    
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <title>Company AI Workbench (Prototype)</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; background: #f6f8fa; color: #24292e; }}
    .container {{ max-width: 1000px; margin: 0 auto; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e1e4e8; padding-bottom: 15px; margin-bottom: 20px; }}
    h1, h2, h3 {{ margin-top: 0; }}
    .card {{ background: #fff; border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
    .ticket {{ border-left: 4px solid #0366d6; }}
    .ticket.active {{ border-left-color: #f66a0a; }}
    .ticket.verification {{ border-left-color: #6f42c1; }}
    .ticket.accepted {{ border-left-color: #28a745; }}
    .badge {{ display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: bold; border-radius: 12px; text-transform: uppercase; }}
    .badge-ready {{ background: #dbedff; color: #0366d6; }}
    .badge-active {{ background: #ffe3c2; color: #c2410c; }}
    .badge-verification {{ background: #f3e8fd; color: #6f42c1; }}
    .badge-accepted {{ background: #dcffe4; color: #1a7f37; }}
    .btn {{ display: inline-block; font-weight: 600; padding: 6px 14px; font-size: 13px; border-radius: 4px; border: 1px solid transparent; cursor: pointer; text-decoration: none; }}
    .btn-primary {{ background: #2ea44f; color: #fff; border-color: rgba(27,31,35,0.15); }}
    .btn-primary:hover {{ background: #2c974b; }}
    .btn-secondary {{ background: #fafbfc; color: #24292e; border-color: rgba(27,31,35,0.15); }}
    .btn-secondary:hover {{ background: #f3f4f6; }}
    .btn-warning {{ background: #f66a0a; color: #fff; }}
    .btn-purple {{ background: #6f42c1; color: #fff; }}
    .form-group {{ margin-bottom: 12px; }}
    label {{ display: block; font-weight: 600; margin-bottom: 4px; font-size: 13px; }}
    input[type="text"], textarea, select {{ width: 100%; box-sizing: border-box; padding: 6px 8px; border: 1px solid #d1d5da; border-radius: 4px; font-size: 13px; }}
    textarea {{ resize: vertical; min-height: 60px; }}
    .inline-form {{ display: inline-block; margin-right: 8px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>Company AI Workbench <span style="font-size: 14px; font-weight: normal; color: #586069;">Prototype UI</span></h1>
        <div style="font-size: 12px; color: #586069;">零前端依賴・直讀 SQLite・SSR 極簡無坑</div>
      </div>
      <div>
        <a href="/" class="btn btn-secondary">重新整理</a>
      </div>
    </div>
    {msg_box}
    {err_box}
    {body}
  </div>
</body>
</html>"""


class PrototypeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        msg = params.get("msg", [""])[0]
        err = params.get("err", [""])[0]

        engine = get_engine()
        workspaces = engine.list_workspaces()
        
        if not workspaces:
            ws = engine.create_workspace("Default Workspace")
            prj = engine.create_project(ws["id"], "Core Product")
            workspaces = [ws]

        content = []

        all_projects = []
        for ws in workspaces:
            all_projects.extend(engine.list_projects(ws["id"]))

        prj_options = "".join(f'<option value="{p["id"]}">{html.escape(p["name"])} ({p["id"]})</option>' for p in all_projects)

        content.append(f"""
        <div class="card">
          <h2>開立 Ticket</h2>
          <form method="POST" action="/ticket/create">
            <div style="display: flex; gap: 10px;">
              <div class="form-group" style="flex: 1;">
                <label>專案 (Project)</label>
                <select name="project_id">{prj_options}</select>
              </div>
              <div class="form-group" style="flex: 2;">
                <label>Ticket 標題</label>
                <input type="text" name="title" required placeholder="例如：實作登入 API">
              </div>
            </div>
            <div class="form-group">
              <label>目標說明 (Goal)</label>
              <input type="text" name="goal" required placeholder="例如：支援 JWT 驗證與錯誤回傳">
            </div>
            <div class="form-group">
              <label>驗收條件 (Criteria，每行一項)</label>
              <textarea name="criteria" required placeholder="單元測試 100% 通過&#10;支援過期自動阻擋"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">建立 Ticket</button>
          </form>
        </div>
        """)

        content.append("<h2>任務看板 (Tickets)</h2>")
        
        has_tickets = False
        for prj in all_projects:
            tickets = engine.list_tickets(prj["id"])
            if not tickets:
                continue
            has_tickets = True
            for tkt in tickets:
                runs = engine.list_runs(tkt["id"])
                latest_run = runs[-1] if runs else None
                status = tkt["status"]
                
                runs_html = ""
                if runs:
                    runs_html = '<div style="margin-top: 10px; font-size: 12px;"><strong>歷史 Runs:</strong><br>'
                    for r in runs:
                        runs_html += f"• <code>{r['id']}</code> ({r['runner']}) - <strong>{r['status']}</strong> ({r['started_at'][:19]})<br>"
                    runs_html += "</div>"

                actions = []
                if status == "ready":
                    actions.append(f"""
                    <form method="POST" action="/run/start" class="inline-form">
                      <input type="hidden" name="ticket_id" value="{tkt['id']}">
                      <button type="submit" class="btn btn-warning">啟動 Run (Fake 模擬)</button>
                    </form>
                    """)
                elif status == "active":
                    if latest_run:
                        actions.append(f"""
                        <form method="POST" action="/run/complete" class="inline-form">
                          <input type="hidden" name="run_id" value="{latest_run['id']}">
                          <button type="submit" class="btn btn-purple">標記 Run 完成 (進 Verification)</button>
                        </form>
                        """)
                elif status == "verification":
                    if latest_run:
                        actions.append(f"""
                        <div style="background: #f8f9fa; border: 1px dashed #6f42c1; padding: 10px; border-radius: 4px; margin-top: 10px;">
                          <h4 style="margin: 0 0 8px 0; color: #6f42c1;">填寫驗證證據 (Verification Gate)</h4>
                          <form method="POST" action="/verify">
                            <input type="hidden" name="run_id" value="{latest_run['id']}">
                            <div class="form-group">
                              <label>證據引用 (Evidence Ref / 測試指令或日誌)</label>
                              <input type="text" name="evidence" required value="pytest tests/ PASS 12/12">
                            </div>
                            <div class="form-group">
                              <label>總結摘要 (Summary)</label>
                              <input type="text" name="summary" required value="驗證通過，符合所有 acceptance criteria">
                            </div>
                            <button type="submit" class="btn btn-purple">提交 Verification 證據</button>
                          </form>
                        </div>
                        """)
                        actions.append(f"""
                        <form method="POST" action="/accept" class="inline-form" style="margin-top: 10px;">
                          <input type="hidden" name="ticket_id" value="{tkt['id']}">
                          <button type="submit" class="btn btn-primary">Josh 正式驗收 (Accept)</button>
                        </form>
                        """)
                elif status == "accepted":
                    actions.append(f'<span style="color: #28a745; font-weight: bold;">已由 {html.escape(tkt["accepted_by"] or "Josh")} 驗收結案</span>')

                criteria_list = "".join(f"<li>{html.escape(c)}</li>" for c in tkt["acceptance_criteria"])
                
                content.append(f"""
                <div class="card ticket {status}">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>{html.escape(tkt['title'])} <span style="font-size: 13px; color: #586069;">#{tkt['id']}</span></h3>
                    <span class="badge badge-{status}">{status}</span>
                  </div>
                  <p style="margin: 4px 0 8px 0; color: #444;"><strong>目標:</strong> {html.escape(tkt['goal'])}</p>
                  <div style="font-size: 13px; color: #586069;">
                    <strong>驗收條件:</strong>
                    <ul style="margin: 4px 0 8px 0; padding-left: 20px;">{criteria_list}</ul>
                  </div>
                  {runs_html}
                  <div style="margin-top: 12px;">
                    {"".join(actions)}
                  </div>
                </div>
                """)

        if not has_tickets:
            content.append('<div class="card" style="text-align: center; color: #586069;">目前沒有 Ticket，請在上列表單建立第一張 Ticket。</div>')

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(render_html("".join(content), message=msg, error=err).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length).decode("utf-8")
        params = parse_qs(post_data)

        def get_val(key: str, default: str = "") -> str:
            return params.get(key, [default])[0].strip()

        engine = get_engine()
        msg = ""
        err = ""

        try:
            if parsed.path == "/ticket/create":
                prj_id = get_val("project_id")
                title = get_val("title")
                goal = get_val("goal")
                raw_crit = get_val("criteria")
                criteria = [c.strip() for c in raw_crit.split("\n") if c.strip()]
                tkt = engine.create_ticket(prj_id, title, goal, criteria)
                msg = f"成功建立 Ticket #{tkt['id']}"

            elif parsed.path == "/run/start":
                ticket_id = get_val("ticket_id")
                run = engine.start_run(ticket_id, runner="fake")
                msg = f"已為 Ticket #{ticket_id} 啟動 Run #{run['id']}"

            elif parsed.path == "/run/complete":
                run_id = get_val("run_id")
                engine.complete_run(run_id)
                msg = f"Run #{run_id} 已完成，Ticket 進入 Verification 驗證階段"

            elif parsed.path == "/verify":
                run_id = get_val("run_id")
                evidence = get_val("evidence")
                summary = get_val("summary")
                engine.verify_run(
                    run_id, status="passed", evidence_ref=evidence[:80] or "ui-evidence", summary=summary,
                    verifier="Josh", verifier_provider="human", evidence_content=evidence,
                )
                msg = f"Run #{run_id} 驗證紀錄已鎖定保存"

            elif parsed.path == "/accept":
                ticket_id = get_val("ticket_id")
                engine.accept_ticket(ticket_id, accepted_by="Josh", note="Approved via Prototype UI")
                msg = f"Ticket #{ticket_id} 已正式驗收通過！"

        except Exception as exc:
            err = str(exc)

        self.send_response(HTTPStatus.SEE_OTHER)
        redirect_url = "/"
        if msg:
            redirect_url += f"?msg={html.escape(msg)}"
        elif err:
            redirect_url += f"?err={html.escape(err)}"
        self.send_header("Location", redirect_url)
        self.end_headers()


def run():
    # 0.0.0.0 so this is reachable from outside the container when run under Docker
    # (127.0.0.1 would only be reachable from inside the container's own network namespace).
    server = HTTPServer(("0.0.0.0", PORT), PrototypeHandler)
    print(f"Company AI Workbench Prototype UI running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
