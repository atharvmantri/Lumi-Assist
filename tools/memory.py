"""Persistent memory tool — JARVIS can remember facts the user tells it."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT
from tools import tool

MEMORY_PATH = PROJECT_ROOT / "data" / "memory.json"


def _load_memory() -> dict[str, Any]:
    if MEMORY_PATH.exists():
        with open(MEMORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"facts": [], "preferences": {}}


def _save_memory(data: dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@tool(
    name="remember",
    description=(
        "Store a fact or preference so JARVIS remembers it in future conversations. "
        "Use when the user says 'remember that...', 'my favorite is...', 'I prefer...', "
        "'don't forget...', 'note that...', etc. The fact persists across sessions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "The fact or preference to remember",
            },
            "category": {
                "type": "string",
                "description": "Optional category: 'personal', 'preference', 'schedule', 'work', 'other'",
            },
        },
        "required": ["fact"],
    },
)
def remember(fact: str, category: str = "other") -> str:
    mem = _load_memory()
    entry = {
        "fact": fact,
        "category": category,
        "timestamp": datetime.now().isoformat(),
        "epoch": time.time(),
    }
    mem["facts"].append(entry)
    _save_memory(mem)
    return f"Remembered: {fact}"


@tool(
    name="recall",
    description=(
        "Search JARVIS's persistent memory for stored facts and preferences. "
        "Use when the user says 'what do you remember about...', 'what do you know about me', "
        "'do you remember my...', 'what facts have I told you', etc."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for in stored facts (leave empty for all facts)",
            },
            "category": {
                "type": "string",
                "description": "Filter by category: 'personal', 'preference', 'schedule', 'work', 'other'",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 10)",
            },
        },
        "required": [],
    },
)
def recall(query: str = "", category: str = "", limit: int = 10) -> str:
    mem = _load_memory()
    facts = mem.get("facts", [])

    if not facts:
        return "I don't have any stored memories yet. Tell me something and I'll remember it."

    # Filter by category
    if category:
        facts = [f for f in facts if f.get("category", "").lower() == category.lower()]

    # Filter by query keyword
    if query:
        q_lower = query.lower()
        facts = [f for f in facts if q_lower in f.get("fact", "").lower()]

    if not facts:
        return f"No memories found" + (f" for category '{category}'" if category else "") + (f" matching '{query}'" if query else "")

    # Sort by most recent
    facts.sort(key=lambda f: f.get("epoch", 0), reverse=True)
    facts = facts[:limit]

    lines = [f"Stored memories ({len(facts)} shown):"]
    for f in facts:
        ts = f.get("timestamp", "?")[:16].replace("T", " ")
        lines.append(f"  [{ts}] {f.get('fact', '')}")

    total = len(mem.get("facts", []))
    if len(facts) < total:
        lines.append(f"  ...and {total - len(facts)} more (use a specific query to narrow)")

    return "\n".join(lines)


@tool(
    name="forget",
    description=(
        "Remove a stored memory by its number. Use when the user says "
        "'forget that...', 'remove the memory about...', 'delete what you remember about...', etc."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for in stored facts to remove",
            },
        },
        "required": ["query"],
    },
)
def forget(query: str) -> str:
    mem = _load_memory()
    facts = mem.get("facts", [])

    if not facts:
        return "No memories to forget."

    q_lower = query.lower()
    # Find matching facts
    to_remove = []
    for i, f in enumerate(facts):
        if q_lower in f.get("fact", "").lower():
            to_remove.append(i)

    if not to_remove:
        return f"No memory found matching '{query}'"

    # Remove from newest to oldest
    removed_facts = []
    for i in reversed(to_remove):
        removed_facts.append(facts.pop(i)["fact"])

    _save_memory(mem)
    removed_str = "; ".join(removed_facts[:3])
    if len(removed_facts) > 3:
        removed_str += f" and {len(removed_facts)-3} more"

    return f"Forgot {len(removed_facts)} memory(ies): {removed_str}"


@tool(
    name="list_memories",
    description="List all stored memories with their categories and timestamps.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_memories() -> str:
    mem = _load_memory()
    facts = mem.get("facts", [])

    if not facts:
        return "No stored memories yet."

    # Count by category
    cats: dict[str, int] = {}
    for f in facts:
        cat = f.get("category", "other")
        cats[cat] = cats.get(cat, 0) + 1

    cat_str = ", ".join(f"{cat}: {count}" for cat, count in sorted(cats.items()))

    lines = [f"Total memories: {len(facts)}"]
    lines.append(f"Categories: {cat_str}")
    lines.append("")

    # Show most recent 10
    recent = sorted(facts, key=lambda f: f.get("epoch", 0), reverse=True)[:10]
    for f in recent:
        ts = f.get("timestamp", "?")[:16].replace("T", " ")
        lines.append(f"  [{ts}] [{f.get('category', '?')}] {f.get('fact', '')}")

    return "\n".join(lines)
