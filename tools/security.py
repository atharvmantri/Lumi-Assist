"""Firewall and security tools."""
from __future__ import annotations

import subprocess
import os
import json
import base64
import secrets
import hashlib
import hmac
import re
from datetime import datetime
from pathlib import Path
import requests
import win32crypt
import concurrent.futures

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
            ["powershell", "-Command", "(Get-ItemProperty HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System).EnableLUA"],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines.append(f"  UAC: {'ENABLED' if '1' in result.stdout else 'DISABLED'}")
    except:
        lines.append("  UAC: could not check")

    return "\n".join(lines)


@tool(
    name="manage_secrets",
    description="Securely store, retrieve, delete, or list credential secrets. Encrypted using Windows DPAPI.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action to take: 'set' (save secret), 'get' (retrieve secret), 'delete' (delete secret), or 'list' (list names of secrets).",
                "enum": ["set", "get", "delete", "list"],
                "default": "list",
            },
            "name": {"type": "string", "description": "Identifier key name of the secret (required for set, get, delete)"},
            "value": {"type": "string", "description": "The secret string value to store (required for action='set')"},
        },
        "required": ["action"],
    },
)
def manage_secrets(action: str, name: str | None = None, value: str | None = None) -> str:
    db_path = Path("data/vault.json")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = {}
    if db_path.exists():
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception:
            pass

    if action == "set":
        if not name or not value:
            return "error: Both 'name' and 'value' are required to save a secret."
        try:
            # Encrypt using DPAPI
            enc_bytes = win32crypt.CryptProtectData(value.encode("utf-8"), "Lumi Vault Key", None, None, None, 0)
            base64_str = base64.b64encode(enc_bytes).decode("utf-8")
            db[name] = base64_str
            
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)
            return f"Successfully saved secret '{name}' to vault."
        except Exception as e:
            return f"error encrypting/saving secret: {e}"

    elif action == "get":
        if not name:
            return "error: 'name' is required to retrieve a secret."
        if name not in db:
            return f"error: Secret '{name}' not found in vault."
        try:
            base64_str = db[name]
            enc_bytes = base64.b64decode(base64_str.encode("utf-8"))
            _, dec_bytes = win32crypt.CryptUnprotectData(enc_bytes, None, None, None, 0)
            return dec_bytes.decode("utf-8")
        except Exception as e:
            return f"error decrypting/retrieving secret: {e}"

    elif action == "delete":
        if not name:
            return "error: 'name' is required to delete a secret."
        if name not in db:
            return f"error: Secret '{name}' not found in vault."
        
        del db[name]
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
        return f"Successfully deleted secret '{name}' from vault."

    elif action == "list":
        if not db:
            return "No secrets stored in vault yet."
        keys_list = list(db.keys())
        return f"Stored Secrets Vault Keys ({len(keys_list)}):\n" + "\n".join(f"  - {k}" for k in keys_list)

    return "error: Invalid action."


