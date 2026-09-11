@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -m venv .venv
) else (
    python -m venv .venv
)
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Ready. Double-click start.bat.
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.10+ or check your network.
pause
exit /b 1
