"""Markdown and HTML utilities."""
from __future__ import annotations

import html
import re

from tools import tool


@tool(
    name="markdown_to_html",
    description="Convert markdown text to HTML.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Markdown text to convert",
            },
        },
        "required": ["text"],
    },
)
def markdown_to_html(text: str) -> str:
    lines = text.split("\n")
    html_lines = []
    in_list = False
    in_code = False

    for line in lines:
        # Code blocks
        if line.startswith("```"):
            if in_code:
                html_lines.append("</code></pre>")
                in_code = False
            else:
                html_lines.append("<pre><code>")
                in_code = True
            continue

        if in_code:
            html_lines.append(html.escape(line))
            continue

        # Headers
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            html_lines.append(f"<h{level}>{header_match.group(2)}</h{level}>")
            continue

        # Lists
        list_match = re.match(r'^[\s]*[-*]\s+(.+)$', line)
        if list_match:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"  <li>{list_match.group(1)}</li>")
            continue
        elif in_list:
            html_lines.append("</ul>")
            in_list = False

        # Empty lines
        if not line.strip():
            html_lines.append("<br>")
            continue

        # Bold and italic
        processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        processed = re.sub(r'(?<![*\w])\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', processed)
        processed = re.sub(r'`([^`]+?)`', r'<code>\1</code>', processed)

        # Links
        processed = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', processed)

        html_lines.append(f"<p>{processed}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_code:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


@tool(
    name="html_to_text",
    description="Convert HTML to plain text (strip all tags).",
    parameters={
        "type": "object",
        "properties": {
            "html_text": {
                "type": "string",
                "description": "HTML text to convert",
            },
        },
        "required": ["html_text"],
    },
)
def html_to_text(html_text: str) -> str:
    # Remove script and style
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    # Remove all tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode entities
    text = html.unescape(text)
    # Clean whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


@tool(
    name="json_to_markdown",
    description="Convert a JSON object to a readable markdown table or list.",
    parameters={
        "type": "object",
        "properties": {
            "json_text": {
                "type": "string",
                "description": "JSON text to convert",
            },
        },
        "required": ["json_text"],
    },
)
def json_to_markdown(json_text: str) -> str:
    import json
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        return f"error: invalid JSON: {e}"

    if isinstance(data, dict):
        lines = ["| Key | Value |", "|---|---|"]
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v)
            lines.append(f"| {k} | {str(v)[:100]} |")
        return "\n".join(lines)
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            headers = list(data[0].keys())
            lines = ["| " + " | ".join(headers) + " |"]
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for item in data:
                row = " | ".join(str(item.get(h, ""))[:50] for h in headers)
                lines.append(f"| {row} |")
            return "\n".join(lines)
        return "\n".join(f"- {item}" for item in data)
    return str(data)
