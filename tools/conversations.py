"""Conversation history tool — let JARVIS search past conversations."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT
from tools import tool

LOG_DIR = PROJECT_ROOT / "data" / "conversations"


def _load_recent(days: int = 7) -> list[dict[str, Any]]:
    """Load conversation logs from the last N days."""
    entries = []
    today = datetime.now()
    for i in range(days):
        day = today - timedelta(days=i)
        path = LOG_DIR / f"{day.strftime('%Y-%m-%d')}.jsonl"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    return entries


@tool(
    name="search_conversations",
    description=(
        "Search past JARVIS conversations. Returns recent turns matching "
        "a keyword in the user's message or the assistant's response. "
        "Useful when the user says 'remember when we talked about X' or "
        "'what did I ask you yesterday about Y'. "
        "Returns: timestamped excerpts of matching turns."
    ),
    parameters={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Word or phrase to search for (case-insensitive)",
            },
            "days": {
                "type": "integer",
                "description": "How many days back to search (default 7, max 30)",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 5)",
            },
        },
        "required": ["keyword"],
    },
)
def search_conversations(keyword: str, days: int = 7, limit: int = 5) -> str:
    if not LOG_DIR.exists():
        return "(no conversation history found)"

    days = min(days, 30)
    entries = _load_recent(days)
    if not entries:
        return f"(no conversations found in the last {days} days)"

    keyword_lower = keyword.lower()
    matches = []
    for entry in entries:
        user_text = (entry.get("user") or "").lower()
        assistant_text = (entry.get("assistant") or "").lower()
        if keyword_lower in user_text or keyword_lower in assistant_text:
            matches.append(entry)

    if not matches:
        return f"(no conversations mentioning '{keyword}' in the last {days} days)"

    # Return most recent matches
    matches.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    lines = []
    for m in matches[:limit]:
        ts = m.get("timestamp", "?")
        user = (m.get("user") or "")[:120]
        assistant = (m.get("assistant") or "")[:120]
        lines.append(f"[{ts}] you: {user}")
        lines.append(f"[{ts}] jarvis: {assistant}")
        lines.append("---")

    total = len(matches)
    shown = min(limit, total)
    return (
        f"Found {total} conversation(s) mentioning '{keyword}'. "
        f"Showing {shown} most recent:\n" + "\n".join(lines)
    )


@tool(
    name="conversation_stats",
    description=(
        "Get statistics about past JARVIS conversations: total turns, "
        "average response length, tools used most frequently, etc. "
        "Use when the user asks 'how many times have we talked' or "
        "'what do I usually ask you about'."
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
def conversation_stats(days: int = 7) -> str:
    if not LOG_DIR.exists():
        return "(no conversation history found)"

    days = min(days, 30)
    entries = _load_recent(days)
    if not entries:
        return f"(no conversations in the last {days} days)"

    total_turns = len(entries)
    avg_response_chars = sum(len(e.get("assistant", "")) for e in entries) / total_turns
    total_tool_calls = sum(len(e.get("tools", [])) for e in entries)

    # Most used tools
    tool_counts: dict[str, int] = {}
    for e in entries:
        for t in e.get("tools", []):
            name = t.get("name", "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1

    top_tools = sorted(tool_counts.items(), key=lambda x: -x[1])[:5]
    top_tools_str = ", ".join(f"{name} ({count}x)" for name, count in top_tools)

    return (
        f"Stats for last {days} days:\n"
        f"  Total turns: {total_turns}\n"
        f"  Avg response length: {avg_response_chars:.0f} chars\n"
        f"  Total tool calls: {total_tool_calls}\n"
        f"  Top tools: {top_tools_str or 'none'}"
    )
