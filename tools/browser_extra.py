"""Browser automation — open, navigate, screenshot, fill forms."""
from __future__ import annotations

import subprocess
import time

from tools import tool


@tool(
    name="open_url_in_browser",
    description="Open a URL in the user's default web browser.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full URL to open (e.g. 'https://google.com')",
            },
        },
        "required": ["url"],
    },
)
def open_url_in_browser(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        import webbrowser
        webbrowser.open(url)
        return f"opened {url} in default browser"
    except Exception as e:
        return f"error opening URL: {e}"


@tool(
    name="browser_search",
    description="Open a web browser and search for the given query using Google.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
        },
        "required": ["query"],
    },
)
def browser_search(query: str) -> str:
    import urllib.parse
    import webbrowser
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    try:
        webbrowser.open(url)
        return f"searched Google for: {query}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="open_browser_devtools",
    description="Open browser developer tools. Sends F12 key to the active window.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def open_browser_devtools() -> str:
    try:
        import pyautogui
        pyautogui.press("f12")
        return "sent F12 to open dev tools"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="refresh_page",
    description="Refresh the current browser page (sends F5).",
    parameters={"type": "object", "properties": {}, "required": []},
)
def refresh_page() -> str:
    try:
        import pyautogui
        pyautogui.press("f5")
        return "refreshed page"
    except Exception as e:
        return f"error: {e}"
