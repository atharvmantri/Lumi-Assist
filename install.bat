@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ============================================================
:: Lumi - Windows installer
:: Creates an isolated Python 3.11 venv and never relies on global pip.
:: ============================================================

title Lumi Installer
color 0B
cd /d "%~dp0"
set "TARGET=%CD%"

echo.
echo  ========================================
echo    Lumi - Voice Assistant Installer
echo  ========================================
echo.

:: ------------------------------------------------------------
:: 1. Python 3.11
:: ------------------------------------------------------------
echo [1/8] Checking Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo  Python 3.11 was not found.
    where winget >nul 2>&1
    if errorlevel 1 (
        echo  [ERROR] Install Python 3.11 from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set /p "INSTALLPY=Install Python 3.11 with winget now? (y/n): "
    if /i not "!INSTALLPY!"=="y" (
        echo  Install Python 3.11 and re-run install.bat.
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements --scope user
    if errorlevel 1 (
        echo  [ERROR] Python installation failed.
        pause
        exit /b 1
    )
    echo  Python was installed. Re-run install.bat so the py launcher refreshes.
    pause
    exit /b 0
)
for /f "tokens=*" %%i in ('py -3.11 --version 2^>^&1') do echo  %%i

:: ------------------------------------------------------------
:: 2. Install location / source
:: ------------------------------------------------------------
echo.
echo [2/8] Install location
 echo  Current folder: %TARGET%
set "CUSTOMDIR="
set /p "CUSTOMDIR=Press Enter to use it, or type another folder: "
if defined CUSTOMDIR (
    if not exist "!CUSTOMDIR!" mkdir "!CUSTOMDIR!" 2>nul
    if errorlevel 1 (
        echo  [ERROR] Could not create "!CUSTOMDIR!".
        pause
        exit /b 1
    )
    set "TARGET=!CUSTOMDIR!"
)
cd /d "!TARGET!"

if exist ".git\" (
    echo  Updating existing repository...
    git pull --ff-only
    if errorlevel 1 (
        echo  [WARNING] git pull could not fast-forward. Continuing with the files already here.
    )
) else (
    :: If this installer is already being run from a downloaded source tree,
    :: main.py will exist even when .git metadata was omitted. Do not clone over it.
    if not exist "main.py" (
        echo  Cloning Lumi...
        git clone https://github.com/atharvmantri/Lumi-Assist.git .
        if errorlevel 1 (
            echo  [ERROR] Git clone failed. Check that Git and internet access are available.
            pause
            exit /b 1
        )
    ) else (
        echo  Using the source files already in this folder.
    )
)

:: ------------------------------------------------------------
:: 3. Isolated venv
:: ------------------------------------------------------------
echo.
echo [3/8] Creating Python 3.11 virtual environment...
if not exist "venv\Scripts\python.exe" (
    py -3.11 -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo  Existing venv found.
)
set "PY=!TARGET!\venv\Scripts\python.exe"
echo  Interpreter: !PY!

:: ------------------------------------------------------------
:: 4. Dependencies
:: ------------------------------------------------------------
echo.
echo [4/8] Installing required packages into Lumi's venv...
"!PY!" -m pip install --upgrade pip
if errorlevel 1 goto :pip_fail
"!PY!" -m pip install -r requirements.txt
if errorlevel 1 goto :pip_fail

:: Default to a reviewer-friendly CPU configuration. If NVIDIA is present and
:: the CUDA runtime wheels install correctly, enable GPU acceleration.
set "STT_DEVICE=cpu"
set "STT_COMPUTE=int8"
set "STT_MODEL=small"
where nvidia-smi >nul 2>&1
if not errorlevel 1 (
    echo  NVIDIA GPU detected. Installing optional CUDA runtime packages...
    "!PY!" -m pip install -r requirements-gpu.txt
    if errorlevel 1 (
        echo  [WARNING] CUDA extras failed; Lumi will use CPU STT instead.
    ) else (
        set "STT_DEVICE=cuda"
        set "STT_COMPUTE=float16"
        set "STT_MODEL=large-v3-turbo"
        echo  GPU acceleration enabled.
    )
) else (
    echo  No NVIDIA GPU detected; using CPU STT ^(small / int8^).
)

:: ------------------------------------------------------------
:: 5. Piper voice
:: ------------------------------------------------------------
echo.
echo [5/8] Preparing Piper TTS voice...
set "VOICE_DIR=models\piper"
if not exist "!VOICE_DIR!" mkdir "!VOICE_DIR!"
if exist "!VOICE_DIR!\en_GB-southern_english_female-low.onnx" if exist "!VOICE_DIR!\en_GB-southern_english_female-low.onnx.json" goto :voice_ready

"!PY!" -m pip install --quiet huggingface-hub
if errorlevel 1 (
    echo  [ERROR] Could not install huggingface-hub for the voice download.
    pause
    exit /b 1
)

"!PY!" -c "from huggingface_hub import hf_hub_download; from pathlib import Path; import shutil; d=Path(r'models\piper'); d.mkdir(parents=True,exist_ok=True); fs=['en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx','en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx.json']; [shutil.copy2(hf_hub_download('rhasspy/piper-voices',f,repo_type='model'), d/Path(f).name) for f in fs]"
if errorlevel 1 (
    echo  [ERROR] Piper voice download failed.
    echo  Check internet access, then re-run install.bat.
    pause
    exit /b 1
)

