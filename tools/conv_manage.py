"""Conversation management — cleanup and statistics."""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

from core.config import PROJECT_ROOT
from core.conversation_log import LOG_DIR, load_dataset
from tools import tool


@tool(
    name="cleanup_conversations",
    description=(
        "Clean up old conversation logs. Removes logs older than the specified "
        "number of days. Returns how many files were cleaned and how many turns were removed."
    ),
    parameters={
        "type": "object",
        "properties": {
            "older_than_days": {
                "type": "integer",
                "description": "Remove logs older than this many days (default 30)",
            },
        },
        "required": [],
    },
)
def cleanup_conversations(older_than_days: int = 30) -> str:
    if not LOG_DIR.exists():
        return "No conversation logs found."

    cutoff = datetime.now() - timedelta(days=older_than_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    files_removed = 0
    turns_removed = 0

    for path in sorted(LOG_DIR.glob("*.jsonl")):
        # Extract date from filename
        date_str = path.stem  # e.g. "2024-01-15"
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        if file_date < cutoff:
            # Count turns before removing
            with open(path, encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            turns_removed += len(lines)
            path.unlink()
            files_removed += 1

    if files_removed == 0:
        return f"No conversation logs older than {older_than_days} days found."

    return (
        f"Cleaned up {files_removed} file(s), removed {turns_removed} turns "
        f"older than {older_than_days} days (before {cutoff_str})."
    )


@tool(
    name="conversation_summary",
    description=(
        "Get a summary of recent conversation activity: turns per day, "
        "most active times, average response length, etc."
    ),
    parameters={
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "How many days back (default 7, max 30)",
            },
        },
        "required": [],
    },
)
def conversation_summary(days: int = 7) -> str:
    if not LOG_DIR.exists():
        return "No conversation logs found."

    days = min(days, 30)
    entries = load_dataset(days=days)
    if not entries:
        return f"No conversations in the last {days} days."

    total_turns = len(entries)
    avg_response = sum(len(e.get("assistant", "")) for e in entries) / total_turns
    avg_user = sum(len(e.get("user", "")) for e in entries) / total_turns
    total_tools = sum(len(e.get("tools", [])) for e in entries)
    avg_time = sum(e.get("metrics", {}).get("total_s", 0) for e in entries) / total_turns

    # Turns per day
    turns_per_day: dict[str, int] = {}
    for e in entries:
        day = e.get("timestamp", "?")[:10]
        turns_per_day[day] = turns_per_day.get(day, 0) + 1

    daily_summary = "\n".join(
        f"  {day}: {count} turn(s)"
        for day, count in sorted(turns_per_day.items())
    )

    # Modes
    modes: dict[str, int] = {}
    for e in entries:
        mode = e.get("mode", "unknown")
        modes[mode] = modes.get(mode, 0) + 1
    mode_str = ", ".join(f"{m}: {c}" for m, c in sorted(modes.items()))

    return (
        f"Conversation Summary (last {days} days)\n"
        f"  Total turns: {total_turns}\n"
        f"  Modes: {mode_str}\n"
        f"  Avg user message: {avg_user:.0f} chars\n"
        f"  Avg JARVIS response: {avg_response:.0f} chars\n"
        f"  Total tool calls: {total_tools}\n"
        f"  Avg turn time: {avg_time:.1f}s\n"
        f"\nTurns per day:\n{daily_summary}"
    )
