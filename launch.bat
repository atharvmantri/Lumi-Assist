@echo off
setlocal
:: Lumi Launcher - starts the tray app after a dependency preflight
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" (
    echo [Lumi] Not installed yet. Run install.bat first.
    pause
    exit /b 1
)

call "%~dp0repair_env.bat"
if errorlevel 1 (
    echo.
    echo [Lumi] Could not repair the project environment.
    echo [Lumi] Run install.bat, then try again.
    pause
    exit /b 1
)

:: Start Lumi in background with no Python console window.
start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0lumi_app.py"
