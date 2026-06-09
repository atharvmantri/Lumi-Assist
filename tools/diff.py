"""File diff and comparison tools."""
from __future__ import annotations

import difflib
from pathlib import Path

from tools import tool


@tool(
    name="diff_files",
    description="Compare two text files and show the differences.",
    parameters={
        "type": "object",
        "properties": {
            "file1": {
                "type": "string",
                "description": "Path to the first file",
            },
            "file2": {
                "type": "string",
                "description": "Path to the second file",
            },
            "context": {
                "type": "integer",
                "description": "Number of context lines (default 3)",
            },
        },
        "required": ["file1", "file2"],
    },
)
def diff_files(file1: str, file2: str, context: int = 3) -> str:
    p1, p2 = Path(file1), Path(file2)

    if not p1.exists():
        return f"error: file not found: {file1}"
    if not p2.exists():
        return f"error: file not found: {file2}"

    try:
        text1 = p1.read_text(encoding="utf-8", errors="replace").splitlines()
        text2 = p2.read_text(encoding="utf-8", errors="replace").splitlines()

        diff = list(difflib.unified_diff(text1, text2, fromfile=p1.name, tofile=p2.name, n=context, lineterm=""))

        if not diff:
            return f"Files are identical: {p1.name} == {p2.name}"

        # Count changes
        added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

        lines = [f"Diff: {p1.name} vs {p2.name} (+{added}, -{removed}):\n"]
        for line in diff[:200]:
            lines.append(line)

        if len(diff) > 200:
            lines.append(f"\n... ({len(diff) - 200} more diff lines)")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="similarity",
    description="Check how similar two texts are (0% to 100%).",
    parameters={
        "type": "object",
        "properties": {
            "text1": {
                "type": "string",
                "description": "First text",
            },
            "text2": {
                "type": "string",
                "description": "Second text",
            },
        },
        "required": ["text1", "text2"],
    },
)
def similarity(text1: str, text2: str) -> str:
    ratio = difflib.SequenceMatcher(None, text1, text2).ratio()
    pct = ratio * 100

    verdict = ""
    if pct >= 95:
        verdict = "Nearly identical"
    elif pct >= 80:
        verdict = "Very similar"
    elif pct >= 60:
        verdict = "Moderately similar"
    elif pct >= 40:
        verdict = "Somewhat similar"
    else:
        verdict = "Very different"

    return f"Similarity: {pct:.1f}% — {verdict}"
