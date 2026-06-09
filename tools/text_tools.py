"""Text tools — manipulate, analyze, and transform text."""
from __future__ import annotations

import hashlib
import re
import textwrap

from tools import tool


@tool(
    name="hash_text",
    description="Compute hash values of text (MD5, SHA1, SHA256).",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to hash",
            },
            "algorithm": {
                "type": "string",
                "description": "Hash algorithm: 'md5', 'sha1', 'sha256' (default 'sha256')",
                "enum": ["md5", "sha1", "sha256"],
            },
        },
        "required": ["text"],
    },
)
def hash_text(text: str, algorithm: str = "sha256") -> str:
    algorithms = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
    }
    h = algorithms[algorithm](text.encode("utf-8")).hexdigest()
    return f"{algorithm}({text[:50]}{'...' if len(text) > 50 else ''}) = {h}"


@tool(
    name="text_analyze",
    description="Analyze text: character count, word count, sentence count, reading time.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to analyze",
            },
        },
        "required": ["text"],
    },
)
def text_analyze(text: str) -> str:
    chars = len(text)
    words = len(text.split())
    sentences = len(re.split(r'[.!?]+', text))
    paragraphs = len([p for p in text.split('\n\n') if p.strip()])
    reading_time_min = words / 200  # average reading speed
    speaking_time_min = words / 130  # average speaking speed

    lines = [f"Text Analysis:"]
    lines.append(f"  Characters: {chars}")
    lines.append(f"  Words: {words}")
    lines.append(f"  Sentences: {sentences}")
    lines.append(f"  Paragraphs: {paragraphs}")
    lines.append(f"  Avg word length: {chars/words:.1f} chars" if words > 0 else "")
    lines.append(f"  Reading time: {reading_time_min:.1f} min")
    lines.append(f"  Speaking time: {speaking_time_min:.1f} min")

    return "\n".join(l for l in lines if l)


@tool(
    name="text_transform",
    description="Transform text: uppercase, lowercase, title case, reverse, or truncate.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to transform",
            },
            "operation": {
                "type": "string",
                "description": "Operation: 'upper', 'lower', 'title', 'reverse', 'truncate' (default 'upper')",
                "enum": ["upper", "lower", "title", "reverse", "truncate"],
            },
            "length": {
                "type": "integer",
                "description": "Max length for truncate operation (default 100)",
            },
        },
        "required": ["text"],
    },
)
def text_transform(text: str, operation: str = "upper", length: int = 100) -> str:
    if operation == "upper":
        return text.upper()
    elif operation == "lower":
        return text.lower()
    elif operation == "title":
        return text.title()
    elif operation == "reverse":
        return text[::-1]
    elif operation == "truncate":
        if len(text) <= length:
            return text
        return text[:length] + "..."
    return f"error: unknown operation '{operation}'"


@tool(
    name="wrap_text",
    description="Wrap text to a specific width. Use to format long text into readable lines.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to wrap",
            },
            "width": {
                "type": "integer",
                "description": "Line width (default 80)",
            },
        },
        "required": ["text"],
    },
)
def wrap_text(text: str, width: int = 80) -> str:
    return textwrap.fill(text, width=width)


@tool(
    name="count_words",
    description="Count words, characters, and sentences in the user's clipboard or provided text.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to count (or leave empty to use clipboard)",
            },
        },
        "required": [],
    },
)
def count_words(text: str = "") -> str:
    if not text:
        try:
            import pyperclip
            text = pyperclip.paste()
        except Exception:
            return "error: no text provided and clipboard unavailable"

    if not text.strip():
        return "No text to count."

    words = len(text.split())
    chars = len(text)
    chars_no_spaces = len(text.replace(" ", ""))
    sentences = len(re.split(r'[.!?]+', text))

    return f"Words: {words}, Characters: {chars} ({chars_no_spaces} without spaces), Sentences: {sentences}"
