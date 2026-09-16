@echo off
setlocal
:: Lumi Voice Mode - terminal stays visible for diagnostics/reviewer testing
cd /d "%~dp0"

title Lumi - Voice Mode

if not exist "venv\Scripts\python.exe" (
    echo [Lumi] Not installed yet. Run install.bat first.
    pause
    exit /b 1
)

echo [Lumi] Checking the project virtual environment...
call "%~dp0repair_env.bat"
if errorlevel 1 (
    echo.
    echo [Lumi] Startup preflight failed.
    echo [Lumi] Do NOT run global `pip install ...`; Lumi uses its own venv.
    echo [Lumi] Run install.bat, then try launch_voice.bat again.
    pause
    exit /b 1
)

echo.
echo Starting Lumi in voice mode...
echo Wake phrase: hey lumi

echo.
"%~dp0venv\Scripts\python.exe" "%~dp0main.py"
set "EXITCODE=%errorlevel%"

echo.
if not "%EXITCODE%"=="0" (
    echo [Lumi] Exited with code %EXITCODE%.
    echo [Lumi] Run this for a detailed health report:
    echo   venv\Scripts\python.exe -m core.diagnostics
)
pause
exit /b %EXITCODE%
