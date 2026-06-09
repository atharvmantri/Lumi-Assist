"""Export conversations to a simple HTML viewer."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT
from core.conversation_log import load_dataset
from tools import tool

LOG_DIR = PROJECT_ROOT / "data" / "conversations"


@tool(
    name="export_conversations_html",
    description=(
        "Export recent conversations to an HTML file you can open in a browser. "
        "Useful for reviewing conversation history visually. "
        "Returns the path to the HTML file."
    ),
    parameters={
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "How many days back to export (default 7, max 30)",
            },
        },
        "required": [],
    },
)
def export_conversations_html(days: int = 7) -> str:
    if not LOG_DIR.exists():
        return "error: no conversation history found"

    days = min(days, 30)
    entries = load_dataset(days=days)
    if not entries:
        return f"error: no conversations in the last {days} days"

    # Build HTML
    rows = []
    for e in entries:
        ts = e.get("timestamp", "?")
        user = html.escape(e.get("user", ""))
        assistant = html.escape(e.get("assistant", ""))
        tools_used = len(e.get("tools", []))
        mode = e.get("mode", "?")
        total_s = e.get("metrics", {}).get("total_s", 0)

        tool_badge = ""
        if tools_used > 0:
            tool_names = ", ".join(t.get("name", "") for t in e["tools"][:3])
            tool_badge = f' <span class="tool-badge">{tools_used} tool(s): {html.escape(tool_names)}</span>'

        rows.append(
            f'<div class="turn">'
            f'<div class="meta">{ts} <span class="mode">{mode}</span> <span class="timing">{total_s:.1f}s</span>{tool_badge}</div>'
            f'<div class="user"><strong>You:</strong> {user}</div>'
            f'<div class="assistant"><strong>JARVIS:</strong> {assistant}</div>'
            f"</div>"
        )

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>JARVIS Conversations — Last {days} Days</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #eee; }}
  h1 {{ color: #f0c040; border-bottom: 2px solid #333; padding-bottom: 10px; }}
  .stats {{ background: #252540; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
  .turn {{ background: #252540; border-radius: 8px; padding: 15px; margin-bottom: 10px; }}
  .meta {{ font-size: 0.8em; color: #888; margin-bottom: 8px; }}
  .mode {{ background: #444; padding: 2px 6px; border-radius: 4px; }}
  .timing {{ color: #aaa; }}
  .tool-badge {{ background: #1a3a5c; color: #4da6ff; padding: 2px 6px; border-radius: 4px; }}
  .user {{ color: #ddd; margin-bottom: 5px; }}
  .assistant {{ color: #f0c040; }}
  .stats span {{ color: #f0c040; font-weight: bold; }}
</style>
</head>
<body>
<h1>🤖 JARVIS Conversations</h1>
<div class="stats">
  <span>{len(entries)}</span> turns in the last <span>{days}</span> days &middot;
  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>
{''.join(rows)}
</body>
</html>"""

    out_path = PROJECT_ROOT / "data" / f"conversations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")

    return f"Exported {len(entries)} turns to {out_path} — open in your browser to review."
