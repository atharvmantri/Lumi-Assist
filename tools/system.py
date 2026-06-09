"""Clipboard, notifications, active-window introspection."""
from __future__ import annotations

from tools import tool


@tool(
    name="clipboard_read",
    description="Read the current contents of the Windows clipboard as text.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def clipboard_read() -> str:
    try:
        import pyperclip
    except ImportError:
        return "error: pyperclip not installed"
    try:
        text = pyperclip.paste() or ""
    except Exception as e:  # noqa: BLE001
        return f"error reading clipboard: {e}"
    if not text:
        return "(clipboard is empty or contains non-text data)"
    if len(text) > 4000:
        return text[:4000] + f"\n... (truncated, {len(text)-4000} more chars)"
    return text


@tool(
    name="clipboard_write",
    description="Replace the Windows clipboard contents with the given text.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to put on the clipboard"},
        },
        "required": ["text"],
    },
)
def clipboard_write(text: str) -> str:
    try:
        import pyperclip
    except ImportError:
        return "error: pyperclip not installed"
    try:
        pyperclip.copy(text)
        return f"copied {len(text)} chars to clipboard"
    except Exception as e:  # noqa: BLE001
        return f"error writing clipboard: {e}"


@tool(
    name="send_notification",
    description="Show a Windows toast notification in the bottom-right corner.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Bold heading"},
            "body": {"type": "string", "description": "Notification body text"},
        },
        "required": ["title", "body"],
    },
)
def send_notification(title: str, body: str) -> str:
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, body, duration=5, threaded=True)
        return f"notification shown: {title!r}"
    except ImportError:
        # Fallback: a PowerShell BurntToast-free toast via msg.exe — actually no,
        # simplest no-dep fallback is a console beep + return; the LLM will speak it.
        return f"(win10toast unavailable; would have shown: {title} — {body})"
    except Exception as e:  # noqa: BLE001
        return f"error showing notification: {e}"


@tool(
    name="get_active_window",
    description="Return the title of the currently focused window on the user's desktop.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_active_window() -> str:
    try:
        import pywinauto
        w = pywinauto.Desktop(backend="uia").get_active()
        return (w.window_text() or "(unnamed window)").strip()
    except Exception as e:  # noqa: BLE001
        return f"error reading active window: {e}"


@tool(
    name="set_volume",
    description=(
        "Set the system master volume. Level is 0-100 (percent). Returns the new level."
    ),
    parameters={
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "Volume 0-100", "minimum": 0, "maximum": 100},
        },
        "required": ["level"],
    },
)
def set_volume(level: int) -> str:
    try:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    except ImportError:
        return "error: pycaw not installed"
    level = max(0, min(100, int(level)))
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol = cast(interface, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"volume set to {level}%"
    except Exception as e:  # noqa: BLE001
        return f"error setting volume: {e}"
