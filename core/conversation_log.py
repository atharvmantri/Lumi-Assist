"""Conversation logger for JARVIS — records every prompt/response pair.

Creates append-only JSONL files so over time we accumulate a dataset of:
  - user input (voice or text)
  - full LLM response
  - tool calls and results
  - timing metrics

Each turn is one JSON line. Files are rotated by date.

Usage:
    from core.conversation_log import log_turn
    log_turn(user_text="what time is it?", response="It's 3pm.", tools=[...], metrics={...})
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT

LOG_DIR = PROJECT_ROOT / "data" / "conversations"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _today_log_path() -> Path:
    """Return today's log file path."""
    return LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"


def log_turn(
    user_text: str,
    response: str,
    *,
    tools_called: list[dict[str, Any]] | None = None,
    metrics: dict[str, float] | None = None,
    mode: str = "voice",  # "voice" | "text" | "dry-run"
) -> None:
    """Append one turn to today's conversation log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "epoch": time.time(),
        "mode": mode,
        "user": user_text,
        "assistant": response,
        "tools": tools_called or [],
        "metrics": metrics or {},
    }
    path = _today_log_path()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_dataset(days: int = 30) -> list[dict[str, Any]]:
    """Load the last N days of conversation logs."""
    entries = []
    today = datetime.now()
    for i in range(days):
        day = today - __import__("datetime").timedelta(days=i)
        path = LOG_DIR / f"{day.strftime('%Y-%m-%d')}.jsonl"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
    return entries
