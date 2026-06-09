"""Regex tools — test, match, and replace with regular expressions."""
from __future__ import annotations

import re

from tools import tool


@tool(
    name="regex_test",
    description="Test a regex pattern against text and show all matches.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to test",
            },
            "text": {
                "type": "string",
                "description": "Text to match against",
            },
            "flags": {
                "type": "string",
                "description": "Regex flags: 'i' (case-insensitive), 'm' (multiline), 's' (dotall), or empty",
            },
        },
        "required": ["pattern", "text"],
    },
)
def regex_test(pattern: str, text: str, flags: str = "") -> str:
    flag = 0
    if "i" in flags.lower():
        flag |= re.IGNORECASE
    if "m" in flags.lower():
        flag |= re.MULTILINE
    if "s" in flags.lower():
        flag |= re.DOTALL

    try:
        compiled = re.compile(pattern, flag)
    except re.error as e:
        return f"error: invalid regex: {e}"

    matches = list(compiled.finditer(text))
    if not matches:
        return f"No matches found for pattern: {pattern}"

    lines = [f"Pattern: {pattern} ({len(matches)} match(es)):"]
    for i, m in enumerate(matches, 1):
        matched = m.group()
        start, end = m.start(), m.end()
        # Show context
        ctx_start = max(0, start - 20)
        ctx_end = min(len(text), end + 20)
        before = text[ctx_start:start]
        after = text[end:ctx_end]
        context = (f"...{before}" if ctx_start > 0 else before) + f"[{matched}]" + (f"{after}..." if ctx_end < len(text) else after)
        lines.append(f"  #{i}: '{matched}' at position {start}-{end}")
        if len(matches) <= 10:
            lines.append(f"       context: {context}")

    return "\n".join(lines)


@tool(
    name="regex_replace",
    description="Replace text using a regex pattern.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to match",
            },
            "replacement": {
                "type": "string",
                "description": "Replacement text (can use \\1, \\2 for groups)",
            },
            "text": {
                "type": "string",
                "description": "Text to process",
            },
        },
        "required": ["pattern", "replacement", "text"],
    },
)
def regex_replace(pattern: str, replacement: str, text: str) -> str:
    try:
        result = re.sub(pattern, replacement, text)
        changes = text != result
        return f"{'Replaced' if changes else 'No changes'}: {len(result)} chars\n\n{result[:2000]}"
    except re.error as e:
        return f"error: {e}"


@tool(
    name="regex_extract",
    description="Extract named capture groups from text using a regex pattern.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex pattern with named groups (e.g. '(?P<name>\\w+)')",
            },
            "text": {
                "type": "string",
                "description": "Text to extract from",
            },
        },
        "required": ["pattern", "text"],
    },
)
def regex_extract(pattern: str, text: str) -> str:
    try:
        compiled = re.compile(pattern)
    except re.error as e:
        return f"error: invalid regex: {e}"

    matches = list(compiled.finditer(text))
    if not matches:
        return "No matches found."

    lines = [f"Extracted ({len(matches)} match(es)):"]
    for i, m in enumerate(matches, 1):
        groups = m.groupdict()
        if groups:
            lines.append(f"  #{i}:")
            for name, value in groups.items():
                lines.append(f"    {name}: {value}")
        else:
            lines.append(f"  #{i}: {m.group()}")

    return "\n".join(lines)
