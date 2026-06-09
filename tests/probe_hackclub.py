"""Direct low-level probe of HackClub's API — bypasses the openai SDK to see
the raw HTTP status, headers, and a short error body. Diagnostic only.

Run:  venv/Scripts/python.exe tests/probe_hackclub.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make repo root importable so we can re-use config.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from core.config import get_env, load_config

cfg = load_config()
key = get_env(cfg["llm"]["api_key_env"], required=True)
base = cfg["llm"]["base_url"].rstrip("/")
model = cfg["llm"]["model"]

print(f"key prefix : {key[:8]}…  (len={len(key)})")
print(f"base_url   : {base}")
print(f"model      : {model}")
print()


def show(resp: requests.Response, label: str) -> None:
    print(f"=== {label} ===")
    print(f"  status : {resp.status_code} {resp.reason}")
    ctype = resp.headers.get("content-type", "")
    print(f"  ctype  : {ctype}")
    body = resp.text
    # Strip HTML noise — keep only the first 600 chars of either JSON or plain text.
    snippet = body[:600].replace("\n", " ⏎ ")
    if "html" in ctype.lower():
        snippet = f"(HTML body, {len(body)} chars; first 200 of <title>+<body>)"
        # Try to grab the page title
        import re
        m = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
        if m:
            snippet += f"  title='{m.group(1).strip()}'"
    print(f"  body   : {snippet}")
    print()


# Probe 1: /models — does it list anything? Does our key work for auth at all?
try:
    r = requests.get(
        f"{base}/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=15,
    )
    show(r, "GET /models (with Bearer key)")
except Exception as e:
    print(f"GET /models  raised {type(e).__name__}: {e}\n")

# Probe 2: /models without auth — HackClub's proxy may not require auth for listing
try:
    r = requests.get(f"{base}/models", timeout=15)
    show(r, "GET /models (no auth)")
except Exception as e:
    print(f"GET /models  raised {type(e).__name__}: {e}\n")

# Probe 3: minimal chat completion, NON-streaming, with auth header
payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Say HELLO."}],
    "max_tokens": 20,
    "stream": False,
}
try:
    r = requests.post(
        f"{base}/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=30,
    )
    show(r, "POST /chat/completions (Bearer, non-stream)")
except Exception as e:
    print(f"POST /chat/completions raised {type(e).__name__}: {e}\n")

# Probe 4: same chat call WITHOUT auth (HackClub's proxy historically didn't need it)
try:
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30,
    )
    show(r, "POST /chat/completions (no auth, non-stream)")
except Exception as e:
    print(f"POST /chat/completions (no auth) raised {type(e).__name__}: {e}\n")

# Probe 5: try the same chat call with the alternative model name (no :free)
payload_alt = dict(payload, model=model.replace(":free", ""))
try:
    r = requests.post(
        f"{base}/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload_alt),
        timeout=30,
    )
    show(r, f"POST /chat/completions (model='{payload_alt['model']}')")
except Exception as e:
    print(f"POST /chat/completions (alt model) raised {type(e).__name__}: {e}\n")
