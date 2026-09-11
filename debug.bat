@echo off
cd /d "%~dp0"
if exist "runtime\python.exe" (
    "runtime\python.exe" main.py
) else (
    ".venv\Scripts\python.exe" main.py
)
pause
