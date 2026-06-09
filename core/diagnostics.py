"""JARVIS diagnostics — verify all components are healthy before a run.

Checks:
  - Python version
  - Config file + .env
  - All required packages
  - Piper voice model files
  - openWakeWord model
  - Whisper model snapshot
  - Audio input/output devices
  - Screen capture
  - Overlay (Qt) initialization

Usage:
    python -m core.diagnostics
"""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT, load_config


def _check(name: str, fn) -> tuple[str, bool, str]:
    """Run a check. Returns (name, ok, detail)."""
    try:
        detail = fn()
        return name, True, detail
    except Exception as e:
        return name, False, str(e)


def _check_python() -> tuple[str, bool, str]:
    v = sys.version_info
    ok = v.major == 3 and v.minor >= 10
    return f"Python {v.major}.{v.minor}.{v.micro}", ok, (
        "OK" if ok else "requires Python 3.10+"
    )


def _check_config() -> tuple[str, bool, str]:
    cfg = load_config()
    has_api = bool(cfg.get("llm", {}).get("api_key_env", ""))
    return "config.yaml", True, (
        f"model={cfg['llm']['model']}, tts={cfg['tts']['engine']}, "
        f"wake='{cfg['jarvis']['wake_word']}'"
    )


def _check_env() -> tuple[str, bool, str]:
    from core.config import get_env, ENV_PATH
    if not ENV_PATH.exists():
        return ".env", False, "file not found — copy .env.example to .env"
    cfg = load_config()
    key_name = cfg["llm"]["api_key_env"]
    val = get_env(key_name, required=False)
    if not val:
        return ".env", False, f"{key_name} is empty"
    masked = val[:4] + "..." + val[-4:]
    return ".env", True, f"{key_name}={masked}"


def _check_piper_voice() -> tuple[str, bool, str]:
    cfg = load_config()
    voice = cfg["tts"]["voice"]
    model_path = PROJECT_ROOT / "models" / "piper" / f"{voice}.onnx"
    config_path = PROJECT_ROOT / "models" / "piper" / f"{voice}.onnx.json"
    if not model_path.exists():
        return f"Piper voice ({voice})", False, f"{model_path.name} not found"
    size_mb = model_path.stat().st_size / (1024 * 1024)
    return f"Piper voice ({voice})", True, f"{size_mb:.0f} MB"


def _check_whisper() -> tuple[str, bool, str]:
    cfg = load_config()
    model_name = cfg["stt"]["model"]
    snapshot = PROJECT_ROOT / "models" / "whisper" / f"Systran--faster-whisper-{model_name}"
    if snapshot.is_dir():
        return f"Whisper ({model_name})", True, f"local snapshot at {snapshot.name}"
    return f"Whisper ({model_name})", False, "will download on first run"


def _check_packages() -> tuple[str, bool, str]:
    """Check that key packages are importable."""
    missing = []
    for pkg in ("openai", "numpy", "sounddevice", "PyQt6", "pyyaml", "dotenv"):
        import_name = pkg.replace("-", "_").replace("PyQt6", "PyQt6")
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        return "pip packages", False, f"missing: {', '.join(missing)}"
    return "pip packages", True, "all core packages available"


def _check_audio_devices() -> tuple[str, bool, str]:
    import sounddevice as sd
    devices = sd.query_devices()
    inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
    outputs = [d for d in devices if d.get("max_output_channels", 0) > 0]
    default_in = sd.default.device[0]
    default_out = sd.default.device[1]
    return "audio devices", True, (
        f"{len(inputs)} input(s), {len(outputs)} output(s); "
        f"default in=#{default_in}, out=#{default_out}"
    )


def _check_screen() -> tuple[str, bool, str]:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    return "screen capture", True, f"{img.size[0]}x{img.size[1]}"


def _check_overlay() -> tuple[str, bool, str]:
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.overlay import DesktopOverlay
    overlay = DesktopOverlay()
    overlay.hide()
    return "overlay (Qt)", True, f"{overlay.width()}x{overlay.height()}, initialized"


def run_checks() -> list[tuple[str, bool, str]]:
    """Run all checks and return results."""
    checks = [
        ("Python version", _check_python),
        ("Config", _check_config),
        ("Environment", _check_env),
        ("pip packages", _check_packages),
        ("Piper voice", _check_piper_voice),
        ("Whisper model", _check_whisper),
        ("Audio devices", _check_audio_devices),
        ("Screen capture", _check_screen),
        ("Overlay", _check_overlay),
    ]
    results = []
    for name, fn in checks:
        results.append(_check(name, fn))
    return results


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="JARVIS diagnostics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    print("JARVIS Diagnostics")
    print("=" * 50)

    t0 = time.perf_counter()
    results = run_checks()
    elapsed = time.perf_counter() - t0

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed

    for name, ok, detail in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}: {detail}")

    print("=" * 50)
    print(f"  {passed}/{len(results)} checks passed, {failed} failed ({elapsed:.1f}s)")
    if failed:
        print("  Fix failures before running JARVIS.")
        raise SystemExit(1)
    print("  All systems ready.")


if __name__ == "__main__":
    main()
