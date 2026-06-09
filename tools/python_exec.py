"""Arbitrary Python execution — the universal escape hatch.

This is Lumi's "do anything not covered by another tool" lever. The model
writes Python; we exec() it and hand back stdout / stderr / return value /
exception. Convenience imports are preloaded into the namespace so the model
doesn't burn tokens importing common modules.

Every execution is logged to logs/python_exec.log with timestamp + full source
+ result. That log is your forensic trail if Lumi ever does something weird.

Safety: this tool can do anything the user can. The system prompt instructs
the model to confirm before destructive operations. Treat this as a power
tool and trust both the model and your own ability to interrupt.
"""
from __future__ import annotations

import builtins
import contextlib
import io
import time
import traceback
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

_LOG_PATH = PROJECT_ROOT / "logs" / "python_exec.log"
_MAX_OUTPUT_CHARS = 6000      # truncate huge prints to keep the LLM context lean


def _looks_like_fragmented_json_not_code(s: str) -> bool:
    """Detect Nemotron's f-string-confusion failure mode.

    When the model's tool-call JSON streaming gets tripped up by f-string
    `{...}` braces, the `code` argument arrives as a dict/list literal whose
    string members contain nonsensical-as-Python fragments like
    {'print(f': 'memory: {percent'}. These compile cleanly (literals are
    valid Python), so we'd silently execute garbage. Catch them up front.

    Also catches the related failure mode where the model sends a top-level
    list/dict literal with no executable purpose — there's no legitimate
    reason to invoke `run_python` with just `[1, 2, 3]` as the source."""
    s = s.strip()
    if not s.startswith(("{", "[")):
        return False

    # Try to parse as a Python expression. If it isn't a single expression
    # (i.e. it's real source code that happens to start with [ or {), this fails.
    import ast
    try:
        node = ast.parse(s, mode="eval")
    except SyntaxError:
        # Starts with { or [ AND doesn't even parse as a literal expression?
        # Also try parsing as a full module — if THAT also fails, it's truly
        # malformed and we should reject (the model is mid-corruption).
        try:
            ast.parse(s, mode="exec")
            return False    # parses as code, just not as a single expression — OK
        except SyntaxError:
            return True     # neither expression nor statements parse → garbage
    if not isinstance(node, ast.Expression):
        return False
    expr = node.body
    if not isinstance(expr, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
        return False

    # If it's a pure literal expression at top level with no statements,
    # there's no point invoking run_python — it produces nothing. Flag it.
    # First check the smoking-gun fingerprints, then fall back to "useless literal".
    suspicious_markers = ("print(", "f'", 'f"', "import ", "def ", "except ", "Exception")
    for txt in _walk_string_constants(expr):
        if any(m in txt for m in suspicious_markers):
            return True
        if txt.count("{") != txt.count("}"):
            return True

    # No fingerprints, but it's still a useless top-level literal (the LLM
    # is confused, just send it back).
    return True


def _walk_string_constants(node) -> list[str]:
    import ast
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            out.append(child.value)
    return out


def _log(code: str, ok: bool, output: str, elapsed: float) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat(timespec="seconds")
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {ts}  {'OK' if ok else 'ERR'}  ({elapsed*1000:.0f}ms) ===\n")
            f.write(">>> CODE\n")
            f.write(code if code.endswith("\n") else code + "\n")
            f.write(">>> RESULT\n")
            f.write((output if output.endswith("\n") else output + "\n") if output else "(no output)\n")
    except Exception:  # noqa: BLE001
        pass


def _build_namespace() -> dict[str, object]:
    """Convenience imports the model can use directly (no import statements needed).

    Anything not in here, the model can still `import foo` itself — no
    restriction. We preload only the ones it'll reach for constantly.
    """
    import datetime as _dt
    import json as _json
    import math as _math
    import os as _os
    import pathlib as _pathlib
    import platform as _platform
    import random as _random
    import re as _re
    import shutil as _shutil
    import subprocess as _subprocess
    import sys as _sys
    import time as _time

    ns: dict[str, object] = {
        "__builtins__": builtins,
        # Stdlib shortcuts
        "os": _os, "sys": _sys, "subprocess": _subprocess, "json": _json,
        "re": _re, "math": _math, "random": _random, "time": _time,
        "datetime": _dt, "datetime_now": _dt.datetime.now,
        "Path": _pathlib.Path, "pathlib": _pathlib, "shutil": _shutil,
        "platform": _platform,
    }

    # Optional but common — don't fail if missing
    try:
        import requests as _requests
        ns["requests"] = _requests
    except ImportError:
        pass
    try:
        import urllib.request as _urlreq
        ns["urlreq"] = _urlreq
    except ImportError:
        pass
    try:
        from PIL import Image as _Image
        ns["Image"] = _Image
    except ImportError:
        pass
    return ns


@tool(
    name="run_python",
    description=(
        "Execute arbitrary Python 3 code on the user's PC and return the output. "
        "Use this for ANYTHING not covered by another tool: complex automation, "
        "data manipulation, API calls, querying installed apps, scripted PC "
        "control, math, file processing, anything else. The code runs with the "
        "user's full permissions. "
        "\n\n"
        "CRITICAL FORMATTING RULES for the `code` parameter:\n"
        "  - Send REAL PYTHON SOURCE CODE as a single string. Not a JSON object. "
        "Not a dict. Not a list of fragments. Source code.\n"
        "  - DO NOT USE F-STRINGS. The `{...}` curly braces inside f-strings "
        "break this tool's argument parsing because they look like nested JSON. "
        "Use `.format()`, percent-formatting, or plain `+` string concatenation "
        "instead. Example: instead of `print(f'cpu: {x}%')` write "
        "`print('cpu: ' + str(x) + '%')` or `print('cpu: {}%'.format(x))`.\n"
        "  - Multi-line code is fine, use `\\n` to separate statements.\n"
        "  - Use `print()` for output you want surfaced.\n"
        "\n"
        "Preloaded names you can use without importing: os, sys, subprocess, "
        "json, re, math, random, time, datetime, Path (pathlib.Path), pathlib, "
        "shutil, platform, requests, urlreq (urllib.request), Image (PIL). "
        "\n\n"
        "Anything you `print()` is captured and returned. The value of the "
        "last expression is also returned (like a Jupyter cell). If the code "
        "raises, the traceback is returned. "
        "\n\n"
        "For destructive operations (rm/shutil.rmtree, format, sending data "
        "externally, modifying system settings), SPEAK A CONFIRMATION FIRST and "
        "only run after the user agrees. For read-only or constructive operations "
        "(reading files, computing things, opening apps), just run."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": (
                    "Python source as a single string. Use .format() not f-strings "
                    "(curly braces break tool-call JSON). Multi-line ok with \\n."
                ),
            },
        },
        "required": ["code"],
    },
)
def run_python(code: str) -> str:
    if not code or not code.strip():
        return "error: empty code"

    # Guard: detect the model's "I sent a JSON dict instead of Python source" failure mode.
    # Symptoms: starts with { or [, contains key:value style dict syntax that's nonsensical
    # as a top-level Python program (e.g. {'print(f': '...'}), nothing else.
    stripped = code.strip()
    if _looks_like_fragmented_json_not_code(stripped):
        return (
            "error: your `code` argument was a JSON object or dict literal, not "
            "Python source. Send actual Python source code as a string. "
            "AVOID f-strings — the `{}` curly braces break this tool's "
            "argument parsing. Use `.format()` or string concatenation. "
            "Example: `import psutil; print('cpu: ' + str(psutil.cpu_percent()) + '%')`"
        )

    namespace = _build_namespace()
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    last_expr_value = None

    # Split into "all but last line" exec'd and "last line" eval'd if it's an
    # expression — REPL-like behavior so the model can write `2+2` and get 4.
    code_stripped = code.rstrip()
    lines = code_stripped.split("\n")
    last_line = lines[-1].rstrip() if lines else ""
    leading = "\n".join(lines[:-1])

    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            if leading.strip():
                exec(compile(leading, "<lumi-run_python>", "exec"), namespace)
            # Try to eval the last line as an expression. If it's a statement
            # (assignment, def, etc.), fall back to exec.
            if last_line:
                try:
                    last_expr_value = eval(
                        compile(last_line, "<lumi-run_python>", "eval"),
                        namespace,
                    )
                except SyntaxError:
                    exec(compile(last_line, "<lumi-run_python>", "exec"), namespace)
    except SystemExit as e:
        elapsed = time.perf_counter() - t0
        msg = f"SystemExit({e.code!r}) — code attempted to exit the process"
        _log(code, ok=False, output=msg, elapsed=elapsed)
        return msg
    except BaseException as e:  # noqa: BLE001 — catch absolutely everything from user code
        elapsed = time.perf_counter() - t0
        tb = traceback.format_exc(limit=8)
        # Trim leading frames inside this module so the model sees the user-code line first
        out_parts = []
        if stdout_buf.getvalue():
            out_parts.append("--- stdout ---\n" + stdout_buf.getvalue().rstrip())
        if stderr_buf.getvalue():
            out_parts.append("--- stderr ---\n" + stderr_buf.getvalue().rstrip())
        out_parts.append(f"--- exception ---\n{type(e).__name__}: {e}\n{tb}")
        msg = "\n".join(out_parts)
        _log(code, ok=False, output=msg, elapsed=elapsed)
        return msg[:_MAX_OUTPUT_CHARS] + ("\n... (truncated)" if len(msg) > _MAX_OUTPUT_CHARS else "")

    elapsed = time.perf_counter() - t0

    # Assemble result
    out_parts = []
    if stdout_buf.getvalue():
        out_parts.append(stdout_buf.getvalue().rstrip())
    if stderr_buf.getvalue():
        out_parts.append("[stderr]\n" + stderr_buf.getvalue().rstrip())
    if last_expr_value is not None:
        try:
            repr_val = repr(last_expr_value)
        except Exception:  # noqa: BLE001
            repr_val = f"<unrepresentable {type(last_expr_value).__name__}>"
        out_parts.append(f"[returned] {repr_val}")

    output = "\n".join(out_parts) if out_parts else "(no output, no return value)"
    if len(output) > _MAX_OUTPUT_CHARS:
        output = output[:_MAX_OUTPUT_CHARS] + f"\n... (truncated, {len(output) - _MAX_OUTPUT_CHARS} more chars)"
    _log(code, ok=True, output=output, elapsed=elapsed)
    return output
