"""Clipboard text transformation tools."""
from __future__ import annotations

import re

from tools import tool


@tool(
    name="transform_clipboard",
    description="Transform clipboard text: uppercase, lowercase, title case, camelCase, snake_case, kebab-case, reverse, trim, deduplicate lines.",
    parameters={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Transformation: 'upper', 'lower', 'title', 'camel', 'snake', 'kebab', 'reverse', 'trim', 'dedup', 'sort', 'shuffle', 'number_lines'",
                "enum": ["upper", "lower", "title", "camel", "snake", "kebab", "reverse", "trim", "dedup", "sort", "shuffle", "number_lines"],
            },
        },
        "required": ["operation"],
    },
)
def transform_clipboard(operation: str) -> str:
    try:
        import pyperclip
    except ImportError:
        return "error: pyperclip not installed"

    try:
        text = pyperclip.paste()
    except Exception as e:
        return f"error reading clipboard: {e}"

    if not text:
        return "Clipboard is empty."

    if operation == "upper":
        result = text.upper()
    elif operation == "lower":
        result = text.lower()
    elif operation == "title":
        result = text.title()
    elif operation == "reverse":
        result = text[::-1]
    elif operation == "trim":
        lines = [l.strip() for l in text.split("\n")]
        result = "\n".join(l for l in lines if l)
    elif operation == "dedup":
        lines = text.split("\n")
        seen = set()
        unique = []
        for l in lines:
            if l not in seen:
                seen.add(l)
                unique.append(l)
        result = "\n".join(unique)
    elif operation == "sort":
        lines = text.split("\n")
        result = "\n".join(sorted(lines, key=str.lower))
    elif operation == "shuffle":
        import random
        lines = text.split("\n")
        random.shuffle(lines)
        result = "\n".join(lines)
    elif operation == "number_lines":
        lines = text.split("\n")
        result = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
    elif operation == "camel":
        words = re.findall(r'\b\w+\b', text)
        if words:
            result = words[0].lower() + ''.join(w.title() for w in words[1:])
        else:
            result = text
    elif operation == "snake":
        words = re.findall(r'\b\w+\b', text)
        result = "_".join(w.lower() for w in words)
    elif operation == "kebab":
        words = re.findall(r'\b\w+\b', text)
        result = "-".join(w.lower() for w in words)
    else:
        return f"error: unknown operation '{operation}'"

    try:
        pyperclip.copy(result)
    except Exception as e:
        return f"error writing clipboard: {e}"

    return f"Transformed clipboard: {operation} ({len(result)} chars)"


@tool(
    name="extract_emails",
    description="Extract email addresses from clipboard text.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def extract_emails() -> str:
    try:
        import pyperclip
    except ImportError:
        return "error: pyperclip not installed"

    try:
        text = pyperclip.paste()
    except Exception as e:
        return f"error reading clipboard: {e}"

    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if not emails:
        return "No email addresses found in clipboard."

    unique = list(set(emails))
    lines = [f"Email Addresses ({len(unique)}):"]
    for e in sorted(unique):
        lines.append(f"  {e}")
    return "\n".join(lines)


@tool(
    name="extract_urls",
    description="Extract URLs from clipboard text.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def extract_urls() -> str:
    try:
        import pyperclip
    except ImportError:
        return "error: pyperclip not installed"

    try:
        text = pyperclip.paste()
    except Exception as e:
        return f"error reading clipboard: {e}"

    urls = re.findall(r'https?://[^\s<>"\')\]]+', text)
    if not urls:
        return "No URLs found in clipboard."

    unique = list(set(urls))
    lines = [f"URLs ({len(unique)}):"]
    for u in sorted(unique):
        lines.append(f"  {u}")
    return "\n".join(lines)
