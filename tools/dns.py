"""DNS tools — lookup, resolve, and query DNS records."""
from __future__ import annotations

import socket
import subprocess

from tools import tool


@tool(
    name="dns_lookup",
    description="Look up IP addresses, query specific DNS servers, check DNS propagation, or find active subdomains.",
    parameters={
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Domain name to look up (e.g. 'google.com')",
            },
            "dns_server": {
                "type": "string",
                "description": "Optional specific DNS server to query (e.g. '8.8.8.8')",
            },
            "check_propagation": {
                "type": "boolean",
                "description": "If true, queries Google, Cloudflare, Quad9, and OpenDNS to verify propagation.",
                "default": False,
            },
            "find_subdomains": {
                "type": "boolean",
                "description": "If true, enumerates common subdomains to check which ones are active.",
                "default": False,
            },
        },
        "required": ["domain"],
    },
)
def dns_lookup(
    domain: str,
    dns_server: str | None = None,
    check_propagation: bool = False,
    find_subdomains: bool = False,
) -> str:
    import concurrent.futures
    import re

    # Helper function to query a specific server using nslookup
    def query_server(dom: str, server: str) -> list[str]:
        try:
            result = subprocess.run(
                ["nslookup", dom, server],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output = result.stdout.strip()
            parts = re.split(r"Non-authoritative answer:", output, flags=re.IGNORECASE)
            answer_part = parts[-1] if len(parts) > 1 else output
            
            ips = re.findall(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)", answer_part)
            ips = [ip for ip in ips if ip != server]
            return list(set(ips))
        except Exception:
            return []

    # If specific DNS server lookup requested
    if dns_server:
        ips = query_server(domain, dns_server)
        if ips:
            return f"DNS Lookup for {domain} via DNS server {dns_server}:\n" + "\n".join(f"  {ip}" for ip in ips)
        else:
            return f"DNS Lookup for {domain} via DNS server {dns_server} failed or returned no A records."

    # If propagation check requested
    if check_propagation:
        resolvers = {
            "Cloudflare (1.1.1.1)": "1.1.1.1",
            "Google (8.8.8.8)": "8.8.8.8",
            "Quad9 (9.9.9.9)": "9.9.9.9",
            "OpenDNS (208.67.222.222)": "208.67.222.222",
        }
        lines = [f"DNS Propagation Check for {domain}:"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(query_server, domain, ip): name for name, ip in resolvers.items()}
            for fut in concurrent.futures.as_completed(futures):
                name = futures[fut]
                try:
                    res_ips = fut.result()
                    if res_ips:
                        lines.append(f"  ✅ {name}: {', '.join(res_ips)}")
                    else:
                        lines.append(f"  ❌ {name}: No records / Timeout")
                except Exception as e:
                    lines.append(f"  ❌ {name}: Error ({e})")
        return "\n".join(lines)

    # If subdomain scanning requested
    if find_subdomains:
        common_subdomains = ["www", "mail", "app", "api", "dev", "stage", "admin", "shop", "blog", "portal", "test", "support", "mx", "vpn", "secure"]
        lines = [f"Subdomain check for {domain}:"]
        active_found = []

        def resolve_subdomain(sub: str) -> tuple[str, str | None]:
            sub_domain = f"{sub}.{domain}"
            try:
                addr = socket.gethostbyname(sub_domain)
                return sub_domain, addr
            except Exception:
                return sub_domain, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(resolve_subdomain, sub) for sub in common_subdomains]
            for fut in concurrent.futures.as_completed(futures):
                sub_domain, addr = fut.result()
                if addr:
                    active_found.append(f"  ✅ {sub_domain} -> {addr}")

        if active_found:
            lines.extend(sorted(active_found))
        else:
            lines.append("  No active common subdomains resolved.")
        return "\n".join(lines)

    # Default lookup
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
