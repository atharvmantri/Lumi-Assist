"""Shell command execution. EVERY shell call is logged to logs/commands.log
per PRD section 13."""
from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool


_LOG_PATH = PROJECT_ROOT / "logs" / "commands.log"


def _log(cmd: str, shell: str, rc: int, stdout: str, stderr: str, elapsed: float) -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            ts = datetime.now().isoformat(timespec="seconds")
            f.write(f"\n=== {ts}  shell={shell}  rc={rc}  elapsed={elapsed:.2f}s ===\n")
            f.write(f"$ {cmd}\n")
            if stdout:
                f.write(f"--- stdout ---\n{stdout}\n")
            if stderr:
                f.write(f"--- stderr ---\n{stderr}\n")
    except Exception:   # noqa: BLE001 — never let logging take down execution
        pass


@tool(
    name="run_command",
    description=(
        "Run a shell command on the user's Windows PC and return its output. "
        "Use shell='powershell' for PowerShell (preferred for anything beyond "
        "trivial commands) or shell='cmd' for legacy CMD. Times out after "
        "30 seconds. Use this for system queries, file ops, scripted automation. "
        "Every command is logged to logs/commands.log."
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute, e.g. 'Get-Process | Select-Object -First 5'",
            },
            "shell": {
                "type": "string",
                "enum": ["powershell", "cmd"],
                "description": "Which shell to use (default powershell)",
                "default": "powershell",
            },
        },
        "required": ["command"],
    },
    confirm=False,   # not gated by default; tighten if you want a per-call prompt
)
def run_command(command: str, shell: str = "powershell") -> str:
    if shell not in ("powershell", "cmd"):
        return f"error: unknown shell {shell!r} (expected 'powershell' or 'cmd')"

    if shell == "powershell":
        argv = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    else:
        argv = ["cmd", "/c", command]

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
            shell=False,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - t0
        _log(command, shell, -1, "", "TIMEOUT after 30s", elapsed)
        return "error: command timed out after 30 seconds"
    except FileNotFoundError as e:
        return f"error: shell not found: {e}"

    elapsed = time.perf_counter() - t0
    _log(command, shell, proc.returncode, proc.stdout, proc.stderr, elapsed)

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode == 0:
        if not out:
            return "(command succeeded with no output)"
        # Truncate huge outputs to keep LLM context manageable.
        if len(out) > 4000:
            out = out[:4000] + f"\n... (truncated, {len(out)-4000} more chars)"
        return out
    # Non-zero exit
    msg = f"command exited with code {proc.returncode}"
    if err:
        msg += f"\nstderr:\n{err[:2000]}"
    if out:
        msg += f"\nstdout:\n{out[:2000]}"
    return msg
