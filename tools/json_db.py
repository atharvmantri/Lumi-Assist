"""JSON database — simple file-based JSON store with queries."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from core.config import PROJECT_ROOT
from tools import tool

DB_DIR = PROJECT_ROOT / "data" / "json_db"


def _get_db(name: str) -> Path:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_DIR / f"{name}.json"


def _load_db(name: str) -> list[dict]:
    path = _get_db(name)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_db(name: str, data: list[dict]) -> None:
    path = _get_db(name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@tool(
    name="db_insert",
    description="Insert a record into a named JSON database collection.",
    parameters={
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "Collection name (e.g. 'contacts', 'inventory')",
            },
            "record": {
                "type": "string",
                "description": "JSON object to insert (e.g. '{\"name\": \"John\", \"age\": 30}')",
            },
        },
        "required": ["collection", "record"],
    },
)
def db_insert(collection: str, record: str) -> str:
    try:
        data = json.loads(record)
    except json.JSONDecodeError as e:
        return f"error: invalid JSON record: {e}"

    if not isinstance(data, dict):
        return "error: record must be a JSON object"

    data["_id"] = int(time.time() * 1000)
    data["_created"] = datetime.now().isoformat()

    db = _load_db(collection)
    db.append(data)
    _save_db(collection, db)

    return f"Inserted into '{collection}' (now {len(db)} records)"


@tool(
    name="db_query",
    description="Query records from a JSON database collection.",
    parameters={
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "Collection name",
            },
            "filter": {
                "type": "string",
                "description": "Optional JSON filter object to match (e.g. '{\"status\": \"active\"}')",
            },
            "limit": {
                "type": "integer",
                "description": "Max results (default 20)",
            },
        },
        "required": ["collection"],
    },
)
def db_query(collection: str, filter: str = "", limit: int = 20) -> str:
    db = _load_db(collection)
    if not db:
        return f"Collection '{collection}' is empty or doesn't exist."

    # Apply filter
    if filter:
        try:
            filt = json.loads(filter)
            db = [r for r in db if all(r.get(k) == v for k, v in filt.items())]
        except json.JSONDecodeError as e:
            return f"error: invalid filter JSON: {e}"

    db = db[:limit]

    lines = [f"Collection '{collection}' ({len(db)} results):"]
    for r in db[:limit]:
        lines.append(f"  {json.dumps(r, ensure_ascii=False)[:200]}")

    return "\n".join(lines)


@tool(
    name="db_count",
    description="Count records in a JSON database collection.",
    parameters={
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "Collection name",
            },
        },
        "required": ["collection"],
    },
)
def db_count(collection: str) -> str:
    db = _load_db(collection)
    return f"Collection '{collection}': {len(db)} records"


@tool(
    name="db_delete",
    description="Delete a JSON database collection or specific records.",
    parameters={
        "type": "object",
        "properties": {
            "collection": {
                "type": "string",
                "description": "Collection name",
            },
            "delete_all": {
                "type": "boolean",
                "description": "Delete entire collection (default false)",
            },
        },
        "required": ["collection"],
    },
)
def db_delete(collection: str, delete_all: bool = False) -> str:
    path = _get_db(collection)
    if delete_all:
        if path.exists():
            path.unlink()
            return f"Deleted collection '{collection}'"
        return f"Collection '{collection}' doesn't exist."
    return "error: specify delete_all=true to delete entire collection, or use a filter to delete specific records"
