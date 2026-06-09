"""System power control — lock, sleep, hibernate, shutdown, restart.

Destructive by nature. The system prompt instructs the model to confirm
before invoking any of these. Tools also require an explicit `confirm=True`
to fire — a defense-in-depth check in case the model decides to ignore
the prompt-level instruction.
"""
from __future__ import annotations

import subprocess

from tools import tool


def _run_rundll(args: list[str]) -> tuple[int, str, str]:
    """Run a rundll32 command (used for lock workstation)."""
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)
    return proc.returncode, proc.stdout, proc.stderr


def _run_shutdown(action_flag: str, *, force: bool = False) -> str:
    """Invoke `shutdown.exe` with the right flag (log off / restart / hibernate / sleep / shutdown)."""
    cmd = ["shutdown", action_flag]
    if force:
        cmd.append("/f")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"
    if proc.returncode == 0:
        verb = action_flag.lstrip("/")
        return f"scheduled {verb} (force={force})"
    return f"shutdown returned {proc.returncode}: {proc.stderr.strip() or 'unknown error'}"


@tool(
    name="lock_workstation",
    description="Lock the workstation (same as Win+L). No confirmation required — the user just gets locked out, nothing destructive.",
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def lock_workstation() -> str:
    rc, out, err = _run_rundll(["rundll32.exe", "user32.dll,LockWorkStation"])
    if rc == 0:
        return "workstation locked"
    return f"error: rc={rc} {err.strip()}"


@tool(
    name="sleep_pc",
    description=(
        "Put the PC to sleep. Destructive in the sense that the user will need "
        "to wake the machine — confirm before invoking. Confirm param must be true."
    ),
    parameters={
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Must be true. Set this after asking the user."},
        },
        "required": [],
    },
)
def sleep_pc(confirm: bool = False) -> str:
    if not confirm:
        return "refused: confirm must be True. Ask the user first."
    return _run_shutdown("/h")    # /h is hibernate; Windows has no clean sleep-from-CLI flag


@tool(
    name="hibernate_pc",
    description=(
        "Hibernate the PC. Confirm param must be true. Use sleep_pc for normal sleep."
    ),
    parameters={
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Must be true."},
        },
        "required": [],
    },
)
def hibernate_pc(confirm: bool = False) -> str:
    if not confirm:
        return "refused: confirm must be True. Ask the user first."
    return _run_shutdown("/h")


@tool(
    name="restart_pc",
    description=(
        "Restart Windows. Confirm param must be true. Set force=True to skip "
        "the 'are you sure you want to close programs' dialog."
    ),
    parameters={
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Must be true."},
            "force": {"type": "boolean", "description": "Force-close running apps (default false)"},
        },
        "required": [],
    },
)
def restart_pc(confirm: bool = False, force: bool = False) -> str:
    if not confirm:
        return "refused: confirm must be True. Ask the user first."
    return _run_shutdown("/r", force=force)


@tool(
    name="shutdown_pc",
    description=(
        "Shut down Windows. Confirm param must be true. Set force=True to skip "
        "the 'are you sure you want to close programs' dialog."
    ),
    parameters={
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Must be true."},
            "force": {"type": "boolean", "description": "Force-close running apps (default false)"},
        },
        "required": [],
    },
)
def shutdown_pc(confirm: bool = False, force: bool = False) -> str:
    if not confirm:
        return "refused: confirm must be True. Ask the user first."
    return _run_shutdown("/s", force=force)