@tool(
    name="generate_password",
    description="Generate a cryptographically secure random password or passphrase.",
    parameters={
        "type": "object",
        "properties": {
            "length": {"type": "integer", "description": "Password length or word count for passphrase (default 16)", "default": 16},
            "method": {
                "type": "string",
                "description": "Generator method: 'password' (character string) or 'passphrase' (readable word sequence).",
                "enum": ["password", "passphrase"],
                "default": "password",
            },
            "use_uppercase": {"type": "boolean", "description": "Include uppercase letters (for password, default true)", "default": True},
            "use_digits": {"type": "boolean", "description": "Include numbers (for password, default true)", "default": True},
            "use_special": {"type": "boolean", "description": "Include special symbols (for password, default true)", "default": True},
        },
    },
)
def generate_password(
    length: int = 16,
    method: str = "password",
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
) -> str:
    if method == "passphrase":
        words_pool = [
            "apple", "banana", "orange", "grape", "cherry", "peach", "lemon", "melon", "berry",
            "water", "river", "stone", "mountain", "forest", "desert", "cloud", "storm", "wind",
            "shadow", "winter", "summer", "autumn", "spring", "gold", "silver", "iron", "copper",
            "bronze", "castle", "knight", "shield", "sword", "arrow", "flight", "falcon", "eagle",
            "hawk", "wolf", "bear", "tiger", "lion", "fox", "deer", "rabbit", "bright", "dark",
            "silent", "loud", "swift", "slow", "heavy", "light", "warm", "cold", "happy", "brave",
        ]
        length = max(3, min(length, 12))
        chosen = [secrets.choice(words_pool) for _ in range(length)]
        return "-".join(chosen)

    # Character password method
    length = max(6, min(length, 128))
    chars = string_lower = "abcdefghijklmnopqrstuvwxyz"
    if use_uppercase:
        chars += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if use_digits:
        chars += "0123456789"
    if use_special:
        chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        
    password = [
        secrets.choice(string_lower),  # ensure at least one lowercase
    ]
    if use_uppercase:
        password.append(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    if use_digits:
        password.append(secrets.choice("0123456789"))
    if use_special:
        password.append(secrets.choice("!@#$%^&*()-_=+[]{}|;:,.<>?"))

    while len(password) < length:
        password.append(secrets.choice(chars))

    # Shuffle character list securely
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


@tool(
    name="hash_verify",
    description="Compute a hash (SHA-256, SHA-512, MD5) for a text or verify a hash comparison.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text to hash or verify"},
            "action": {
                "type": "string",
                "description": "Action: 'hash' (generate hash) or 'verify' (check matches)",
                "enum": ["hash", "verify"],
                "default": "hash",
            },
            "algorithm": {
                "type": "string",
                "description": "Hash algorithm: 'sha256', 'sha512', 'md5', or 'bcrypt'",
                "enum": ["sha256", "sha512", "md5", "bcrypt"],
                "default": "sha256",
            },
            "expected_hash": {"type": "string", "description": "The expected hash to compare against (required for action='verify')"},
        },
        "required": ["text"],
    },
)
def hash_verify(
    text: str,
    action: str = "hash",
    algorithm: str = "sha256",
    expected_hash: str | None = None,
) -> str:
    algorithm = algorithm.lower()
    
    if algorithm == "bcrypt":
        try:
            import bcrypt
        except ImportError:
            return "error: bcrypt library is not installed. Run `pip install bcrypt`."

        if action == "hash":
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(text.encode("utf-8"), salt)
            return hashed.decode("utf-8")
        else: # verify
            if not expected_hash:
                return "error: 'expected_hash' is required to verify bcrypt."
            try:
                matched = bcrypt.checkpw(text.encode("utf-8"), expected_hash.encode("utf-8"))
                return "Verification SUCCESS. Password matches hash." if matched else "Verification FAILED. Password does not match hash."
            except Exception as e:
                return f"Verification error: {e}"

    # Standard hashlib algorithms
    h_func = getattr(hashlib, algorithm, None)
    if not h_func:
        return f"error: Unsupported hash algorithm '{algorithm}'."

    computed = h_func(text.encode("utf-8")).hexdigest()

    if action == "hash":
        return computed
    else: # verify
        if not expected_hash:
            return f"error: 'expected_hash' parameter is required for action='verify'."
        matched = hmac.compare_digest(computed.lower(), expected_hash.lower())
        return f"Verification SUCCESS. Text matches expected {algorithm} hash." if matched else f"Verification FAILED. Text does not match expected {algorithm} hash."


