"""Windows Registry read/query tools."""
from __future__ import annotations

import winreg
from tools import tool


@tool(
    name="registry_read",
    description="Read a Windows Registry value.",
    parameters={
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Registry key path (e.g. 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion')",
            },
            "value": {
                "type": "string",
                "description": "Value name to read (empty string for default)",
            },
            "hive": {
                "type": "string",
                "description": "Registry hive: 'HKLM' or 'HKCU' (default 'HKCU')",
                "enum": ["HKLM", "HKCU"],
            },
        },
        "required": ["key", "value"],
    },
)
def registry_read(key: str, value: str, hive: str = "HKCU") -> str:
    hive_map = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }

    try:
        hkey = winreg.OpenKey(hive_map[hive], key, 0, winreg.KEY_READ)
        val, val_type = winreg.QueryValueEx(hkey, value)
        winreg.CloseKey(hkey)

        type_names = {
            winreg.REG_SZ: "STRING",
            winreg.REG_DWORD: "DWORD",
            winreg.REG_BINARY: "BINARY",
            winreg.REG_EXPAND_SZ: "EXPAND_SZ",
            winreg.REG_MULTI_SZ: "MULTI_SZ",
        }
        type_name = type_names.get(val_type, f"UNKNOWN({val_type})")

        return f"[{hive}\\{key}]\n  {value or '(default)'} = {val} ({type_name})"
    except FileNotFoundError:
        return f"error: key or value not found: {hive}\\{key}\\{value}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="registry_list",
    description="List all values under a registry key.",
    parameters={
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "Registry key path",
            },
            "hive": {
                "type": "string",
                "description": "Registry hive: 'HKLM' or 'HKCU' (default 'HKCU')",
                "enum": ["HKLM", "HKCU"],
            },
        },
        "required": ["key"],
    },
)
def registry_list(key: str, hive: str = "HKCU") -> str:
    hive_map = {
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
    }

    try:
        hkey = winreg.OpenKey(hive_map[hive], key, 0, winreg.KEY_READ)
        info = winreg.QueryInfoKey(hkey)

        lines = [f"Key: {hive}\\{key}"]
        lines.append(f"  Subkeys: {info[0]}, Values: {info[1]}")

        if info[1] > 0:
            lines.append(f"\nValues:")
            for i in range(info[1]):
                name, val, val_type = winreg.EnumValue(hkey, i)
                type_names = {1: "STRING", 4: "DWORD", 3: "BINARY", 2: "EXPAND_SZ", 7: "MULTI_SZ"}
                tname = type_names.get(val_type, f"TYPE_{val_type}")
                display = str(val)[:100]
                lines.append(f"  {name or '(default)'}: {display} ({tname})")

        winreg.CloseKey(hkey)
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="get_startup_programs",
    description="List programs that run at Windows startup.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_startup_programs() -> str:
    paths = [
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ]

    lines = ["Startup Programs:"]
    for hive, key in paths:
        hive_name = "HKCU" if hive == winreg.HKEY_CURRENT_USER else "HKLM"
        lines.append(f"\n  {hive_name}\\{key}:")
        try:
            hkey = winreg.OpenKey(hive, key, 0, winreg.KEY_READ)
            info = winreg.QueryInfoKey(hkey)
            for i in range(info[1]):
                name, val, _ = winreg.EnumValue(hkey, i)
                lines.append(f"    {name}: {val[:100]}")
            winreg.CloseKey(hkey)
        except Exception as e:
            lines.append(f"    error: {e}")

    return "\n".join(lines)
