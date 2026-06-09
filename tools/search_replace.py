"""Text search in files — grep-like functionality."""
from __future__ import annotations

import re
from pathlib import Path

from tools import tool


@tool(
    name="search_in_files",
    description="Search for text in files within a directory (grep-like).",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text or regex pattern to search for",
            },
            "directory": {
                "type": "string",
                "description": "Directory to search in (default: current directory)",
            },
            "file_pattern": {
                "type": "string",
                "description": "File glob pattern (e.g. '*.py', '*.md', '*')",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Case-sensitive search (default false)",
            },
            "max_results": {
                "type": "integer",
                "description": "Max matches to return (default 50)",
            },
        },
        "required": ["pattern"],
    },
)
def search_in_files(pattern: str, directory: str = "", file_pattern: str = "*", case_sensitive: bool = False, max_results: int = 50) -> str:
    target = Path(directory) if directory else Path.cwd()
    if not target.exists():
        return f"error: directory not found: {directory or '.'}"

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        return f"error: invalid regex: {e}"

    results = []
    files_searched = 0

    for f in target.rglob(file_pattern):
        if not f.is_file():
            continue
        files_searched += 1
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.split("\n"), 1):
                if compiled.search(line):
                    rel = f.relative_to(target)
                    results.append((str(rel), i, line.strip()))
                    if len(results) >= max_results:
                        break
        except (PermissionError, OSError):
            pass
        if len(results) >= max_results:
            break

    if not results:
        return f"No matches for '{pattern}' in {files_searched} files."

    lines = [f"Search for '{pattern}' ({len(results)} matches in {files_searched} files):"]
    for filepath, lineno, content in results:
        ctx = content[:150] + ("..." if len(content) > 150 else "")
        lines.append(f"  {filepath}:{lineno}: {ctx}")

    return "\n".join(lines)


@tool(
    name="replace_in_files",
    description="Find and replace text across multiple files.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text or regex pattern to find",
            },
            "replacement": {
                "type": "string",
                "description": "Replacement text",
            },
            "directory": {
                "type": "string",
                "description": "Directory to search in (default: current directory)",
            },
            "file_pattern": {
                "type": "string",
                "description": "File glob pattern (e.g. '*.py')",
            },
            "dry_run": {
                "type": "boolean",
                "description": "Show what would change without modifying files (default true)",
            },
        },
        "required": ["pattern", "replacement"],
    },
)
def replace_in_files(pattern: str, replacement: str, directory: str = "", file_pattern: str = "*", dry_run: bool = True) -> str:
    target = Path(directory) if directory else Path.cwd()

    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return f"error: invalid regex: {e}"

    changed = 0
    total_replacements = 0
    lines = [f"{'[DRY RUN] ' if dry_run else ''}Replace '{pattern}' → '{replacement}':"]

    for f in target.rglob(file_pattern):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            new_text, count = compiled.subn(replacement, text)
            if count > 0:
                if not dry_run:
                    f.write_text(new_text, encoding="utf-8")
                lines.append(f"  {f.relative_to(target)}: {count} replacement(s)")
                changed += 1
                total_replacements += count
        except (PermissionError, OSError):
            pass

    lines.append(f"\n{'Would change' if dry_run else 'Changed'} {changed} file(s), {total_replacements} total replacement(s)")
    return "\n".join(lines)
