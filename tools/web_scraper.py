"""Web scraping tools — fetch and extract content from web pages."""
from __future__ import annotations

import re
import urllib.request
import urllib.parse

from tools import tool


@tool(
    name="fetch_page",
    description="Fetch a web page and extract its text content (strips HTML).",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (default 3000)",
            },
        },
        "required": ["url"],
    },
)
def fetch_page(url: str, max_chars: int = 3000) -> str:
    import time as _time
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        t0 = _time.perf_counter()
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed = _time.perf_counter() - t0
            html = resp.read().decode("utf-8", errors="replace")

            # Strip HTML
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            status = resp.status
            content_type = resp.headers.get("Content-Type", "")

            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n... ({len(text) - max_chars} more chars)"

            return (
                f"GET {url} → {status} ({elapsed*1000:.0f}ms)\n"
                f"Content-Type: {content_type}\n\n{text[:max_chars+200]}"
            )
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"URL unreachable: {e.reason}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="fetch_page_links",
    description="Extract all links from a web page.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to extract links from",
            },
        },
        "required": ["url"],
    },
)
def fetch_page_links(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")

        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Extract href links
        links = re.findall(r'href=["\']([^"\']+)["\']', html)

        # Filter to unique
        seen = set()
        unique = []
        for l in links:
            if l not in seen and not l.startswith(("javascript:", "mailto:")):
                seen.add(l)
                unique.append(l)

        if not unique:
            return f"No links found on {url}"

        lines = [f"Links on {url} ({len(unique)}):"]
        for l in unique[:50]:
            lines.append(f"  {l}")
        if len(unique) > 50:
            lines.append(f"  ...and {len(unique)-50} more")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="fetch_page_images",
    description="Extract all image URLs from a web page.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to extract images from",
            },
        },
        "required": ["url"],
    },
)
def fetch_page_images(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")

        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Extract image sources
        images = re.findall(r'src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp|svg|avif))["\']', html, re.IGNORECASE)
        images += re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html)

        seen = set()
        unique = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique.append(img)

        if not unique:
            return f"No images found on {url}"

        lines = [f"Images on {url} ({len(unique)}):"]
        for img in unique[:30]:
            lines.append(f"  {img}")
        if len(unique) > 30:
            lines.append(f"  ...and {len(unique)-30} more")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"
