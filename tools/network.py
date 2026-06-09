"""Network tools — connectivity, IP, DNS, speed test."""
from __future__ import annotations

import socket
import subprocess
import urllib.request
import json

from tools import tool


@tool(
    name="get_network_info",
    description=(
        "Get network information: local IP, public IP, DNS servers, "
        "WiFi name, connection type. Use when the user asks about their network."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_network_info() -> str:
    lines = []

    # Local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        lines.append(f"Local IP: {local_ip}")
    except Exception as e:
        lines.append(f"Local IP: error ({e})")

    # Public IP
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5) as resp:
            data = json.loads(resp.read())
            lines.append(f"Public IP: {data.get('ip', 'unknown')}")
    except Exception:
        lines.append("Public IP: could not fetch")

    # DNS servers
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-DnsClientServerAddress | Where-Object { $_.AddressFamily -eq 2 } | Select-Object -ExpandProperty ServerAddresses"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        dns = result.stdout.strip().split("\n")
        dns = [d.strip() for d in dns if d.strip()]
        if dns:
            lines.append(f"DNS: {', '.join(dns[:4])}")
    except Exception:
        pass

    # WiFi name
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in result.stdout.split("\n"):
            if "SSID" in line and "BSSID" not in line:
                name = line.split(":", 1)[-1].strip()
                lines.append(f"WiFi: {name}")
                break
    except Exception:
        pass

    return "\n".join(lines) if lines else "No network info available."


@tool(
    name="ping",
    description="Ping a host and return the result. Use to check if a server or website is reachable.",
    parameters={
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "Hostname or IP to ping (e.g. 'google.com', '8.8.8.8')",
            },
            "count": {
                "type": "integer",
                "description": "Number of pings (default 4)",
            },
        },
        "required": ["host"],
    },
)
def ping(host: str, count: int = 4) -> str:
    count = max(1, min(count, 10))
    try:
        result = subprocess.run(
            ["ping", "-n", str(count), host],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.strip()
        # Parse key stats
        lines = output.split("\n")
        # Find the statistics lines
        stats = []
        for line in lines:
            if "Lost" in line or "Minimum" in line or "Average" in line:
                stats.append(line.strip())

        if stats:
            return f"Ping to {host}:\n" + "\n".join(stats)

        # Fallback: just show last 3 lines
        return f"Ping to {host}:\n" + "\n".join(lines[-4:])
    except subprocess.TimeoutExpired:
        return f"Ping to {host} timed out after 15s"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="internet_speed_test",
    description="Run a quick internet speed test. Returns download speed in Mbps.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def internet_speed_test() -> str:
    # Quick test: download a known file and measure speed
    try:
        # Use a small fast.com-style test
        test_url = "https://speed.cloudflare.com/__down?bytes=5000000"  # 5MB
        import time as _time
        t0 = _time.perf_counter()
        with urllib.request.urlopen(test_url, timeout=30) as resp:
            data = resp.read()
        elapsed = _time.perf_counter() - t0

        size_mb = len(data) / (1024 * 1024)
        speed_mbps = (size_mb * 8) / elapsed  # megabits per second

        return (
            f"Speed test results:\n"
            f"  Download: {speed_mbps:.1f} Mbps\n"
            f"  Data: {size_mb:.1f} MB in {elapsed:.1f}s"
        )
    except Exception as e:
        return f"error running speed test: {e}"
