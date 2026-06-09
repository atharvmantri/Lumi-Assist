"""Media control tools — volume, playback, brightness, etc."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="media_play_pause",
    description="Toggle play/pause for the currently active media player.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def media_play_pause() -> str:
    try:
        import pyautogui
        pyautogui.press("playpause")
        return "toggled play/pause"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="media_next",
    description="Skip to the next track in the currently active media player.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def media_next() -> str:
    try:
        import pyautogui
        pyautogui.press("nexttrack")
        return "skipped to next track"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="media_previous",
    description="Go back to the previous track in the currently active media player.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def media_previous() -> str:
    try:
        import pyautogui
        pyautogui.press("prevtrack")
        return "went to previous track"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="volume_up",
    description="Increase the system volume by a small amount (about 5%).",
    parameters={"type": "object", "properties": {}, "required": []},
)
def volume_up() -> str:
    try:
        import pyautogui
        for _ in range(2):
            pyautogui.press("volumeup")
        return "volume increased"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="volume_down",
    description="Decrease the system volume by a small amount (about 5%).",
    parameters={"type": "object", "properties": {}, "required": []},
)
def volume_down() -> str:
    try:
        import pyautogui
        for _ in range(2):
            pyautogui.press("volumedown")
        return "volume decreased"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="mute",
    description="Mute or unmute the system audio.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def mute() -> str:
    try:
        import pyautogui
        pyautogui.press("volumemute")
        return "toggled mute"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="set_brightness",
    description="Set the screen brightness level (Windows 10/11). Level is 0-100.",
    parameters={
        "type": "object",
        "properties": {
            "level": {
                "type": "integer",
                "description": "Brightness 0-100",
                "minimum": 0,
                "maximum": 100,
            },
        },
        "required": ["level"],
    },
)
def set_brightness(level: int) -> str:
    level = max(0, min(100, int(level)))
    try:
        # PowerShell WMI method for brightness
        ps_cmd = f'(Get-WmiObject -Namespace "root/wmi" -Class WmiMonitorBrightnessMethods).WmiSetBrightness(0, {level})'
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"brightness set to {level}%"
        return f"error setting brightness: {result.stderr.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="keyboard_type",
    description="Type text as if from the keyboard. Use when the user asks to type something into an active field.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to type",
            },
        },
        "required": ["text"],
    },
)
def keyboard_type(text: str) -> str:
    try:
        import pyautogui
        pyautogui.write(text, interval=0.02)
        return f"typed {len(text)} characters"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="keyboard_press",
    description="Press a keyboard shortcut or hotkey. Examples: 'ctrl+c', 'alt+tab', 'win+d', 'ctrl+shift+esc'.",
    parameters={
        "type": "object",
        "properties": {
            "keys": {
                "type": "string",
                "description": "Keyboard shortcut, e.g. 'ctrl+c', 'alt+tab', 'win+d', 'f11'",
            },
        },
        "required": ["keys"],
    },
)
def keyboard_press(keys: str) -> str:
    try:
        import pyautogui
        # Parse keys like "ctrl+c", "alt+tab", "win+d"
        parts = keys.lower().split("+")
        pyautogui.hotkey(*parts)
        return f"pressed {keys}"
    except Exception as e:
        return f"error: {e}"
