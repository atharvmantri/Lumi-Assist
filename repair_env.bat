@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY=%CD%\venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [Lumi] Virtual environment not found: "%PY%"
    echo [Lumi] Run install.bat first.
    exit /b 10
)

:: The project is supported on Python 3.11. A stale venv created by another
:: Python can look healthy to global pip while still breaking Lumi, so repair it
:: in-place rather than asking the user/reviewer to diagnose interpreter paths.
"%PY%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [Lumi] Existing venv is not Python 3.11. Rebuilding it...
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo [Lumi] ERROR: Python 3.11 is not available. Run install.bat first.
        exit /b 14
    )
    rmdir /s /q "%CD%\venv"
    py -3.11 -m venv "%CD%\venv"
    if errorlevel 1 (
        echo [Lumi] ERROR: could not rebuild the Python 3.11 venv.
        exit /b 15
    )
)

:: IMPORTANT: always inspect/install packages through Lumi's own venv Python.
:: A global `pip install numpy` may target another Python version and will not
:: make the module visible to venv\Scripts\python.exe.
"%PY%" -c "import openai, numpy, yaml, dotenv, sounddevice, PyQt6, faster_whisper, piper, psutil" >nul 2>&1
if not errorlevel 1 goto :healthy

echo [Lumi] One or more required packages are missing from this project's venv.
echo [Lumi] Repairing with: "%PY%" -m pip install -r requirements.txt
"%PY%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [Lumi] ERROR: could not upgrade pip.
    exit /b 11
)

"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [Lumi] ERROR: dependency repair failed.
    echo [Lumi] Re-run install.bat and copy the first pip error shown.
    exit /b 12
)

"%PY%" -c "import openai, numpy, yaml, dotenv, sounddevice, PyQt6, faster_whisper, piper, psutil" >nul 2>&1
if errorlevel 1 (
    echo [Lumi] ERROR: core imports still fail after repair.
    echo [Lumi] Run: "%PY%" -m core.diagnostics
    exit /b 13
)

:healthy
"%PY%" -c "import sys, numpy; print('[Lumi] Environment OK - Python ' + sys.version.split()[0] + ', NumPy ' + numpy.__version__ + ', interpreter: ' + sys.executable)"
exit /b 0
