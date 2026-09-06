@echo off
setlocal enabledelayedexpansion

title Company AI Workbench

echo ======================================================================
echo    Company AI Workbench - 一鍵啟動 (One-Click Launcher)
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHONPATH=%SCRIPT_DIR%src;%SCRIPT_DIR%prototype"

REM 1. 優先檢查常見虛擬環境
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PY_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
    goto :FOUND_PY
)

if exist "E:\Workspace\ai-tool-core\.venv\Scripts\python.exe" (
    set "PY_EXE=E:\Workspace\ai-tool-core\.venv\Scripts\python.exe"
    goto :FOUND_PY
)

REM 2. 檢查系統 Python
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_EXE=python"
    goto :FOUND_PY
)

echo [錯誤] 找不到可用之 Python 執行檔！
echo 請確認已安裝 Python 3.12+ 並將其加入系統 PATH。
pause
exit /b 1

:FOUND_PY
echo [資訊] 使用 Python 執行器: %PY_EXE%
echo [資訊] 正在啟動控制台: http://127.0.0.1:8088/
echo [提示] 瀏覽器即將自動開啟，若未開啟請手動前往上述網址。
echo [提示] 按下 Ctrl+C 可隨時停止服務。
echo.

"%PY_EXE%" -m company_workbench.ui_server --host 127.0.0.1 --port 8088

if %ERRORLEVEL% neq 0 (
    echo.
    echo [警告] 服務異常退出 (Exit Code: %ERRORLEVEL%)
    pause
)
