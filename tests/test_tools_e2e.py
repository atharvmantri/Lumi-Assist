"""End-to-end tool smoke test — no mic, no TTS playback. Verifies:
  - Knowledge questions skip tools entirely
  - Tool-calling questions trigger the right tool + read the result
  - Multi-step intents chain tool calls
  - run_python actually executes Python and returns its output

Run:  venv/Scripts/python.exe tests/test_tools_e2e.py
"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force UTF-8 so non-ASCII output doesn't crash on Windows cp1252 default.
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from core import executor                       # noqa: E402, F401 — loads tools
from core.llm import LLMClient                  # noqa: E402


def run_one(client: LLMClient, prompt: str, expect_tool: bool, expect_tool_name: str | None) -> tuple[bool, str]:
    """Send `prompt`. Return (passed, summary)."""
    tools_used: list[str] = []

    def on_tool(event: str, payload: dict) -> None:
        if event == "call":
            tools_used.append(payload["name"])
            args = payload.get("args") or {}
            args_repr = ", ".join(f"{k}={v!r}" for k, v in args.items())
            if len(args_repr) > 100:
                args_repr = args_repr[:100] + "..."
            print(f"    [→tool] {payload['name']}({args_repr})")
        elif event == "result":
            r = str(payload.get("result", "")).replace("\n", " ⏎ ")
            if len(r) > 160:
                r = r[:160] + "..."
            print(f"    [←tool] {payload['name']}: {r}")

    print(f"\nyou> {prompt}")
    print("jarvis> ", end="", flush=True)
    t0 = time.perf_counter()
    reply_parts: list[str] = []
    for tok in client.stream(prompt, tools=executor.get_schemas(), on_tool_event=on_tool):
        sys.stdout.write(tok)
        sys.stdout.flush()
        reply_parts.append(tok)
    elapsed = time.perf_counter() - t0
    print(f"  [{elapsed:.1f}s, tools={tools_used}]")
    reply = "".join(reply_parts).strip()

    # Verdict
    if expect_tool:
        if not tools_used:
            return False, f"expected a tool call (looking for {expect_tool_name}); got none"
        if expect_tool_name and expect_tool_name not in tools_used:
            return False, f"expected tool {expect_tool_name!r} in {tools_used}"
    else:
        if tools_used:
            return False, f"expected NO tool call; got {tools_used}"
    if not reply:
        return False, "empty reply"
    return True, f"ok ({elapsed:.1f}s)"


def main() -> int:
    client = LLMClient()
    print(f"[setup] {len(executor.list_tools())} tools registered, sys_chars={len(client.system_prompt)}")

    tests: list[tuple[str, bool, str | None]] = [
        # (prompt, expect_a_tool_call, expected_tool_name_or_None)
        ("What's two times seventeen? Answer in one short sentence, no tools.", False, None),
        ("Read whatever's in my clipboard right now and tell me what it is in one sentence.", True, "clipboard_read"),
        ("Use the list_dir tool to count entries in the current directory. Reply with just the count.", True, "list_dir"),
        # Yesterday's failures with Nemotron's streaming tool-call corruption:
        ("Use run_python to print the current CPU usage percent via psutil. Reply with just the number.", True, "run_python"),
        ("Use run_python to print how much RAM I'm using in GB (psutil.virtual_memory().used / 1e9). One sentence.", True, "run_python"),
        # Today's failures from the real voice loop:
        ("Get the title of the top Hacker News story right now and read it to me.", True, "run_python"),
        ("Take a screenshot.", True, "take_screenshot"),
        # Web search via ddgs:
        ("Search the web for the current temperature in Mumbai and tell me in one sentence.", True, "web_search"),
    ]

    results = []
    for prompt, expect_tool, name in tests:
        passed, summary = run_one(client, prompt, expect_tool, name)
        results.append((prompt, passed, summary))
        # New conversation per test so previous tool calls don't bias the next
        client.reset()

    print("\n" + "=" * 60)
    passed_n = sum(1 for _, p, _ in results if p)
    for prompt, passed, summary in results:
        flag = "PASS" if passed else "FAIL"
        print(f"  [{flag}] {prompt[:60]}  →  {summary}")
    print(f"\n{passed_n}/{len(results)} tests passed")
    return 0 if passed_n == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
