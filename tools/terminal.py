"""Terminal and shell history tools."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tools import tool


@tool(
    name="get_terminal_history",
    description="Get recent PowerShell command history.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max commands to show (default 20)",
            },
        },
        "required": [],
    },
)
def get_terminal_history(limit: int = 20) -> str:
    try:
        ps_cmd = f"Get-History -Count {limit} | Select-Object Id, CommandLine | Format-Table -AutoSize"
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.stdout.strip():
            return f"Recent PowerShell Commands:\n{result.stdout.strip()}"
        return "No PowerShell history available."
    except Exception as e:
        return f"error: {e}"


@tool(
    name="run_as_admin",
    description="Run a command with elevated (admin) privileges.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command to run as admin",
            },
        },
        "required": ["command"],
    },
)
def run_as_admin(command: str) -> str:
    try:
        import subprocess
        subprocess.run(
            ["powershell", "-Command", f"Start-Process powershell -Verb RunAs -ArgumentList '-Command', '{command}'"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Launched admin prompt with: {command}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_env_var",
    description="Get the value of any system or user environment variable.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Environment variable name",
            },
        },
        "required": ["name"],
    },
)
def get_env_var(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return f"Environment variable '{name}' is not set."
    return f"{name} = {value}"


@tool(
    name="set_env_var",
    description="Set a user environment variable (requires restart of apps to take effect).",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Variable name",
            },
            "value": {
                "type": "string",
                "description": "Variable value",
            },
        },
        "required": ["name", "value"],
    },
)
def set_env_var(name: str, value: str) -> str:
    try:
        ps_cmd = f'[Environment]::SetEnvironmentVariable("{name}", "{value}", "User")'
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Set user environment variable: {name}={value}"
        return f"error: {result.stderr.strip()}"
    except Exception as e:
        return f"error: {e}"
