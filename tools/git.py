"""Git integration tools."""
from __future__ import annotations

import subprocess
from pathlib import Path

from tools import tool


@tool(
    name="git_status",
    description="Get git status of the current repository.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def git_status() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        if not result.stdout.strip():
            return "Working tree clean — no changes."
        lines = ["Git Status:"]
        for line in result.stdout.strip().split("\n"):
            lines.append(f"  {line}")
        return "\n".join(lines)
    except FileNotFoundError:
        return "error: git not found"


@tool(
    name="git_log",
    description="View recent git commits.",
    parameters={
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of commits to show (default 10)",
            },
        },
        "required": [],
    },
)
def git_log(count: int = 10) -> str:
    try:
        result = subprocess.run(
            ["git", "log", f"--pretty=format:%h %s (%cr)", f"-{count}"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        lines = ["Recent Commits:"]
        for line in result.stdout.strip().split("\n"):
            lines.append(f"  {line}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="git_diff",
    description="Show git diff of unstaged changes.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def git_diff() -> str:
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        if not result.stdout.strip():
            return "No unstaged changes."
        return f"Git Diff:\n{result.stdout.strip()[:4000]}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="git_branch",
    description="List git branches and show current branch.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "-v"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path.cwd()),
        )
        if result.returncode != 0:
            return f"error: {result.stderr.strip()[:200]}"
        lines = ["Branches:"]
        for line in result.stdout.strip().split("\n"):
            current = "*" if line.startswith("*") else " "
            lines.append(f"  {current} {line.strip()}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"
