"""Tool dispatch + lifecycle for JARVIS.

The executor owns the bridge between the LLM and the registered tools:

  - get_schemas()                → list[dict] for chat/completions `tools` param
  - dispatch(name, args_json)    → str  (the tool's textual return value)
  - Every dispatch is timed and logged to logs/executor.log
  - Exceptions are caught and stringified back to the LLM (never crashes the loop)
  - Args are JSON-decoded once per call; bad JSON returns a structured error
  - EVERY failure is also recorded to the learning store so JARVIS can
    recognize repeat-mistake patterns and inject hints + lessons over time

Importing this module triggers `import tools`, which loads every tools/*.py via
the autoloader in tools/__init__.py and populates tools.REGISTRY.
"""
from __future__ import annotations

import inspect
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import tools                            # noqa: F401 — side-effect: registers tools
from core.config import PROJECT_ROOT
from core.learning import get_store
from tools import REGISTRY


_LOG_PATH = PROJECT_ROOT / "logs" / "executor.log"


def get_schemas() -> list[dict[str, Any]]:
    """Return the registered tools formatted for chat/completions `tools` param."""
    return [spec.to_openai_schema() for spec in REGISTRY.values()]


def list_tools() -> list[str]:
    return sorted(REGISTRY.keys())


def _log(name: str, args: dict[str, Any], result: str, ok: bool, elapsed: float) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat(timespec="seconds")
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            verdict = "OK" if ok else "ERR"
            f.write(f"\n=== {ts}  {verdict}  {name}({elapsed*1000:.0f}ms) ===\n")
            f.write(f"args   : {json.dumps(args, default=str)[:1500]}\n")
            short = result if len(result) < 1500 else result[:1500] + f"\n... ({len(result)-1500} more chars)"
            f.write(f"result : {short}\n")
    except Exception:    # noqa: BLE001
        pass


def dispatch(name: str, arguments: str | dict[str, Any]) -> str:
    """Execute a tool by name. `arguments` is either the raw JSON string the
    model emitted, or an already-decoded dict. Returns a textual result for the LLM.
    """
    spec = REGISTRY.get(name)
    if spec is None:
        msg = f"error: no such tool {name!r}. Available: {', '.join(sorted(REGISTRY))}"
        _record_mistake_with_hint(name, {"_raw_arguments": str(arguments)[:200]}, msg, turn_id=_current_turn_id())
        return msg

    # Decode args
    if isinstance(arguments, str):
        raw = arguments or "{}"
        try:
            args = json.loads(raw)
        except json.JSONDecodeError as e:
            msg = f"error: malformed JSON arguments to {name}: {e}; got: {raw[:200]}"
            _record_mistake_with_hint(name, {"_raw_arguments": raw[:200]}, msg, turn_id=_current_turn_id())
            return msg
    elif isinstance(arguments, dict):
        args = arguments
    else:
        return f"error: arguments must be JSON string or dict, got {type(arguments).__name__}"

    if not isinstance(args, dict):
        return f"error: arguments must decode to an object, got {type(args).__name__}"

    # Filter args to the function's actual parameters — defensively skip extras
    # the model invented. Missing required params will raise TypeError caught below.
    sig = inspect.signature(spec.func)
    accepts_var_kw = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if not accepts_var_kw:
        allowed = set(sig.parameters)
        filtered = {k: v for k, v in args.items() if k in allowed}
        if len(filtered) != len(args):
            dropped = sorted(set(args) - allowed)
            print(f"[exec] {name}: dropped unknown args {dropped}")
        args = filtered

    t0 = time.perf_counter()
    try:
        result = spec.func(**args)
    except TypeError as e:
        # Most common: missing required arg, or wrong type. Surface clearly.
        elapsed = time.perf_counter() - t0
        msg = f"error calling {name}: {e}"
        _log(name, args, msg, ok=False, elapsed=elapsed)
        _record_mistake_with_hint(name, args, msg, turn_id=_current_turn_id())
        return msg
    except Exception as e:   # noqa: BLE001
        elapsed = time.perf_counter() - t0
        msg = f"error in {name}: {type(e).__name__}: {e}"
        _log(name, args, msg + "\n" + traceback.format_exc(limit=4), ok=False, elapsed=elapsed)
        _record_mistake_with_hint(name, args, msg, turn_id=_current_turn_id())
        return msg

    elapsed = time.perf_counter() - t0
    text = str(result) if result is not None else "(no return value)"
    _log(name, args, text, ok=True, elapsed=elapsed)

    # Record success in learning store (lightweight — no transcript, just confirmation).
    # We attach a tiny note so the next time this exact (tool, args) fails, the
    # hint can point at "you've done this successfully before, here's how".
    try:
        get_store().record_success(tool=name, args=args, turn_id=_current_turn_id())
    except Exception:  # noqa: BLE001
        pass

    return text


# Per-turn id so the learning store can correlate failures within a single
# user request. Set by the LLM client before streaming starts.
_turn_id_holder: list[str] = [""]


def _current_turn_id() -> str:
    return _turn_id_holder[0]


def set_turn_id(turn_id: str) -> None:
    """Called by the LLM client at the start of each user turn.

    All mistakes recorded during this turn are tagged with this id so the
    learning store could (in future) correlate multiple failures from the
    same request.
    """
    _turn_id_holder[0] = turn_id


def _record_mistake_with_hint(name: str, args: dict[str, Any], msg: str, *, turn_id: str) -> None:
    """Record the failure in the learning store and, if it's a repeat,
    attach a 'you've hit this before' hint to the message returned to the LLM.
    The hint is computed AFTER recording so the count accurately includes the
    current failure (we want the hint to fire on the 2nd and onward hits).
    """
    try:
        store = get_store()
    except Exception:  # noqa: BLE001
        return
    # 1. Record the failure FIRST so the count for the hint includes it.
    store.record_mistake(tool=name, args=args, error_message=msg, turn_id=turn_id)
    # 2. Now compute the hint. If this is the 2nd+ occurrence of this
    #    (tool, error_class), the hint will be returned.
    hint = store.hint_for_failure(tool=name, error_message=msg, args=args)
    if hint:
        _pending_hints.append((name, hint))


_pending_hints: list[tuple[str, str]] = []


def fetch_pending_hint() -> str | None:
    """Pop the most recent repeat-failure hint so the LLM client can append it
    to the tool result the model is about to see. Returns None if no hint is queued.
    """
    if not _pending_hints:
        return None
    # Pop the LAST queued hint (most recent failure)
    name, hint = _pending_hints[-1]
    _pending_hints.clear()
    return hint


def clear_pending_hints() -> None:
    _pending_hints.clear()


# ---------------------------------------------------------------------------
# CLI for inspecting / smoke-testing the registry
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="JARVIS executor")
    parser.add_argument("--list", action="store_true", help="List registered tools + descriptions")
    parser.add_argument("--schemas", action="store_true", help="Print full JSON schemas")
    parser.add_argument("--call", metavar="NAME", help="Call a tool directly: --call NAME --args JSON")
    parser.add_argument("--args", default="{}", help="JSON args for --call (default '{}')")
    a = parser.parse_args()

    if a.list:
        for name in sorted(REGISTRY):
            spec = REGISTRY[name]
            print(f"{name:22s}  {spec.description.splitlines()[0][:80]}")
        return
    if a.schemas:
        print(json.dumps(get_schemas(), indent=2))
        return
    if a.call:
        out = dispatch(a.call, a.args)
        print(out)
        return
    parser.print_help()


if __name__ == "__main__":
    main()
