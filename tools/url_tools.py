"""URL shortener via free APIs."""
from __future__ import annotations

import urllib.request
import json

from tools import tool


@tool(
    name="shorten_url",
    description="Shorten a long URL using a free URL shortening service.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The long URL to shorten",
            },
        },
        "required": ["url"],
    },
)
def shorten_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        # Use is.gd (free, no API key)
        api_url = f"https://is.gd/create.php?format=json&url={urllib.request.quote(url, safe=':/')}"
        with urllib.request.urlopen(api_url, timeout=10) as resp:
            data = json.loads(resp.read())

        if "shorturl" in data:
            return f"Shortened URL:\n  Original: {url}\n  Short: {data['shorturl']}"
        elif "errormessage" in data:
            return f"error: {data['errormessage']}"
        return f"error: unexpected response"
    except Exception as e:
        return f"error shortening URL: {e}"


@tool(
    name="expand_url",
    description="Expand a shortened URL to get the full destination URL.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The shortened URL to expand",
            },
        },
        "required": ["url"],
    },
)
def expand_url(url: str) -> str:
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            final_url = resp.url
            if final_url != url:
                return f"Expanded URL:\n  Short: {url}\n  Full: {final_url}"
            return f"URL is already the full URL: {url}"
    except Exception as e:
        return f"error expanding URL: {e}"


@tool(
    name="check_url",
    description="Check if a URL is accessible and get its HTTP status code and response time.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to check",
            },
        },
        "required": ["url"],
    },
)
def check_url(url: str) -> str:
    import time as _time
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        t0 = _time.perf_counter()
        with urllib.request.urlopen(url, timeout=10) as resp:
            elapsed = _time.perf_counter() - t0
            status = resp.status
            headers = dict(resp.headers)
            content_type = headers.get("Content-Type", "unknown")
            content_length = headers.get("Content-Length", "unknown")

            return (
                f"URL Status: {status} OK\n"
                f"  Response time: {elapsed*1000:.0f}ms\n"
                f"  Content-Type: {content_type}\n"
                f"  Size: {content_length} bytes"
            )
    except urllib.error.HTTPError as e:
        return f"URL returned HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL unreachable: {e.reason}"
    except Exception as e:
        return f"error checking URL: {e}"
