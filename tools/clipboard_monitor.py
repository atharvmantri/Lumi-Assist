"""Clipboard chain monitoring — auto-detect clipboard changes."""
from __future__ import annotations

import time
from datetime import datetime

from tools import tool

_last_clipboard = {"text": "", "time": None}


@tool(
    name="clipboard_monitor",
    description="Check if the clipboard has changed since last check. Returns new content if changed.",
    parameters={
        "type": "object",
        "properties": {
            "auto_clear": {
                "type": "boolean",
                "description": "Clear the clipboard after reading (default false)",
            },
        },
        "required": [],
    },
)
def clipboard_monitor(auto_clear: bool = False) -> str:
    global _last_clipboard
    try:
        import pyperclip
    except ImportError:
        return "error: pyperclip not installed"

    try:
        current = pyperclip.paste()
    except Exception as e:
        return f"error reading clipboard: {e}"

    if current == _last_clipboard["text"]:
        return "Clipboard unchanged since last check."

    old = _last_clipboard["text"]
    _last_clipboard = {"text": current, "time": datetime.now().isoformat()}

    if auto_clear:
        pyperclip.copy("")

    new_text = current[:500] + ("..." if len(current) > 500 else "")
    return (
        f"Clipboard changed!\n"
        f"  Length: {len(current)} chars\n"
        f"  Time: {_last_clipboard['time'][11:19]}\n"
        f"  Content: {new_text}"
    )


@tool(
    name="clipboard_compare",
    description="Compare current clipboard with a given text and report similarity.",
    parameters={
        "type": "object",
        "properties": {
            "expected": {
                "type": "string",
                "description": "Expected text to compare against",
            },
        },
        "required": ["expected"],
    },
)
def clipboard_compare(expected: str) -> str:
    try:
        import pyperclip
    except ImportError:
        return "error: pyperclip not installed"

    try:
        current = pyperclip.paste()
    except Exception as e:
        return f"error reading clipboard: {e}"

    if not current:
        return "Clipboard is empty."

    import difflib
    ratio = difflib.SequenceMatcher(None, current, expected).ratio()

    lines = [f"Clipboard Comparison:"]
    lines.append(f"  Similarity: {ratio*100:.1f}%")
    lines.append(f"  Clipboard: {len(current)} chars")
    lines.append(f"  Expected: {len(expected)} chars")

    if ratio < 0.5:
        lines.append("  Verdict: Very different")
    elif ratio < 0.8:
        lines.append("  Verdict: Somewhat different")
    elif ratio < 0.95:
        lines.append("  Verdict: Close but not identical")
    else:
        lines.append("  Verdict: Nearly identical")

    return "\n".join(lines)
