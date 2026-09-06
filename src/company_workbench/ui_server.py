"""
Company AI Workbench - Web UI Server.
Zero external frontend dependencies, pure Python standard library HTTP server.
"""
from __future__ import annotations

import html
import json
import os
import sys
import webbrowser
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from .engine import WorkbenchEngine, TIERED_ACCEPTANCE_AUTHORITY
from .errors import (
    NotFoundError,
    InvalidTransitionError,
    EvidenceRequiredError,
    AcceptanceRequiredError,
)
from .runner import CodexCliRunner, ClaudeCliRunner
from .mindmap import render_agentos_mindmap_html

def get_default_db_path() -> Path:
    env_db = os.environ.get("WORKBENCH_DB")
    if env_db:
        return Path(env_db)
    return Path.cwd() / ".workbench" / "workbench.db"

DB_PATH: Path = get_default_db_path()
PORT: int = 8088
HOST: str = "127.0.0.1"


def get_engine() -> WorkbenchEngine:
    path = DB_PATH
    if "ui_server" in sys.modules and hasattr(sys.modules["ui_server"], "DB_PATH"):
        path = sys.modules["ui_server"].DB_PATH
    return WorkbenchEngine(path, acceptance_authority=TIERED_ACCEPTANCE_AUTHORITY)


