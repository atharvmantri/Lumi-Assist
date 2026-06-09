"""Tier-7 hard stress tests against the current free-Mistral model.

Each test sends a prompt, captures the Lumi reply, and runs one of three
validators on it:
  - has_tool(name)   — at least one of these tool names fired
  - replies_contain(substrs) — case-insensitive substrings must all appear
  - replies_dont_contain(substrs) — anti-patterns (e.g. fake JSON tool calls)

A turn is considered a PASS only if the reply is non-empty AND the validator
passes AND Lumi didn't bail with the 'I'm stuck' doom-loop message.

Run:  venv/Scripts/python.exe tests/test_hard.py
"""
from __future__ import annotations

import io
import re
import sys
import time
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from core import executor                           # noqa: E402
from core.llm import LLMClient                      # noqa: E402


Validator = Callable[[str, list[str]], tuple[bool, str]]


def make_validator(
    *,
    has_tool: list[str] | None = None,
    must_contain: list[str] | None = None,
    must_not_contain: list[str] | None = None,
) -> Validator:
    has_tool = [t.lower() for t in (has_tool or [])]
    must_contain = [s.lower() for s in (must_contain or [])]
    must_not_contain = [s.lower() for s in (must_not_contain or [])]

    def validate(reply: str, tools_used: list[str]) -> tuple[bool, str]:
        if "i'm stuck" in reply.lower() or "i tried the same" in reply.lower():
            return False, "doom-loop guard fired"
        if has_tool:
            if not any(t in [u.lower() for u in tools_used] for t in has_tool):
                return False, f"no tool fired (expected one of {has_tool}, got {tools_used})"
        rl = reply.lower()
        for s in must_contain:
            if s.lower() not in rl:
                return False, f"reply missing required phrase {s!r}"
        for s in must_not_contain:
            if s.lower() in rl:
                return False, f"reply contains anti-pattern {s!r}"
        return True, "ok"

    return validate


TESTS: list[tuple[str, str, Validator]] = [
    # -------- Numerical / stateful --------
    ("primes-1-100",
     "How many prime numbers are there between 1 and 100? Just the count, no tool needed.",
     make_validator(must_contain=["25"])),

    ("2^53+1-overflow",
     "What is 2^53 + 1, and is that result larger than what a normal 64-bit integer can hold?",
     make_validator(must_contain=["9007199254740993"])),

    ("lumi-uptime",
     "How many seconds have I been running this Lumi process? Use run_python to find the current process uptime.",
     make_validator(has_tool=["run_python"], must_contain=["second"])),

    # -------- Live data --------
    ("bitcoin-price",
     "What is the current price of Bitcoin in USD right now? Search the web if you have to.",
     make_validator(has_tool=["web_search"], must_contain=["$"])),

    ("sunlight-time",
     "How many seconds does it take light to travel from the Sun to Earth? (about 150 million km, light goes 300,000 km/s)",
     make_validator(must_contain=["500"])),

    ("mosteller-bsa",
     "Calculate the body surface area in square meters for a 180cm tall, 75kg person using the Mosteller formula. Show me the formula and the result.",
     make_validator(has_tool=["run_python"], must_contain=["mosteller"])),

    # -------- Multi-step chains --------
    ("hn-direct-fetch",
     "Get the title of the top story on Hacker News right now. Use run_python to call the HN API at https://hacker-news.firebaseio.com/v0/topstories.json and fetch the first item's title directly — do NOT just trust the web search snippet.",
     make_validator(has_tool=["run_python", "web_search"], must_not_contain=["f-string"])),

    ("open-notepad-then-active",
     "Open Notepad, then tell me what window title is in the foreground.",
     make_validator(has_tool=["open_app"], must_contain=["notepad"])),

    ("largest-py-clipboard-read",
     "Find the largest .py file in this project, copy its name to the clipboard, then read the first 10 lines of it and tell me what it does. Reply in two short sentences.",
     make_validator(has_tool=["run_python", "clipboard_write", "read_file"])),

    # -------- Robustness --------
    ("hn-top-3",
     "Get the titles of the top 3 stories on Hacker News right now. Use run_python to fetch them directly from the HN API. Reply with just the three titles, one per line.",
     make_validator(has_tool=["run_python"], must_not_contain=["f-string"])),

    ("anthropic-news",
     "Search the web for the most recent news about Anthropic and give me a one-sentence summary.",
     make_validator(has_tool=["web_search"])),

    ("battery-status",
     "Run psutil.sensors_battery() in Python and tell me my charging status. If I have no battery, just say so.",
     make_validator(has_tool=["run_python"], must_contain=["battery"])),

    # -------- Judgment / off-script --------
    ("csv-read-no-file",
     "Imagine I have a CSV file at downloads/test.csv. Without actually reading the file, show me the Python code to read its first 5 rows. Just the code, don't run anything.",
     make_validator(must_contain=["read_csv", "csv", "pandas"])),

    ("fib20",
     "Write a Python one-liner to compute the first 20 Fibonacci numbers. Use .format() for any string output, NOT f-strings. Then run it and show me the result.",
     make_validator(has_tool=["run_python"], must_not_contain=["f-string"])),

    ("open-youtube-then-list",
     "Open YouTube in my browser, wait a moment, then list my open windows.",
     make_validator(has_tool=["open_url"], must_contain=["window"])),

    # -------- Tooling weirdness --------
    ("screenshot-then-window-count",
     "Take a screenshot, then tell me how many windows are visible right now (not minimized). Reply with just the count.",
     make_validator(has_tool=["take_screenshot"])),

    ("clipboard-word-count",
     "Read my clipboard, then count how many words are in it. Reply with just the number.",
     make_validator(has_tool=["clipboard_read"])),

    ("python-processes",
     "Use run_python to list the process names that have 'python' in them right now. Reply with just the first 5 names, one per line.",
     make_validator(has_tool=["run_python"], must_contain=["python"])),

    # -------- Conversational stress --------
    ("giraffe-fun-fact",
     "Tell me one fun fact about giraffes in one sentence, then copy that sentence to my clipboard.",
     make_validator(has_tool=["clipboard_write"], must_contain=["giraffe"])),

    ("reverse-string",
     "Reverse the string 'Lumi is online' and tell me the result. Just the reversed string.",
     make_validator(must_contain=["enilno si SIVRAJ"])),

    ("meaning-of-life",
     "What is the meaning of life, the universe, and everything?",
     make_validator(must_contain=["42"])),

    # -------- Hardcore --------
    ("main-py-first-3-lines",
     "Use run_python to read the file main.py in this project and tell me its first 3 lines, exactly as they appear.",
     make_validator(has_tool=["run_python"], must_contain=["main"])),

    ("sha256-lumi",
     "Use run_python to compute the SHA-256 hash of the string 'lumi' and tell me the first 8 hex characters.",
     make_validator(has_tool=["run_python"])),

    ("sum-1-to-100",
     "Compute, in one line of Python, the sum of all integers from 1 to 100. Show me the code and the result. (No f-strings.)",
     make_validator(has_tool=["run_python"], must_contain=["5050"], must_not_contain=["f-string"])),

    # -------- NEW: the 6 new power tools --------
    ("disk-usage-c",
     "How much disk space is free on C: drive? Just give me the number in GB.",
     make_validator(has_tool=["get_disk_usage"])),

    ("gpu-stats",
     "Tell me my current GPU temperature in degrees C. Use the get_gpu_stats tool.",
     make_validator(has_tool=["get_gpu_stats"], must_contain=["°C", "GPU"])),

    ("compress-folder",
     "Create a folder called notes_test, put a file in it called hi.txt that says 'hi', then compress the folder to a .zip. Use run_python for the folder+file creation, then compress_folder for the zip.",
     make_validator(has_tool=["run_python", "compress_folder"])),

    ("lock-workstation-tool",
     "Lock my workstation.",
     make_validator(has_tool=["lock_workstation"], must_contain=["lock"])),

    ("shutdown-safety",
     "Shut down my PC.",
     make_validator(has_tool=["shutdown_pc"])),

    ("shutdown-safety-check",
     "If you can read the last 3 lines of the shutdown_pc tool result above, tell me whether the system accepted the request or refused it, and why.",
     make_validator(must_contain=["refus"])),
]


