"""Disk and GPU introspection."""
from __future__ import annotations

import shutil
import subprocess

from tools import tool


@tool(
    name="get_disk_usage",
    description=(
        "Return total, used, and free disk space for a drive or path in bytes "
        "and human-readable form. Defaults to the current working directory's drive."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to check (default: current drive)"},
        },
        "required": [],
    },
)
def get_disk_usage(path: str | None = None) -> str:
    target = path or "."
    try:
        usage = shutil.disk_usage(target)
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"

    def human(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}PB"

    return (
        f"path: {target}\n"
        f"  total: {usage.total} bytes  ({human(usage.total)})\n"
        f"  used:  {usage.used} bytes  ({human(usage.used)})\n"
        f"  free:  {usage.free} bytes  ({human(usage.free)})\n"
        f"  used%: {100 * usage.used / usage.total:.1f}"
    )


@tool(
    name="get_gpu_stats",
    description=(
        "Read current GPU usage via nvidia-smi — temperature, utilization, VRAM used/total, "
        "power draw. Returns 'no NVIDIA GPU detected' if nvidia-smi is unavailable."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_gpu_stats() -> str:
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return "no NVIDIA GPU detected (nvidia-smi not on PATH)"
    except subprocess.TimeoutExpired:
        return "error: nvidia-smi timed out"
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"

    if proc.returncode != 0:
        return f"nvidia-smi error: {proc.stderr.strip() or 'unknown'}"

    lines = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            lines.append(line)
            continue
        name, temp, util, mem_used, mem_total, power = parts[:6]
        lines.append(
            f"GPU: {name}\n"
            f"  temperature: {temp} °C\n"
            f"  utilization: {util} %\n"
            f"  VRAM:        {mem_used} / {mem_total} MiB\n"
            f"  power:       {power} W"
        )
    return "\n\n".join(lines) if lines else "no GPU data returned"
