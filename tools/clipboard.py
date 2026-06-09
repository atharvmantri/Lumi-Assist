"""Clipboard history — track and recall clipboard items.
Uses clipboard_read/write from tools.system for basic operations.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

CLIPBOARD_PATH = PROJECT_ROOT / "data" / "clipboard_history.json"


def _load_history() -> list[dict]:
    if CLIPBOARD_PATH.exists():
        with open(CLIPBOARD_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_history(history: list[dict]) -> None:
    CLIPBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = history[-50:]
    with open(CLIPBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


@tool(
    name="clipboard_history",
    description="Show recent clipboard history. The clipboard tracks every copy operation.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent items to show (default 10)",
            },
        },
        "required": [],
    },
)
def clipboard_history(limit: int = 10) -> str:
    history = _load_history()
    if not history:
        return "No clipboard history recorded."

    items = history[-limit:]
    items.reverse()  # newest first

    lines = [f"Recent clipboard ({len(items)} items):"]
    for i, item in enumerate(items, 1):
        ts = item.get("timestamp", "?")[:16].replace("T", " ")
        text = item.get("text", "")[:80]
        length = item.get("length", 0)
        lines.append(f"  #{i} [{ts}] ({length} chars) {text}")

    return "\n".join(lines)


@tool(
    name="clipboard_clear_history",
    description="Clear all clipboard history.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def clipboard_clear_history() -> str:
    history = _load_history()
    count = len(history)
    _save_history([])
    return f"Cleared {count} clipboard history entries."
