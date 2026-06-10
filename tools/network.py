"""Network tools — connectivity, IP, DNS, speed test."""
from __future__ import annotations

import socket
import subprocess
import urllib.request
import json
import time
import ssl
from datetime import datetime
import hmac
import hashlib
import concurrent.futures
from pathlib import Path
import requests

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


@tool(
    name="ping_host",
    description="Check if a host is reachable and measure latency. Can use standard ICMP ping or TCP port connection check.",
    parameters={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Hostname or IP to check"},
            "port": {"type": "integer", "description": "Optional port to test via TCP (e.g. 80, 443). If provided, TCP handshake is used.", "default": 80},
            "method": {"type": "string", "description": "Method to use: 'icmp', 'tcp', or 'auto' (try icmp first, fallback to tcp)", "enum": ["icmp", "tcp", "auto"], "default": "auto"},
        },
        "required": ["host"],
    },
)
def ping_host(host: str, port: int = 80, method: str = "auto") -> str:
    import time

    results = []

    # 1. ICMP Ping Check
    icmp_success = False
    icmp_latency = None
    if method in ("icmp", "auto"):
        try:
            # Run 2 pings
            result = subprocess.run(
                ["ping", "-n", "2", host],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            output = result.stdout.strip()
            if result.returncode == 0:
                # Find Average latency line
                avg_line = [line.strip() for line in output.split("\n") if "Average" in line]
                if avg_line:
                    results.append(f"ICMP Ping succeeded: {avg_line[0]}")
                    icmp_success = True
                else:
                    # Generic success output check
                    results.append("ICMP Ping succeeded, details:\n" + "\n".join(output.split("\n")[-2:]))
                    icmp_success = True
            else:
                results.append(f"ICMP Ping failed (exit code {result.returncode})")
        except subprocess.TimeoutExpired:
            results.append("ICMP Ping timed out (5s limit)")
        except Exception as e:
            results.append(f"ICMP Ping error: {e}")

    # 2. TCP Port Check
    tcp_success = False
    tcp_latency = None
    if method == "tcp" or (method == "auto" and not icmp_success):
        try:
            t0 = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((host, port))
            tcp_latency = (time.perf_counter() - t0) * 1000
            s.close()
            results.append(f"TCP connection to {host}:{port} succeeded in {tcp_latency:.1f}ms.")
            tcp_success = True
        except Exception as e:
            results.append(f"TCP connection to {host}:{port} failed: {e}")

    summary = f"Ping Host Status for {host}:\n" + "\n".join(f"  {r}" for r in results)
    return summary


@tool(
    name="port_scan",
    description="Scan a host for open ports within safety limits (max 100 ports).",
    parameters={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "IP address or hostname to scan"},
            "port_range": {
                "type": "string",
                "description": "Comma-separated list (e.g. '80,443'), range (e.g. '20-30'), or 'common' for standard ports.",
                "default": "common",
            },
            "timeout": {"type": "number", "description": "Timeout in seconds per port connection (default 1.0, max 3.0)", "default": 1.0},
        },
        "required": ["host"],
    },
)
def port_scan(host: str, port_range: str = "common", timeout: float = 1.0) -> str:
    timeout = max(0.1, min(timeout, 3.0))
    
    common_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1433, 3306, 3389, 5432, 8080]
    ports_to_scan = []

    if port_range == "common":
        ports_to_scan = common_ports
    elif "-" in port_range:
        try:
            start_p, end_p = map(int, port_range.split("-"))
            ports_to_scan = list(range(start_p, end_p + 1))
        except ValueError:
            return "error: Invalid port range format. Use e.g. '20-30'."
    else:
        try:
            ports_to_scan = [int(p.strip()) for p in port_range.split(",") if p.strip()]
        except ValueError:
            return "error: Invalid port format. Use comma-separated list like '80,443'."

    if not ports_to_scan:
        return "error: No ports specified to scan."

    if len(ports_to_scan) > 100:
        ports_to_scan = ports_to_scan[:100]
        trimmed = True
    else:
        trimmed = False

    open_ports = []
    
    def check_port(p):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((host, p))
            s.close()
            if result == 0:
                return p, True
        except Exception:
            pass
        return p, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_port, port): port for port in ports_to_scan}
        for fut in concurrent.futures.as_completed(futures):
            port, is_open = fut.result()
            if is_open:
                open_ports.append(port)

    open_ports.sort()

    res_str = f"Port scan results for {host} (timeout {timeout}s):\n"
    if open_ports:
        res_str += f"Open ports: {', '.join(map(str, open_ports))}"
    else:
        res_str += "No open ports found in the scanned list."

    if trimmed:
        res_str += "\nNote: Scan list was truncated to first 100 ports for safety."
        
    return res_str


