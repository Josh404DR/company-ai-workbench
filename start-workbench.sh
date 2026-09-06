#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="$SCRIPT_DIR/src:$SCRIPT_DIR/prototype:$PYTHONPATH"

if [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PY_BIN="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "[錯誤] 找不到 Python 執行檔，請確認已安裝 Python 3.12+"
    exit 1
fi

echo "======================================================================"
echo "   Company AI Workbench - 啟動中..."
echo "   網址: http://127.0.0.1:8088/"
echo "======================================================================"

exec "$PY_BIN" -m company_workbench.ui_server --host 127.0.0.1 --port 8088
