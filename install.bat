@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Lumi - Installer
:: Run: install.bat
:: ============================================================

title Lumi Installer
color 0B

echo.
echo  ========================================
echo    Lumi - Voice Assistant Installer
echo  ========================================
echo.

cd /d "%~dp0"
set "TARGET=%cd%"

:: Step 1 - Check Python
echo [1/9] Checking Python 3.11...
py -3.11 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  Python 3.11 not found.
    echo  Would you like to install it now? (y/n)
    set /p installpy=
    if /i "!installpy!"=="y" (
        echo  Installing Python 3.11 via winget...
        winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements --scope user
        if !errorlevel! neq 0 (
            echo  [ERROR] Installation failed. Please install Python 3.11 manually:
            echo    https://www.python.org/downloads/
            pause
            exit /b 1
        )
        echo  Done. Please re-run install.bat.
        pause
        exit /b 0
    ) else (
        echo  Install Python 3.11 from https://www.python.org/downloads/ and re-run.
        pause
        exit /b 1
    )
)
for /f "tokens=*" %%i in ('py -3.11 --version 2^>^&1') do echo  %%i

:: Step 2 - Install directory
echo.
echo [2/9] Install location:
echo  %TARGET%
echo.
echo  Press Enter to use this folder, or type a different path:
set /p customdir=
if not "!customdir!"=="" (
    if not exist "!customdir!" mkdir "!customdir!" 2>nul
    set "TARGET=!customdir!"
)

cd /d "!TARGET!"

:: Step 3 - Clone or update
echo.
echo [3/9] Getting Lumi source...
if exist ".git" (
    echo  Updating existing installation...
    git pull --quiet
) else (
    echo  Cloning repository...
    git clone --quiet https://github.com/atharvmantri/Lumi-Assist.git .
)
if %errorlevel% neq 0 (
    echo  [ERROR] Git operation failed. Make sure git is installed.
    pause
    exit /b 1
)
echo  Done.

:: Step 4 - Virtual environment
echo.
echo [4/9] Creating virtual environment...
if not exist "venv\" (
    py -3.11 -m venv venv
    echo  Done.
) else (
    echo  Already exists.
)

:: Step 5 - Install dependencies
echo.
echo [5/9] Installing Python packages ^(this takes a few minutes^)...
call venv\Scripts\activate.bat
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  [WARNING] Some packages failed. Lumi will still work on CPU.
)
echo  Done.

:: Step 6 - Download voice model
echo.
echo [6/9] Downloading Piper TTS voice model...
set "VOICE_DIR=models\piper"
if not exist "%VOICE_DIR%" mkdir "%VOICE_DIR%"
if exist "%VOICE_DIR%\en_GB-southern_english_female-low.onnx" (
    echo  Already downloaded.
) else (
    echo  Downloading ^(about 40 MB^)...
    py -m pip install --quiet huggingface-hub
    py -c "from huggingface_hub import hf_hub_download; hf_hub_download('rhassys/piper-voices', 'en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx', local_dir='%VOICE_DIR%', repo_type='model')"
    py -c "from huggingface_hub import hf_hub_download; hf_hub_download('rhassys/piper-voices', 'en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx.json', local_dir='%VOICE_DIR%', repo_type='model')"
    echo  Done.
)

:: Step 7 - Configuration
echo.
echo [7/9] Configuration
echo.

if not exist ".env" (
    echo  Enter your LLM API key:
    set /p apikey=
) else (
    for /f "tokens=2 delims==" %%a in ('findstr "HACKCLUB_API_KEY" .env 2^>nul') do set "apikey=%%a"
    if "!apikey!"=="" (
        echo  Enter your LLM API key:
        set /p apikey=
    ) else (
        echo  Found existing API key: !apikey:~0,8!...
    )
)

echo.
echo  Choose provider:
echo    1. HackClub (free)
echo    2. OpenRouter
echo    3. OpenAI
echo    4. Anthropic (Claude)
echo    5. Google (Gemini)
echo    6. Custom
set /p provchoice=

set "PROVIDER=HackClub (Free)"
set "API_ENV=HACKCLUB_API_KEY"
set "BASE_URL=https://ai.hackclub.com/proxy/v1"
set "DEF_MODEL=openrouter/free"