@tool(
    name="jwt_decode_validate",
    description="Decode and inspect JSON Web Tokens (JWT) and optionally validate their signatures.",
    parameters={
        "type": "object",
        "properties": {
            "token": {"type": "string", "description": "The JWT string to decode and validate"},
            "secret": {"type": "string", "description": "HMAC secret key to verify signature (optional)"},
        },
        "required": ["token"],
    },
)
def jwt_decode_validate(token: str, secret: str | None = None) -> str:
    parts = token.split(".")
    if len(parts) != 3:
        return "error: Invalid JWT format. Token must contain exactly 3 dot-separated parts."

    header_b64, payload_b64, signature_b64 = parts

    def base64url_decode(s: str) -> bytes:
        rem = len(s) % 4
        if rem > 0:
            s += "=" * (4 - rem)
        return base64.urlsafe_b64decode(s.encode("utf-8"))

    try:
        header = json.loads(base64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(base64url_decode(payload_b64).decode("utf-8"))
    except Exception as e:
        return f"error decoding JWT sections: {e}"

    lines = [
        "JWT Contents:",
        "  Header:",
        json.dumps(header, indent=4),
        "  Payload:",
        json.dumps(payload, indent=4),
    ]

    # Expiry validation check
    exp = payload.get("exp")
    if exp:
        try:
            exp_time = datetime.fromtimestamp(int(exp))
            lines.append(f"  Expires: {exp_time} UTC")
            if exp_time < datetime.utcnow():
                lines.append("  ⚠️ Token status: EXPIRED!")
            else:
                lines.append("  Token status: ACTIVE (not expired)")
        except Exception:
            pass

    # Signature verification
    if secret:
        alg = header.get("alg", "HS256")
        if alg != "HS256":
            lines.append(f"  ⚠️ Signature verification skipped: Only HS256 is supported (found {alg}).")
        else:
            try:
                # Compute signature hash
                signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
                computed_sig_bytes = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
                computed_sig_b64 = base64.urlsafe_b64encode(computed_sig_bytes).decode("utf-8").replace("=", "")
                
                if hmac.compare_digest(computed_sig_b64, signature_b64):
                    lines.append("  ✅ Signature Verification: SUCCESS (Signature matches computed hash)")
                else:
                    lines.append("  ❌ Signature Verification: FAILED (Signature mismatch)")
            except Exception as e:
                lines.append(f"  ❌ Signature Verification error: {e}")

    return "\n".join(lines)


@tool(
    name="ssh_key_manager",
    description="Generate, rotate, list, or delete SSH key pairs inside ~/.ssh/ folder.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Action: 'create' (generate keys), 'list' (list keys), 'delete' (remove keys), or 'rotate' (replace key pair).",
                "enum": ["create", "list", "delete", "rotate"],
                "default": "list",
            },
            "key_name": {"type": "string", "description": "Identifier file name of the SSH key (default 'id_rsa')", "default": "id_rsa"},
            "key_type": {
                "type": "string",
                "description": "Algorithm: 'rsa' or 'ed25519' (default 'rsa')",
                "enum": ["rsa", "ed25519"],
                "default": "rsa",
            },
            "comment": {"type": "string", "description": "Optional email/comment to embed in public key"},
        },
        "required": ["action"],
    },
)
def ssh_key_manager(
    action: str,
    key_name: str = "id_rsa",
    key_type: str = "rsa",
    comment: str | None = None,
) -> str:
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = ssh_dir / key_name
    pub_path = ssh_dir / f"{key_name}.pub"

    if action == "create":
        if key_path.exists():
            return f"error: SSH key pair '{key_name}' already exists in {ssh_dir}."
        
        # Build command: ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ""
        cmd = ["ssh-keygen", "-t", key_type, "-f", str(key_path), "-N", ""]
        if comment:
            cmd.extend(["-C", comment])
            
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                with open(pub_path, "r", encoding="utf-8") as f:
                    pub_key = f.read().strip()
                return f"Successfully generated SSH key pair '{key_name}' in {ssh_dir}.\n\nPublic Key:\n{pub_key}"
            return f"error generating key: {result.stderr.strip()}"
        except FileNotFoundError:
            return "error: ssh-keygen command not found on PATH. OpenSSH Client must be installed."
        except Exception as e:
            return f"error: {e}"

    elif action == "delete":
        deleted = []
        for p in (key_path, pub_path):
            if p.exists():
                os.remove(p)
                deleted.append(p.name)
        if deleted:
            return f"Successfully deleted SSH key files: {', '.join(deleted)}"
        return f"SSH key pair '{key_name}' not found."

    elif action == "rotate":
        # Delete old key files and create new ones
        del_res = ssh_key_manager("delete", key_name)
        create_res = ssh_key_manager("create", key_name, key_type, comment)
        return f"Key rotation stats:\n- Delete old: {del_res}\n- Create new: {create_res}"

    elif action == "list":
        # Find all files in ~/.ssh that don't have .pub extension, and check if their pub exists
        keys = []
        for p in ssh_dir.iterdir():
            if p.is_file() and not p.suffix == ".pub":
                pub_chk = p.with_suffix(p.suffix + ".pub")
                if pub_chk.exists():
                    keys.append(p.name)
        if not keys:
            return f"No SSH key pairs found in {ssh_dir}."
        return f"Stored SSH Keys in {ssh_dir}:\n" + "\n".join(f"  - {k} (public key: {k}.pub)" for k in keys)

    return "error: Invalid action."


