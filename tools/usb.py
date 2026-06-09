"""USB and removable drive tools."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="list_usb_devices",
    description="List all connected USB devices.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_usb_devices() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-PnpDevice -Class USB | Where-Object { $_.Status -eq 'OK' } | Select-Object FriendlyName, InstanceId | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if not result.stdout.strip():
            return "No USB devices found."
        return f"USB Devices:\n{result.stdout.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="list_drives",
    description="List all drives and volumes including USB drives with their letters, labels, and free space.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_drives() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Volume | Where-Object { $_.DriveLetter } | Select-Object DriveLetter, FileSystemLabel, FileSystem, SizeRemaining, Size | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if not result.stdout.strip():
            return "No drives found."
        return f"Drives:\n{result.stdout.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="eject_drive",
    description="Safely eject a USB drive by its drive letter.",
    parameters={
        "type": "object",
        "properties": {
            "drive_letter": {
                "type": "string",
                "description": "Drive letter to eject (e.g. 'E', 'F')",
            },
        },
        "required": ["drive_letter"],
    },
)
def eject_drive(drive_letter: str) -> str:
    letter = drive_letter[0].upper()
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"(New-Object -ComObject Shell.Application).Namespace(17).ParseName('{letter}:').InvokeVerb('Eject')"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Sent eject command for {letter}: drive"
    except Exception as e:
        return f"error ejecting {letter}: {e}"
