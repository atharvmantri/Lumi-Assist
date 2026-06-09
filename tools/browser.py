"""Web search + opening URLs in the user's default browser."""
from __future__ import annotations

import webbrowser

from tools import tool


@tool(
    name="open_url",
    description=(
        "Open a URL in the user's default web browser. Use when the user asks "
        "to 'open <site>', 'go to <url>', or after a web_search when they want "
        "to visit a specific result."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Full URL (must include https:// or http://)"},
        },
        "required": ["url"],
    },
)
def open_url(url: str) -> str:
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    try:
        webbrowser.open(url, new=2)   # new=2 → new tab
        return f"opened {url}"
    except Exception as e:  # noqa: BLE001
        return f"error opening url: {e}"


@tool(
    name="web_search",
    description=(
        "Search the web (DuckDuckGo) and return the top results. Use this when "
        "the user asks for current information, news, prices, definitions, or "
        "anything that needs real-time data. Returns a numbered list of "
        "{title, url, snippet}."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "How many results (default 5, max 10)", "default": 5},
        },
        "required": ["query"],
    },
)
def web_search(query: str, max_results: int = 5) -> str:
    max_results = max(1, min(int(max_results or 5), 10))
    # ddgs is the renamed successor of duckduckgo-search; same DDGS API.
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # type: ignore[no-redef]
        except ImportError:
            return "error: neither `ddgs` nor `duckduckgo-search` is installed"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:  # noqa: BLE001
        return f"error searching: {e}"

    if not results:
        return f"no results for {query!r}"

    lines = []
    for i, r in enumerate(results, 1):
        title = (r.get("title") or "").strip()
        href = (r.get("href") or r.get("url") or "").strip()
        snippet = (r.get("body") or r.get("snippet") or "").strip()
        lines.append(f"{i}. {title}\n   {href}\n   {snippet[:200]}")
    return "\n\n".join(lines)
