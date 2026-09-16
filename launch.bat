@echo off
setlocal
:: Lumi Launcher - production tray/overlay path after a dependency preflight
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

:: main.py is the canonical voice pipeline used by the reviewer/debug launcher.
:: Using the same entry point here prevents the normal tray launcher and the
:: certification path from drifting into two different runtimes.
start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0main.py"