@tool(
    name="dependency_audit",
    description="Scan package configuration files (requirements.txt, package.json) for known vulnerabilities using the OSV.dev database.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to 'requirements.txt' or 'package.json'"},
        },
        "required": ["file_path"],
    },
)
def dependency_audit(file_path: str) -> str:
    path = Path(file_path)
    if not path.is_file():
        return f"error: file not found: {file_path}"

    ext = path.name.lower()
    packages = []

    try:
        if ext == "requirements.txt":
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Parse name and version: e.g. requests>=2.31.0 or requests==2.31.0
                    parts = re.split(r"[=<>~!]", line)
                    name = parts[0].strip()
                    version = ""
                    ver_match = re.search(r"==\s*([\d\.\w\-]+)", line)
                    if ver_match:
                        version = ver_match.group(1).strip()
                    if name:
                        packages.append({"name": name, "version": version, "ecosystem": "PyPI"})

        elif ext == "package.json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                for k, v in {**deps, **dev_deps}.items():
                    # Strip dependency constraint signs: ^1.2.3 -> 1.2.3
                    ver = re.sub(r"[^\d\.\w\-]", "", str(v))
                    packages.append({"name": k, "version": ver, "ecosystem": "npm"})
        else:
            return "error: Unsupported configuration file. Only 'requirements.txt' and 'package.json' are supported."
    except Exception as e:
        return f"error parsing file: {e}"

    if not packages:
        return f"No packages parsed from {path.name}."

    # Query OSV.dev API concurrently
    vulns = []
    
    def check_vuln(pkg):
        payload = {
            "package": {"name": pkg["name"], "ecosystem": pkg["ecosystem"]},
        }
        if pkg["version"]:
            payload["version"] = pkg["version"]
            
        try:
            resp = requests.post("https://api.osv.dev/v1/query", json=payload, timeout=5)
            if resp.status_code == 200:
                results = resp.json()
                if "vulns" in results:
                    return pkg["name"], pkg["version"], results["vulns"]
        except Exception:
            pass
        return pkg["name"], pkg["version"], []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check_vuln, pkg) for pkg in packages]
        for fut in concurrent.futures.as_completed(futures):
            name, ver, pkg_vulns = fut.result()
            if pkg_vulns:
                vulns.append((name, ver, pkg_vulns))

    if not vulns:
        return f"Dependency audit complete. Checked {len(packages)} packages. No known vulnerabilities found."

    lines = [f"⚠️ VULNERABLE PACKAGES FOUND ({len(vulns)}):"]
    for name, ver, p_vulns in vulns:
        lines.append(f"Package: {name} (version: {ver or 'any'})")
        for idx, v in enumerate(p_vulns[:3], 1):
            lines.append(f"  [{idx}] ID: {v.get('id')} | Summary: {v.get('summary')}")
        if len(p_vulns) > 3:
            lines.append(f"  ... and {len(p_vulns) - 3} more vulnerabilities.")
        lines.append("")
        
    return "\n".join(lines).strip()


@tool(
    name="secrets_scan",
    description="Scan files in the workspace (excluding venv, node_modules) for accidentally committed API keys or credentials.",
    parameters={
        "type": "object",
        "properties": {
            "search_path": {"type": "string", "description": "Local workspace folder to scan (defaults to project workspace)"},
        },
    },
)
def secrets_scan(search_path: str | None = None) -> str:
    from core.config import PROJECT_ROOT
    scan_dir = Path(search_path) if search_path else PROJECT_ROOT
    
    if not scan_dir.is_dir():
        return f"error: Scan target is not a directory: {scan_dir}"

    exclude_dirs = {".git", "venv", ".idea", "node_modules", "build", "dist", "data", "logs", "__pycache__"}
    exclude_exts = {".exe", ".pyc", ".png", ".jpg", ".zip", ".tar", ".gz", ".ico", ".spec", ".msi"}

    # Patterns matching secrets
    patterns = {
        "AWS Client ID": re.compile(r"AKIA[0-9A-Z]{16}"),
        "AWS Secret Key": re.compile(r"(?i)aws(.{0,20})?['\"][0-9a-zA-Z\/+]{40}['\"]"),
        "GitHub Access Token": re.compile(r"gh[oprs]_[0-9a-zA-Z]{36,255}"),
        "Stripe Secret Key": re.compile(r"sk_live_[0-9a-zA-Z]{24}"),
        "Generic Secret/Password Assignment": re.compile(r"(?i)(api_key|client_secret|client_token|db_password|passwd)\s*[:=]\s*['\"][0-9a-zA-Z]{16,}['\"]"),
    }

    findings = []
    
    # Traverse directories recursively
    for root, dirs, files in os.walk(scan_dir):
        # Exclude directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            p = Path(root) / file
            if p.suffix.lower() in exclude_exts:
                continue
            
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, 1):
                        for name, regex in patterns.items():
                            match = regex.search(line)
                            if match:
                                # Obfuscate secret for safety
                                secret = match.group(0)
                                obfuscated = secret[:8] + "..." + secret[-4:] if len(secret) > 12 else "********"
                                findings.append({
                                    "file": str(p.relative_to(scan_dir)),
                                    "line": line_idx,
                                    "type": name,
                                    "value": obfuscated,
                                })
            except Exception:
                pass

    if not findings:
        return "Secrets Scan complete: No API keys or credentials found in code."

    lines = [f"⚠️ SECRETS / CREDENTIALS DETECTED ({len(findings)}):"]
    for f in findings:
        lines.append(f"  - File: {f['file']}:{f['line']}")
        lines.append(f"    Type: {f['type']}")
        lines.append(f"    Found: {f['value']}")
        lines.append("")
        
    return "\n".join(lines).strip()