@tool(
    name="ssl_certificate_check",
    description="Validate a host's TLS/SSL certificate, check expiration, issuer details, and chain trust.",
    parameters={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "Hostname to check (e.g. 'google.com')"},
            "port": {"type": "integer", "description": "Port to connect to (default 443)", "default": 443},
            "timeout": {"type": "number", "description": "Connection timeout in seconds (default 5.0)", "default": 5.0},
        },
        "required": ["host"],
    },
)
def ssl_certificate_check(host: str, port: int = 443, timeout: float = 5.0) -> str:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
    except ssl.SSLCertVerificationError as e:
        return f"SSL Verification Error: {e.reason or str(e)}\nCertificate is not trusted or host mismatched."
    except Exception as e:
        return f"SSL Connection Error: {e}"

    if not cert:
        return f"Could not retrieve SSL certificate from {host}:{port}"

    lines = [f"SSL Certificate verification for {host}:"]

    # Subject details
    subject = dict(x[0] for x in cert.get("subject", []))
    lines.append(f"  Subject CN: {subject.get('commonName')}")
    lines.append(f"  Organization: {subject.get('organizationName', 'N/A')}")

    # Issuer details
    issuer = dict(x[0] for x in cert.get("issuer", []))
    lines.append(f"  Issuer CN: {issuer.get('commonName')}")
    lines.append(f"  Issuer Org: {issuer.get('organizationName', 'N/A')}")

    # Dates
    not_before_str = cert.get("notBefore")
    not_after_str = cert.get("notAfter")
    lines.append(f"  Valid From: {not_before_str}")
    lines.append(f"  Valid Until: {not_after_str}")

    try:
        # Date parsing
        # format: e.g. "Feb 26 12:00:00 2027 GMT"
        # Since standard GMT is parsed, let's parse using strptime.
        fmt = "%b %d %H:%M:%S %Y %Z"
        expiry = datetime.strptime(not_after_str, fmt)
        remaining = expiry - datetime.utcnow()
        days_rem = remaining.days
        
        if days_rem < 0:
            lines.append(f"  ⚠️ EXPIRED: Certificate expired {-days_rem} days ago.")
        elif days_rem <= 30:
            lines.append(f"  ⚠️ WARNING: Certificate expires in {days_rem} days!")
        else:
            lines.append(f"  Status: Valid (expires in {days_rem} days)")
    except Exception as e:
        lines.append(f"  Status Parsing Error: {e}")

    # Subject Alt Names
    alt_names = [name[1] for name in cert.get("subjectAltName", []) if name[0] == "DNS"]
    if alt_names:
        lines.append(f"  Alt Names (first 5): {', '.join(alt_names[:5])}")
        if len(alt_names) > 5:
            lines.append(f"  ... and {len(alt_names) - 5} more alt names")

    return "\n".join(lines)


@tool(
    name="api_tester",
    description="Send HTTP requests (GET, POST, PUT, DELETE, etc.) with custom headers and body to test APIs.",
    parameters={
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "description": "HTTP Method: GET, POST, PUT, DELETE, PATCH, etc.",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
                "default": "GET",
            },
            "url": {"type": "string", "description": "The API endpoint URL"},
            "headers": {"type": "object", "description": "Optional dictionary of custom headers"},
            "body": {"type": "string", "description": "Optional raw body content"},
            "json_body": {"type": "object", "description": "Optional JSON payload object (body will be ignored if json_body is provided)"},
            "timeout": {"type": "number", "description": "Timeout in seconds (default 10.0)", "default": 10.0},
        },
        "required": ["url"],
    },
)
def api_tester(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    body: str | None = None,
    json_body: dict | None = None,
    timeout: float = 10.0,
) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    method = method.upper()
    timeout = max(1.0, min(timeout, 30.0))

    try:
        t0 = time.perf_counter()
        if json_body:
            resp = requests.request(method, url, headers=headers, json=json_body, timeout=timeout)
        else:
            resp = requests.request(method, url, headers=headers, data=body, timeout=timeout)
        elapsed = (time.perf_counter() - t0) * 1000
    except Exception as e:
        return f"Request failed: {e}"

    lines = [
        f"HTTP Response: {resp.status_code} {resp.reason}",
        f"Time Elapsed: {elapsed:.1f}ms",
        f"Content-Length: {len(resp.content)} bytes",
        "",
        "=== Headers ===",
    ]
    for k, v in resp.headers.items():
        lines.append(f"{k}: {v}")
    lines.append("")

    lines.append("=== Body ===")
    content_type = resp.headers.get("Content-Type", "")
    if "json" in content_type.lower():
        try:
            pretty_json = json.dumps(resp.json(), indent=2)
            lines.append(pretty_json[:2000])
            if len(pretty_json) > 2000:
                lines.append(f"... ({len(pretty_json) - 2000} more JSON characters)")
        except Exception:
            lines.append(resp.text[:2000])
    else:
        lines.append(resp.text[:2000])
        if len(resp.text) > 2000:
            lines.append(f"... ({len(resp.text) - 2000} more characters)")

    return "\n".join(lines)


