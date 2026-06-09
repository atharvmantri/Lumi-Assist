"""Process management — kill processes by name or PID."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="kill_process",
    description="Kill a running process by name or PID. Use when the user says 'close Chrome', 'kill notepad', 'stop that process', etc.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Process name (e.g. 'chrome.exe', 'notepad.exe') or PID number",
            },
        },
        "required": ["name"],
    },
)
def kill_process(name: str) -> str:
    if not name:
        return "error: no process name provided"

    # Try PID first
    try:
        pid = int(name)
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Killed process PID {pid}"
        return f"error killing PID {pid}: {result.stderr.strip()}"
    except ValueError:
        pass

    # Kill by name
    if not name.lower().endswith(".exe"):
        name = name + ".exe"

    result = subprocess.run(
        ["taskkill", "/IM", name, "/F"],
        capture_output=True, text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode == 0:
        return f"Killed {name}"
    if "not found" in result.stderr.lower() or "could not be found" in result.stderr.lower():
        return f"No running process found: {name}"
    return f"error killing {name}: {result.stderr.strip()}"


@tool(
    name="list_processes",
    description="List running processes with their PID and memory usage. Returns top 20 by memory.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_processes() -> str:
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = result.stdout.strip().split("\n")
        processes = []
        for line in lines:
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) >= 5:
                name = parts[0]
                pid = parts[1]
                mem = parts[4]
                processes.append((name, pid, mem))

        # Sort by memory (descending) — parse "1,234 K" format
        def parse_mem(m: str) -> int:
            try:
                return int(m.replace(",", "").replace(" K", ""))
            except (ValueError, AttributeError):
                return 0

        processes.sort(key=lambda p: parse_mem(p[2]), reverse=True)

        lines = ["Top 20 processes by memory:"]
        for name, pid, mem in processes[:20]:
            lines.append(f"  {name:30s} PID {pid:>6s}  {mem}")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"
