"""Daily briefing — JARVIS can give a morning briefing."""
from __future__ import annotations

import subprocess
from datetime import datetime

from tools import tool


@tool(
    name="daily_briefing",
    description=(
        "Get a daily briefing: current time, weather, system status, "
        "recent tasks, and any notes. Use when the user says 'good morning', "
        "'daily briefing', 'what's the plan today', 'morning summary', etc."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)
def daily_briefing() -> str:
    lines = []
    now = datetime.now()

    # Time
    lines.append(f"Good {'morning' if now.hour < 12 else 'afternoon' if now.hour < 18 else 'evening'}!")
    lines.append(f"Time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}")

    # Weather
    try:
        from tools.weather import get_weather
        weather = get_weather()
        # Extract first line only
        weather_line = weather.split("\n")[0] if "\n" in weather else weather
        lines.append(f"Weather: {weather_line}")
    except Exception:
        lines.append("Weather: unavailable")

    # System info
    try:
        import psutil
        # CPU
        cpu = psutil.cpu_percent(interval=0.1)
        lines.append(f"CPU: {cpu}%")

        # RAM
        mem = psutil.virtual_memory()
        lines.append(f"RAM: {mem.percent}% used")

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            lines.append(f"Battery: {battery.percent}% {'(charging)' if battery.power_plugged else '(on battery)'}")

        # Uptime
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = now - boot
        days = uptime.days
        hours = uptime.seconds // 3600
        lines.append(f"Uptime: {days}d {hours}h")
    except Exception:
        lines.append("System info: unavailable")

    # Pending tasks
    try:
        from tools.tasks import list_tasks
        tasks = list_tasks("pending")
        task_lines = [l for l in tasks.split("\n") if l.strip().startswith("[ ]")]
        if task_lines:
            lines.append(f"\nPending tasks ({len(task_lines)}):")
            for t in task_lines[:5]:
                lines.append(f"  {t.strip()}")
            if len(task_lines) > 5:
                lines.append(f"  ...and {len(task_lines)-5} more")
        else:
            lines.append("\nNo pending tasks.")
    except Exception:
        pass

    # Recent notes
    try:
        from tools.notes import list_notes
        notes = list_notes()
        note_lines = [l for l in notes.split("\n") if l.strip().startswith("[")]
        if note_lines:
            lines.append(f"\nRecent notes:")
            for n in note_lines[:3]:
                lines.append(f"  {n.strip()}")
    except Exception:
        pass

    return "\n".join(lines)
