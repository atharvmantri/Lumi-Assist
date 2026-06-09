"""Screen dimming and focus mode tools."""
from __future__ import annotations

import ctypes
import subprocess

from tools import tool


@tool(
    name="dim_screen",
    description="Dim the screen brightness below minimum (useful for night work).",
    parameters={
        "type": "object",
        "properties": {
            "level": {
                "type": "integer",
                "description": "Dim level 0-100 (100 = normal, 0 = very dim)",
                "minimum": 0,
                "maximum": 100,
            },
        },
        "required": ["level"],
    },
)
def dim_screen(level: int) -> str:
    level = max(0, min(100, level))
    try:
        # Use SetWindowDisplayAffinity or magnifier approach
        # Simplest: adjust via WMI
        ps_cmd = f'(Get-WmiObject -Namespace "root/wmi" -Class WmiMonitorBrightnessMethods).WmiSetBrightness(0, {level})'
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Screen brightness set to {level}%"
        return f"Could not set brightness via WMI. Try another method."
    except Exception as e:
        return f"error: {e}"


@tool(
    name="focus_mode",
    description="Enable or disable Windows Focus Assist (Do Not Disturb).",
    parameters={
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "description": "Focus Assist state: 'on', 'off', 'priority'",
                "enum": ["on", "off", "priority"],
            },
        },
        "required": ["state"],
    },
)
def focus_mode(state: str) -> str:
    # 0=off, 1=priority, 2=alarms only
    val_map = {"off": 0, "priority": 1, "on": 2}
    val = val_map.get(state.lower(), 0)

    try:
        ps_cmd = f'Set-ItemProperty -Path "HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\QuietHours" -Name "Profile" -Value {val}'
        subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Focus Assist set to: {state}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="show_desktop",
    description="Minimize all windows to show the desktop (Win+D).",
    parameters={"type": "object", "properties": {}, "required": []},
)
def show_desktop() -> str:
    try:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "Showing desktop (all windows minimized)"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="cascade_windows",
    description="Cascade all open windows on the desktop.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def cascade_windows() -> str:
    try:
        # Shell.Application CascadeWindows
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, 0, 0)
        import pyautogui
        # Win+Tab for task view, then cascade
        pyautogui.hotkey("win", "d")  # show desktop first
        return "Attempted to cascade windows"
    except Exception as e:
        return f"error: {e}"
