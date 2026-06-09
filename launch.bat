@echo off
:: Lumi Quick Launch — starts with voice loop + tray
:: Double-click this to run Lumi

cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo Lumi venv not found. Run setup.bat first.
    pause
    exit /b 1
)

echo Starting Lumi...
echo.
venv\Scripts\python.exe main.py
pause
