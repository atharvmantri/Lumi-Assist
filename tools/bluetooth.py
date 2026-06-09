"""Bluetooth device management."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="bluetooth_devices",
    description="List paired Bluetooth devices and their connection status.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def bluetooth_devices() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PnpDevice -Class Bluetooth | Where-Object { $_.Status -eq 'OK' } | Select-Object FriendlyName, Status, Present | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        output = result.stdout.strip()
        if not output:
            return "No Bluetooth devices found."
        return f"Bluetooth Devices:\n{output}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="toggle_bluetooth",
    description="Turn Bluetooth on or off.",
    parameters={
        "type": "object",
        "properties": {
            "state": {
                "type": "string",
                "description": "Turn bluetooth 'on' or 'off'",
                "enum": ["on", "off"],
            },
        },
        "required": ["state"],
    },
)
def toggle_bluetooth(state: str) -> str:
    try:
        if state.lower() == "on":
            ps_cmd = "(New-Object -ComObject Shell.Application).Namespace('shell:::{21EC2020-3AEA-1069-A2DD-08002B30309D}').Items() | Where-Object { $_.Name -eq 'Bluetooth' } | ForEach-Object { $_.InvokeVerb('connect') }"
        else:
            ps_cmd = "Get-Service bthserv | Stop-Service -Force"
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Bluetooth turned {state}"
    except Exception as e:
        return f"error toggling Bluetooth: {e}"
