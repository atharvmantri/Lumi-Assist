"""Storage analysis — find large files, disk hogs, cleanup candidates."""
from __future__ import annotations

import os
from pathlib import Path

from tools import tool


@tool(
    name="find_large_files",
    description="Find the largest files in a folder tree.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder to scan (default: current directory)",
            },
            "limit": {
                "type": "integer",
                "description": "Max files to show (default 20)",
            },
            "min_size_mb": {
                "type": "integer",
                "description": "Minimum file size in MB (default 10)",
            },
        },
        "required": [],
    },
)
def find_large_files(folder: str = "", limit: int = 20, min_size_mb: int = 10) -> str:
    target = Path(folder) if folder else Path.cwd()
    if not target.exists():
        return f"error: folder not found: {folder or '.'}"

    min_bytes = min_size_mb * 1024 * 1024
    large_files = []

    for root, dirs, files in os.walk(target):
        # Skip hidden/system dirs
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            try:
                fp = Path(root) / f
                size = fp.stat().st_size
                if size >= min_bytes:
                    large_files.append((fp, size))
            except (PermissionError, OSError):
                pass

    large_files.sort(key=lambda x: -x[1])
    large_files = large_files[:limit]

    if not large_files:
        return f"No files >= {min_size_mb} MB found in {target}"

    lines = [f"Large Files in {target} (>= {min_size_mb} MB):"]
    for i, (fp, size) in enumerate(large_files, 1):
        size_mb = size / (1024 * 1024)
        lines.append(f"  {i}. {size_mb:.0f} MB — {fp}")

    total = sum(s for _, s in large_files)
    lines.append(f"\nTotal shown: {total/(1024*1024):.0f} MB ({len(large_files)} files)")
    return "\n".join(lines)


@tool(
    name="disk_hogs",
    description="Find which folders are using the most disk space.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder to analyze (default: current directory)",
            },
            "depth": {
                "type": "integer",
                "description": "Analysis depth levels (default 1)",
            },
        },
        "required": [],
    },
)
def disk_hogs(folder: str = "", depth: int = 1) -> str:
    target = Path(folder) if folder else Path.cwd()
    if not target.exists():
        return f"error: folder not found: {folder or '.'}"

    def dir_size(path: Path) -> int:
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    try:
                        total += entry.stat().st_size
                    except (PermissionError, OSError):
                        pass
        except:
            pass
        return total

    subdirs = [d for d in target.iterdir() if d.is_dir() and not d.name.startswith(".")]
    sizes = [(d, dir_size(d)) for d in subdirs]
    sizes.sort(key=lambda x: -x[1])

    lines = [f"Disk Usage in {target}:"]
    for d, size in sizes:
        if size > 1024 * 1024:  # >= 1 MB
            if size > 1024**3:
                size_str = f"{size/(1024**3):.1f} GB"
            else:
                size_str = f"{size/(1024**2):.0f} MB"
            lines.append(f"  {size_str:>10s} — {d.name}/")

    return "\n".join(lines)


@tool(
    name="storage_summary",
    description="Get a storage usage summary for all drives.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def storage_summary() -> str:
    try:
        import psutil
    except ImportError:
        return "error: psutil not installed"

    lines = ["Storage Summary:"]
    total_used = 0
    total_size = 0

    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            total_used += usage.used
            total_size += usage.total

            if usage.total > 1024**3:
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)
                pct = usage.percent
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                lines.append(f"\n  {part.device} ({part.fstype})")
                lines.append(f"  [{bar}] {pct:.0f}%")
                lines.append(f"  {used_gb:.0f} GB used / {free_gb:.0f} GB free / {total_gb:.0f} GB total")
        except:
            pass

    if total_size > 0:
        total_pct = (total_used / total_size) * 100
        lines.append(f"\n  TOTAL: {total_used/(1024**3):.0f} GB used / {total_size/(1024**3):.0f} GB total ({total_pct:.0f}%)")

    return "\n".join(lines)
