@echo off
setlocal enabledelayedexpansion

title Company AI Workbench

echo ======================================================================
echo    Company AI Workbench - One-Click Launcher
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHONPATH=%SCRIPT_DIR%src;%SCRIPT_DIR%prototype"

REM 1. Check workspace virtualenv
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PY_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
    goto :FOUND_PY
)

if exist "E:\Workspace\ai-tool-core\.venv\Scripts\python.exe" (
    set "PY_EXE=E:\Workspace\ai-tool-core\.venv\Scripts\python.exe"
    goto :FOUND_PY
)

REM 2. Check system Python
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_EXE=python"
    goto :FOUND_PY
)

echo [ERROR] Cannot find available Python interpreter!
echo Please make sure Python 3.12+ is installed and added to PATH.
pause
exit /b 1

:FOUND_PY
echo [INFO] Using Python interpreter: %PY_EXE%
echo [INFO] Starting Web UI dashboard at http://127.0.0.1:8088/
echo [INFO] Browser will open automatically. Press Ctrl+C to stop.
echo.

"%PY_EXE%" -m company_workbench.ui_server --host 127.0.0.1 --port 8088

if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Server stopped with Exit Code: %ERRORLEVEL%
    pause
)

