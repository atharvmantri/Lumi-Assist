"""File read / write / list within (or below) the user's machine.

No sandboxing right now — Lumi can write anywhere the user can. The system
prompt instructs it to confirm destructive actions; we rely on that until v1.1.
"""
from __future__ import annotations

import os
from pathlib import Path

from tools import tool


_MAX_READ_BYTES = 64 * 1024     # 64 KB cap — bigger files get truncated


def _expand(path: str) -> Path:
    """Expand ~, env vars, and resolve to absolute. Doesn't require existence."""
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


@tool(
    name="write_file",
    description=(
        "Create or overwrite a text file. The path may be absolute or relative "
        "(resolved against the user's current working directory). Use this for "
        "drafting notes, writing code, saving content. Creates parent directories "
        "as needed. Confirm before overwriting important files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path, e.g. 'notes/todo.txt' or 'C:\\\\Users\\\\me\\\\hi.txt'"},
            "content": {"type": "string", "description": "Full file contents"},
        },
        "required": ["path", "content"],
    },
)
def write_file(path: str, content: str) -> str:
    p = _expand(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(content, encoding="utf-8")
        verb = "overwrote" if existed else "wrote"
        return f"{verb} {p} ({len(content)} chars)"
    except Exception as e:  # noqa: BLE001
        return f"error writing {p}: {e}"


@tool(
    name="read_file",
    description=(
        "Read a text file and return its contents (truncated to ~64 KB). "
        "Use for inspecting files the user mentions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"},
        },
        "required": ["path"],
    },
)
def read_file(path: str) -> str:
    p = _expand(path)
    if not p.exists():
        return f"error: {p} does not exist"
    if not p.is_file():
        return f"error: {p} is not a file"
    try:
        size = p.stat().st_size
        if size > _MAX_READ_BYTES:
            return (
                p.read_text(encoding="utf-8", errors="replace")[:_MAX_READ_BYTES]
                + f"\n... (truncated, {size - _MAX_READ_BYTES} more bytes)"
            )
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return f"error reading {p}: {e}"


@tool(
    name="list_dir",
    description=(
        "List the contents of a directory (files + subdirs, one per line). "
        "Use this to browse the filesystem when the user asks 'what's in X'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path (default: current working directory)"},
        },
        "required": [],
    },
)
def list_dir(path: str | None = None) -> str:
    p = _expand(path) if path else Path.cwd()
    if not p.exists():
        return f"error: {p} does not exist"
    if not p.is_dir():
        return f"error: {p} is not a directory"
    try:
        entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for e in entries[:200]:    # cap output
            marker = "/" if e.is_dir() else ""
            try:
                size = e.stat().st_size if e.is_file() else ""
            except OSError:
                size = ""
            lines.append(f"{e.name}{marker}\t{size}" if size != "" else f"{e.name}{marker}")
        more = "" if len(entries) <= 200 else f"\n... ({len(entries) - 200} more)"
        return "\n".join(lines) + more if lines else "(empty)"
    except Exception as e:  # noqa: BLE001
        return f"error listing {p}: {e}"