@tool(
    name="firewall_rule_manager",
    description="Add, delete, enable, or disable Windows Firewall rules (requires Administrator privileges).",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Firewall configuration action.",
                "enum": ["add", "delete", "enable", "disable"],
            },
            "name": {"type": "string", "description": "Unique display name for the firewall rule"},
            "port": {"type": "integer", "description": "Local port number (required for action='add')"},
            "protocol": {
                "type": "string",
                "description": "Protocol (required for action='add')",
                "enum": ["TCP", "UDP"],
                "default": "TCP",
            },
            "direction": {
                "type": "string",
                "description": "Traffic direction: 'inbound' or 'outbound' (required for action='add')",
                "enum": ["inbound", "outbound"],
                "default": "inbound",
            },
        },
        "required": ["action", "name"],
    },
)
def firewall_rule_manager(
    action: str,
    name: str,
    port: int | None = None,
    protocol: str = "TCP",
    direction: str = "inbound",
) -> str:
    try:
        if action == "add":
            if port is None:
                return "error: 'port' parameter is required to add a rule."
            dir_param = "Inbound" if direction == "inbound" else "Outbound"
            ps_cmd = f"New-NetFirewallRule -DisplayName '{name}' -Direction {dir_param} -LocalPort {port} -Protocol {protocol} -Action Allow"
        elif action == "delete":
            ps_cmd = f"Remove-NetFirewallRule -DisplayName '{name}'"
        elif action == "enable":
            ps_cmd = f"Enable-NetFirewallRule -DisplayName '{name}'"
        elif action == "disable":
            ps_cmd = f"Disable-NetFirewallRule -DisplayName '{name}'"
        else:
            return "error: Invalid action."

        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return f"Successfully executed firewall action '{action}' on rule '{name}'."
        
        # Check for privilege errors
        stderr = result.stderr.strip()
        if "UnauthorizedAccessException" in stderr or "Access is denied" in stderr:
            return "error: Administrator privileges are required to configure Windows Firewall rules."
        return f"error running firewall command: {stderr}"
        
    except Exception as e:
        return f"error: {e}"


