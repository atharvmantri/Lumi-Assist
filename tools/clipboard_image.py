"""Clipboard image tools — capture and save screenshots from clipboard."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

SCREENSHOTS_DIR = PROJECT_ROOT / "data" / "screenshots"


@tool(
    name="clipboard_image_save",
    description="Save the current clipboard image to a file.",
    parameters={
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Output path (default: data/screenshots/clipboard_TIMESTAMP.png)",
            },
        },
        "required": [],
    },
)
def clipboard_image_save(output_path: str = "") -> str:
    try:
        from PIL import ImageGrab
    except ImportError:
        return "error: Pillow not installed"

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        img = ImageGrab.grabclipboard()
        if img is None:
            return "error: no image in clipboard (clipboard may contain text instead)"

        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(SCREENSHOTS_DIR / f"clipboard_{ts}.png")

        img.save(output_path, "PNG")
        return f"Saved clipboard image: {output_path} ({img.size[0]}x{img.size[1]})"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="full_screenshot",
    description="Take a full desktop screenshot and save it.",
    parameters={
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Output path (default: data/screenshots/screenshot_TIMESTAMP.png)",
            },
        },
        "required": [],
    },
)
def full_screenshot(output_path: str = "") -> str:
    try:
        from PIL import ImageGrab
    except ImportError:
        return "error: Pillow not installed"

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        img = ImageGrab.grab(all_screens=True)

        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(SCREENSHOTS_DIR / f"screenshot_{ts}.png")

        img.save(output_path, "PNG")
        return f"Screenshot saved: {output_path} ({img.size[0]}x{img.size[1]})"
    except Exception as e:
        return f"error: {e}"
