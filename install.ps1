<#
  Lumi - One-line installer
  Usage: irm https://raw.githubusercontent.com/atharvmantri/Lumi-Assist/main/install.ps1 | iex

  Does everything end-to-end:
  1. Installs Python 3.11 via winget (if missing)
  2. Clones the Lumi-Assist repo
  3. Creates a virtual environment
  4. Installs all dependencies
  5. Downloads the Piper TTS voice model
  6. Collects your API key interactively
  7. Runs diagnostics
  8. Creates a desktop shortcut for one-click launch
#>

$ErrorActionPreference = "Stop"

# --- Colors ---
function Write-Status  { param($m) Write-Host "[*] $m" -ForegroundColor Cyan }
function Write-Ok      { param($m) Write-Host "[OK] $m" -ForegroundColor Green }
function Write-Err     { param($m) Write-Host "[ERR] $m" -ForegroundColor Red }
function Write-Prompt  { param($m) Write-Host " > $m" -ForegroundColor Yellow }

# ============================
# Banner
# ============================
Write-Host ""
Write-Host "  __    _       _       " -ForegroundColor Magenta
Write-Host " |  |  |_|___ _| |_ ___ " -ForegroundColor Magenta
Write-Host " |  |__| |   | . | -_|  " -ForegroundColor Magenta
Write-Host " |_____|_|_|_|___|___|  " -ForegroundColor Magenta
Write-Host ""
Write-Host "  Lumi - Voice Assistant Installer" -ForegroundColor White
Write-Host "  https://github.com/atharvmantri/Lumi-Assist" -ForegroundColor DarkGray
Write-Host ""

# ============================
# Step 1 - Python
# ============================
Write-Status "Checking Python 3.11..."
$py = Get-Command py -ErrorAction SilentlyContinue
$has311 = $false
if ($py) {
    $ver = & py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $has311 = $true
        Write-Ok "Found: $ver"
    }
}
if (-not $has311) {
    Write-Prompt "Python 3.11 not found. Installing via winget..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Err "winget not available. Install Python 3.11 manually from python.org, then re-run this installer."
        exit 1
    }
    & winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements --scope user
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Python installation failed."
        exit 1
    }
    # Refresh PATH in this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Ok "Python 3.11 installed."
}

# ============================
# Step 2 - Clone repo
# ============================
$installDir = Join-Path $env:USERPROFILE "Lumi"
if (Test-Path $installDir) {
    Write-Status "Lumi already installed at $installDir - updating..."
    Set-Location $installDir
    git pull --quiet 2>$null
} else {
    Write-Status "Cloning Lumi-Assist..."
    git clone --quiet https://github.com/atharvmantri/Lumi-Assist.git $installDir
    Set-Location $installDir
    Write-Ok "Cloned to $installDir"
}

# ============================
# Step 3 - Virtual environment
# ============================
$venvPy = Join-Path $installDir "venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Status "Creating virtual environment..."
    & py -3.11 -m venv venv
    Write-Ok "venv created."
} else {
    Write-Ok "venv already exists."
}

# ============================
# Step 4 - Install dependencies
# ============================
Write-Status "Installing Python packages..."
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Err "Some packages failed to install (often CUDA-related). Lumi will still work on CPU."
}
Write-Ok "Dependencies installed."

# ============================
# Step 5 - Download Piper voice
# ============================
$voiceDir = Join-Path $installDir "models\piper"
$voiceOnnx = Join-Path $voiceDir "en_GB-southern_english_female-low.onnx"
if (-not (Test-Path $voiceOnnx)) {
    Write-Status "Downloading Piper TTS voice model (~40 MB)..."
    New-Item -ItemType Directory -Force -Path $voiceDir | Out-Null
    & $venvPy -m pip install --quiet huggingface-hub
    & $venvPy -c "from huggingface_hub import hf_hub_download; hf_hub_download('rhassys/piper-voices', 'en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx', local_dir='$voiceDir', repo_type='model')"
    & $venvPy -c "from huggingface_hub import hf_hub_download; hf_hub_download('rhassys/piper-voices', 'en/en_GB/southern_english_female/low/en_GB-southern_english_female-low.onnx.json', local_dir='$voiceDir', repo_type='model')"
    Write-Ok "Voice model downloaded."
} else {
    Write-Ok "Voice model already present."
}

# ============================
# Step 6 - Directories
# ============================
Write-Status "Creating data directories..."
$subdirs = @("data\conversations", "logs\learning", "logs\screenshots")
foreach ($sd in $subdirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $installDir $sd) | Out-Null
}

# ============================
# Step 7 - API key
# ============================
$envPath = Join-Path $installDir ".env"
$hasKey = $false
if (Test-Path $envPath) {
    $content = Get-Content $envPath -Raw
    if ($content -match "HACKCLUB_API_KEY=sk-") {
        $hasKey = $true
    }
}
if (-not $hasKey) {
    Write-Host ""
    Write-Prompt "Enter your HackClub API key (get one at https://hackclub.com/):"
    $key = Read-Host "API Key"
    if (-not $key -or $key -eq "your_key_here") {
        Write-Err "No valid API key provided. You must edit .env manually later."
    } else {
        "HACKCLUB_API_KEY=$key" | Out-File -FilePath $envPath -Encoding utf8 -Force
        Write-Ok "API key saved to .env"
    }
} else {
    Write-Ok ".env already has an API key."
}

# ============================
# Step 8 - Diagnostics
# ============================
Write-Host ""
Write-Status "Running diagnostics..."
$diag = & $venvPy -m core.diagnostics 2>&1
Write-Host $diag -ForegroundColor DarkGray
if ($LASTEXITCODE -ne 0) {
    Write-Err "Some diagnostics failed. Review the output above."
} else {
    Write-Ok "All checks passed."
}

# ============================
# Step 9 - Desktop shortcut
# ============================
Write-Status "Creating desktop shortcut..."
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Lumi.lnk"
if (Test-Path $shortcutPath) { Remove-Item $shortcutPath -Force }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "cmd.exe"
$shortcut.Arguments = "/c `"$venvPy`" main.py"
$shortcut.WorkingDirectory = $installDir
$shortcut.WindowStyle = 1
$shortcut.Save()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($shell) | Out-Null
Write-Ok "Shortcut created on desktop: Lumi.lnk"

# ============================
# Done
# ============================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Lumi is ready!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Launch:" -ForegroundColor White
Write-Host "    Double-click the Lumi icon on your desktop" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Or from terminal:" -ForegroundColor White
Write-Host "    cd $installDir" -ForegroundColor DarkGray
Write-Host "    venv\Scripts\activate" -ForegroundColor DarkGray
Write-Host "    python main.py" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Modes:" -ForegroundColor White
Write-Host "    python main.py --type     Text input (no mic)" -ForegroundColor DarkGray
Write-Host "    python main.py --dry-run  Single test turn" -ForegroundColor DarkGray
Write-Host "    python main.py --no-tray  Terminal only" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Re-run installer anytime:" -ForegroundColor White
Write-Host "    irm https://raw.githubusercontent.com/atharvmantri/Lumi-Assist/main/install.ps1 | iex" -ForegroundColor Yellow
Write-Host ""
