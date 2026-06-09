"""Quick notes tool — JARVIS can store and retrieve quick notes."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

NOTES_PATH = PROJECT_ROOT / "data" / "notes.json"


def _load_notes() -> list[dict]:
    if NOTES_PATH.exists():
        with open(NOTES_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_notes(notes: list[dict]) -> None:
    NOTES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTES_PATH, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


@tool(
    name="add_note",
    description=(
        "Add a quick note. Use when the user says 'take a note', 'note this down', "
        "'remember this', 'make a note that...', etc. Notes persist across sessions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The note text",
            },
            "title": {
                "type": "string",
                "description": "Optional short title for the note",
            },
        },
        "required": ["text"],
    },
)
def add_note(text: str, title: str = "") -> str:
    notes = _load_notes()
    entry = {
        "id": len(notes) + 1,
        "title": title or text[:40] + ("..." if len(text) > 40 else ""),
        "text": text,
        "created": datetime.now().isoformat(),
        "epoch": time.time(),
    }
    notes.append(entry)
    _save_notes(notes)
    return f"Note added: {entry['title']}"


@tool(
    name="list_notes",
    description="List all stored notes.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_notes() -> str:
    notes = _load_notes()
    if not notes:
        return "No notes stored."

    lines = [f"Notes ({len(notes)} total):"]
    for n in notes:
        ts = n.get("created", "?")[:16].replace("T", " ")
        lines.append(f"  [{ts}] #{n.get('id', '?')} {n.get('title', '')}")
    return "\n".join(lines)


@tool(
    name="read_note",
    description="Read the full text of a note by its ID or title keyword.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Note ID number or title keyword to search",
            },
        },
        "required": ["query"],
    },
)
def read_note(query: str) -> str:
    notes = _load_notes()

    # Try ID first
    try:
        note_id = int(query)
        for n in notes:
            if n.get("id") == note_id:
                ts = n.get("created", "?")[:16].replace("T", " ")
                return f"Note #{note_id} ({ts}):\n{n.get('text', '')}"
    except ValueError:
        pass

    # Search by title keyword
    q_lower = query.lower()
    matches = [n for n in notes if q_lower in n.get("title", "").lower() or q_lower in n.get("text", "").lower()]
    if not matches:
        return f"No note found matching '{query}'"

    # Return most recent match
    matches.sort(key=lambda n: n.get("epoch", 0), reverse=True)
    n = matches[0]
    ts = n.get("created", "?")[:16].replace("T", " ")
    return f"Note #{n.get('id', '?')} ({ts}):\n{n.get('text', '')}"


@tool(
    name="delete_note",
    description="Delete a note by its ID or title keyword.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Note ID or title keyword to delete",
            },
        },
        "required": ["query"],
    },
)
def delete_note(query: str) -> str:
    notes = _load_notes()

    # Try ID first
    try:
        note_id = int(query)
        for i, n in enumerate(notes):
            if n.get("id") == note_id:
                title = notes.pop(i).get("title", "")
                _save_notes(notes)
                return f"Deleted note #{note_id}: {title}"
    except ValueError:
        pass

    # Search by keyword
    q_lower = query.lower()
    for i, n in enumerate(notes):
        if q_lower in n.get("title", "").lower() or q_lower in n.get("text", "").lower():
            title = notes.pop(i).get("title", "")
            _save_notes(notes)
            return f"Deleted note: {title}"

    return f"No note found matching '{query}'"
