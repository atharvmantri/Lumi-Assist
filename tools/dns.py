"""DNS tools — lookup, resolve, and query DNS records."""
from __future__ import annotations

import socket
import subprocess

from tools import tool


@tool(
    name="dns_lookup",
    description="Look up the IP address(es) for a domain name.",
    parameters={
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Domain name to look up (e.g. 'google.com')",
            },
        },
        "required": ["domain"],
    },
)
def dns_lookup(domain: str) -> str:
    try:
        results = socket.getaddrinfo(domain, None, socket.AF_INET)
        ips = list(set(r[4][0] for r in results))
        return f"DNS Lookup for {domain}:\n" + "\n".join(f"  {ip}" for ip in ips)
    except socket.gaierror as e:
        return f"error: {e}"


@tool(
    name="dns_records",
    description="Query DNS records (A, MX, NS, TXT) using nslookup.",
    parameters={
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Domain to query",
            },
            "record_type": {
                "type": "string",
                "description": "Record type: 'A', 'MX', 'NS', 'TXT', 'CNAME', 'AAAA'",
                "enum": ["A", "MX", "NS", "TXT", "CNAME", "AAAA"],
            },
        },
        "required": ["domain"],
    },
)
def dns_records(domain: str, record_type: str = "A") -> str:
    try:
        result = subprocess.run(
            ["nslookup", f"-type={record_type}", domain],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return f"nslookup error: {result.stderr.strip()[:200]}"
        return f"DNS {record_type} records for {domain}:\n\n{result.stdout.strip()[:2000]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="reverse_dns",
    description="Perform reverse DNS lookup (IP to hostname).",
    parameters={
        "type": "object",
        "properties": {
            "ip": {
                "type": "string",
                "description": "IP address to reverse lookup",
            },
        },
        "required": ["ip"],
    },
)
def reverse_dns(ip: str) -> str:
    try:
        hostname, aliases, _ = socket.gethostbyaddr(ip)
        result = f"Reverse DNS for {ip}: {hostname}"
        if aliases:
            result += f"\nAliases: {', '.join(aliases)}"
        return result
    except socket.herror as e:
        return f"error: {e}"


@tool(
    name="traceroute",
    description="Trace the network route to a host.",
    parameters={
        "type": "object",
        "properties": {
            "host": {
                "type": "string",
                "description": "Hostname or IP to trace",
            },
            "max_hops": {
                "type": "integer",
                "description": "Maximum number of hops (default 15)",
            },
        },
        "required": ["host"],
    },
)
def traceroute(host: str, max_hops: int = 15) -> str:
    try:
        result = subprocess.run(
            ["tracert", "-d", "-h", str(max_hops), host],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        output = result.stdout.strip()
        if not output:
            return f"traceroute to {host} failed: {result.stderr.strip()[:200]}"
        return f"Traceroute to {host}:\n\n{output[:3000]}"
    except Exception as e:
        return f"error: {e}"
