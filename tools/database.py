"""Database tools — SQLite query and inspection."""
from __future__ import annotations

import sqlite3
import os
import zipfile
from datetime import datetime
import shutil
import json
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


def get_db_connection(uri: str):
    import urllib.parse
    if uri.startswith("sqlite:///"):
        path = uri[10:]
        return sqlite3.connect(path), "sqlite"
    elif not ("://" in uri):
        return sqlite3.connect(uri), "sqlite"
    
    parsed = urllib.parse.urlparse(uri)
    scheme = parsed.scheme.lower()
    
    if scheme in ("postgresql", "postgres"):
        try:
            import psycopg2
            return psycopg2.connect(uri), "postgres"
        except ImportError:
            try:
                import pg8000
                db = parsed.path.lstrip('/')
                return pg8000.dbapi.connect(
                    host=parsed.hostname,
                    user=parsed.username,
                    password=parsed.password,
                    port=parsed.port or 5432,
                    database=db
                ), "postgres"
            except ImportError:
                raise ImportError("Neither `psycopg2` nor `pg8000` is installed to connect to PostgreSQL.")
                
    elif scheme == "mysql":
        try:
            import pymysql
            db = parsed.path.lstrip('/')
            return pymysql.connect(
                host=parsed.hostname,
                user=parsed.username,
                password=parsed.password,
                port=parsed.port or 3306,
                database=db
            ), "mysql"
        except ImportError:
            try:
                import mysql.connector
                db = parsed.path.lstrip('/')
                return mysql.connector.connect(
                    host=parsed.hostname,
                    user=parsed.username,
                    password=parsed.password,
                    port=parsed.port or 3306,
                    database=db
                ), "mysql"
            except ImportError:
                raise ImportError("Neither `pymysql` nor `mysql-connector-python` is installed to connect to MySQL.")
    else:
        raise ValueError(f"Unsupported database scheme: {scheme}")


@tool(
    name="query_database",
    description="Execute SQL queries (SELECT, INSERT, UPDATE, DELETE, etc.) against a database.",
    parameters={
        "type": "object",
        "properties": {
            "connection_uri": {"type": "string", "description": "Database URI (e.g. 'sqlite:///path/to/db.db' or local SQLite file path)"},
            "query": {"type": "string", "description": "SQL query to execute"},
            "params": {"type": "array", "description": "Optional parameters for parameterized query (list of values)"},
            "limit": {"type": "integer", "description": "Max rows to return (default 50)", "default": 50},
        },
        "required": ["connection_uri", "query"],
    },
)
def query_database(connection_uri: str, query: str, params: list | None = None, limit: int = 50) -> str:
    try:
        conn, db_type = get_db_connection(connection_uri)
        cursor = conn.cursor()
        
        p_args = params or []
        cursor.execute(query, p_args)
        
        is_select = False
        description = cursor.description
        if description is not None:
            is_select = True
            
        if is_select:
            columns = [desc[0] for desc in description]
            rows = cursor.fetchmany(limit)
            conn.close()
            if not rows:
                return "Query executed successfully. 0 rows returned."
            
            lines = [f"Database Query Results ({len(rows)} rows shown):"]
            header = " | ".join(f"{c[:20]:20s}" for c in columns)
            lines.append(f"  {header}")
            lines.append(f"  {'-' * len(header)}")
            for row in rows:
                row_str = " | ".join(f"{str(v)[:20]:20s}" for v in row)
                lines.append(f"  {row_str}")
            return "\n".join(lines)
        else:
            conn.commit()
            rowcount = cursor.rowcount
            lastrowid = getattr(cursor, "lastrowid", None)
            conn.close()
            res = f"Query executed successfully. {rowcount} rows affected."
            if lastrowid is not None and lastrowid > 0:
                res += f" Last Inserted ID: {lastrowid}."
            return res
            
    except Exception as e:
        return f"error executing query: {e}"


