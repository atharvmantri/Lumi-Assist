@echo off
:: Lumi Voice Mode - Runs with terminal for voice input
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo Lumi not installed. Run install.bat first.
    pause
    exit /b 1
)

title Lumi - Voice Mode
echo Starting Lumi in voice mode...
echo.
venv\Scripts\python.exe main.py
pause
