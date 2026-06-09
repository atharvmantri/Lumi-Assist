"""Windows shortcut (.lnk) creation tools."""
from __future__ import annotations

import os
from pathlib import Path

from tools import tool


@tool(
    name="create_shortcut",
    description="Create a Windows desktop shortcut (.lnk) to a file, folder, or URL.",
    parameters={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Path to the target file, folder, or URL",
            },
            "name": {
                "type": "string",
                "description": "Shortcut name (without .lnk extension)",
            },
            "location": {
                "type": "string",
                "description": "Where to create: 'desktop', 'start-menu', 'folder' (default 'desktop')",
                "enum": ["desktop", "start-menu", "folder"],
            },
            "working_dir": {
                "type": "string",
                "description": "Working directory for the shortcut",
            },
        },
        "required": ["target", "name"],
    },
)
def create_shortcut(target: str, name: str, location: str = "desktop", working_dir: str = "") -> str:
    if location == "desktop":
        dest_dir = Path.home() / "Desktop"
    elif location == "start-menu":
        dest_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    else:
        dest_dir = Path(target).parent

    dest_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = dest_dir / f"{name}.lnk"

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(shortcut_path))

        if target.startswith(("http://", "https://")):
            shortcut.TargetPath = "explorer.exe"
            shortcut.Arguments = target
        else:
            shortcut.TargetPath = target
            if working_dir:
                shortcut.WorkingDirectory = working_dir
            else:
                shortcut.WorkingDirectory = str(Path(target).parent)

        shortcut.save()
        return f"Shortcut created: {shortcut_path} → {target}"
    except ImportError:
        # Fallback: create a .url file for web links
        if target.startswith(("http://", "https://")):
            url_path = dest_dir / f"{name}.url"
            with open(url_path, "w") as f:
                f.write(f"[InternetShortcut]\nURL={target}\n")
            return f"URL shortcut created: {url_path} → {target}"
        return "error: pywin32 not installed (needed for .lnk files). Install with: pip install pywin32"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="open_startup_folder",
    description="Open the Windows Startup folder to manage programs that run at login.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def open_startup_folder() -> str:
    try:
        startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        if startup.exists():
            os.startfile(str(startup))
            return f"Opened Startup folder: {startup}"
        return "Startup folder not found."
    except Exception as e:
        return f"error: {e}"