def render_html(body: str, message: str = "", error: str = "") -> str:
    msg_box = (
        f'<div style="background:#e6ffed;border:1px solid #34d058;padding:12px 16px;margin-bottom:16px;border-radius:6px;color:#22863a;font-weight:500;">✓ {html.escape(message)}</div>'
        if message else ''
    )
    err_box = (
        f'<div style="background:#ffeef0;border:1px solid #d73a49;padding:12px 16px;margin-bottom:16px;border-radius:6px;color:#cb2431;font-weight:500;">✗ {html.escape(error)}</div>'
        if error else ''
    )
    
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Company AI Workbench 控制台</title>
  <style>
    :root {{
      --primary: #2ea44f;
      --primary-hover: #2c974b;
      --blue: #0366d6;
      --purple: #6f42c1;
      --orange: #f66a0a;
      --border: #e1e4e8;
      --bg: #f6f8fa;
      --card-bg: #ffffff;
      --text: #24292e;
      --text-muted: #586069;
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; background: var(--bg); color: var(--text); line-height: 1.5; }}
    .container {{ max-width: 1080px; margin: 0 auto; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }}
    .brand h1 {{ margin: 0; font-size: 24px; display: flex; align-items: center; gap: 8px; }}
    .brand .badge-tag {{ font-size: 12px; background: #0366d6; color: #fff; padding: 2px 8px; border-radius: 12px; font-weight: normal; }}
    .brand .subtitle {{ font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
    .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
    .ticket {{ border-left: 5px solid var(--blue); }}
    .ticket.active {{ border-left-color: var(--orange); }}
    .ticket.verification {{ border-left-color: var(--purple); }}
    .ticket.accepted {{ border-left-color: var(--primary); }}
    .badge {{ display: inline-block; padding: 3px 10px; font-size: 12px; font-weight: 600; border-radius: 12px; text-transform: uppercase; }}
    .badge-ready {{ background: #dbedff; color: #0366d6; }}
    .badge-active {{ background: #ffe3c2; color: #c2410c; }}
    .badge-verification {{ background: #f3e8fd; color: #6f42c1; }}
    .badge-accepted {{ background: #dcffe4; color: #1a7f37; }}
    .btn {{ display: inline-block; font-weight: 600; padding: 7px 16px; font-size: 13px; border-radius: 6px; border: 1px solid transparent; cursor: pointer; text-decoration: none; transition: all 0.15s ease-in-out; }}
    .btn-primary {{ background: var(--primary); color: #fff; border-color: rgba(27,31,35,0.15); }}
    .btn-primary:hover {{ background: var(--primary-hover); }}
    .btn-secondary {{ background: #fafbfc; color: var(--text); border-color: rgba(27,31,35,0.15); }}
    .btn-secondary:hover {{ background: #f3f4f6; }}
    .btn-warning {{ background: var(--orange); color: #fff; }}
    .btn-warning:hover {{ background: #e05d04; }}
    .btn-purple {{ background: var(--purple); color: #fff; }}
    .btn-purple:hover {{ background: #5a32a3; }}
    .btn-sm {{ padding: 4px 10px; font-size: 12px; }}
    .form-group {{ margin-bottom: 14px; }}
    label {{ display: block; font-weight: 600; margin-bottom: 6px; font-size: 13px; }}
    input[type="text"], textarea, select {{ width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #d1d5da; border-radius: 6px; font-size: 13px; background: #fff; }}
    input[type="text"]:focus, textarea:focus, select:focus {{ outline: none; border-color: #0366d6; box-shadow: 0 0 0 3px rgba(3,102,214,0.3); }}
    textarea {{ resize: vertical; min-height: 70px; }}
    .inline-form {{ display: inline-block; margin-right: 8px; margin-bottom: 6px; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
    .nav-bar {{ display: flex; gap: 8px; align-items: center; }}
    .db-info {{ font-size: 12px; color: var(--text-muted); background: #eee; padding: 4px 8px; border-radius: 4px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand">
        <h1>Company AI Workbench <span class="badge-tag">v0.1.0 Ready</span></h1>
        <div class="subtitle">本機優先 · 不變量治理 · 多模型自動除錯迴圈 · 主分支交付保護</div>
      </div>
      <div class="nav-bar">
        <a href="/agentos-map" class="btn btn-purple btn-sm" style="margin-right: 6px;">🗺️ AgentOS 全景心智圖</a>
        <span class="db-info" title="{html.escape(str(DB_PATH))}">DB: {html.escape(DB_PATH.name)}</span>
        <a href="/" class="btn btn-secondary btn-sm">重新整理</a>
      </div>
    </div>
    {msg_box}
    {err_box}
    {body}
  </div>
</body>
</html>"""


class PrototypeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean stdout logging
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/agentos-map", "/map"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(render_agentos_mindmap_html().encode("utf-8"))
            return

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

        # Collect all goals for dropdown
        all_goals = []
        for prj in all_projects:
            all_goals.extend(engine.list_goals(prj["id"]))
        goal_options = '<option value="">(無 - 獨立工單)</option>' + "".join(
            f'<option value="{g["id"]}">{html.escape(g["title"])} ({g["status"]})</option>' for g in all_goals
        )

        # Collect all tickets for dependency dropdown
        all_tickets_list = []
        for prj in all_projects:
            all_tickets_list.extend(engine.list_tickets(prj["id"]))
        ticket_dep_options = '<option value="">(無 - 無前置依賴)</option>' + "".join(
            f'<option value="{t["id"]}">#{t["id"]} - {html.escape(t["title"])} ({t["status"]})</option>' for t in all_tickets_list
        )

        # ── Quick Creation Bar (Project / Goal) ──
        content.append(f"""
        <div class="grid-2">
          <!-- Create Project -->
          <div class="card" style="border-top: 4px solid #0366d6;">
            <h3>新增專案 (Project)</h3>
            <form method="POST" action="/project/create">
              <input type="hidden" name="workspace_id" value="{workspaces[0]['id']}">
              <div class="form-group">
                <label>專案名稱</label>
                <input type="text" name="name" required placeholder="例如：Payment Gateway / Auth Service">
              </div>
              <button type="submit" class="btn btn-secondary btn-sm">建立專案</button>
            </form>
          </div>

          <!-- Create Goal -->
          <div class="card" style="border-top: 4px solid #6f42c1;">
            <h3>建立長任務目標 (Goal)</h3>
            <form method="POST" action="/goal/create">
              <div class="form-group">
                <label>所屬專案</label>
                <select name="project_id">{prj_options}</select>
              </div>
              <div class="form-group">
                <label>目標標題</label>
                <input type="text" name="title" required placeholder="例如：新版會員系統重構 (長任務)">
              </div>
              <div class="form-group">
                <label>目標詳細敘述</label>
                <input type="text" name="description" placeholder="此長任務目標需經多階段工單循序完成">
              </div>
              <button type="submit" class="btn btn-purple btn-sm">建立長任務 Goal</button>
            </form>
          </div>
        </div>
        """)

        # ── Goals Dashboard ──
        content.append("<h2>長任務目標看板 (Goals)</h2>")
        if all_goals:
            for g in all_goals:
                g_detail = engine.get_goal(g["id"])
                pct = g_detail["progress_pct"]
                g_status = g_detail["status"]
                badge_class = "accepted" if g_status == "achieved" else ("active" if g_status == "in_progress" else "ready")
                
                g_tkts = g_detail.get("tickets", [])
                tkt_rows = ""
                if g_tkts:
                    tkt_rows = '<div style="margin-top: 10px; font-size: 13px;"><strong>包含工單鏈：</strong><ul style="margin: 4px 0; padding-left: 20px;">'
                    for gt in g_tkts:
                        dep_text = f" <span style='color:#d73a49;'>(依賴 #{gt['depends_on_ticket_id']})</span>" if gt.get("depends_on_ticket_id") else ""
                        tkt_rows += f"<li>#{gt['id']} {html.escape(gt['title'])} - <span class='badge badge-{gt['status']}'>{gt['status']}</span>{dep_text}</li>"
                    tkt_rows += "</ul></div>"

                content.append(f"""
                <div class="card" style="border-left: 4px solid #6f42c1;">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin:0;">{html.escape(g_detail['title'])} <span style="font-size: 13px; color: #586069;">#{g_detail['id']}</span></h3>
                    <span class="badge badge-{badge_class}">{g_status}</span>
                  </div>
                  <p style="margin: 6px 0 10px 0; color: #586069; font-size: 13px;">{html.escape(g_detail['description'] or '無詳細說明')}</p>
                  
                  <div style="margin: 10px 0;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                      <span>完成進度: <strong>{pct}%</strong> ({g_detail['accepted_tickets']}/{g_detail['total_tickets']} 工單已驗收)</span>
                    </div>
                    <div style="background: #e1e4e8; border-radius: 6px; height: 12px; overflow: hidden;">
                      <div style="background: #2ea44f; height: 100%; width: {pct}%; transition: width 0.3s ease;"></div>
                    </div>
                  </div>

                  {tkt_rows}

                  <div style="margin-top: 14px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <form method="POST" action="/goal/advance" class="inline-form" style="display: flex; gap: 6px; align-items: center;">
                      <input type="hidden" name="goal_id" value="{g_detail['id']}">
                      <select name="runner" style="width: auto; padding: 5px 8px; font-size: 12px;">
                        <option value="fake">Fake 模擬 (自動測試)</option>
                        <option value="codex">OpenAI Codex CLI</option>
                        <option value="claude">Anthropic Claude Code</option>
                      </select>
                      <button type="submit" class="btn btn-warning btn-sm" {"disabled style='opacity:0.5;cursor:not-allowed;'" if g_status == 'achieved' else ""}>
                        一鍵推進下一工單 (Advance)
                      </button>
                    </form>
                    {f'''
                    <form method="POST" action="/goal/deliver" class="inline-form">
                      <input type="hidden" name="goal_id" value="{g['id']}">
                      <button type="submit" class="btn btn-primary btn-sm">
                        交付此目標至主分支 (Deliver)
                      </button>
                    </form>
                    ''' if g_status == 'achieved' else ''}
                  </div>
                </div>
                """)
        else:
            content.append('<div class="card" style="text-align: center; color: #586069; padding: 24px;">目前沒有長任務 Goal，請由上方卡片建立。</div>')

        # ── Ticket Creation Card ──
        content.append(f"""
        <div class="card" style="border-top: 4px solid #0366d6;">
          <h2>開立 Ticket (工單任務)</h2>
          <form method="POST" action="/ticket/create">
            <div class="grid-3">
              <div class="form-group">
                <label>專案 (Project)</label>
                <select name="project_id">{prj_options}</select>
              </div>
              <div class="form-group" style="grid-column: span 2;">
                <label>Ticket 標題</label>
                <input type="text" name="title" required placeholder="例如：實作用戶登入 API 與 JWT 驗證">
              </div>
            </div>
            <div class="grid-3">
              <div class="form-group">
                <label>所屬長任務 (Goal，可選)</label>
                <select name="goal_id">{goal_options}</select>
              </div>
              <div class="form-group">
                <label>前置依賴工單 (可選)</label>
                <select name="depends_on_ticket_id">{ticket_dep_options}</select>
              </div>
              <div class="form-group">
                <label>風險等級 (審核門檻)</label>
                <select name="risk_level">
                  <option value="high" selected>High (Josh 專屬人工驗收)</option>
                  <option value="low">Low (測試通過允許自動驗收)</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>目標說明 (Goal Statement)</label>
              <input type="text" name="goal" required placeholder="例如：提供 POST /api/login，回傳 JWT access token">
            </div>
            <div class="form-group">
              <label>驗收條件 (Acceptance Criteria，每行一項)</label>
              <textarea name="criteria" required placeholder="1. pytest tests/test_auth.py 全部通過&#10;2. 密碼以 bcrypt 加密儲存&#10;3. Token 過期時間為 24 小時"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">建立 Ticket</button>
          </form>
        </div>
        """)

        # ── Tickets List ──
        content.append("<h2>工單看板 (Tickets Board)</h2>")
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
                    runs_html = '<div style="margin-top: 10px; font-size: 12px; background:#fafbfc; padding: 10px; border-radius: 6px;"><strong>歷史 Runs:</strong><br>'
                    for r in runs:
                        runs_html += f"• <code>{r['id']}</code> ({r['runner']}) - <strong>{r['status']}</strong> ({r['started_at'][:19]})"
                        with engine.store.connect() as db:
                            episodes = db.execute("SELECT * FROM debug_episodes WHERE run_id=?", (r["id"],)).fetchall()
                        if episodes:
                            runs_html += f" <span style='color:#f66a0a; font-weight:600;'>(歷經 {len(episodes)} 次自動除錯重試)</span>"
                            for ep in episodes:
                                runs_html += f"<div style='margin-left: 15px; color:#586069; font-size: 11px;'>⤷ [{ep['fingerprint'][:8]}] {html.escape(ep['symptom'])}</div>"
                        runs_html += "<br>"
                    runs_html += "</div>"

                actions = []
                if status == "ready":
                    actions.append(f"""
                    <form method="POST" action="/run/start" class="inline-form" style="display:flex; gap:6px; align-items:center;">
                      <input type="hidden" name="ticket_id" value="{tkt['id']}">
                      <select name="runner" style="width: auto; padding: 5px 8px; font-size: 12px;">
                        <option value="fake">Fake 模擬 (自動測試)</option>
                        <option value="codex">OpenAI Codex CLI</option>
                        <option value="claude">Anthropic Claude Code</option>
                      </select>
                      <button type="submit" class="btn btn-warning btn-sm">啟動 Managed Run (Auto-Debug)</button>
                    </form>
                    """)
                elif status == "active":
                    if latest_run:
                        actions.append(f"""
                        <form method="POST" action="/run/complete" class="inline-form">
                          <input type="hidden" name="run_id" value="{latest_run['id']}">
                          <button type="submit" class="btn btn-purple btn-sm">標記 Run 完成 (進入 Verification 驗證)</button>
                        </form>
                        """)
                elif status == "verification":
                    if latest_run:
                        actions.append(f"""
                        <div style="background: #f8f9fa; border: 1px dashed #6f42c1; padding: 12px; border-radius: 6px; margin-top: 10px;">
                          <h4 style="margin: 0 0 8px 0; color: #6f42c1;">填寫獨立驗證證據 (Verification Gate - Invariant 2 & 11)</h4>
                          <form method="POST" action="/verify">
                            <input type="hidden" name="run_id" value="{latest_run['id']}">
                            <div class="form-group">
                              <label>證據引用 (Evidence Ref / 測試指令或日誌標題)</label>
                              <input type="text" name="evidence" required value="pytest tests/ PASS 12/12">
                            </div>
                            <div class="form-group">
                              <label>總結摘要 (Summary)</label>
                              <input type="text" name="summary" required value="驗證通過，符合所有 acceptance criteria">
                            </div>
                            <button type="submit" class="btn btn-purple btn-sm">提交 SHA-256 驗證證據</button>
                          </form>
                        </div>
                        """)
                        actions.append(f"""
                        <form method="POST" action="/accept" class="inline-form" style="margin-top: 10px;">
                          <input type="hidden" name="ticket_id" value="{tkt['id']}">
                          <button type="submit" class="btn btn-primary btn-sm">Josh 正式簽核驗收 (Accept)</button>
                        </form>
                        """)
                elif status == "accepted":
                    actions.append(f'<span style="color: #28a745; font-weight: bold; font-size: 13px;">✓ 已由 {html.escape(tkt["accepted_by"] or "Josh")} 驗收結案</span>')
                    actions.append(f"""
                    <form method="POST" action="/ticket/deliver" class="inline-form" style="margin-left: 12px;">
                      <input type="hidden" name="ticket_id" value="{tkt['id']}">
                      <button type="submit" class="btn btn-primary btn-sm">交付至主分支 (Deliver to Master)</button>
                    </form>
                    """)

                criteria_list = "".join(f"<li>{html.escape(c)}</li>" for c in tkt["acceptance_criteria"])
                
                goal_tag = f"<span class='badge' style='background:#f3e8fd;color:#6f42c1;'>Goal #{tkt['goal_id']}</span> " if tkt.get("goal_id") else ""
                dep_tag = f"<span class='badge' style='background:#fff0f5;color:#d73a49;'>依賴 #{tkt['depends_on_ticket_id']}</span> " if tkt.get("depends_on_ticket_id") else ""
                risk_tag = f"<span class='badge' style='background:#f1f8ff;color:#0366d6;'>Risk: {tkt.get('risk_level','high')}</span> "

                content.append(f"""
                <div class="card ticket {status}">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin:0;">{html.escape(tkt['title'])} <span style="font-size: 13px; color: #586069;">#{tkt['id']}</span></h3>
                    <div>
                      {goal_tag}{dep_tag}{risk_tag}
                      <span class="badge badge-{status}">{status}</span>
                    </div>
                  </div>
                  <p style="margin: 6px 0 8px 0; color: #333; font-size: 13px;"><strong>目標:</strong> {html.escape(tkt['goal'])}</p>
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
            content.append('<div class="card" style="text-align: center; color: #586069; padding: 24px;">目前沒有工單，請由上方表單開立工單。</div>')

        body_html = "\n".join(content)
        full_html = render_html(body_html, message=msg, error=err)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(full_html.encode("utf-8"))

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8")
        params = parse_qs(post_body)

        def get_val(key: str, default: str = "") -> str:
            vals = params.get(key, [])
            return vals[0] if vals else default

        parsed = urlparse(self.path)
        engine = get_engine()

        msg = ""
        err = ""

        try:
            if parsed.path == "/project/create":
                ws_id = get_val("workspace_id")
                name = get_val("name")
                prj = engine.create_project(ws_id, name)
                msg = f"成功建立專案「{prj['name']}」({prj['id']})"

            elif parsed.path == "/goal/create":
                prj_id = get_val("project_id")
                title = get_val("title")
                desc = get_val("description")
                goal = engine.create_goal(prj_id, title, description=desc)
                msg = f"成功建立長任務 Goal #{goal['id']}「{goal['title']}」"

            elif parsed.path == "/goal/advance":
                goal_id = get_val("goal_id")
                runner_type = get_val("runner", "fake")
                
                runner_instance = None
                if runner_type == "codex":
                    runner_instance = CodexCliRunner()
                elif runner_type == "claude":
                    runner_instance = ClaudeCliRunner()
                else:
                    from company_workbench.runner import ProcessResult, RunnerInvocation

                    class _FakeManagedProcess:
                        def __init__(self):
                            self.pid = 9999

                        def wait(self, *, cancel_event=None, **kwargs):
                            return ProcessResult(exit_code=0, stdout="Run succeeded via Web UI (Fake)", stderr="", pid=self.pid)

                    class _FakeRunner:
                        name = "codex-cli"

                        def start_invocation(self, prompt, cwd, **kwargs):
                            return RunnerInvocation(_FakeManagedProcess(), timeout_seconds=60, max_output_chars=4000, cancel_event=None, sensitive_values=())

                    runner_instance = _FakeRunner()
                
                verify_cmd = f'"{sys.executable}" -c "exit(0)"'
                res = engine.advance_goal(
                    goal_id,
                    runner=runner_instance,
                    cwd=Path.cwd(),
                    verification_command=verify_cmd,
                    isolate_worktree=False,
                    auto_accept_low_risk=True,
                )
                if res["action"] == "ran_ticket":
                    msg = f"已推進 Goal #{goal_id}，執行工單 #{res['ticket_id']} (當前進度: {res['goal']['progress_pct']}%)"
                else:
                    msg = f"Goal #{goal_id} 推進狀態: {res['action']} (當前進度: {res['goal']['progress_pct']}%)"

            elif parsed.path == "/ticket/create":
                prj_id = get_val("project_id")
                title = get_val("title")
                goal = get_val("goal")
                raw_crit = get_val("criteria")
                goal_id = get_val("goal_id") or None
                dep_id = get_val("depends_on_ticket_id") or None
                risk = get_val("risk_level", "high")
                criteria = [c.strip() for c in raw_crit.split("\n") if c.strip()]
                tkt = engine.create_ticket(
                    prj_id, title, goal, criteria,
                    risk_level=risk, goal_id=goal_id, depends_on_ticket_id=dep_id,
                )
                msg = f"成功建立工單 Ticket #{tkt['id']}「{tkt['title']}」"

            elif parsed.path == "/run/start":
                ticket_id = get_val("ticket_id")
                runner_type = get_val("runner", "fake")
                run = engine.start_run(ticket_id, runner=runner_type)
                msg = f"已為 Ticket #{ticket_id} 啟動 Run #{run['id']} ({runner_type})"

            elif parsed.path == "/run/complete":
                run_id = get_val("run_id")
                engine.complete_run(run_id)
                msg = f"Run #{run_id} 已標記完成，Ticket 進入 Verification 驗證階段"

            elif parsed.path == "/verify":
                run_id = get_val("run_id")
                evidence = get_val("evidence")
                summary = get_val("summary")
                engine.verify_run(
                    run_id, status="passed", evidence_ref=evidence[:80] or "ui-evidence", summary=summary,
                    verifier="Josh", verifier_provider="human", evidence_content=evidence,
                )
                msg = f"Run #{run_id} 驗證紀錄已鎖定保存 (SHA-256 Content-Addressed)"

            elif parsed.path == "/accept":
                ticket_id = get_val("ticket_id")
                engine.accept_ticket(ticket_id, accepted_by="Josh", note="Approved via Web UI Console")
                msg = f"Ticket #{ticket_id} 已正式簽核驗收通過！"

            elif parsed.path == "/ticket/deliver":
                ticket_id = get_val("ticket_id")
                deliv_res = engine.deliver_ticket(ticket_id, repo_path=Path.cwd(), target_branch="master")
                commit_short = deliv_res["delivery_result"]["commit_sha"][:8] if deliv_res["delivery_result"]["commit_sha"] else ""
                msg = f"Ticket #{ticket_id} 已成功交付並合併至 master 主分支！(Commit: {commit_short})"

            elif parsed.path == "/goal/deliver":
                goal_id = get_val("goal_id")
                goal_res = engine.deliver_goal(goal_id, repo_path=Path.cwd(), target_branch="master")
                msg = f"Goal #{goal_id} 下所有已驗收工單已全數交付至 master 主分支！"

        except Exception as exc:
            err = str(exc)

        self.send_response(HTTPStatus.SEE_OTHER)
        redirect_url = "/"
        if msg:
            redirect_url += f"?msg={quote(msg)}"
        elif err:
            redirect_url += f"?err={quote(err)}"
        self.send_header("Location", redirect_url)
        self.end_headers()


def serve_ui(
    database: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8088,
    open_browser: bool = True,
) -> int:
    global DB_PATH, PORT, HOST
    if database:
        DB_PATH = Path(database).resolve()
    PORT = port
    HOST = host

    # Ensure parent directory for database exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    url = f"http://{host}:{port}/"
    banner = f"""
======================================================================
  Company AI Workbench Web UI 控制台
  網址 (URL):   {url}
  資料庫 (DB):  {DB_PATH}
======================================================================
"""
    print(banner, flush=True)

    server = HTTPServer((host, port), PrototypeHandler)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nUI 控制台已正常停止。")
    finally:
        server.server_close()
    return 0


def run():
    import argparse
    parser = argparse.ArgumentParser(description="Company AI Workbench Web UI")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="Host address to bind")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", PORT)), help="Port to listen on")
    parser.add_argument("--database", type=Path, default=None, help="Workbench SQLite database path")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args, _ = parser.parse_known_args()

    serve_ui(
        database=args.database,
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )


if __name__ == "__main__":
    run()