:voice_ready
echo  Voice files ready.

:: ------------------------------------------------------------
:: 6. LLM configuration
:: ------------------------------------------------------------
echo.
echo [6/8] LLM configuration
 echo  Choose an OpenAI-compatible provider:
 echo    1. HackClub AI ^(default^)
 echo    2. OpenRouter
 echo    3. OpenAI
 echo    4. Google Gemini ^(OpenAI-compatible endpoint^)
 echo    5. Custom OpenAI-compatible endpoint
set "PROVCHOICE=1"
set /p "PROVCHOICE=Choice [1]: "
if not defined PROVCHOICE set "PROVCHOICE=1"

set "PROVIDER_ID=hackclub"
set "API_ENV=HACKCLUB_API_KEY"
set "BASE_URL=https://ai.hackclub.com/proxy/v1"
set "DEF_MODEL=openrouter/free"

if "!PROVCHOICE!"=="2" (
    set "PROVIDER_ID=openrouter"
    set "API_ENV=OPENROUTER_API_KEY"
    set "BASE_URL=https://openrouter.ai/api/v1"
    set "DEF_MODEL=openrouter/auto"
)
if "!PROVCHOICE!"=="3" (
    set "PROVIDER_ID=openai"
    set "API_ENV=OPENAI_API_KEY"
    set "BASE_URL=https://api.openai.com/v1"
    set "DEF_MODEL=gpt-4o-mini"
)
if "!PROVCHOICE!"=="4" (
    set "PROVIDER_ID=google"
    set "API_ENV=GOOGLE_API_KEY"
    set "BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/"
    set "DEF_MODEL=gemini-2.5-flash"
)
if "!PROVCHOICE!"=="5" (
    set "PROVIDER_ID=custom"
    set "API_ENV=CUSTOM_API_KEY"
    set /p "BASE_URL=Base URL: "
    set /p "DEF_MODEL=Model name: "
)

set "MODELNAME="
set /p "MODELNAME=Model name [!DEF_MODEL!]: "
if not defined MODELNAME set "MODELNAME=!DEF_MODEL!"

set "APIKEY="
set /p "APIKEY=API key for !API_ENV!: "
if not defined APIKEY (
    echo  [ERROR] An API key is required for the LLM connection.
    pause
    exit /b 1
)

> ".env" echo !API_ENV!=!APIKEY!

:: Keep the repository's config.yaml pristine. Machine-specific choices go in
:: config.local.yaml and are deep-merged by core/config.py.
(
    echo # Generated by install.bat - safe to edit locally
    echo lumi:
    echo   wake_word: "hey lumi"
    echo   wake_word_sensitivity: 0.5
    echo stt:
    echo   model: "!STT_MODEL!"
    echo   device: "!STT_DEVICE!"
    echo   compute_type: "!STT_COMPUTE!"
    echo llm:
    echo   provider: "!PROVIDER_ID!"
    echo   api_key_env: "!API_ENV!"
    echo   model: "!MODELNAME!"
    echo   base_url: "!BASE_URL!"
) > "config.local.yaml"

:: ------------------------------------------------------------
:: 7. Local directories + diagnostics
:: ------------------------------------------------------------
echo.
echo [7/8] Running installation checks...
if not exist "data\conversations" mkdir "data\conversations"
if not exist "logs\learning" mkdir "logs\learning"
if not exist "logs\screenshots" mkdir "logs\screenshots"
if not exist "data\wake_samples" mkdir "data\wake_samples"

call repair_env.bat
if errorlevel 1 (
    echo  [ERROR] Core dependency preflight failed.
    pause
    exit /b 1
)

"!PY!" -m core.diagnostics
if errorlevel 1 (
    echo.
    echo  [WARNING] One or more hardware/runtime checks failed.
    echo  The detailed report above tells you exactly what still needs attention.
) else (
    echo  Diagnostics passed.
)

:: ------------------------------------------------------------
:: 8. Shortcut / done
:: ------------------------------------------------------------
echo.
echo [8/8] Finalizing...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Lumi.lnk')); $s.TargetPath='!TARGET!\launch.bat'; $s.WorkingDirectory='!TARGET!'; $s.Save()" >nul 2>&1

echo.
echo  ========================================
echo    Installation Complete
 echo  ========================================
echo.
echo  Location:   !TARGET!
echo  Wake word:  hey lumi
 echo  STT:        !STT_MODEL! on !STT_DEVICE! ^(!STT_COMPUTE!^)
echo  Provider:   !PROVIDER_ID!
echo  Model:      !MODELNAME!
echo.
echo  Reviewer/debug launch:
 echo    .\launch_voice.bat
 echo.
echo  Normal tray launch:
 echo    .\launch.bat
 echo.
echo  NOTE: package installs must use Lumi's venv, e.g.:
 echo    venv\Scripts\python.exe -m pip install PACKAGE
 echo  Global `pip install` may point at another Python and will not fix this venv.
echo.
pause
exit /b 0

:pip_fail
echo.
echo  [ERROR] Python dependency installation failed.
echo  Nothing is intentionally ignored here because missing core packages
 echo  ^(especially NumPy^) make Lumi unable to start.
echo.
echo  Retry manually with the exact project interpreter:
 echo    venv\Scripts\python.exe -m pip install -r requirements.txt
 echo.
pause
exit /b 1
