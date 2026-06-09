"""Task/todo list management tool."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

TASKS_PATH = PROJECT_ROOT / "data" / "tasks.json"


def _load_tasks() -> list[dict]:
    if TASKS_PATH.exists():
        with open(TASKS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_tasks(tasks: list[dict]) -> None:
    TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_PATH, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


@tool(
    name="add_task",
    description=(
        "Add a task or todo item. Use when the user says 'add a task', "
        "'remind me to...', 'add to my todo list', 'I need to...', etc."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The task description",
            },
            "priority": {
                "type": "string",
                "description": "Priority: 'high', 'medium', 'low' (default 'medium')",
                "enum": ["high", "medium", "low"],
            },
        },
        "required": ["text"],
    },
)
def add_task(text: str, priority: str = "medium") -> str:
    tasks = _load_tasks()
    entry = {
        "id": len(tasks) + 1,
        "text": text,
        "priority": priority,
        "status": "pending",
        "created": datetime.now().isoformat(),
        "epoch": time.time(),
    }
    tasks.append(entry)
    _save_tasks(tasks)
    return f"Task added: {text} (priority: {priority})"


@tool(
    name="complete_task",
    description="Mark a task as completed by its ID or keyword.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Task ID or keyword to mark complete",
            },
        },
        "required": ["query"],
    },
)
def complete_task(query: str) -> str:
    tasks = _load_tasks()

    # Try ID first
    try:
        task_id = int(query)
        for t in tasks:
            if t.get("id") == task_id and t.get("status") != "completed":
                t["status"] = "completed"
                t["completed"] = datetime.now().isoformat()
                _save_tasks(tasks)
                return f"Task #{task_id} completed: {t['text']}"
    except ValueError:
        pass

    # Search by keyword
    q_lower = query.lower()
    for t in tasks:
        if t.get("status") == "pending" and q_lower in t.get("text", "").lower():
            t["status"] = "completed"
            t["completed"] = datetime.now().isoformat()
            _save_tasks(tasks)
            return f"Task completed: {t['text']}"

    return f"No pending task found matching '{query}'"


@tool(
    name="list_tasks",
    description="List all tasks, optionally filtered by status.",
    parameters={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status: 'pending', 'completed', 'all' (default 'pending')",
                "enum": ["pending", "completed", "all"],
            },
        },
        "required": [],
    },
)
def list_tasks(status: str = "pending") -> str:
    tasks = _load_tasks()

    if status != "all":
        tasks = [t for t in tasks if t.get("status") == status]

    if not tasks:
        return f"No {status} tasks."

    lines = [f"Tasks ({status}):"]
    pending_count = 0
    for t in tasks:
        if t.get("status") == "pending":
            pending_count += 1
        p = {"high": "!", "medium": "~", "low": "."}.get(t.get("priority", "medium"), "~")
        check = "[x]" if t.get("status") == "completed" else "[ ]"
        lines.append(f"  {check} #{t.get('id', '?')} [{p}] {t.get('text', '')}")

    if status == "all":
        pending = sum(1 for t in tasks if t.get("status") == "pending")
        lines.append(f"\n{pending} pending, {len(tasks) - pending} completed")

    return "\n".join(lines)


@tool(
    name="delete_task",
    description="Delete a task by its ID or keyword.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Task ID or keyword to delete",
            },
        },
        "required": ["query"],
    },
)
def delete_task(query: str) -> str:
    tasks = _load_tasks()

    # Try ID first
    try:
        task_id = int(query)
        for i, t in enumerate(tasks):
            if t.get("id") == task_id:
                text = tasks.pop(i).get("text", "")
                _save_tasks(tasks)
                return f"Deleted task #{task_id}: {text}"
    except ValueError:
        pass

    # Search by keyword
    q_lower = query.lower()
    for i, t in enumerate(tasks):
        if q_lower in t.get("text", "").lower():
            text = tasks.pop(i).get("text", "")
            _save_tasks(tasks)
            return f"Deleted task: {text}"

    return f"No task found matching '{query}'"
