"""Lumi diagnostics — verify a Windows installation before launch.

Run:
    python -m core.diagnostics
"""
from __future__ import annotations

import importlib
import sys
import time
from typing import Any, Callable

from core.config import PROJECT_ROOT, load_config

CheckResult = tuple[str, bool, str]


def _check(name: str, fn: Callable[[], Any]) -> CheckResult:
    """Run one diagnostic and preserve an explicit (name, ok, detail) result.

    Older versions accidentally wrapped every returned tuple as a successful
    result, so even missing packages / API keys appeared green. This helper is
    deliberately strict so failures actually propagate to the final exit code.
    """
    try:
        result = fn()
        if isinstance(result, tuple) and len(result) == 3:
            result_name, ok, detail = result
            return str(result_name), bool(ok), str(detail)
        return name, True, str(result)
    except Exception as exc:  # noqa: BLE001
        return name, False, f"{type(exc).__name__}: {exc}"


def _check_python() -> CheckResult:
    v = sys.version_info
    ok = v.major == 3 and v.minor == 11
    detail = "OK" if ok else "Lumi's supported runtime is Python 3.11"
    return f"Python {v.major}.{v.minor}.{v.micro}", ok, detail


def _check_config() -> CheckResult:
    cfg = load_config()
    required_sections = ("lumi", "stt", "llm", "tts")
    missing = [name for name in required_sections if not isinstance(cfg.get(name), dict)]
    if missing:
        return "config.yaml", False, f"missing section(s): {', '.join(missing)}"

    required_paths = (
        ("lumi", "wake_word"),
        ("stt", "model"),
        ("stt", "device"),
        ("stt", "compute_type"),
        ("llm", "api_key_env"),
        ("llm", "model"),
        ("llm", "base_url"),
        ("tts", "voice"),
    )
    missing_keys = [f"{section}.{key}" for section, key in required_paths if key not in cfg[section]]
    if missing_keys:
        return "config.yaml", False, f"missing key(s): {', '.join(missing_keys)}"

    return "config.yaml", True, (
        f"wake='{cfg['lumi']['wake_word']}', "
        f"stt={cfg['stt']['model']}@{cfg['stt']['device']}, "
        f"llm={cfg['llm']['model']}"
    )


def _check_env() -> CheckResult:
    from core.config import ENV_PATH, get_env

    if not ENV_PATH.exists():
        return ".env", False, "file not found — run install.bat or copy .env.example"
    cfg = load_config()
    key_name = cfg["llm"]["api_key_env"]
    value = get_env(key_name, required=False)
    if not value:
        return ".env", False, f"{key_name} is empty"
    masked = value[:4] + "..." + value[-4:] if len(value) >= 10 else "(set)"
    return ".env", True, f"{key_name}={masked}"


def _check_packages() -> CheckResult:
    packages = (
        ("openai", "openai"),
        ("numpy", "numpy"),
        ("sounddevice", "sounddevice"),
        ("PyQt6", "PyQt6"),
        ("PyYAML", "yaml"),
        ("python-dotenv", "dotenv"),
        ("faster-whisper", "faster_whisper"),
        ("piper-tts", "piper"),
    )
    missing: list[str] = []
    for package_name, import_name in packages:
        try:
            importlib.import_module(import_name)
        except Exception:  # import can fail because a native dependency is broken
            missing.append(package_name)

    if missing:
        return "pip packages", False, (
            "missing/broken: " + ", ".join(missing) +
            "; repair with venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )

    import numpy as np
    return "pip packages", True, f"core imports OK; NumPy {np.__version__}; {sys.executable}"


def _check_piper_voice() -> CheckResult:
    cfg = load_config()
    voice = cfg["tts"]["voice"]
    models_dir = PROJECT_ROOT / "models" / "piper"
    model_path = models_dir / f"{voice}.onnx"
    config_path = models_dir / f"{voice}.onnx.json"
    missing = [p.name for p in (model_path, config_path) if not p.exists()]
    if missing:
        return f"Piper voice ({voice})", False, f"missing: {', '.join(missing)}"
    size_mb = model_path.stat().st_size / (1024 * 1024)
    return f"Piper voice ({voice})", True, f"model + config present ({size_mb:.0f} MB model)"


def _check_whisper() -> CheckResult:
    """Whisper is allowed to download lazily on first launch."""
    cfg = load_config()
    model_name = cfg["stt"]["model"]
    snapshot = PROJECT_ROOT / "models" / "whisper" / f"Systran--faster-whisper-{model_name}"
    if snapshot.is_dir():
        return f"Whisper ({model_name})", True, f"cached at {snapshot.name}"
    return f"Whisper ({model_name})", True, "not cached yet — will download automatically on first run"


def _check_audio_devices() -> CheckResult:
    import sounddevice as sd

    devices = sd.query_devices()
    inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
    outputs = [d for d in devices if d.get("max_output_channels", 0) > 0]
    if not inputs or not outputs:
        return "audio devices", False, f"{len(inputs)} input(s), {len(outputs)} output(s)"
    default_in, default_out = sd.default.device
    return "audio devices", True, (
        f"{len(inputs)} input(s), {len(outputs)} output(s); "
        f"default in=#{default_in}, out=#{default_out}"
    )


def _check_screen() -> CheckResult:
    from PIL import ImageGrab

    image = ImageGrab.grab()
    return "screen capture", True, f"{image.size[0]}x{image.size[1]}"


def _check_overlay() -> CheckResult:
    from PyQt6.QtWidgets import QApplication
    from ui.overlay import DesktopOverlay

    app = QApplication.instance() or QApplication([])
    overlay = DesktopOverlay()
    overlay.hide()
    detail = f"{overlay.width()}x{overlay.height()}, initialized"
    overlay.deleteLater()
    return "overlay (Qt)", True, detail


def run_checks() -> list[CheckResult]:
    checks: list[tuple[str, Callable[[], Any]]] = [
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
    return [_check(name, fn) for name, fn in checks]


def main() -> None:
    print("Lumi Diagnostics")
    print("=" * 70)

    started = time.perf_counter()
    results = run_checks()
    elapsed = time.perf_counter() - started

    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print("=" * 70)
    print(f"  {passed}/{len(results)} checks passed, {failed} failed ({elapsed:.1f}s)")

    if failed:
        print("  Fix the failed checks before re-certification/testing.")
        raise SystemExit(1)
    print("  All systems ready.")


if __name__ == "__main__":
    main()
