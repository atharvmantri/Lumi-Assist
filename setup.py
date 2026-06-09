"""JARVIS setup wizard — interactive first-run installer.

Run:  python setup.py

Checks Python 3.11, creates venv, installs deps, downloads models,
prompts for HackClub API key, and runs smoke tests.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / "venv" / "Scripts" / "python.exe"


def run(cmd: list[str], label: str = "") -> bool:
    """Run a command and return True on success."""
    if label:
        print(f"  >> {label}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  FAILED: {' '.join(cmd)}")
        if proc.stderr:
            print(f"  {proc.stderr.strip()[:300]}")
        return False
    return True


def main() -> int:
    print("=" * 50)
    print("  JARVIS Setup Wizard")
    print("=" * 50)
    print()

    # 1. Python 3.11
    print("[1/6] Checking Python 3.11...")
    result = subprocess.run(["py", "-3.11", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print("  Python 3.11 not found. Installing via winget...")
        if not run(
            ["winget", "install", "--id", "Python.Python.3.11", "--silent",
             "--accept-source-agreements", "--accept-package-agreements", "--scope", "user"],
            "Installing Python 3.11",
        ):
            print("  Please install Python 3.11 manually from python.org")
            return 1
        print("  Python 3.11 installed.")
    else:
        print(f"  {result.stdout.strip()}")

    # 2. Virtual environment
    print("\n[2/6] Creating virtual environment...")
    if not (ROOT / "venv").exists():
        if not run(["py", "-3.11", "-m", "venv", "venv"], "Creating venv"):
            return 1
        print("  venv created.")
    else:
        print("  venv already exists, skipping.")

    # 3. Dependencies
    print("\n[3/6] Installing Python packages...")
    if not run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], "Installing requirements"):
        return 1
    print("  Installing torch with CUDA 12.1...")
    if not run(
        [str(VENV_PYTHON), "-m", "pip", "install", "torch",
         "--index-url", "https://download.pytorch.org/whl/cu121"],
        "Installing torch",
    ):
        print("  WARNING: torch install may have failed. JARVIS will still work without GPU STT.")

    # 4. Model downloads
    print("\n[4/6] Downloading model weights...")
    whisper_dir = ROOT / "models" / "whisper"
    whisper_dir.mkdir(parents=True, exist_ok=True)

    print("  Downloading Whisper large-v3 (~3 GB)...")
    if not run(
        [str(VENV_PYTHON), "-c",
         "from faster_whisper import WhisperModel; "
         "WhisperModel('large-v3', device='cuda', compute_type='float16', "
         "download_root='models/whisper')"],
        "Downloading Whisper",
    ):
        print("  WARNING: Whisper download failed. You can retry later.")

    print("  Downloading Piper voice...")
    piper_dir = ROOT / "models" / "piper"
    piper_dir.mkdir(parents=True, exist_ok=True)
    voice_base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/southern_english_female/low"
    for name in ("en_GB-southern_english_female-low.onnx", "en_GB-southern_english_female-low.onnx.json"):
        dest = piper_dir / name
        if not dest.exists():
            try:
                urllib.request.urlretrieve(f"{voice_base}/{name}", dest)
                print(f"  Downloaded {name} ({dest.stat().st_size // 1024} KB)")
            except Exception as e:
                print(f"  WARNING: Failed to download {name}: {e}")
        else:
            print(f"  {name} already exists, skipping.")

    # 5. API key
    print("\n[5/6] Setting up API key...")
    env_path = ROOT / ".env"
    if not env_path.exists():
        api_key = input("  Enter your HackClub AI API key: ").strip()
        env_path.write_text(f"HACKCLUB_API_KEY={api_key}\n", encoding="utf-8")
        print("  API key saved to .env.")
    else:
        print("  .env already exists, skipping.")

    # 6. Smoke test
    print("\n[6/6] Running smoke tests...")
    print("  Testing LLM connection...")
    result = subprocess.run(
        [str(VENV_PYTHON), "-m", "core.llm", "--smoke-test"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("  LLM smoke test FAILED. Check your API key in .env.")
        print(result.stdout[-500:] if result.stdout else result.stderr[-500:])
        return 1
    print("  LLM smoke test passed.")

    print()
    print("=" * 50)
    print("  Setup complete!")
    print("=" * 50)
    print()
    print("Run JARVIS with:")
    print("  python main.py            # Full voice loop")
    print("  python main.py --type     # Text input mode")
    print("  python main.py --dry-run  # One-shot test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
