"""Power management and battery optimization tools."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="get_power_plan",
    description="Get the current Windows power plan.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_power_plan() -> str:
    try:
        result = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = []
        for line in result.stdout.strip().split("\n"):
            if "*" in line:
                name = line.split(":")[1].strip()
                lines.append(f"Current Power Plan: {name}")
            elif "GUID" in line or "Power Scheme" in line:
                name = line.split(":")[1].strip() if ":" in line else line.strip()
                lines.append(f"  Available: {name}")
        return "\n".join(lines) if lines else result.stdout.strip()
    except Exception as e:
        return f"error: {e}"


@tool(
    name="set_power_plan",
    description="Change the Windows power plan.",
    parameters={
        "type": "object",
        "properties": {
            "plan": {
                "type": "string",
                "description": "Power plan: 'balanced', 'high', 'power-saver', 'ultimate'",
                "enum": ["balanced", "high", "power-saver", "ultimate"],
            },
        },
        "required": ["plan"],
    },
)
def set_power_plan(plan: str) -> str:
    plan_guids = {
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "high": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "power-saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "ultimate": "e9a42b02-d5df-448d-aa00-03f14749eb61",
    }

    guid = plan_guids.get(plan.lower().replace(" ", "-"))
    if not guid:
        return f"error: unknown plan '{plan}'. Use: balanced, high, power-saver, ultimate"

    try:
        result = subprocess.run(
            ["powercfg", "/setactive", guid],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Power plan set to: {plan}"
        return f"error: {result.stderr.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_battery_report",
    description="Generate a detailed Windows battery health report.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_battery_report() -> str:
    import os
    from datetime import datetime
    from pathlib import Path

    report_path = Path(os.environ.get("TEMP", ".")) / f"battery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    try:
        result = subprocess.run(
            ["powercfg", "/batteryreport", "/output", str(report_path)],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Battery report generated: {report_path}\nOpen it in your browser to view detailed battery health, capacity history, and usage data."
        return f"error generating report: {result.stderr.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_sleep_settings",
    description="Get Windows sleep and hibernate settings.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_sleep_settings() -> str:
    try:
        result = subprocess.run(
            ["powercfg", "/a"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return f"Available Sleep States:\n\n{result.stdout.strip()}"
    except Exception as e:
        return f"error: {e}"