if "!provchoice!"=="2" (
    set "PROVIDER=OpenRouter"
    set "API_ENV=OPENROUTER_API_KEY"
    set "BASE_URL=https://openrouter.ai/api/v1"
    set "DEF_MODEL=openrouter/auto"
)
if "!provchoice!"=="3" (
    set "PROVIDER=OpenAI"
    set "API_ENV=OPENAI_API_KEY"
    set "BASE_URL=https://api.openai.com/v1"
    set "DEF_MODEL=gpt-4o"
)
if "!provchoice!"=="4" (
    set "PROVIDER=Anthropic (Claude)"
    set "API_ENV=ANTHROPIC_API_KEY"
    set "BASE_URL=https://api.anthropic.com/v1"
    set "DEF_MODEL=claude-sonnet-4-6"
)
if "!provchoice!"=="5" (
    set "PROVIDER=Google (Gemini)"
    set "API_ENV=GOOGLE_API_KEY"
    set "BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/"
    set "DEF_MODEL=gemini-2.5-flash"
)
if "!provchoice!"=="6" (
    set "PROVIDER=Custom"
    set "API_ENV=CUSTOM_API_KEY"
    echo  Enter base URL:
    set /p BASE_URL=
    echo  Enter model name:
    set /p DEF_MODEL=
)

echo.
echo  Enter model name (or press Enter for default: !DEF_MODEL!):
set /p modelname=
if "!modelname!"=="" set "modelname=!DEF_MODEL!"

:: Save config
set "PROVIDER_CLEAN=!PROVIDER!"
set "PROVIDER_CLEAN=!PROVIDER_CLEAN: (=!"
set "PROVIDER_CLEAN=!PROVIDER_CLEAN:)=!"
set "PROVIDER_CLEAN=!PROVIDER_CLEAN: =_!"
set "PROVIDER_CLEAN=!PROVIDER_CLEAN:,=!"
set "PROVIDER_CLEAN=!PROVIDER_CLEAN:.=!"

echo lumi:
echo   wake_word: "hey lumi"
echo   wake_word_sensitivity: 0.5 > config.yaml
echo.
echo stt:
echo   model: "large-v3"
echo   device: "cuda"
echo   compute_type: "float16"
echo   silence_threshold_ms: 1500
echo   language: null >> config.yaml
echo.
echo llm:
echo   provider: "!PROVIDER_CLEAN!"
echo   api_key_env: "!API_ENV!"
echo   model: "!modelname!"
echo   base_url: "!BASE_URL!"
echo   max_tokens: 2048
echo   temperature: 0.7
echo   system_prompt_path: "prompts/system.md"
echo   history_turns: 20 >> config.yaml
echo.
echo tts:
echo   engine: "piper"
echo   voice: "en_GB-southern_english_female-low"
echo   device: "cpu"
echo   speed: 1.0 >> config.yaml
echo.
echo ui:
echo   theme: "dark"
echo   opacity: 0.88
echo   always_on_top: true
echo   show_transcript: true
echo   window_position: [80, 80] >> config.yaml
echo.
echo audio:
echo   input_device: "default"
echo   output_device: "default"
echo   sample_rate: 16000 >> config.yaml

:: Save API key
echo !API_ENV!=!apikey! > .env

:: Create directories
if not exist "data\conversations" mkdir "data\conversations"
if not exist "logs\learning" mkdir "logs\learning"
if not exist "logs\screenshots" mkdir "logs\screenshots"
if not exist "data\wake_samples" mkdir "data\wake_samples"

:: Step 8 - Wake word training option
echo.
echo [8/9] Wake Word Detection
echo.
echo  Lumi detects: "hey lumi", "ok lumi", "yo lumi", "lumi"
echo  Works immediately with energy-based detection.
echo.
echo  For better accuracy, train a custom model using your voice.
echo  This requires recording samples and running training.
echo.
echo  Would you like to set up wake word training now? (y/n)
set /p trainwake=
if /i "!trainwake!"=="y" (
    echo.
    echo  Installing training dependencies...
    pip install --quiet livekit-wakeword[listener]
    echo.
    echo  Starting voice recorder...
    echo  Say each phrase naturally when prompted.
    echo.
    pause
    py record_wake_samples.py
    if exist "data\wake_samples\positive" (
        echo.
        echo  Training custom model...
        echo  This may take 10-30 minutes depending on your hardware.
        echo.
        pip install --quiet livekit-wakeword[train,eval,export]
        livekit-wakeword run configs/lumi.yaml
        echo.
        echo  Custom wake word model trained and saved!
    ) else (
        echo.
        echo  No samples recorded. Using energy-based detection.
    )
) else (
    echo  Using energy-based detection.
    echo  Train a custom model later:
    echo    1. python record_wake_samples.py
    echo    2. pip install livekit-wakeword[train,eval,export]
    echo    3. livekit-wakeword run configs/lumi.yaml
)

:: Step 9 - Done
echo.
echo [9/9] Finalizing...

echo.
echo  ========================================
echo    Installation Complete!
echo  ========================================
echo.
echo  Provider:  !PROVIDER!
echo  Model:     !modelname!
echo  Voice:     British Female (Southern)
echo  Wake Word: hey lumi (or ok lumi, yo lumi, lumi)
echo  Location:  !TARGET!
echo.
echo  To start Lumi, double-click launch.bat
echo  (No terminal window will appear)
echo.
echo  For voice input mode:
echo    Double-click launch_voice.bat
echo.
pause
