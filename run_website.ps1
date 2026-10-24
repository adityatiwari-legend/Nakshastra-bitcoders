# LunaSafe Mission Control - PowerShell Launcher
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting LunaSafe Mission Control Web Platform...         " -ForegroundColor Yellow
Write-Host "  URL: http://localhost:8050                               " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

# Launch default browser after 2 seconds
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8050"
} | Out-Null

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    & $venvPython "web_server.py"
} else {
    python "web_server.py"
}
