"""Windows accessibility tools."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="toggle_narrator",
    description="Turn Windows Narrator (screen reader) on or off.",
    parameters={
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "description": "Turn narrator 'on' or 'off'",
                "enum": ["on", "off"],
            },
        },
        "required": ["state"],
    },
)
def toggle_narrator(state: str) -> str:
    try:
        import pyautogui
        pyautogui.hotkey("win", "ctrl", "enter")
        return f"Toggled Narrator ({state})"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="toggle_magnifier",
    description="Open or close Windows Magnifier.",
    parameters={
        "type": "object",
        "properties": {
            "zoom": {
                "type": "integer",
                "description": "Zoom level percentage (100-800, default 200)",
            },
        },
        "required": [],
    },
)
def toggle_magnifier(zoom: int = 200) -> str:
    try:
        import pyautogui
        pyautogui.hotkey("win", "plus")  # Open magnifier
        # Adjust zoom
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", f"Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\ScreenMagnifier' -Name 'Magnification' -Value {zoom}"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Magnifier opened at {zoom}% zoom"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="text_size",
    description="Change Windows text size.",
    parameters={
        "type": "object",
        "properties": {
            "size": {
                "type": "integer",
                "description": "Text size percentage (100-225, 100=default)",
                "minimum": 100,
                "maximum": 225,
            },
        },
        "required": ["size"],
    },
)
def text_size(size: int) -> str:
    size = max(100, min(225, size))
    try:
        ps_cmd = f'Set-ItemProperty -Path "HKCU:\\Control Panel\\Desktop\\WindowMetrics" -Name "AppliedDPI" -Value {int(size * 96 / 100)}'
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Text size set to {size}% (requires sign out to take effect)"
    except Exception as e:
        return f"error: {e}"
