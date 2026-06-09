"""System info and diagnostics summary tool."""
from __future__ import annotations

import platform
import subprocess

from tools import tool


@tool(
    name="system_report",
    description="Generate a comprehensive system report: OS, CPU, RAM, GPU, disk, network, installed software.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def system_report() -> str:
    lines = ["=" * 60, "  SYSTEM REPORT", "=" * 60, ""]

    # OS
    lines.append(f"OS: Windows {platform.release()} {platform.version()}")
    lines.append(f"Architecture: {platform.machine()}")
    lines.append(f"Python: {platform.python_version()}")
    lines.append("")

    # CPU
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines.append(f"CPU:\n{result.stdout.strip()[:200]}")
    except:
        pass

    # RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        lines.append(f"RAM: {mem.total/(1024**3):.0f} GB total, {mem.available/(1024**3):.0f} GB available ({100-mem.percent:.0f}% free)")
    except:
        lines.append("RAM: could not determine")

    # GPU
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | Format-List"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines.append(f"GPU:\n{result.stdout.strip()[:200]}")
    except:
        pass

    # Disk
    try:
        import psutil
        lines.append("\nDisks:")
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                lines.append(f"  {part.device} ({part.fstype}): {usage.used/(1024**3):.0f}GB / {usage.total/(1024**3):.0f}GB ({usage.percent:.0f}% used)")
            except:
                pass
    except:
        pass

    # Network
    try:
        result = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        # Extract just the adapter names and IPs
        lines.append("\nNetwork:")
        for line in result.stdout.split("\n"):
            if "IPv4" in line or "Description" in line:
                lines.append(f"  {line.strip()}")
    except:
        pass

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
