@echo off
:: JARVIS Quick Launch — starts with voice loop + tray
:: Double-click this to run JARVIS

cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo JARVIS venv not found. Run setup.bat first.
    pause
    exit /b 1
)

echo Starting JARVIS...
echo.
venv\Scripts\python.exe main.py
pause
