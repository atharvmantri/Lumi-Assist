@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: JARVIS — One-command setup for Windows 11
:: Run as: setup.bat
:: ============================================================

echo.
echo ========================================
echo   JARVIS Setup — Windows 11
echo ========================================
echo.

:: --- Check Python 3.11 ---
echo [1/8] Checking Python 3.11...
where py >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python Launcher not found. Install Python 3.11 from:
    echo   https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

py -3.11 --version >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python 3.11 not found. Install it from:
    echo   https://www.python.org/downloads/
    echo Then re-run this script.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('py -3.11 --version 2^>^&1') do set PY_VER=%%i
echo Found: %PY_VER%
echo.

:: --- Create virtual environment ---
echo [2/8] Creating virtual environment...
if exist venv\ (
    echo Venv exists — skipping. Delete venv\ to recreate.
) else (
    py -3.11 -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create venv.
        pause
        exit /b 1
    )
    echo Done.
)
echo.

:: --- Install pip dependencies ---
echo [3/8] Installing Python dependencies (this takes a few minutes)...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Some packages failed to install.
    echo This is often CUDA-related — JARVIS will still work on CPU.
    echo.
)
echo.

:: --- Create directories ---
echo [4/8] Creating project directories...
if not exist data\conversations mkdir data\conversations
if not exist logs mkdir logs
if not exist logs\learning mkdir logs\learning
if not exist logs\screenshots mkdir logs\screenshots
if not exist models\piper mkdir models\piper
echo Done.
echo.

:: --- Create .env template ---
echo [5/8] Setting up environment file...
if not exist .env (
    echo # JARVIS environment variables > .env
    echo # Get your HackClub API key from: https://hackclub.com/ >> .env
    echo HACKCLUB_API_KEY= >> .env
    echo.
    echo Created .env — edit it and add your HACKCLUB_API_KEY.
) else (
    echo .env already exists — skipping.
)
echo.

:: --- Download Piper voice model ---
echo [6/8] Checking Piper voice model...
set "VOICE_FILE=models\piper\en_GB-southern_english_female-low.onnx"
if not exist "!VOICE_FILE!" (
    echo Downloading British female voice (en_GB-southern_english_female-low)...
    echo This may take a minute...
    pip install huggingface-hub >nul 2>&1
    py -c "from huggingface_hub import hf_hub_download; hf_hub_download('rhassys/piper-voices', 'en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx', local_dir='models/piper', repo_type='model')"
    if !errorlevel! neq 0 (
        echo.
        echo WARNING: Voice download failed. Retry manually:
        echo   pip install huggingface-hub
        echo   python -c "from huggingface_hub import hf_hub_download; hf_hub_download('rhassys/piper-voices', 'en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx', local_dir='models/piper')"
    ) else (
        echo Voice downloaded.
    )
) else (
    echo Voice model already present.
)
echo.

:: --- Create local config ---
echo [7/8] Setting up local config...
if not exist config.local.yaml (
    echo # Override config.yaml settings here (git-ignored) > config.local.yaml
    echo # Example: change TTS voice or LLM model >> config.local.yaml
    echo Created config.local.yaml for local overrides.
) else (
    echo config.local.yaml already exists — skipping.
)
echo.

:: --- Run diagnostics ---
echo [8/8] Running diagnostics...
venv\Scripts\python.exe -m core.diagnostics
if %errorlevel% neq 0 (
    echo.
    echo Some checks failed. Review the output above.
    echo JARVIS may still work — some checks are optional.
    echo.
) else (
    echo All checks passed!
    echo.
)

echo ========================================
echo   Setup complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env and add your HACKCLUB_API_KEY
echo   2. Run: venv\Scripts\activate
echo   3. Run: python main.py
echo.
echo Optional modes:
echo   python main.py --type     Text input mode (no mic)
echo   python main.py --dry-run  Test without mic/wake word
echo   python main.py --no-tray  Terminal only (no tray icon)
echo.
echo To run diagnostics anytime: python -m core.diagnostics
echo.
pause
