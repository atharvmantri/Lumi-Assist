"""App launching + window focus."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from tools import tool


# A few aliases for apps whose Windows command isn't obvious from natural language.
_ALIASES = {
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "paint": "mspaint",
    "task manager": "taskmgr",
    "terminal": "wt",          # Windows Terminal if installed
    "windows terminal": "wt",
    "powershell": "powershell",
    "cmd": "cmd",
    "command prompt": "cmd",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "obs": "obs",
}


def _resolve(name: str) -> str:
    """Map a friendly name to a launchable command. Returns the command as-is
    if no alias matched — Windows' shell-resolved Start Menu will often find it."""
    key = name.strip().lower()
    return _ALIASES.get(key, name.strip())


@tool(
    name="open_app",
    description=(
        "Launch a Windows application by friendly name. Examples: 'notepad', "
        "'vs code', 'chrome', 'calculator', 'spotify'. Returns the resolved "
        "command that was launched, or an error if the app can't be found."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Friendly app name (e.g. 'notepad', 'vs code', 'spotify')",
            },
        },
        "required": ["name"],
    },
)
def open_app(name: str) -> str:
    cmd = _resolve(name)
    # Try Start menu / PATH lookup first (handles installed apps, AppX packages).
    # Falling back to `start` lets Windows resolve via Start Menu shortcuts.
    try:
        # `start ""` is the magic incantation; the empty title prevents start
        # from treating the next arg as a window title.
        subprocess.Popen(
            ["cmd", "/c", "start", "", cmd],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return f"launched {cmd!r}"
    except FileNotFoundError:
        return f"error: could not launch {cmd!r}"


@tool(
    name="focus_window",
    description=(
        "Bring an already-open window to the foreground. Matches by partial "
        "title (case-insensitive). Use get_window_list first if you're unsure "
        "what's open."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title_contains": {
                "type": "string",
                "description": "Substring to match against window titles",
            },
        },
        "required": ["title_contains"],
    },
)
def focus_window(title_contains: str) -> str:
    try:
        import pywinauto.findwindows as fw
        from pywinauto.application import Application
    except ImportError:
        return "error: pywinauto not installed; install requirements.txt"

    needle = title_contains.lower()
    handles = []
    try:
        handles = fw.find_windows(title_re=f".*{title_contains}.*", visible_only=True)
    except Exception:
        pass
    if not handles:
        # Fallback: scan all visible window titles
        try:
            import pywinauto
            for w in pywinauto.Desktop(backend="uia").windows():
                if needle in (w.window_text() or "").lower():
                    handles.append(w.handle)
                    break
        except Exception as e:  # noqa: BLE001
            return f"error: window lookup failed: {e}"
    if not handles:
        return f"no visible window matched {title_contains!r}"
    try:
        app = Application().connect(handle=handles[0])
        app.window(handle=handles[0]).set_focus()
        return f"focused window (handle={handles[0]})"
    except Exception as e:  # noqa: BLE001
        return f"error: couldn't focus window: {e}"


@tool(
    name="get_window_list",
    description="List the titles of all visible top-level windows currently open on the desktop.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_window_list() -> str:
    try:
        import pywinauto
    except ImportError:
        return "error: pywinauto not installed"
    titles: list[str] = []
    try:
        for w in pywinauto.Desktop(backend="uia").windows():
            t = (w.window_text() or "").strip()
            if t:
                titles.append(t)
    except Exception as e:  # noqa: BLE001
        return f"error enumerating windows: {e}"
    if not titles:
        return "no visible windows"
    return "\n".join(titles[:40])    # cap at 40 to keep the LLM context small
