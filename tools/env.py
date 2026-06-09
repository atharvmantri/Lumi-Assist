"""Environment variable and PATH management."""
from __future__ import annotations

import os

from tools import tool


@tool(
    name="get_env",
    description="Get the value of an environment variable.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Environment variable name (e.g. 'PATH', 'USERNAME', 'TEMP')",
            },
        },
        "required": ["name"],
    },
)
def get_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return f"Environment variable '{name}' is not set."
    if len(value) > 1000:
        return f"{name} ({len(value)} chars, truncated):\n{value[:1000]}..."
    return f"{name} = {value}"


@tool(
    name="list_env",
    description="List all environment variables or filter by a keyword.",
    parameters={
        "type": "object",
        "properties": {
            "filter": {
                "type": "string",
                "description": "Optional keyword to filter variable names",
            },
        },
        "required": [],
    },
)
def list_env(filter: str = "") -> str:
    env_vars = dict(os.environ)
    if filter:
        env_vars = {k: v for k, v in env_vars.items() if filter.lower() in k.lower()}

    if not env_vars:
        return f"No environment variables found" + (f" matching '{filter}'" if filter else "")

    lines = [f"Environment Variables ({len(env_vars)}):"]
    for key in sorted(env_vars):
        val = env_vars[key]
        display = val[:80] + "..." if len(val) > 80 else val
        lines.append(f"  {key}={display}")

    return "\n".join(lines)


@tool(
    name="get_path",
    description="Show the system PATH with one directory per line.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def get_path() -> str:
    path_str = os.environ.get("PATH", "")
    if not path_str:
        return "PATH is not set."

    dirs = path_str.split(os.pathsep)
    lines = [f"PATH ({len(dirs)} directories):"]
    for i, d in enumerate(dirs, 1):
        lines.append(f"  {i}. {d}")

    return "\n".join(lines)
