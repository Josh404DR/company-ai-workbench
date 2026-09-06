"""
UI Server compatibility shim.
Re-exports from company_workbench.ui_server.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is on path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from company_workbench.ui_server import (
    DB_PATH,
    PORT,
    HOST,
    PrototypeHandler,
    get_default_db_path,
    get_engine,
    render_html,
    serve_ui,
    run,
)

if __name__ == "__main__":
    run()