@tool(
    name="intrusion_detection_log",
    description="Analyze Windows Event security logs or auth log files for brute force or anomalous login patterns.",
    parameters={
        "type": "object",
        "properties": {
            "log_path": {"type": "string", "description": "Optional custom auth log file path. If empty, queries Windows Security Event logs (requires Admin permissions)."},
            "max_events": {"type": "integer", "description": "Max events to retrieve (default 20)", "default": 20},
        },
    },
)
def intrusion_detection_log(log_path: str | None = None, max_events: int = 20) -> str:
    max_events = max(1, min(max_events, 100))
    
    if log_path:
        # Parse custom auth log file path
        path = Path(log_path)
        if not path.is_file():
            return f"error: log file not found: {log_path}"
        try:
            brute_force_ips = {}
            total_failed = 0
            
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    # Look for SSH failed logon patterns
                    # e.g. "Failed password for invalid user admin from 192.168.1.100 port..."
                    if "failed password" in line.lower() or "authentication failure" in line.lower():
                        total_failed += 1
                        # Extract IP address
                        ip_match = re.search(r"from\s+((?:\d{1,3}\.){3}\d{1,3})", line)
                        if ip_match:
                            ip = ip_match.group(1)
                            brute_force_ips[ip] = brute_force_ips.get(ip, 0) + 1
            
            lines = [f"Intrusion detection analysis for file '{log_path}':"]
            lines.append(f"  - Total failed login attempts found: {total_failed}")
            
            suspects = [ip for ip, count in brute_force_ips.items() if count >= 3]
            if suspects:
                lines.append("  - ⚠️ Potential Brute-Force IP Addresses (>=3 failures):")
                for ip in suspects:
                    lines.append(f"    * IP: {ip} -> {brute_force_ips[ip]} attempts")
            else:
                lines.append("  - No brute-force anomalies detected (no single IP with >=3 failures).")
                
            return "\n".join(lines)
        except Exception as e:
            return f"error analyzing log file: {e}"

    # Default: Windows Security Event logs (Event ID 4625 = Logon Failure)
    try:
        # Run PowerShell command to fetch logon failures
        ps_cmd = f"Get-WinEvent -FilterHashtable @{{LogName='Security';ID=4625}} -MaxEvents {max_events} | Select-Object TimeCreated, Message | ConvertTo-Json"
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "No events were found" in stderr:
                return "Intrusion detection log check: No recent Windows Logon Failures (Event ID 4625) found."
            if "UnauthorizedAccessException" in stderr:
                return "error: Administrator privileges are required to read the Windows Security Event Log."
            return f"error reading event log: {stderr}"
            
        data = json.loads(result.stdout)
        events = data if isinstance(data, list) else [data]
        
        lines = [f"Windows Logon Failures Event Log Audit (showing last {len(events)}):"]
        for idx, ev in enumerate(events, 1):
            time_created = ev.get("TimeCreated")
            message = ev.get("Message", "")
            
            # Extract account and source IP from message
            account = "unknown"
            ip = "unknown"
            acc_match = re.search(r"Account Name:\s*([^\r\n]+)", message)
            if acc_match:
                account = acc_match.group(1).strip()
            ip_match = re.search(r"Source Network Address:\s*([^\r\n]+)", message)
            if ip_match:
                ip = ip_match.group(1).strip()
                
            lines.append(f"  [{idx}] {time_created} | Account: {account} | IP: {ip}")
            
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="encrypt_decrypt",
    description="Symmetrically encrypt or decrypt files/strings using AES-256 Fernet tokens.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Encryption action: 'encrypt' or 'decrypt'.",
                "enum": ["encrypt", "decrypt"],
            },
            "data": {"type": "string", "description": "The text string to encrypt/decrypt (or file path if is_file=true)"},
            "key": {"type": "string", "description": "Base64-url encoded 32-byte Fernet key. If empty, a key will be generated for you on encryption."},
            "is_file": {"type": "boolean", "description": "Set to true if data is a local file path (default false)", "default": False},
        },
        "required": ["action", "data"],
    },
)
def encrypt_decrypt(
    action: str,
    data: str,
    key: str | None = None,
    is_file: bool = False,
) -> str:
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return "error: cryptography package is not installed. Run `pip install cryptography` to use encryption."

    # Parse or generate Fernet key
    try:
        f_key = key.encode("utf-8") if key else Fernet.generate_key()
        fernet = Fernet(f_key)
    except Exception as e:
        return f"error initializing key: {e}. Key must be a valid 32-byte base64-url string."

    if is_file:
        # File encryption/decryption
        path = Path(data)
        if not path.is_file():
            return f"error: File not found: {data}"
            
        try:
            with open(path, "rb") as f:
                file_bytes = f.read()
                
            if action == "encrypt":
                processed = fernet.encrypt(file_bytes)
                dest = path.with_suffix(path.suffix + ".enc")
            else: # decrypt
                processed = fernet.decrypt(file_bytes)
                dest = path.with_suffix("").with_name(path.stem.replace(".enc", "_decrypted"))
                
            with open(dest, "wb") as f:
                f.write(processed)
                
            res = f"Successfully {action}ed file '{data}' -> '{dest}'."
            if not key and action == "encrypt":
                res += f"\nSecret Key (SAVE THIS TO DECRYPT): {f_key.decode('utf-8')}"
            return res
        except Exception as e:
            return f"error processing file: {e}"

    else:
        # String encryption/decryption
        try:
            if action == "encrypt":
                processed = fernet.encrypt(data.encode("utf-8")).decode("utf-8")
                res = f"Encrypted text: {processed}"
                if not key:
                    res += f"\nSecret Key (SAVE THIS TO DECRYPT): {f_key.decode('utf-8')}"
                return res
            else: # decrypt
                processed = fernet.decrypt(data.encode("utf-8")).decode("utf-8")
                return f"Decrypted text: {processed}"
        except Exception as e:
            return f"error processing text: {e}"
