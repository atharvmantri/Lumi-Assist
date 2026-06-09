"""Database tools — SQLite query and inspection."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from tools import tool


@tool(
    name="sqlite_query",
    description="Execute a SQL query on a SQLite database file. Use for reading data from .db or .sqlite files.",
    parameters={
        "type": "object",
        "properties": {
            "db_path": {
                "type": "string",
                "description": "Path to the SQLite database file",
            },
            "query": {
                "type": "string",
                "description": "SQL query to execute (SELECT only for safety)",
            },
            "limit": {
                "type": "integer",
                "description": "Max rows to return (default 50)",
            },
        },
        "required": ["db_path", "query"],
    },
)
def sqlite_query(db_path: str, query: str, limit: int = 50) -> str:
    # Safety: only allow SELECT queries
    if not query.strip().upper().startswith("SELECT"):
        return "error: only SELECT queries are allowed for safety"

    p = Path(db_path)
    if not p.exists():
        return f"error: database not found: {db_path}"

    try:
        conn = sqlite3.connect(str(p))
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchmany(limit)
        conn.close()

        if not rows:
            return "Query returned 0 rows."

        lines = [f"SQLite Query ({len(rows)} rows):"]

        # Column headers
        header = " | ".join(f"{c[:15]:15s}" for c in columns)
        lines.append(f"  {header}")
        lines.append(f"  {'-' * len(header)}")

        # Rows
        for row in rows[:limit]:
            row_str = " | ".join(f"{str(v)[:15]:15s}" for v in row)
            lines.append(f"  {row_str}")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="sqlite_tables",
    description="List all tables in a SQLite database with their column names.",
    parameters={
        "type": "object",
        "properties": {
            "db_path": {
                "type": "string",
                "description": "Path to the SQLite database file",
            },
        },
        "required": ["db_path"],
    },
)
def sqlite_tables(db_path: str) -> str:
    p = Path(db_path)
    if not p.exists():
        return f"error: database not found: {db_path}"

    try:
        conn = sqlite3.connect(str(p))
        cursor = conn.cursor()

        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            return "No tables found in database."

        lines = [f"Database Tables ({len(tables)}):"]
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            lines.append(f"  {table}: {', '.join(cols)}")

        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="sqlite_count",
    description="Get row counts for all tables in a SQLite database.",
    parameters={
        "type": "object",
        "properties": {
            "db_path": {
                "type": "string",
                "description": "Path to the SQLite database file",
            },
        },
        "required": ["db_path"],
    },
)
def sqlite_count(db_path: str) -> str:
    p = Path(db_path)
    if not p.exists():
        return f"error: database not found: {db_path}"

    try:
        conn = sqlite3.connect(str(p))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]

        lines = [f"Table Row Counts:"]
        total = 0
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            lines.append(f"  {table}: {count:,} rows")
            total += count

        lines.append(f"\nTotal: {total:,} rows across {len(tables)} tables")
        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"
