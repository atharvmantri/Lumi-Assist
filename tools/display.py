"""Screen layout and display management."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="screen_resolution",
    description="Get or set the screen resolution.",
    parameters={
        "type": "object",
        "properties": {
            "width": {
                "type": "integer",
                "description": "Width in pixels (set mode only)",
            },
            "height": {
                "type": "integer",
                "description": "Height in pixels (set mode only)",
            },
        },
        "required": [],
    },
)
def screen_resolution(width: int = 0, height: int = 0) -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::AllScreens | ForEach-Object { $_.Bounds.Width.ToString() + 'x' + $_.Bounds.Height.ToString() + ' (' + ($_.Primary.ToString()) + ')' }"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        screens = [s.strip() for s in result.stdout.strip().split("\n") if s.strip()]
        if not screens:
            return "No displays found."
        lines = [f"Displays ({len(screens)}):"]
        for i, s in enumerate(screens, 1):
            lines.append(f"  Display {i}: {s}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="toggle_dark_mode",
    description="Toggle between Windows dark mode and light mode.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def toggle_dark_mode() -> str:
    try:
        # Read current mode
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ItemPropertyValue -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' -Name 'AppsUseLightTheme'"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        current = result.stdout.strip()
        new_val = "0" if current == "1" else "1"
        mode_name = "Dark" if new_val == "0" else "Light"

        subprocess.run(
            ["powershell", "-Command",
             f"Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' -Name 'AppsUseLightTheme' -Value {new_val}"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Switched to {mode_name} mode"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="screenshot_region",
    description="Take a screenshot of a specific region of the screen.",
    parameters={
        "type": "object",
        "properties": {
            "x": {
                "type": "integer",
                "description": "X coordinate of top-left corner",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate of top-left corner",
            },
            "width": {
                "type": "integer",
                "description": "Width of region",
            },
            "height": {
                "type": "integer",
                "description": "Height of region",
            },
        },
        "required": ["x", "y", "width", "height"],
    },
)
def screenshot_region(x: int, y: int, width: int, height: int) -> str:
    from tools.screen import take_screenshot
    return take_screenshot(region=[x, y, x + width, y + height])
