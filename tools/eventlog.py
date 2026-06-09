"""System event log tools."""
from __future__ import annotations

import subprocess
from datetime import datetime

from tools import tool


@tool(
    name="event_log_errors",
    description="Get recent error events from the Windows Event Log.",
    parameters={
        "type": "object",
        "properties": {
            "hours": {
                "type": "integer",
                "description": "Look back this many hours (default 24)",
            },
            "limit": {
                "type": "integer",
                "description": "Max events to return (default 20)",
            },
        },
        "required": [],
    },
)
def event_log_errors(hours: int = 24, limit: int = 20) -> str:
    try:
        ps_cmd = f"""
        $cutoff = (Get-Date).AddHours(-{hours})
        Get-EventLog -LogName System -EntryType Error -After $cutoff -Newest {limit} |
        Select-Object TimeGenerated, Source, Message |
        Format-List
        """
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.strip()
        if not output:
            return f"No system errors in the last {hours} hours."
        return f"System Errors (last {hours}h):\n\n{output[:4000]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="event_log_app_errors",
    description="Get recent application crash events from Windows Event Log.",
    parameters={
        "type": "object",
        "properties": {
            "hours": {
                "type": "integer",
                "description": "Look back this many hours (default 24)",
            },
        },
        "required": [],
    },
)
def event_log_app_errors(hours: int = 24) -> str:
    try:
        ps_cmd = f"""
        $cutoff = (Get-Date).AddHours(-{hours})
        Get-WinEvent -FilterHashtable @{{LogName='Application'; Level=2; StartTime=$cutoff}} -MaxEvents 20 |
        Select-Object TimeCreated, ProviderName, Message |
        Format-List
        """
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.strip()
        if not output:
            return f"No application crashes in the last {hours} hours."
        return f"Application Crashes (last {hours}h):\n\n{output[:4000]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_last_shutdown_time",
    description="Find when the system was last shut down or rebooted.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_last_shutdown_time() -> str:
    try:
        ps_cmd = """
        Get-WinEvent -FilterHashtable @{LogName='System'; ID=1074} -MaxEvents 5 |
        Select-Object TimeCreated, Message | Format-List
        """
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.strip()
        if not output:
            return "No shutdown/reboot events found in event log."
        return f"Recent Shutdown Events:\n\n{output[:2000]}"
    except Exception as e:
        return f"error: {e}"
