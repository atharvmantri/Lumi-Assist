"""System cleanup — free disk space, clear caches."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool


@tool(
    name="clean_temp_files",
    description="Clean temporary files from Windows temp folders to free disk space.",
    parameters={
        "type": "object",
        "properties": {
            "dry_run": {
                "type": "boolean",
                "description": "If true, show what would be deleted without actually deleting (default false)",
            },
        },
        "required": [],
    },
)
def clean_temp_files(dry_run: bool = False) -> str:
    temp_dirs = [
        Path(os.environ.get("TEMP", "")),
        Path(os.environ.get("TMP", "")),
        PROJECT_ROOT / "logs" / "screenshots",
    ]
    # Remove empty entries
    temp_dirs = [d for d in temp_dirs if d.exists() and d.is_dir()]

    total_freed = 0
    files_cleaned = 0
    lines = [f"{'[DRY RUN] ' if dry_run else ''}Cleaning temp files..."]

    for temp_dir in temp_dirs:
        dir_freed = 0
        dir_files = 0
        for f in temp_dir.rglob("*"):
            if f.is_file():
                try:
                    size = f.stat().st_size
                    if not dry_run:
                        f.unlink()
                    dir_freed += size
                    dir_files += 1
                except (PermissionError, OSError):
                    pass

        lines.append(f"  {temp_dir}: {dir_files} files, {dir_freed/1024/1024:.1f} MB")
        total_freed += dir_freed
        files_cleaned += dir_files

    lines.append(f"\nTotal: {files_cleaned} files, {total_freed/1024/1024:.1f} MB freed")
    return "\n".join(lines)


@tool(
    name="clear_dns_cache",
    description="Clear the DNS resolver cache. Use when network issues or DNS changes aren't taking effect.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def clear_dns_cache() -> str:
    try:
        result = subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.strip()
        return f"DNS cache cleared:\n{output}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_event_log",
    description="Get recent Windows event log entries (errors, warnings).",
    parameters={
        "type": "object",
        "properties": {
            "level": {
                "type": "string",
                "description": "Event level: 'error', 'warning', 'all' (default 'error')",
                "enum": ["error", "warning", "all"],
            },
            "limit": {
                "type": "integer",
                "description": "Max events to return (default 10)",
            },
        },
        "required": [],
    },
)
def get_event_log(level: str = "error", limit: int = 10) -> str:
    ps_level = "Error" if level == "error" else "Warning" if level == "warning" else ""
    ps_cmd = f"Get-EventLog -LogName System -EntryType {ps_level} -Newest {limit} | Format-List TimeGenerated, EntryType, Source, Message"

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.strip()
        if not output:
            return f"No {level} events found in system log."
        return f"Recent {level} events:\n\n{output[:3000]}"
    except Exception as e:
        return f"error: {e}"
