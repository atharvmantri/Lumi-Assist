"""Task Manager — manage running processes with detailed info."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="task_manager_summary",
    description="Get a Task Manager-style summary: process count, CPU, memory, disk, network usage.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def task_manager_summary() -> str:
    try:
        import psutil
    except ImportError:
        return "error: psutil not installed"

    lines = ["Task Manager Summary:"]

    # Process count
    procs = list(psutil.process_iter())
    lines.append(f"  Processes: {len(procs)}")

    # CPU
    cpu = psutil.cpu_percent(interval=0.2)
    lines.append(f"  CPU: {cpu}%")

    # Memory
    mem = psutil.virtual_memory()
    lines.append(f"  Memory: {mem.used/(1024**3):.1f} GB / {mem.total/(1024**3):.1f} GB ({mem.percent}%)")

    # Disk I/O
    try:
        disk = psutil.disk_io_counters()
        if disk:
            lines.append(f"  Disk R/W: {disk.read_bytes/(1024**2):.0f} MB / {disk.write_bytes/(1024**2):.0f} MB (since boot)")
    except:
        pass

    # Network I/O
    try:
        net = psutil.net_io_counters()
        if net:
            lines.append(f"  Net ↑↓: {net.bytes_sent/(1024**2):.0f} MB / {net.bytes_recv/(1024**2):.0f} MB (since boot)")
    except:
        pass

    # Top 5 by CPU
    lines.append(f"\n  Top 5 by CPU:")
    cpu_procs = []
    for p in psutil.process_iter(['name', 'cpu_percent']):
        try:
            cpu_procs.append((p.info['name'], p.info['cpu_percent'] or 0))
        except:
            pass
    cpu_procs.sort(key=lambda x: -x[1])
    for name, pct in cpu_procs[:5]:
        if pct > 0:
            lines.append(f"    {name:25s} {pct:.1f}%")

    # Top 5 by RAM
    lines.append(f"\n  Top 5 by Memory:")
    mem_procs = []
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            mem_procs.append((p.info['name'], p.info['memory_info'].rss / (1024**2)))
        except:
            pass
    mem_procs.sort(key=lambda x: -x[1])
    for name, mb in mem_procs[:5]:
        if mb > 10:
            lines.append(f"    {name:25s} {mb:.0f} MB")

    return "\n".join(lines)


@tool(
    name="get_process_details",
    description="Get detailed info about a specific process by name or PID.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Process name or PID",
            },
        },
        "required": ["query"],
    },
)
def get_process_details(query: str) -> str:
    try:
        import psutil
    except ImportError:
        return "error: psutil not installed"

    # Try PID first
    try:
        pid = int(query)
        proc = psutil.Process(pid)
        info = proc.as_dict(['name', 'exe', 'cmdline', 'memory_info', 'cpu_percent', 'create_time', 'status'])
        from datetime import datetime
        created = datetime.fromtimestamp(info.get('create_time', 0)).strftime('%Y-%m-%d %H:%M')
        mem_mb = info.get('memory_info')
        mem_str = f"{mem_mb.rss/(1024**2):.0f} MB" if mem_mb else "unknown"
        return (
            f"Process #{pid}:\n"
            f"  Name: {info.get('name', '?')}\n"
            f"  Executable: {info.get('exe', '?')}\n"
            f"  Memory: {mem_str}\n"
            f"  CPU: {info.get('cpu_percent', 0):.1f}%\n"
            f"  Status: {info.get('status', '?')}\n"
            f"  Started: {created}\n"
            f"  Command: {' '.join(info.get('cmdline') or ['?'])}"
        )
    except ValueError:
        pass

    # Search by name
    matches = []
    for p in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            if query.lower() in (p.info['name'] or '').lower():
                mem = p.info['memory_info']
                mem_str = f"{mem.rss/(1024**2):.0f} MB" if mem else "?"
                matches.append(f"  PID {p.info['pid']}: {p.info['name']} ({mem_str})")
        except:
            pass

    if matches:
        return f"Processes matching '{query}':\n" + "\n".join(matches)
    return f"No process found matching '{query}'"
