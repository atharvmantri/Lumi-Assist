"""System locale and regional settings tools."""
from __future__ import annotations

import locale
import os
import subprocess

from tools import tool


@tool(
    name="get_locale_info",
    description="Get system locale and regional settings: language, date format, currency, timezone.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_locale_info() -> str:
    lines = ["System Locale & Regional Settings:"]

    # Current locale
    try:
        loc = locale.getdefaultlocale()
        lines.append(f"  Locale: {loc[0] or 'system default'}")
    except:
        pass

    # Timezone
    try:
        import time
        tz = time.tzname
        lines.append(f"  Timezone: {tz[0]} / {tz[1]} (UTC{time.timezone//3600:+d})")
    except:
        pass

    # Windows culture
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Culture | Select-Object Name, DisplayName, NumberFormat, DateTimeFormat | Format-List"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.stdout.strip():
            lines.append(f"\n  Culture:\n" + "\n".join(f"    {l}" for l in result.stdout.strip().split("\n")[:10]))
    except:
        pass

    return "\n".join(lines)


@tool(
    name="get_system_language",
    description="Get the system's current display and input language.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_system_language() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-WinUserLanguageList | Select-Object LanguageTag, EnglishName | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.stdout.strip():
            return f"System Languages:\n{result.stdout.strip()}"
        return "Could not determine system language."
    except Exception as e:
        return f"error: {e}"
