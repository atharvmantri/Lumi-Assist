"""Time tracking — log and review time spent on tasks."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

TIMELOG_PATH = PROJECT_ROOT / "data" / "timelog.json"


def _load_timelog() -> list[dict]:
    if TIMELOG_PATH.exists():
        with open(TIMELOG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_timelog(log: list[dict]) -> None:
    TIMELOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TIMELOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


@tool(
    name="timer_start",
    description="Start tracking time for a task or activity.",
    parameters={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "What you're working on",
            },
        },
        "required": ["task"],
    },
)
def timer_start(task: str) -> str:
    log = _load_timelog()

    # Check if there's already an active timer
    for entry in log:
        if entry.get("status") == "running":
            return f"A timer is already running: {entry['task']} (started {entry['start'][:16].replace('T', ' ')}). Stop it first with timer_stop."

    entry = {
        "task": task,
        "start": datetime.now().isoformat(),
        "status": "running",
    }
    log.append(entry)
    _save_timelog(log)

    return f"Timer started: {task} at {datetime.now().strftime('%H:%M:%S')}"


@tool(
    name="timer_stop",
    description="Stop the currently running timer.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def timer_stop() -> str:
    log = _load_timelog()

    for entry in log:
        if entry.get("status") == "running":
            entry["status"] = "stopped"
            entry["stop"] = datetime.now().isoformat()
            start = datetime.fromisoformat(entry["start"])
            stop = datetime.fromisoformat(entry["stop"])
            delta = stop - start
            total_secs = int(delta.total_seconds())
            hours = total_secs // 3600
            mins = (total_secs % 3600) // 60
            secs = total_secs % 60

            _save_timelog(log)
            return f"Timer stopped: {entry['task']} — {hours}h {mins}m {secs}s"

    return "No active timer found. Use timer_start to begin tracking."


@tool(
    name="time_report",
    description="Show a report of logged time for today or the last N days.",
    parameters={
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "How many days back to include (default 7)",
            },
        },
        "required": [],
    },
)
def time_report(days: int = 7) -> str:
    log = _load_timelog()
    if not log:
        return "No time entries recorded."

    cutoff = datetime.now() - timedelta(days=days)
    entries = [e for e in log if datetime.fromisoformat(e["start"]) >= cutoff]

    if not entries:
        return f"No time entries in the last {days} days."

    # Group by task
    task_totals: dict[str, int] = {}
    for e in entries:
        if e.get("stop"):
            start = datetime.fromisoformat(e["start"])
            stop = datetime.fromisoformat(e["stop"])
            secs = int((stop - start).total_seconds())
            task_totals[e["task"]] = task_totals.get(e["task"], 0) + secs

    lines = [f"Time Report (last {days} days):"]
    total_secs = 0
    for task, secs in sorted(task_totals.items(), key=lambda x: -x[1]):
        hours = secs // 3600
        mins = (secs % 3600) // 60
        lines.append(f"  {task}: {hours}h {mins}m")
        total_secs += secs

    total_hours = total_secs // 3600
    total_mins = (total_secs % 3600) // 60
    lines.append(f"\nTotal: {total_hours}h {total_mins}m across {len(task_totals)} task(s)")

    # Active timer
    active = [e for e in log if e.get("status") == "running"]
    if active:
        e = active[-1]
        start = datetime.fromisoformat(e["start"])
        elapsed = datetime.now() - start
        el_secs = int(elapsed.total_seconds())
        lines.append(f"\n⏱ Active: {e['task']} ({el_secs // 3600}h {(el_secs % 3600) // 60}m)")

    return "\n".join(lines)


@tool(
    name="time_clear",
    description="Clear all time tracking entries.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def time_clear() -> str:
    log = _load_timelog()
    count = len(log)
    _save_timelog([])
    return f"Cleared {count} time tracking entries."
