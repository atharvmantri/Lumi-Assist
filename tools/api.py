"""API testing tools — make HTTP requests."""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse

from tools import tool


@tool(
    name="http_get",
    description="Make an HTTP GET request to a URL and return the response.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to GET",
            },
            "headers": {
                "type": "string",
                "description": "Optional JSON string of headers (e.g. '{\"Authorization\": \"Bearer ...\"}')",
            },
        },
        "required": ["url"],
    },
)
def http_get(url: str, headers: str = "") -> str:
    import time as _time
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "JARVIS/1.0")

        if headers:
            try:
                header_dict = json.loads(headers)
                for k, v in header_dict.items():
                    req.add_header(k, v)
            except json.JSONDecodeError:
                return f"error: invalid headers JSON"

        t0 = _time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = _time.perf_counter() - t0
            status = resp.status
            data = resp.read()

            # Try to decode as JSON
            try:
                content = data.decode("utf-8")
                parsed = json.loads(content)
                return f"GET {url} → {status} ({elapsed*1000:.0f}ms)\n\n{json.dumps(parsed, indent=2, ensure_ascii=False)[:4000]}"
            except (json.JSONDecodeError, UnicodeDecodeError):
                size = len(data)
                text = data.decode("utf-8", errors="replace")[:1000]
                return f"GET {url} → {status} ({elapsed*1000:.0f}ms, {size:,} bytes)\n\n{text[:1000]}"

    except urllib.error.HTTPError as e:
        return f"GET {url} → HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"GET {url} → unreachable: {e.reason}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="http_post",
    description="Make an HTTP POST request with JSON body.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to POST to",
            },
            "body": {
                "type": "string",
                "description": "JSON body to send",
            },
        },
        "required": ["url", "body"],
    },
)
def http_post(url: str, body: str) -> str:
    import time as _time
    try:
        data = body.encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "JARVIS/1.0")

        t0 = _time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = _time.perf_counter() - t0
            status = resp.status
            response_data = resp.read().decode("utf-8")

            try:
                parsed = json.loads(response_data)
                return f"POST {url} → {status} ({elapsed*1000:.0f}ms)\n\n{json.dumps(parsed, indent=2, ensure_ascii=False)[:4000]}"
            except (json.JSONDecodeError, ValueError):
                return f"POST {url} → {status} ({elapsed*1000:.0f}ms)\n\n{response_data[:1000]}"

    except Exception as e:
        return f"error: {e}"


@tool(
    name="http_head",
    description="Make an HTTP HEAD request to check if a URL is accessible.",
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to HEAD",
            },
        },
        "required": ["url"],
    },
)
def http_head(url: str) -> str:
    import time as _time
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "JARVIS/1.0")

        t0 = _time.perf_counter()
        with urllib.request.urlopen(req, timeout=10) as resp:
            elapsed = _time.perf_counter() - t0
            headers = dict(resp.headers)

            lines = [f"HEAD {url} → {resp.status} ({elapsed*1000:.0f}ms)"]
            for key in ["Content-Type", "Content-Length", "Server", "Last-Modified", "ETag"]:
                if key in headers:
                    lines.append(f"  {key}: {headers[key]}")

            return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"
