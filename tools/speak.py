"""Proactive voice output — let JARVIS speak on demand."""
from __future__ import annotations

import threading
import time

from tools import tool


@tool(
    name="speak",
    description=(
        "Speak a text out loud through the system speakers using JARVIS's TTS engine. "
        "Use this when you want to proactively say something to the user without "
        "waiting for them to ask — e.g. announcing a timer, a reminder, or a "
        "system event. The text should be short (1-2 sentences) and TTS-friendly."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to speak out loud",
            },
        },
        "required": ["text"],
    },
)
def speak(text: str) -> str:
    """Speak text using JARVIS's TTS in a background thread."""
    try:
        from core.tts import TTS
    except ImportError:
        return "error: TTS module not available"

    # Speak in background thread so the LLM can continue
    def _speak_bg():
        try:
            tts = TTS(verbose=False)
            tts.speak(text)
        except Exception:
            pass  # best-effort

    t = threading.Thread(target=_speak_bg, daemon=True)
    t.start()

    # Brief wait so the LLM doesn't respond before speech starts
    time.sleep(0.3)

    return f"speaking: {text[:50]}{'...' if len(text) > 50 else ''}"
