"""Scheduled task management via Windows Task Scheduler."""
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime

from tools import tool


@tool(
    name="create_scheduled_task",
    description="Create a Windows scheduled task to run a program or script at a specific time or on a schedule.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Task name identifier",
            },
            "command": {
                "type": "string",
                "description": "Command or program to run (e.g. 'python C:\\scripts\\backup.py')",
            },
            "schedule": {
                "type": "string",
                "description": "Schedule: 'once HH:MM', 'daily HH:MM', 'weekly DAY HH:MM' (e.g. 'daily 09:00')",
            },
        },
        "required": ["name", "command", "schedule"],
    },
)
def create_scheduled_task(name: str, command: str, schedule: str) -> str:
    try:
        parts = schedule.lower().split()
        if len(parts) < 2:
            return f"error: schedule format is 'TYPE TIME', e.g. 'daily 09:00' or 'once 14:30'"

        sched_type = parts[0]
        sched_time = parts[1]

        # Build schtasks command
        if sched_type == "once":
            date_str = datetime.now().strftime("%m/%d/%Y")
            cmd = ["schtasks", "/Create", "/TN", name, "/TR", command, "/SC", "ONCE", "/ST", sched_time, "/SD", date_str, "/F"]
        elif sched_type == "daily":
            cmd = ["schtasks", "/Create", "/TN", name, "/TR", command, "/SC", "DAILY", "/ST", sched_time, "/F"]
        elif sched_type == "weekly":
            if len(parts) < 3:
                return "error: weekly schedule needs a day, e.g. 'weekly Monday 09:00'"
            day_map = {
                "monday": "MON", "tuesday": "TUE", "wednesday": "WED",
                "thursday": "THU", "friday": "FRI", "saturday": "SAT", "sunday": "SUN",
            }
            day = day_map.get(parts[1].lower(), "MON")
            cmd = ["schtasks", "/Create", "/TN", name, "/TR", command, "/SC", "WEEKLY", "/D", day, "/ST", parts[2] if len(parts) > 2 else sched_time, "/F"]
        else:
            return f"error: unknown schedule type '{sched_type}'. Use: once, daily, weekly"

        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Scheduled task '{name}' created: {schedule}"
        return f"error creating task: {result.stderr.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="list_scheduled_tasks",
    description="List all Windows scheduled tasks.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_scheduled_tasks() -> str:
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) <= 1:
            return "No scheduled tasks found."

        # Parse CSV output
        tasks = []
        for line in lines[1:]:  # skip header
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) >= 4:
                tasks.append({"name": parts[0], "next_run": parts[1], "status": parts[2], "schedule": parts[3]})

        tasks = tasks[:30]  # cap
        out_lines = [f"Scheduled Tasks ({len(tasks)} shown):"]
        for t in tasks:
            out_lines.append(f"  {t['name']:40s} {t['schedule']:20s} [{t['status']}] next: {t['next_run']}")

        return "\n".join(out_lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="delete_scheduled_task",
    description="Delete a scheduled task by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Task name to delete",
            },
        },
        "required": ["name"],
    },
)
def delete_scheduled_task(name: str) -> str:
    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", name, "/F"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Deleted scheduled task: {name}"
        return f"error deleting task: {result.stderr.strip()}"
    except Exception as e:
        return f"error: {e}"
