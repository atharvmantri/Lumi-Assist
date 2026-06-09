"""Timer, alarm, and reminder tools for JARVIS."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable

from tools import tool

# Global timer registry — survives across tool calls
_timers: dict[str, dict[str, Any]] = {}
_timer_id_counter = 0


@tool(
    name="set_timer",
    description=(
        "Set a countdown timer. After the specified duration, a notification fires "
        "and the user is alerted. Returns a timer ID so the user can cancel it. "
        "Use when the user says 'set a timer for X minutes' or 'remind me in X seconds'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "duration_seconds": {
                "type": "integer",
                "description": "Timer duration in seconds (max 86400 for 24 hours)",
            },
            "label": {
                "type": "string",
                "description": "Optional label for the timer, e.g. 'pasta', 'meeting'",
            },
        },
        "required": ["duration_seconds"],
    },
)
def set_timer(duration_seconds: int, label: str = "") -> str:
    global _timer_id_counter
    duration_seconds = max(1, min(duration_seconds, 86400))
    _timer_id_counter += 1
    timer_id = f"timer-{_timer_id_counter}"

    label_str = f" ({label})" if label else ""
    end_time = datetime.now() + timedelta(seconds=duration_seconds)

    def _fire() -> None:
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                "JARVIS Timer",
                f"Timer{label_str} finished! {duration_seconds}s elapsed.",
                duration=10,
                threaded=True,
            )
        except Exception:
            pass  # best-effort notification

    t = threading.Timer(duration_seconds, _fire)
    t.daemon = True
    t.start()

    _timers[timer_id] = {
        "id": timer_id,
        "label": label,
        "duration": duration_seconds,
        "end_time": end_time.isoformat(),
        "thread": t,
    }

    # Human-readable duration
    if duration_seconds >= 3600:
        h = duration_seconds // 3600
        m = (duration_seconds % 3600) // 60
        dur_str = f"{h}h {m}m" if m else f"{h}h"
    elif duration_seconds >= 60:
        m = duration_seconds // 60
        s = duration_seconds % 60
        dur_str = f"{m}m {s}s" if s else f"{m}m"
    else:
        dur_str = f"{duration_seconds}s"

    return f"Timer{label_str} set for {dur_str}. ID: {timer_id}"


@tool(
    name="cancel_timer",
    description="Cancel a previously set timer by its ID.",
    parameters={
        "type": "object",
        "properties": {
            "timer_id": {"type": "string", "description": "The timer ID returned by set_timer"},
        },
        "required": ["timer_id"],
    },
)
def cancel_timer(timer_id: str) -> str:
    entry = _timers.get(timer_id)
    if not entry:
        return f"error: no timer found with ID {timer_id}"
    entry["thread"].cancel()
    del _timers[timer_id]
    return f"Timer {timer_id} cancelled."


@tool(
    name="list_timers",
    description="List all active timers with their remaining time.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_timers() -> str:
    if not _timers:
        return "No active timers."
    lines = ["Active timers:"]
    now = datetime.now()
    for tid, entry in list(_timers.items()):
        end = datetime.fromisoformat(entry["end_time"])
        remaining = end - now
        if remaining.total_seconds() <= 0:
            lines.append(f"  {tid} (label: {entry['label'] or 'none'}) — about to finish")
        else:
            secs = int(remaining.total_seconds())
            lines.append(f"  {tid} (label: {entry['label'] or 'none'}) — {secs}s remaining")
    return "\n".join(lines)
