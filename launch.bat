@echo off
:: Lumi Launcher - Runs as tray app with NO terminal window
cd /d "%~dp0"

if not exist venv\Scripts\pythonw.exe (
    echo Lumi not installed. Run install.bat first.
    pause
    exit /b 1
)

:: Start Lumi in background (no window)
start "" venv\Scripts\pythonw.exe lumi_app.py
