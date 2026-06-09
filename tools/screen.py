"""Screen capture + OCR — let JARVIS see what's on screen.

Two tools:
  take_screenshot   — captures the full desktop (or a region), saves a PNG,
                      and returns the path. The model can mention the path
                      in its spoken reply or use it later via run_python.
  get_screen_text   — captures the screen and OCRs it with Tesseract.
                      Returns extracted text. Requires Tesseract binary on PATH.

Screenshots accumulate in logs/screenshots/ with timestamped filenames so
nothing gets clobbered. The folder is gitignored.
"""
from __future__ import annotations

import shutil
import time
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

_SHOTS_DIR = PROJECT_ROOT / "logs" / "screenshots"


def _capture(region: tuple[int, int, int, int] | None) -> "PIL.Image.Image":  # type: ignore[name-defined]
    """Grab the screen (or a sub-region) as a PIL Image. Imports lazily."""
    from PIL import ImageGrab
    bbox = region if region else None
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    return img


@tool(
    name="take_screenshot",
    description=(
        "Capture the current desktop screen (or a rectangular region) as a PNG, "
        "save it under logs/screenshots/, and return the full path. Use this when "
        "the user asks to take a screenshot, or when you need to see what's on "
        "screen before answering (then follow up with get_screen_text for OCR, "
        "or pass the path to a model that can read images). "
        "Region is optional: omit to capture all displays, or specify as "
        "[left, top, right, bottom] in screen pixels for a sub-region."
    ),
    parameters={
        "type": "object",
        "properties": {
            "region": {
                "type": "array",
                "description": "Optional [left, top, right, bottom] in pixels",
                "items": {"type": "integer"},
                "minItems": 4,
                "maxItems": 4,
            },
        },
        "required": [],
    },
)
def take_screenshot(region: list[int] | None = None) -> str:
    try:
        from PIL import ImageGrab  # noqa: F401 — explicit import to surface a friendly error
    except ImportError:
        return "error: Pillow not installed (need PIL.ImageGrab)"

    bbox: tuple[int, int, int, int] | None = None
    if region:
        if len(region) != 4:
            return f"error: region must be 4 ints [left, top, right, bottom], got {region!r}"
        bbox = (int(region[0]), int(region[1]), int(region[2]), int(region[3]))

    _SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    out_path = _SHOTS_DIR / f"shot_{ts}.png"
    try:
        img = _capture(bbox)
        img.save(out_path, "PNG")
        return f"saved {img.size[0]}x{img.size[1]} screenshot to {out_path}"
    except Exception as e:  # noqa: BLE001
        return f"error capturing screen: {e}"


@tool(
    name="get_screen_text",
    description=(
        "Capture the screen (or a region) and run OCR to extract all visible text. "
        "Returns the text as a single string with newlines between lines. Use this "
        "when the user asks about what's on screen, or when you need to read text "
        "from a window that doesn't have an obvious API. Requires Tesseract OCR "
        "to be installed on the system."
    ),
    parameters={
        "type": "object",
        "properties": {
            "region": {
                "type": "array",
                "description": "Optional [left, top, right, bottom] in pixels",
                "items": {"type": "integer"},
                "minItems": 4,
                "maxItems": 4,
            },
        },
        "required": [],
    },
)
def get_screen_text(region: list[int] | None = None) -> str:
    # Confirm Tesseract binary is present before importing pytesseract (better error)
    if not shutil.which("tesseract"):
        return (
            "error: Tesseract binary not found on PATH. "
            "Install from https://github.com/UB-Mannheim/tesseract/wiki "
            "(Windows) and restart this app, then try again."
        )
    try:
        import pytesseract
    except ImportError:
        return "error: pytesseract not installed"

    bbox: tuple[int, int, int, int] | None = None
    if region:
        if len(region) != 4:
            return f"error: region must be 4 ints [left, top, right, bottom], got {region!r}"
        bbox = (int(region[0]), int(region[1]), int(region[2]), int(region[3]))

    try:
        img = _capture(bbox)
        text = pytesseract.image_to_string(img)
        text = (text or "").strip()
        if not text:
            return "(no text detected on screen)"
        # Keep payload manageable
        if len(text) > 6000:
            text = text[:6000] + f"\n... (truncated, {len(text) - 6000} more chars)"
        return text
    except Exception as e:  # noqa: BLE001
        return f"error reading screen text: {e}"