@tool(
    name="webhook_manager",
    description="Create, validate, list, and forward webhook payloads. Stored in data/webhooks.json.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action to take: 'save' (store webhook config), 'list' (list saved), 'delete' (remove saved), 'send' (dispatch webhook), or 'verify_signature' (validate HMAC-SHA256 signature).",
                "enum": ["save", "list", "delete", "send", "verify_signature"],
                "default": "list",
            },
            "name": {"type": "string", "description": "Saved webhook config name (required for save, delete, send)"},
            "url": {"type": "string", "description": "Webhook endpoint URL (required for save or quick send)"},
            "headers": {"type": "object", "description": "Optional dictionary of headers for the webhook request"},
            "payload": {"type": "object", "description": "Optional JSON payload object to send"},
            "signature_header": {"type": "string", "description": "Header name containing signature (required for verify_signature)"},
            "signature": {"type": "string", "description": "Expected signature string (required for verify_signature)"},
            "secret": {"type": "string", "description": "HMAC secret key used for signing (required for verify_signature)"},
        },
        "required": ["action"],
    },
)
def webhook_manager(
    action: str,
    name: str | None = None,
    url: str | None = None,
    headers: dict | None = None,
    payload: dict | None = None,
    signature_header: str | None = None,
    signature: str | None = None,
    secret: str | None = None,
) -> str:
    db_path = Path("data/webhooks.json")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = {}
    if db_path.exists():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

    if action == "save":
        if not name:
            return "error: 'name' is required to save a webhook."
        if not url:
            return "error: 'url' is required to save a webhook."
        
        db[name] = {
            "url": url,
            "headers": headers or {},
            "payload": payload or {},
            "updated_at": datetime.now().isoformat(),
        }
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        return f"Successfully saved webhook '{name}' config."

    elif action == "list":
        if not db:
            return "No webhooks configured yet. Save one using action='save'."
        lines = ["=== Configured Webhooks ==="]
        for k, v in db.items():
            lines.append(f"- {k}\n  URL: {v['url']}\n  Headers: {json.dumps(v['headers'])}")
        return "\n".join(lines)

    elif action == "delete":
        if not name:
            return "error: 'name' is required to delete a webhook config."
        if name not in db:
            return f"Webhook config '{name}' not found."
        
        del db[name]
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        return f"Successfully deleted webhook config '{name}'."

    elif action == "send":
        target_url = url
        target_headers = headers or {}
        target_payload = payload or {}

        if name:
            if name not in db:
                return f"error: Saved webhook '{name}' not found."
            config = db[name]
            if not target_url:
                target_url = config["url"]
            # Merge headers/payload from config
            merged_headers = config.get("headers", {}).copy()
            merged_headers.update(target_headers)
            target_headers = merged_headers

            merged_payload = config.get("payload", {}).copy()
            merged_payload.update(target_payload)
            target_payload = merged_payload

        if not target_url:
            return "error: Webhook URL is required (either directly or via saved config name)."

        try:
            resp = requests.post(target_url, headers=target_headers, json=target_payload, timeout=10)
            return (
                f"Webhook dispatched successfully!\n"
                f"Target URL: {target_url}\n"
                f"Response Status: {resp.status_code} {resp.reason}\n"
                f"Response Body: {resp.text[:500]}"
            )
        except Exception as e:
            return f"Failed to dispatch webhook: {e}"

    elif action == "verify_signature":
        if not payload:
            return "error: 'payload' (dict) is required for signature verification."
        if not signature_header:
            return "error: 'signature_header' is required for signature verification."
        if not signature:
            return "error: 'signature' is required for signature verification."
        if not secret:
            return "error: 'secret' is required for signature verification."

        # Compute HMAC-SHA256 signature
        # Standard signature verification checks against raw body
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        secret_bytes = secret.encode("utf-8")
        computed = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()

        # Some signatures have prefixes, e.g. "sha256=" or "t=...,v1="
        # Let's check for standard exact match, prefix match or clean up hex
        expected_sig = signature.lower()
        if "=" in expected_sig:
            expected_sig = expected_sig.split("=")[-1]

        if hmac.compare_digest(computed, expected_sig):
            return "Signature Verification: SUCCESS. Signature matches computed HMAC-SHA256 hash."
        else:
            # Check if perhaps it matched with normal spaces JSON
            payload_bytes_spaced = json.dumps(payload).encode("utf-8")
            computed_spaced = hmac.new(secret_bytes, payload_bytes_spaced, hashlib.sha256).hexdigest()
            if hmac.compare_digest(computed_spaced, expected_sig):
                return "Signature Verification: SUCCESS (with spaces JSON). Signature matches computed HMAC-SHA256 hash."
            
            return f"Signature Verification: FAILED.\nComputed: {computed}\nExpected: {expected_sig}"

    return "error: Invalid action."
