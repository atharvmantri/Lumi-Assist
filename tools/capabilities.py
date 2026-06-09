"""Capability listing — Lumi can describe what it can do."""
from __future__ import annotations

from tools import tool, REGISTRY


@tool(
    name="list_capabilities",
    description=(
        "List everything Lumi can do. Use when the user asks "
        "'what can you do', 'what are your capabilities', 'help', "
        "'what tools do you have', etc. Returns a categorized summary."
    ),
    parameters={"type": "object", "properties": {}, "required": []},
)
def list_capabilities() -> str:
    # Group tools by module
    modules: dict[str, list[str]] = {}
    for name, spec in sorted(REGISTRY.items()):
        mod = spec.module.split(".")[-1]
        modules.setdefault(mod, []).append(name)

    category_labels = {
        "apps": "App Control",
        "archive": "Archives",
        "browser": "Web & Browser",
        "conv_manage": "Conversation Management",
        "conversations": "Conversation Search",
        "disk": "System Monitoring",
        "export_html": "Export",
        "file_search": "File Operations",
        "files": "File Operations",
        "media_control": "Media & Keyboard",
        "memory": "Memory & Facts",
        "network": "Network",
        "notes": "Notes",
        "python_exec": "Code Execution",
        "screen": "Screen",
        "self_test": "Diagnostics",
        "shell": "Shell Commands",
        "speak": "Voice",
        "system": "System & Clipboard",
        "system_info": "System Info",
        "system_power": "Power Control",
        "tasks": "Tasks & Todos",
        "timer": "Timers & Reminders",
        "weather": "Weather & Time",
    }

    lines = ["Lumi Capabilities:"]
    total = 0
    for mod in sorted(modules, key=lambda m: category_labels.get(m, m)):
        tools_list = modules[mod]
        label = category_labels.get(mod, mod.title())
        lines.append(f"\n  {label}:")
        for t in tools_list:
            desc = REGISTRY[t].description.split(".")[0]
            lines.append(f"    - {t}: {desc}")
            total += 1

    lines.insert(1, f"\n  {total} tools across {len(modules)} categories\n")
    return "\n".join(lines)
