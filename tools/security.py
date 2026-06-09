"""Firewall and security tools."""
from __future__ import annotations

import subprocess

from tools import tool


@tool(
    name="firewall_rules",
    description="List Windows Firewall rules, optionally filtered by enabled status or direction.",
    parameters={
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "description": "Filter by direction: 'inbound', 'outbound', 'all' (default 'inbound')",
                "enum": ["inbound", "outbound", "all"],
            },
            "enabled": {
                "type": "boolean",
                "description": "Show only enabled rules (default true)",
            },
            "limit": {
                "type": "integer",
                "description": "Max rules to show (default 30)",
            },
        },
        "required": [],
    },
)
def firewall_rules(direction: str = "inbound", enabled: bool = True, limit: int = 30) -> str:
    try:
        dir_filter = "Inbound" if direction == "inbound" else "Outbound" if direction == "outbound" else ""

        ps_cmd = f"Get-NetFirewallRule"
        if enabled:
            ps_cmd += " | Where-Object {{ $_.Enabled -eq 'True' }}"
        if dir_filter:
            ps_cmd += f" | Where-Object {{ $_.Direction -eq '{dir_filter}' }}"
        ps_cmd += f" | Select-Object -First {limit} DisplayName, Profile, Direction, Action, Enabled | Format-Table -AutoSize"

        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if not result.stdout.strip():
            return f"No firewall rules found" + (f" ({direction}, enabled)" if enabled else "")
        return f"Firewall Rules:\n{result.stdout.strip()[:4000]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="open_ports",
    description="List all currently open/listening network ports.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def open_ports() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess | Sort-Object LocalPort | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if not result.stdout.strip():
            return "No listening ports found."
        return f"Open Ports:\n{result.stdout.strip()}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="active_connections",
    description="Show active network connections with remote addresses and ports.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max connections to show (default 30)",
            },
        },
        "required": [],
    },
)
def active_connections(limit: int = 30) -> str:
    try:
        result = subprocess.run(
            ["netstat", "-an", "-p", "TCP"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = result.stdout.strip().split("\n")
        # Filter for ESTABLISHED
        established = [l for l in lines if "ESTABLISHED" in l]
        listening = [l for l in lines if "LISTENING" in l]

        out_lines = [f"Active Connections ({len(established)} established, {len(listening)} listening):"]
        for l in established[:limit]:
            out_lines.append(f"  {l.strip()}")

        if len(established) > limit:
            out_lines.append(f"  ...and {len(established) - limit} more")

        return "\n".join(out_lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="windows_security_audit",
    description="Quick Windows security audit: UAC status, defender status, firewall status.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def windows_security_audit() -> str:
    lines = ["Windows Security Audit:"]

    # Windows Defender
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-MpPreference | Select-Object DisableRealtimeMonitoring, DisableBehaviorMonitoring"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines.append(f"  Defender: {'DISABLED' if 'True' in result.stdout else 'ENABLED'}")
    except:
        lines.append("  Defender: could not check")

    # Firewall
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-NetFirewallProfile | Where-Object {$_.Enabled -eq $true} | Select-Object Name"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        profiles = [l.strip() for l in result.stdout.strip().split("\n") if l.strip() and "----" not in l]
        lines.append(f"  Firewall: {len(profiles)} profile(s) enabled")
    except:
        lines.append("  Firewall: could not check")

    # UAC
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-ItemProperty HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System -Name EnableLUA"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines.append(f"  UAC: {'ENABLED' if '1' in result.stdout else 'DISABLED'}")
    except:
        lines.append("  UAC: could not check")

    return "\n".join(lines)
