"""System info and monitoring tools."""
from __future__ import annotations

import subprocess
import time
from datetime import datetime

from tools import tool


@tool(
    name="get_uptime",
    description="Get how long the computer has been running since last boot.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_uptime() -> str:
    try:
        import psutil
        boot = datetime.fromtimestamp(psutil.boot_time())
        now = datetime.now()
        delta = now - boot
        days = delta.days
        hours = delta.seconds // 3600
        mins = (delta.seconds % 3600) // 60
        return f"Uptime: {days} days, {hours} hours, {mins} minutes (booted: {boot.strftime('%Y-%m-%d %H:%M')})"
    except ImportError:
        return "error: psutil not installed"


@tool(
    name="get_disk_info",
    description="Get disk usage information for all drives. Shows total, used, and free space.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_disk_info() -> str:
    try:
        import psutil
    except ImportError:
        return "error: psutil not installed"

    lines = ["Disk Usage:"]
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            free_gb = usage.free / (1024**3)
            pct = usage.percent
            lines.append(f"  {part.device} ({part.fstype}): {used_gb:.0f}GB / {total_gb:.0f}GB ({pct:.0f}% used, {free_gb:.0f}GB free)")
        except PermissionError:
            continue

    return "\n".join(lines)


@tool(
    name="get_temperature",
    description="Get hardware temperature readings (CPU, GPU) if available.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_temperature() -> str:
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if not temps:
            return "Temperature sensors not available on this system."

        lines = ["Hardware Temperatures:"]
        for name, entries in temps.items():
            for entry in entries:
                label = entry.label or name
                current = entry.current
                high = entry.high or "N/A"
                crit = entry.critical or "N/A"
                lines.append(f"  {label}: {current:.0f}°C (high: {high}, critical: {crit})")

        return "\n".join(lines)
    except ImportError:
        return "error: psutil not installed"
    except Exception as e:
        return f"error reading temperatures: {e}"


@tool(
    name="get_network_interfaces",
    description="List all network interfaces with their IP addresses and status.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_network_interfaces() -> str:
    try:
        import psutil
    except ImportError:
        return "error: psutil not installed"

    lines = ["Network Interfaces:"]
    for name, addrs in psutil.net_if_addrs().items():
        stats = psutil.net_if_stats().get(name)
        status = "UP" if (stats and stats.isup) else "DOWN"
        lines.append(f"  {name} [{status}]")
        for addr in addrs:
            if addr.family.name == "AF_INET":
                lines.append(f"    IPv4: {addr.address}")
            elif addr.family.name == "AF_INET6":
                lines.append(f"    IPv6: {addr.address}")

    return "\n".join(lines)


@tool(
    name="get_io_stats",
    description="Get disk I/O and network I/O statistics since boot.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_io_stats() -> str:
    try:
        import psutil
    except ImportError:
        return "error: psutil not installed"

    lines = ["I/O Statistics (since boot):"]

    # Disk I/O
    disk = psutil.disk_io_counters()
    if disk:
        lines.append(f"  Disk: read={disk.read_bytes/(1024**3):.1f}GB, write={disk.write_bytes/(1024**3):.1f}GB")

    # Network I/O
    net = psutil.net_io_counters()
    if net:
        lines.append(f"  Network: received={net.bytes_recv/(1024**3):.1f}GB, sent={net.bytes_sent/(1024**3):.1f}GB")
        lines.append(f"  Packets: in={net.packets_in}, out={net.packets_out}")
        if net.dropin > 0 or net.dropout > 0:
            lines.append(f"  Drops: in={net.dropin}, out={net.dropout}")

    return "\n".join(lines)