def run_one(client: LLMClient, label: str, prompt: str, validator: Validator) -> tuple[bool, str]:
    tools_used: list[str] = []

    def on_tool(event: str, payload: dict) -> None:
        if event == "call":
            tools_used.append(payload["name"])
            args = payload.get("args") or {}
            args_repr = ", ".join(f"{k}={v!r}" for k, v in args.items())
            if len(args_repr) > 80:
                args_repr = args_repr[:80] + "..."
            print(f"    [→tool] {payload['name']}({args_repr})")
        elif event == "result":
            r = str(payload.get("result", "")).replace("\n", " ⏎ ")
            if len(r) > 140:
                r = r[:140] + "..."
            print(f"    [←tool] {payload['name']}: {r}")

    print(f"\n--- {label} ---")
    print(f"  you: {prompt}")
    t0 = time.perf_counter()
    reply_parts: list[str] = []
    try:
        for tok in client.stream(prompt, tools=executor.get_schemas(), on_tool_event=on_tool):
            sys.stdout.write(tok)
            sys.stdout.flush()
            reply_parts.append(tok)
    except Exception as e:  # noqa: BLE001
        print(f"\n  EXCEPTION: {e}")
        return False, str(e)[:120]
    elapsed = time.perf_counter() - t0
    print()
    print(f"  [{elapsed:.1f}s  tools={tools_used}]")
    reply = "".join(reply_parts).strip()
    ok, summary = validator(reply, tools_used)
    return ok, summary


def main() -> int:
    client = LLMClient()
    print(f"[setup] model={client.model}")
    print(f"[setup] {len(executor.list_tools())} tools, sys_chars={len(client.system_prompt)}")

    results: list[tuple[str, bool, str]] = []
    for label, prompt, validator in TESTS:
        ok, summary = run_one(client, label, prompt, validator)
        flag = "PASS" if ok else "FAIL"
        print(f"  [{flag}] {label}  →  {summary}")
        results.append((label, ok, summary))
        client.reset()    # fresh context per test

    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in results if p)
    print(f"\n{passed}/{len(results)} hard tests passed")
    if passed < len(results):
        print("\nFailures:")
        for label, ok, summary in results:
            if not ok:
                print(f"  - {label}: {summary}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
