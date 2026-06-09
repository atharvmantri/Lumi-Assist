"""Service management — start, stop, enable, disable Windows services."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="list_services",
    description="List Windows services, optionally filtered by status or name.",
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status: 'running', 'stopped', 'all' (default 'running')",
                "enum": ["running", "stopped", "all"],
            },
            "query": {
                "type": "string",
                "description": "Optional text to filter service names",
            },
        },
        "required": [],
    },
)
def list_services(status: str = "running", query: str = "") -> str:
    try:
        ps_filter = ""
        if status == "running":
            ps_filter = "| Where-Object { $_.Status -eq 'Running' }"
        elif status == "stopped":
            ps_filter = "| Where-Object { $_.Status -eq 'Stopped' }"

        ps_cmd = f"Get-Service {ps_filter} | Select-Object Name, DisplayName, Status, StartType | Sort-Object Name | Format-Table -AutoSize"

        if query:
            ps_cmd = f"Get-Service | Where-Object {{ $_.Name -match '{query}' -or $_.DisplayName -match '{query}' }} | Select-Object Name, DisplayName, Status, StartType | Format-Table -AutoSize"

        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if not result.stdout.strip():
            return f"No services found" + (f" matching '{query}'" if query else f" with status '{status}'")
        return f"Windows Services:\n{result.stdout.strip()[:4000]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="start_service",
    description="Start a Windows service by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Service name (e.g. 'Spooler', 'wuauserv')",
            },
        },
        "required": ["name"],
    },
)
def start_service(name: str) -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Start-Service -Name '{name}'"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Started service: {name}"
        return f"error starting {name}: {result.stderr.strip()[:200]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="stop_service",
    description="Stop a Windows service by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Service name to stop",
            },
        },
        "required": ["name"],
    },
)
def stop_service(name: str) -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Stop-Service -Name '{name}' -Force"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Stopped service: {name}"
        return f"error stopping {name}: {result.stderr.strip()[:200]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="restart_service",
    description="Restart a Windows service by name.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Service name to restart",
            },
        },
        "required": ["name"],
    },
)
def restart_service(name: str) -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Restart-Service -Name '{name}'"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Restarted service: {name}"
        return f"error restarting {name}: {result.stderr.strip()[:200]}"
    except Exception as e:
        return f"error: {e}"
