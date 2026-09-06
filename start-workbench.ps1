Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Company AI Workbench - One-Click Launcher (PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$env:PYTHONPATH = "$scriptDir\src;$scriptDir\prototype"

$pyExe = "python"
if (Test-Path "$scriptDir\.venv\Scripts\python.exe") {
    $pyExe = "$scriptDir\.venv\Scripts\python.exe"
} elseif (Test-Path "E:\Workspace\ai-tool-core\.venv\Scripts\python.exe") {
    $pyExe = "E:\Workspace\ai-tool-core\.venv\Scripts\python.exe"
}

Write-Host "[INFO] Using Python: $pyExe" -ForegroundColor Green
Write-Host "[INFO] Starting Web UI at: http://127.0.0.1:8088/" -ForegroundColor Green
Write-Host "[TIP] Browser will open automatically. Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host ""

& $pyExe -m company_workbench.ui_server --host 127.0.0.1 --port 8088
