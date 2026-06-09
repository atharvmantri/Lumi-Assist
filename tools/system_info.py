"""System info, battery, CPU, memory, disk — PC status tools."""
from __future__ import annotations

import platform
import shutil
from datetime import datetime

from tools import tool


@tool(
    name="get_system_info",
    description=(
        "Get a summary of the PC's system information: OS version, CPU, RAM, GPU, "
        "disk space, uptime. Use when the user asks about their computer specs, "
        "how much disk space is left, or how long it's been running."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_system_info() -> str:
    lines = []
    # OS
    lines.append(f"OS: Windows {platform.release()} ({platform.version()})")
    lines.append(f"Machine: {platform.machine()}")
    lines.append(f"Python: {platform.python_version()}")

    # CPU
    try:
        import psutil
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "unknown"
        cpu_pct = psutil.cpu_percent(interval=0.1)
        lines.append(f"CPU: {cpu_count} cores @ {freq_str}, {cpu_pct}% usage")

        # RAM
        mem = psutil.virtual_memory()
        lines.append(f"RAM: {mem.used/1024**3:.1f} GB / {mem.total/1024**3:.1f} GB ({mem.percent}% used)")

        # Disk
        disk = shutil.disk_usage("C:\\")
        lines.append(f"Disk C: {disk.free/1024**3:.0f} GB free of {disk.total/1024**3:.0f} GB")

        # Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        lines.append(f"Uptime: {uptime.days}d {uptime.seconds//3600}h {(uptime.seconds%3600)//60}m")

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            lines.append(f"Battery: {battery.percent}% {'(charging)' if battery.power_plugged else '(on battery)'}")
    except ImportError:
        lines.append("(psutil not installed — limited info)")

    return "\n".join(lines)


@tool(
    name="get_battery",
    description="Get the current battery percentage and charging status.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_battery() -> str:
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery is None:
            return "no battery detected (desktop PC)"
        pct = battery.percent
        charging = battery.power_plugged
        secs_left = battery.secsleft
        if secs_left and secs_left != psutil.POWER_TIME_UNLIMIT:
            hours = secs_left // 3600
            mins = (secs_left % 3600) // 60
            return f"Battery: {pct}% {'(charging)' if charging else f'{hours}h {mins}m remaining'}"
        return f"Battery: {pct}% {'(charging)' if charging else '(discharging, time unknown)'}"
    except ImportError:
        return "error: psutil not installed"
    except Exception as e:
        return f"error reading battery: {e}"


@tool(
    name="get_cpu_usage",
    description="Get the current CPU usage percentage across all cores.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_cpu_usage() -> str:
    try:
        import psutil
        pct = psutil.cpu_percent(interval=0.2)
        per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
        return f"CPU: {pct}% overall. Per-core: {', '.join(f'{p}%' for p in per_cpu[:8])}" + (f" and {len(per_cpu)-8} more" if len(per_cpu) > 8 else "")
    except ImportError:
        return "error: psutil not installed"
    except Exception as e:
        return f"error reading CPU: {e}"


@tool(
    name="get_processes",
    description=(
        "List the top processes by CPU or memory usage. "
        "Returns the top 10 processes sorted by the given metric."
    ),
    parameters={
        "type": "object",
        "properties": {
            "sort_by": {
                "type": "string",
                "description": "Sort by 'cpu' or 'memory' (default 'cpu')",
                "enum": ["cpu", "memory"],
            },
        },
        "required": [],
    },
)
def get_processes(sort_by: str = "cpu") -> str:
    try:
        import psutil
    except ImportError:
        return "error: psutil not installed"

    procs = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            procs.append({
                "name": info.get("name", "?") or "?",
                "cpu": info.get("cpu_percent", 0) or 0,
                "mem": info.get("memory_percent", 0) or 0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if sort_by == "memory":
        procs.sort(key=lambda p: p["mem"], reverse=True)
    else:
        procs.sort(key=lambda p: p["cpu"], reverse=True)

    lines = [f"Top 10 by {sort_by}:"]
    for p in procs[:10]:
        if sort_by == "memory":
            lines.append(f"  {p['name']:25s} {p['mem']:.1f}% RAM")
        else:
            lines.append(f"  {p['name']:25s} {p['cpu']:.1f}% CPU")
    return "\n".join(lines)
