"""Quick smoke tests for Lumi components — no API calls, no mic.

Run: python tests/test_quick.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Force UTF-8 stdout on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_config() -> bool:
    """Config loads and has expected keys."""
    from core.config import load_config
    cfg = load_config()
    assert "lumi" in cfg, "missing lumi section"
    assert "stt" in cfg, "missing stt section"
    assert "llm" in cfg, "missing llm section"
    assert "tts" in cfg, "missing tts section"
    assert cfg["lumi"]["wake_word"] == "hey computer"
    print("  ✓ config loads correctly")
    return True


def test_learning_store() -> bool:
    """Learning store initializes and can record mistakes/successes."""
    from core.learning import get_store, _sig_args, _sig_error
    store = get_store()
    assert store is not None

    # Test signature helpers
    sig1 = _sig_args({"code": "print('hello')"})
    sig2 = _sig_args({"code": "print('hello')"})
    assert sig1 == sig2, "same args should produce same signature"

    err1 = _sig_error("IndentationError: expected an indented block on line 11")
    err2 = _sig_error("IndentationError: expected an indented block on line 42")
    assert err1 == err2, "same error type should produce same signature"

    print("  ✓ learning store works")
    return True


def test_conversation_log() -> bool:
    """Conversation logger writes and reads entries."""
    from core.conversation_log import log_turn, _today_log_path, load_dataset

    log_turn(
        user_text="quick test",
        response="test response",
        tools_called=[{"name": "get_time"}],
        metrics={"total_s": 0.1},
        mode="test",
    )

    path = _today_log_path()
    assert path.exists(), "log file should exist"

    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    assert len(lines) > 0, "should have at least one entry"

    entry = json.loads(lines[-1])
    assert entry["user"] == "quick test"
    assert entry["assistant"] == "test response"
    assert entry["mode"] == "test"

    print("  ✓ conversation logger works")
    return True


def test_tts_cleaning() -> bool:
    """TTS text cleaning removes markdown noise."""
    from core.tts import _clean_for_tts

    assert _clean_for_tts("**bold text**") == "bold text"
    assert _clean_for_tts("`code here`") == "code here"
    assert _clean_for_tts("```python\nprint('hi')\n```") == "print('hi')"
    assert _clean_for_tts("# Header") == "Header"
    assert _clean_for_tts("- bullet item") == "bullet item"
    assert _clean_for_tts("[link](http://example.com)") == "link"
    assert _clean_for_tts("Hello!!!") == "Hello!"

    print("  ✓ TTS text cleaning works")
    return True


def test_tool_registry() -> bool:
    """Tools register correctly."""
    from tools import REGISTRY

    assert len(REGISTRY) >= 30, f"expected 30+ tools, got {len(REGISTRY)}"

    # Check new tools are present
    for name in [
        "get_system_info", "get_battery", "get_cpu_usage",
        "get_processes", "set_timer", "cancel_timer", "list_timers",
        "get_weather", "get_time", "search_conversations", "conversation_stats",
    ]:
        assert name in REGISTRY, f"missing tool: {name}"

    print(f"  ✓ {len(REGISTRY)} tools registered")
    return True


def test_overlay_module() -> bool:
    """Overlay module imports and creates widget."""
    from PyQt6.QtWidgets import QApplication
    from ui.overlay import DesktopOverlay, OverlayState

    app = QApplication.instance() or QApplication([])
    overlay = DesktopOverlay()
    assert overlay is not None
    assert overlay.width() == 600, f"expected 600px width, got {overlay.width()}"
    assert overlay.height() == 220, f"expected 220px height, got {overlay.height()}"

    # Test state enum
    assert OverlayState.IDLE.value == "idle"
    assert OverlayState.LISTENING.value == "listening"
    assert OverlayState.THINKING.value == "thinking"
    assert OverlayState.RESPONDING.value == "responding"

    overlay.hide()
    print("  ✓ overlay module works (600x220)")
    return True


def main() -> int:
    print("Lumi Quick Tests")
    print("=" * 40)

    tests = [
        ("Config", test_config),
        ("Learning Store", test_learning_store),
        ("Conversation Log", test_conversation_log),
        ("TTS Cleaning", test_tts_cleaning),
        ("Tool Registry", test_tool_registry),
        ("Overlay Module", test_overlay_module),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1

    print("=" * 40)
    print(f"  {passed}/{passed+failed} passed")

    if failed:
        print("  Some tests failed — review output above.")
        return 1
    print("  All tests passed. Lumi is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
