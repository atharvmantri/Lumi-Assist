"""Printer management tools."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="list_printers",
    description="List all installed printers and their status.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_printers() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Printer | Select-Object Name, DriverName, PortName, PrinterStatus, Shared | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if not result.stdout.strip():
            return "No printers installed."
        return f"Printers:\n{result.stdout.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="print_queue",
    description="Show the current print queue for a printer.",
    parameters={
        "type": "object",
        "properties": {
            "printer": {
                "type": "string",
                "description": "Printer name (default: default printer)",
            },
        },
        "required": [],
    },
)
def print_queue(printer: str = "") -> str:
    try:
        if printer:
            ps_cmd = f"Get-PrintJob -PrinterName '{printer}' | Select-Object Id, DocumentName, Owner, JobStatus, PagesPrinted, TotalPages | Format-Table -AutoSize"
        else:
            ps_cmd = "Get-PrintJob | Select-Object Id, PrinterName, DocumentName, Owner, JobStatus | Format-Table -AutoSize"
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if not result.stdout.strip():
            return f"Print queue is empty{' for ' + printer if printer else ''}."
        return f"Print Queue:\n{result.stdout.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="clear_print_queue",
    description="Clear all pending print jobs for a printer.",
    parameters={
        "type": "object",
        "properties": {
            "printer": {
                "type": "string",
                "description": "Printer name to clear (default: all printers)",
            },
        },
        "required": [],
    },
)
def clear_print_queue(printer: str = "") -> str:
    try:
        if printer:
            ps_cmd = f"Get-PrintJob -PrinterName '{printer}' | Remove-PrintJob"
        else:
            ps_cmd = "Get-PrintJob | Remove-PrintJob"
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Print queue cleared{' for ' + printer if printer else ' (all printers)'}"
    except Exception as e:
        return f"error: {e}"
