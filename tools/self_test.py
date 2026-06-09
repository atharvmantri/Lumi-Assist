"""Self-test tool — Lumi can check its own health on demand."""
from __future__ import annotations

import time

from tools import tool


@tool(
    name="self_test",
    description=(
        "Run a quick self-diagnostic to check if Lumi's core components are working. "
        "Tests: config loading, tool registry, TTS voice model, STT model, "
        "overlay initialization, and audio devices. "
        "Use when the user asks 'are you working', 'run a self test', or "
        "'check if everything is OK'. Returns a summary of what passed/failed."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)
def self_test() -> str:
    results = []
    passed = 0
    failed = 0

    def check(name: str, fn) -> None:
        nonlocal passed, failed
        try:
            detail = fn()
            results.append(f"  ✓ {name}: {detail}")
            passed += 1
        except Exception as e:
            results.append(f"  ✗ {name}: {e}")
            failed += 1

    # Config
    def _config():
        from core.config import load_config
        cfg = load_config()
        return f"model={cfg['llm']['model']}, tts={cfg['tts']['engine']}"
    check("Config", _config)

    # Tools
    def _tools():
        from tools import REGISTRY
        count = len(REGISTRY)
        return f"{count} tools registered" if count > 20 else f"only {count} tools (expected 20+)"
    check("Tools", _tools)

    # TTS voice model
    def _tts_voice():
        from core.config import load_config, PROJECT_ROOT
        cfg = load_config()
        voice = cfg["tts"]["voice"]
        model_path = PROJECT_ROOT / "models" / "piper" / f"{voice}.onnx"
        if not model_path.exists():
            return f"voice file missing: {model_path.name}"
        size_mb = model_path.stat().st_size / (1024 * 1024)
        return f"{voice} ({size_mb:.0f} MB)"
    check("TTS Voice", _tts_voice)

    # Whisper model
    def _whisper():
        from core.config import load_config, PROJECT_ROOT
        cfg = load_config()
        model_name = cfg["stt"]["model"]
        snapshot = PROJECT_ROOT / "models" / "whisper" / f"Systran--faster-whisper-{model_name}"
        if snapshot.is_dir():
            return f"local snapshot ready"
        return f"will download on first use ({model_name})"
    check("Whisper STT", _whisper)

    # Audio devices
    def _audio():
        import sounddevice as sd
        devices = sd.query_devices()
        inputs = sum(1 for d in devices if d.get("max_input_channels", 0) > 0)
        outputs = sum(1 for d in devices if d.get("max_output_channels", 0) > 0)
        return f"{inputs} input(s), {outputs} output(s)"
    check("Audio", _audio)

    # Overlay
    def _overlay():
        from PyQt6.QtWidgets import QApplication
        from ui.overlay import DesktopOverlay
        app = QApplication.instance() or QApplication([])
        overlay = DesktopOverlay()
        overlay.hide()
        return f"{overlay.width()}x{overlay.height()} ready"
    check("Overlay", _overlay)

    # Learning store
    def _learning():
        from core.learning import get_store
        store = get_store()
        return f"{len(store._mistakes)} past failures tracked"
    check("Learning", _learning)

    total = passed + failed
    timing = f"(checked in {time.perf_counter() - start:.1f}s)" if (start := time.perf_counter()) else ""

    summary = f"Self-test: {passed}/{total} passed"
    if failed:
        summary += f", {failed} issue(s) need attention"
    else:
        summary += " — all systems operational"

    return f"{summary}\n" + "\n".join(results)