@tool(
    name="database_schema_inspect",
    description="Inspect tables, columns, indexes, and relationships in a database.",
    parameters={
        "type": "object",
        "properties": {
            "connection_uri": {"type": "string", "description": "Database URI or local SQLite file path"},
        },
        "required": ["connection_uri"],
    },
)
def database_schema_inspect(connection_uri: str) -> str:
    try:
        conn, db_type = get_db_connection(connection_uri)
        cursor = conn.cursor()
        
        lines = [f"Schema Inspection for {connection_uri}:", ""]
        
        if db_type == "sqlite":
            cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            if not tables:
                return "No tables found in SQLite database."
                
            for tbl, ddl in tables:
                lines.append(f"Table: {tbl}")
                cursor.execute(f"PRAGMA table_info({tbl})")
                cols = cursor.fetchall()
                for c in cols:
                    pk_marker = " [PK]" if c[5] else ""
                    null_marker = " NOT NULL" if c[3] else ""
                    default_marker = f" DEFAULT {c[4]}" if c[4] is not None else ""
                    lines.append(f"  - {c[1]} ({c[2]}){pk_marker}{null_marker}{default_marker}")
                
                cursor.execute(f"PRAGMA index_list({tbl})")
                idxs = cursor.fetchall()
                for idx in idxs:
                    unique_marker = " UNIQUE" if idx[2] else ""
                    lines.append(f"  Index: {idx[1]}{unique_marker}")
                
                cursor.execute(f"PRAGMA foreign_key_list({tbl})")
                fks = cursor.fetchall()
                for fk in fks:
                    lines.append(f"  Relationship: {tbl}.{fk[3]} -> {fk[2]}.{fk[4]} (ON DELETE: {fk[6]})")
                
                lines.append("")
                
        elif db_type in ("postgres", "mysql"):
            table_schema_clause = "table_schema = 'public'" if db_type == "postgres" else "table_schema = database()"
            cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND {table_schema_clause}")
            tables = [r[0] for r in cursor.fetchall()]
            if not tables:
                return f"No tables found in {db_type} database."
                
            for tbl in tables:
                lines.append(f"Table: {tbl}")
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND {table_schema_clause}
                    ORDER BY ordinal_position
                """, (tbl,))
                cols = cursor.fetchall()
                for c in cols:
                    null_marker = " NOT NULL" if c[2] == "NO" else ""
                    default_marker = f" DEFAULT {c[3]}" if c[3] is not None else ""
                    lines.append(f"  - {c[0]} ({c[1]}){null_marker}{default_marker}")
                
                try:
                    cursor.execute(f"""
                        SELECT kcu.column_name, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name 
                        FROM information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                          AND ccu.table_schema = tc.table_schema
                        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s AND tc.table_schema = %s
                    """, (tbl, 'public' if db_type == 'postgres' else 'database()'))
                    fks = cursor.fetchall()
                    for fk in fks:
                        lines.append(f"  Relationship: {tbl}.{fk[0]} -> {fk[1]}.{fk[2]}")
                except Exception:
                    pass
                
                lines.append("")
                
        conn.close()
        return "\n".join(lines).strip()
    except Exception as e:
        return f"error inspecting database schema: {e}"


@tool(
    name="database_migrate",
    description="Run database schema migrations or rollbacks. Keeps track of migrations in 'lumi_migrations' table.",
    parameters={
        "type": "object",
        "properties": {
            "connection_uri": {"type": "string", "description": "Database URI or local SQLite file path"},
            "action": {
                "type": "string",
                "description": "Migration action: 'run' (apply new migration), 'rollback' (undo last migration), 'status' (list migrations)",
                "enum": ["run", "rollback", "status"],
                "default": "status",
            },
            "migration_name": {"type": "string", "description": "Identifier name for the migration (required for action='run')"},
            "up_sql": {"type": "string", "description": "SQL code to execute for migrating up (required for action='run')"},
            "down_sql": {"type": "string", "description": "SQL code to execute for rolling back (required for action='run' to enable rollbacks later)"},
        },
        "required": ["connection_uri"],
    },
)
def database_migrate(
    connection_uri: str,
    action: str = "status",
    migration_name: str | None = None,
    up_sql: str | None = None,
    down_sql: str | None = None,
) -> str:
    try:
        conn, db_type = get_db_connection(connection_uri)
        cursor = conn.cursor()
        
        if db_type == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lumi_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    up_sql TEXT,
                    down_sql TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lumi_migrations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) UNIQUE,
                    up_sql TEXT,
                    down_sql TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """ if db_type == "mysql" else """
                CREATE TABLE IF NOT EXISTS lumi_migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE,
                    up_sql TEXT,
                    down_sql TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()

        if action == "status":
            cursor.execute("SELECT id, name, applied_at FROM lumi_migrations ORDER BY id ASC")
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return "No migrations have been applied yet."
            lines = ["Applied Migrations:"]
            for r in rows:
                lines.append(f"  [{r[0]}] {r[1]} (Applied at: {r[2]})")
            return "\n".join(lines)

        elif action == "run":
            if not migration_name:
                return "error: 'migration_name' is required to run migration."
            if not up_sql:
                return "error: 'up_sql' is required to run migration."
            
            cursor.execute("SELECT id FROM lumi_migrations WHERE name = ?", (migration_name,) if db_type == "sqlite" else [migration_name])
            if cursor.fetchone():
                conn.close()
                return f"Migration '{migration_name}' has already been applied."

            try:
                if db_type == "sqlite":
                    cursor.executescript(up_sql)
                else:
                    for statement in up_sql.split(";"):
                        if statement.strip():
                            cursor.execute(statement)
                
                ins_sql = "INSERT INTO lumi_migrations (name, up_sql, down_sql) VALUES (?, ?, ?)"
                if db_type != "sqlite":
                    ins_sql = "INSERT INTO lumi_migrations (name, up_sql, down_sql) VALUES (%s, %s, %s)"
                
                cursor.execute(ins_sql, (migration_name, up_sql, down_sql or ""))
                conn.commit()
                conn.close()
                return f"Successfully applied migration '{migration_name}'."
            except Exception as migrate_err:
                conn.rollback()
                conn.close()
                return f"Migration failed and rolled back: {migrate_err}"

        elif action == "rollback":
            cursor.execute("SELECT id, name, down_sql FROM lumi_migrations ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                conn.close()
                return "No migrations found to rollback."
            
            mig_id, mig_name, mig_down_sql = row
            if not mig_down_sql or not mig_down_sql.strip():
                del_sql = "DELETE FROM lumi_migrations WHERE id = ?" if db_type == "sqlite" else "DELETE FROM lumi_migrations WHERE id = %s"
                cursor.execute(del_sql, (mig_id,) if db_type == "sqlite" else [mig_id])
                conn.commit()
                conn.close()
                return f"Migration '{mig_name}' rolled back (no down_sql executed, tracking entry removed)."

            try:
                if db_type == "sqlite":
                    cursor.executescript(mig_down_sql)
                else:
                    for statement in mig_down_sql.split(";"):
                        if statement.strip():
                            cursor.execute(statement)
                
                del_sql = "DELETE FROM lumi_migrations WHERE id = ?" if db_type == "sqlite" else "DELETE FROM lumi_migrations WHERE id = %s"
                cursor.execute(del_sql, (mig_id,) if db_type == "sqlite" else [mig_id])
                conn.commit()
                conn.close()
                return f"Successfully rolled back migration '{mig_name}'."
            except Exception as rollback_err:
                conn.rollback()
                conn.close()
                return f"Rollback failed: {rollback_err}"

    except Exception as e:
        return f"error managing migration: {e}"


@tool(
    name="backup_database",
    description="Create a compressed ZIP backup of a SQLite database. Can also schedule regular backups.",
    parameters={
        "type": "object",
        "properties": {
            "db_path": {"type": "string", "description": "Local path to the SQLite database file"},
            "backup_dir": {"type": "string", "description": "Directory to save backup files (default 'data/backups')"},
            "schedule_interval": {"type": "string", "description": "Optional schedule: 'daily HH:MM', 'weekly DAY HH:MM' (e.g. 'daily 03:00') to schedule regular backups via Windows Task Scheduler."},
        },
        "required": ["db_path"],
    },
)
def backup_database(db_path: str, backup_dir: str = "data/backups", schedule_interval: str | None = None) -> str:
    db_file = Path(db_path)
    if not db_file.is_file():
        return f"error: database file not found: {db_path}"

    backup_folder = Path(backup_dir)
    backup_folder.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{db_file.stem}_backup_{timestamp}.db"
    temp_backup_path = backup_folder / backup_filename
    zip_backup_path = backup_folder / f"{backup_filename}.zip"

    try:
        src = sqlite3.connect(str(db_file))
        dst = sqlite3.connect(str(temp_backup_path))
        src.backup(dst)
        src.close()
        dst.close()
        
        with zipfile.ZipFile(zip_backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(temp_backup_path, arcname=backup_filename)
        
        os.remove(temp_backup_path)
        
        result_msg = f"Successfully backed up '{db_path}' to '{zip_backup_path}' ({zip_backup_path.stat().st_size} bytes)."
    except Exception as e:
        if temp_backup_path.exists():
            os.remove(temp_backup_path)
        return f"error executing database backup: {e}"

    if schedule_interval:
        try:
            from tools.scheduler import create_scheduled_task
            task_name = f"Lumi_DB_Backup_{db_file.stem}"
            python_path = Path("venv/Scripts/python.exe").resolve()
            if not python_path.exists():
                python_path = Path("python").resolve()
                
            abs_db_path = db_file.resolve()
            abs_backup_dir = backup_folder.resolve()
            
            cmd_str = f'"{python_path}" -c "from tools.database import backup_database; backup_database(r\'{abs_db_path}\', r\'{abs_backup_dir}\')"'
            
            sched_res = create_scheduled_task(task_name, cmd_str, schedule_interval)
            result_msg += f"\nBackup Schedule: {sched_res}"
        except Exception as sched_err:
            result_msg += f"\nFailed to schedule backup task: {sched_err}"
            
    return result_msg


@tool(
    name="sync_databases",
    description="Synchronize tables and data from a source database to a destination database.",
    parameters={
        "type": "object",
        "properties": {
            "src_uri": {"type": "string", "description": "Source database connection URI or file path"},
            "dest_uri": {"type": "string", "description": "Destination database connection URI or file path"},
            "tables": {"type": "array", "items": {"type": "string"}, "description": "Optional list of tables to sync. If empty, syncs all tables."},
        },
        "required": ["src_uri", "dest_uri"],
    },
)
def sync_databases(src_uri: str, dest_uri: str, tables: list[str] | None = None) -> str:
    try:
        src_conn, src_type = get_db_connection(src_uri)
        dest_conn, dest_type = get_db_connection(dest_uri)
        
        src_cursor = src_conn.cursor()
        dest_cursor = dest_conn.cursor()
        
        target_tables = tables
        if not target_tables:
            if src_type == "sqlite":
                src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                target_tables = [r[0] for r in src_cursor.fetchall()]
            else:
                table_schema_clause = "table_schema = 'public'" if src_type == "postgres" else "table_schema = database()"
                src_cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND {table_schema_clause}")
                target_tables = [r[0] for r in src_cursor.fetchall()]

        if not target_tables:
            src_conn.close()
            dest_conn.close()
            return "No tables found in source database to sync."

        report = [f"Synchronized databases from {src_type} to {dest_type}:"]
        
        for table in target_tables:
            try:
                if src_type == "sqlite":
                    src_cursor.execute(f"PRAGMA table_info({table})")
                    columns_info = src_cursor.fetchall()
                    columns = [c[1] for c in columns_info]
                    types = [c[2] for c in columns_info]
                else:
                    table_schema_clause = "table_schema = 'public'" if src_type == "postgres" else "table_schema = database()"
                    src_cursor.execute(f"""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = %s AND {table_schema_clause}
                        ORDER BY ordinal_position
                    """, (table,))
                    columns_info = src_cursor.fetchall()
                    columns = [c[0] for c in columns_info]
                    types = [c[1] for c in columns_info]

                if not columns:
                    report.append(f"  - Table '{table}' has no columns, skipping.")
                    continue

                col_defs = []
                for name, col_type in zip(columns, types):
                    col_defs.append(f"{name} {col_type}")
                
                dest_cursor.execute(f"DROP TABLE IF EXISTS {table}")
                dest_cursor.execute(f"CREATE TABLE {table} ({', '.join(col_defs)})")
                
                src_cursor.execute(f"SELECT {', '.join(columns)} FROM {table}")
                
                row_count = 0
                placeholder = "?" if dest_type == "sqlite" else "%s"
                placeholders = ", ".join([placeholder] * len(columns))
                insert_query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                
                while True:
                    rows = src_cursor.fetchmany(500)
                    if not rows:
                        break
                    dest_cursor.executemany(insert_query, rows)
                    row_count += len(rows)

                dest_conn.commit()
                report.append(f"  - Synced '{table}': {row_count} rows copied.")
            except Exception as table_err:
                report.append(f"  - Failed syncing '{table}': {table_err}")
                dest_conn.rollback()

        src_conn.close()
        dest_conn.close()
        return "\n".join(report)
    except Exception as e:
        return f"error syncing databases: {e}"
