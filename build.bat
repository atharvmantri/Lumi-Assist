@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Lumi - Build standalone Windows .exe
:: Run: build.bat
:: ============================================================

echo.
echo ========================================
echo   Lumi - Building Windows App
echo ========================================
echo.

cd /d "%~dp0"

:: Check venv
if not exist venv\Scripts\python.exe (
    echo ERROR: venv not found. Run install.ps1 or setup.bat first.
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller...
venv\Scripts\python.exe -m pip install --quiet pyinstaller
if %errorlevel% neq 0 (
    echo ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)
echo Done.
echo.

echo [2/3] Building Lumi.exe with PyInstaller...
echo This takes 1-2 minutes...
echo.

venv\Scripts\python.exe -m PyInstaller ^
    --name "Lumi" ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --icon=NONE ^
    --add-data "config.yaml;." ^
    --add-data "prompts;prompts" ^
    --add-data "tools;tools" ^
    --add-data "ui;ui" ^
    --add-data "core;core" ^
    --add-data "requirements.txt;." ^
    --hidden-import=openai ^
    --hidden-import=faster_whisper ^
    --hidden-import=piper ^
    --hidden-import=openwakeword ^
    --hidden-import=PyQt6 ^
    --hidden-import=sounddevice ^
    --hidden-import=numpy ^
    --hidden-import=psutil ^
    --hidden-import=pyperclip ^
    --hidden-import=PIL ^
    --hidden-import=win10toast ^
    --hidden-import=pywinauto ^
    --hidden-import=pyautogui ^
    --hidden-import=comtypes ^
    --hidden-import=pycaw ^
    --hidden-import=win32api ^
    --hidden-import=win32con ^
    --hidden-import=win32gui ^
    --hidden-import=scipy.signal ^
    --hidden-import=scipy ^
    --hidden-import=duckduckgo_search ^
    --hidden-import=ddgs ^
    --hidden-import=yaml ^
    --hidden-import=dotenv ^
    --hidden-import=requests ^
    --hidden-import=wave ^
    --hidden-import=urllib ^
    --hidden-import=ctypes ^
    --hidden-import=json ^
    --hidden-import=re ^
    --hidden-import=queue ^
    --hidden-import=threading ^
    --hidden-import=dataclasses ^
    --hidden-import=enum ^
    --hidden-import=math ^
    --hidden-import=hashlib ^
    --hidden-import=subprocess ^
    --hidden-import=shutil ^
    --hidden-import=socket ^
    --hidden-import=csv ^
    --hidden-import=difflib ^
    --hidden-import=textwrap ^
    --hidden-import=colorsys ^
    --hidden-import=secrets ^
    --hidden-import=string ^
    --hidden-import=calendar ^
    --hidden-import=locale ^
    --hidden-import=ast ^
    --hidden-import=operator ^
    --hidden-import=time ^
    --hidden-import=io ^
    --hidden-import=platform ^
    --hidden-import=os ^
    --hidden-import=pathlib ^
    --hidden-import=signal ^
    --hidden-import=argparse ^
    --hidden-import=typing ^
    --hidden-import=xml ^
    --hidden-import=xml.etree ^
    --hidden-import=winreg ^
    --hidden-import=smtplib ^
    --hidden-import=email.mime.text ^
    --hidden-import=email.mime.multipart ^
    --hidden-import=wave ^
    --hidden-import=ntsecuritycon ^
    --hidden-import=win32security ^
    --hidden-import=win32com.client ^
    --hidden-import=win32com ^
    --hidden-import=piper ^
    --collect-all openwakeword ^
    --collect-all faster_whisper ^
    --collect-all piper-tts ^
    main.py

if %errorlevel% neq 0 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)
echo.
echo Done.
echo.

:: Copy config and CUDA DLLs
echo [3/3] Copying runtime files...
set "DLL_SRC=venv\Lib\site-packages"
if exist "!DLL_SRC!\nvidia\cublas\bin\" (
    copy /Y "!DLL_SRC!\nvidia\cublas\bin\*.dll" dist\Lumi\ >nul 2>&1
    copy /Y "!DLL_SRC!\nvidia\cudnn\bin\*.dll" dist\Lumi\ >nul 2>&1
    copy /Y "!DLL_SRC!\nvidia\cuda_nvrtc\bin\*.dll" dist\Lumi\ >nul 2>&1
    echo CUDA DLLs copied.
) else (
    echo WARNING: CUDA packages not found. Lumi will use CPU for STT.
)
copy /Y config.yaml dist\Lumi\ >nul 2>&1
if exist .env copy /Y .env dist\Lumi\ >nul 2>&1

echo.
echo ========================================
echo   Lumi.exe built successfully!
echo ========================================
echo.
echo  Location: dist\Lumi\Lumi.exe
echo.
echo  To run:   dist\Lumi\Lumi.exe
echo  To test:  dist\Lumi\Lumi.exe --dry-run
echo.
echo  To distribute: copy the entire dist\Lumi\ folder
echo  (including _internal\, models\, data\, logs\, .env)
echo.
pause
