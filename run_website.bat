@echo off
cd /d "%~dp0"
echo ============================================================
echo  Starting OrbisLuna Mission Control Web Platform...
echo  URL: http://localhost:8050
echo ============================================================

REM Give server 1 second to start before opening browser
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8050"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" web_server.py
) else (
    python web_server.py
)
pause
