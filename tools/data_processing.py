"""Spreadsheet, formatting, and mock data processing tools."""
from __future__ import annotations

import csv
import io
import json
import os
import random
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from tools import tool


@tool(
    name="parse_csv_excel",
    description="Read, filter, and extract columns from a CSV or Excel spreadsheet file.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the CSV or Excel file"},
            "sheet_name": {"type": "string", "description": "Excel sheet name to read (optional, defaults to first sheet)"},
            "filters": {"type": "object", "description": "Optional dictionary of column-value filter mappings (e.g. {'Status': 'Active'})"},
            "columns": {"type": "array", "items": {"type": "string"}, "description": "Optional list of columns to extract"},
            "limit": {"type": "integer", "description": "Max rows to return (default 50)", "default": 50},
        },
        "required": ["file_path"],
    },
)
def parse_csv_excel(
    file_path: str,
    sheet_name: str | None = None,
    filters: dict | None = None,
    columns: list[str] | None = None,
    limit: int = 50,
) -> str:
    path = Path(file_path)
    if not path.is_file():
        return f"error: file not found: {file_path}"

    ext = path.suffix.lower()
    rows = []

    if ext == ".csv":
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            return f"error reading CSV: {e}"
    elif ext in (".xlsx", ".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(path), data_only=True)
            sheet = wb[sheet_name] if sheet_name else wb.active
            
            # Extract headers
            headers = [cell.value for cell in sheet[1]]
            headers = [str(h).strip() for h in headers if h is not None]
            
            for row_cells in sheet.iter_rows(min_row=2, values_only=True):
                # Map columns to values
                row_dict = {}
                for idx, val in enumerate(row_cells):
                    if idx < len(headers):
                        row_dict[headers[idx]] = "" if val is None else str(val).strip()
                if any(row_dict.values()): # skip empty rows
                    rows.append(row_dict)
        except ImportError:
            return "error: openpyxl is required to parse Excel files. Please run `pip install openpyxl`."
        except Exception as e:
            return f"error reading Excel: {e}"
    else:
        return f"error: unsupported file extension '{ext}'. Only CSV and Excel (.xlsx, .xls) are supported."

    if not rows:
        return "Spreadsheet contains 0 rows."

    # 1. Apply filters
    filtered_rows = []
    if filters:
        for r in rows:
            match = True
            for f_col, f_val in filters.items():
                r_val = r.get(f_col)
                if r_val is None or str(r_val).lower() != str(f_val).lower():
                    match = False
                    break
            if match:
                filtered_rows.append(r)
    else:
        filtered_rows = rows

    if not filtered_rows:
        return "Query executed successfully, but 0 rows matched the filters."

    # 2. Select target columns
    selected_cols = columns if columns else list(filtered_rows[0].keys())
    output_rows = []
    for r in filtered_rows[:limit]:
        new_row = {col: r.get(col, "") for col in selected_cols}
        output_rows.append(new_row)

    # 3. Format output
    lines = [f"Parsed spreadsheet ({len(filtered_rows)} rows matched, showing up to {limit}):"]
    header_str = " | ".join(f"{c[:15]:15s}" for c in selected_cols)
    lines.append(f"  {header_str}")
    lines.append(f"  {'-' * len(header_str)}")
    
    for r in output_rows:
        row_str = " | ".join(f"{str(r[c])[:15]:15s}" for c in selected_cols)
        lines.append(f"  {row_str}")

    if len(filtered_rows) > limit:
        lines.append(f"\n  ... and {len(filtered_rows) - limit} more matching rows.")

    return "\n".join(lines)


@tool(
    name="convert_data_format",
    description="Convert data files between JSON, XML, YAML, CSV, and Parquet formats.",
    parameters={
        "type": "object",
        "properties": {
            "source_path": {"type": "string", "description": "Path to the source file"},
            "dest_path": {"type": "string", "description": "Path to the destination file to create"},
            "source_format": {"type": "string", "description": "Source format (optional, detected from extension)", "enum": ["json", "csv", "xml", "yaml", "parquet"]},
            "dest_format": {"type": "string", "description": "Destination format (optional, detected from extension)", "enum": ["json", "csv", "xml", "yaml", "parquet"]},
        },
        "required": ["source_path", "dest_path"],
    },
)
def convert_data_format(
    source_path: str,
    dest_path: str,
    source_format: str | None = None,
    dest_format: str | None = None,
) -> str:
    src = Path(source_path)
    dst = Path(dest_path)
    if not src.is_file():
        return f"error: source file not found: {source_path}"

    src_fmt = source_format or src.suffix.lstrip(".").lower()
    dst_fmt = dest_format or dst.suffix.lstrip(".").lower()

    supported = ("json", "csv", "xml", "yaml", "yml", "parquet")
    if src_fmt not in supported or dst_fmt not in supported:
        return f"error: unsupported formats. Supported formats: {supported}"

    # Handle alias
    if src_fmt == "yml":
        src_fmt = "yaml"
    if dst_fmt == "yml":
        dst_fmt = "yaml"

    # 1. Read source data into intermediate python structures (list of dicts, or dict)
    data = None
    try:
        if src_fmt == "json":
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif src_fmt == "csv":
            with open(src, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                data = list(reader)
        elif src_fmt == "yaml":
            try:
                import yaml
                with open(src, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except ImportError:
                return "error: PyYAML is required to parse YAML files."
        elif src_fmt == "xml":
            tree = ET.parse(src)
            root = tree.getroot()
            # Simple XML to List of Dicts parsing
            # Assumes format: <root><row><col1>val1</col1>...</row>...</root>
            # Or nested child tags
            rows = []
            for child in root:
                row = {}
                for grandchild in child:
                    row[grandchild.tag] = grandchild.text or ""
                if row:
                    rows.append(row)
            data = rows if rows else {"tag": root.tag, "text": root.text or ""}
        elif src_fmt == "parquet":
            try:
                import pandas as pd
                df = pd.read_parquet(str(src))
                data = df.to_dict(orient="records")
            except ImportError:
                return "error: pandas and pyarrow/fastparquet are required to read Parquet files."
    except Exception as read_err:
        return f"error reading or parsing source file: {read_err}"

    if data is None:
        return "error: no data extracted from source file."

    # 2. Write data to destination format
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst_fmt == "json":
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif dst_fmt == "yaml":
            try:
                import yaml
                with open(dst, "w", encoding="utf-8") as f:
                    yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
            except ImportError:
                return "error: PyYAML is required to write YAML files."
        elif dst_fmt == "csv":
            # Data must be list of dicts to write to CSV
            rows_list = data
            if isinstance(data, dict):
                rows_list = [data]
            if not isinstance(rows_list, list) or not rows_list:
                return "error: JSON/YAML structure must be a list of objects to export to CSV."
            
            # Extract headers from keys of all items
            headers = set()
            for item in rows_list:
                if isinstance(item, dict):
                    headers.update(item.keys())
            headers = sorted(list(headers))

            with open(dst, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for item in rows_list:
                    if isinstance(item, dict):
                        # Ensure all keys exist
                        row_data = {h: item.get(h, "") for h in headers}
                        writer.writerow(row_data)
        elif dst_fmt == "xml":
            # List of dicts -> <root><row><col>val</col></row></root>
            root_el = ET.Element("root")
            if isinstance(data, list):
                for row in data:
                    row_el = ET.SubElement(root_el, "row")
                    if isinstance(row, dict):
                        for k, v in row.items():
                            col_el = ET.SubElement(row_el, str(k))
                            col_el.text = str(v)
            elif isinstance(data, dict):
                for k, v in data.items():
                    col_el = ET.SubElement(root_el, str(k))
                    col_el.text = str(v)
            
            tree = ET.ElementTree(root_el)
            # Pretty-printed XML output
            # Standard xml.etree.ElementTree indentation
            ET.indent(tree, space="  ", level=0)
            tree.write(dst, encoding="utf-8", xml_declaration=True)
        elif dst_fmt == "parquet":
            try:
                import pandas as pd
                df = pd.DataFrame(data)
                df.to_parquet(str(dst), index=False)
            except ImportError:
                return "error: pandas and pyarrow/fastparquet are required to write Parquet files."
                
        return f"Successfully converted format and saved to '{dest_path}'."
    except Exception as write_err:
        return f"error converting and writing destination file: {write_err}"


@tool(
    name="data_cleanse",
    description="Cleanse data files by removing duplicates, trimming spaces, and standardizing address/phone formats.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the input CSV or JSON data file"},
            "output_path": {"type": "string", "description": "Path to save cleaned data (optional, overwrites input if not specified)"},
            "operations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["duplicates", "whitespace", "standardize_phone", "standardize_address", "null_to_empty"],
                },
                "description": "Cleanse operations to perform (default: all)",
            },
        },
        "required": ["file_path"],
    },
)
def data_cleanse(
    file_path: str,
    output_path: str | None = None,
    operations: list[str] | None = None,
) -> str:
    path = Path(file_path)
    if not path.is_file():
        return f"error: file not found: {file_path}"

    ext = path.suffix.lower()
    if ext not in (".csv", ".json"):
        return f"error: unsupported file format '{ext}'. Only CSV and JSON are supported."

    # Load data
    rows = []
    try:
        if ext == ".csv":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        else: # JSON
            with open(path, "r", encoding="utf-8") as f:
                rows = json.load(f)
                if not isinstance(rows, list):
                    return "error: JSON file must contain a list of objects."
    except Exception as e:
        return f"error loading file: {e}"

    if not rows:
        return "File contains no records to cleanse."

    target_ops = operations or ["duplicates", "whitespace", "standardize_phone", "standardize_address", "null_to_empty"]
    
    dup_removed = 0
    records_modified = 0

    # 1. Remove duplicates
    if "duplicates" in target_ops:
        seen = []
        unique_rows = []
        for r in rows:
            # Hash dict by sorted tuple of items
            serialized = json.dumps(r, sort_keys=True)
            if serialized not in seen:
                seen.append(serialized)
                unique_rows.append(r)
            else:
                dup_removed += 1
        rows = unique_rows

    # Standardize helpers
    address_subs = {
        r"\bStreet\b": "St.", r"\bAvenue\b": "Ave.", r"\bRoad\b": "Rd.", 
        r"\bBoulevard\b": "Blvd.", r"\bDrive\b": "Dr.", r"\bCourt\b": "Ct.", 
        r"\bLane\b": "Ln.", r"\bParkway\b": "Pkwy.", r"\bSquare\b": "Sq."
    }

    def clean_phone(phone_str: str) -> str:
        digits = re.sub(r"\D", "", phone_str)
        if len(digits) == 10:
            return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
        elif len(digits) == 11 and digits.startswith("1"):
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
        elif len(digits) > 10:
            return f"+{digits}"
        return phone_str # return as-is if unrecognized

    def clean_address(addr_str: str) -> str:
        cleaned = addr_str.strip()
        for pattern, replacement in address_subs.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        # title case for words
        words = cleaned.split()
        title_words = [w.capitalize() if not w.endswith(".") else w for w in words]
        return " ".join(title_words)

    # 2. Cell operations
    for r in rows:
        modified_row = False
        for key, val in r.items():
            if val is None:
                if "null_to_empty" in target_ops:
                    r[key] = ""
                    modified_row = True
                continue

            val_str = str(val)
            cleaned_val = val_str

            if "whitespace" in target_ops:
                cleaned_val = cleaned_val.strip()

            if "standardize_phone" in target_ops and ("phone" in key.lower() or "mobile" in key.lower() or "tel" in key.lower()):
                cleaned_val = clean_phone(cleaned_val)

            if "standardize_address" in target_ops and ("address" in key.lower() or "street" in key.lower() or "location" in key.lower()):
                cleaned_val = clean_address(cleaned_val)

            if cleaned_val != val_str:
                r[key] = cleaned_val
                modified_row = True
        
        if modified_row:
            records_modified += 1

    # Save cleaned data
    dest = Path(output_path) if output_path else path
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if ext == ".csv":
            # Get headers from keys of all items
            headers = set()
            for r in rows:
                headers.update(r.keys())
            headers = sorted(list(headers))

            with open(dest, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for r in rows:
                    row_data = {h: r.get(h, "") for h in headers}
                    writer.writerow(row_data)
        else: # JSON
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"error saving cleaned file: {e}"

    return (
        f"Data Cleansing Completed for '{file_path}':\n"
        f"  - Total records remaining: {len(rows)}\n"
        f"  - Duplicates removed: {dup_removed}\n"
        f"  - Records standardized/modified: {records_modified}\n"
        f"  - Saved results to: '{dest}'"
    )


@tool(
    name="generate_mock_data",
    description="Generate realistic mock datasets for testing and validation based on a schema description.",
    parameters={
        "type": "object",
        "properties": {
            "schema": {
                "type": "object",
                "description": "Mock schema dict mapping column name to generator type (e.g. {'id': 'id', 'name': 'name', 'email': 'email', 'phone': 'phone', 'age': 'integer'}). Valid types: id, name, email, phone, date, integer, float, boolean, address, text.",
            },
            "num_rows": {"type": "integer", "description": "Number of rows to generate (default 100)", "default": 100},
            "output_path": {"type": "string", "description": "Optional file path to save the mock dataset"},
            "output_format": {"type": "string", "description": "Output format: 'json' or 'csv' (default 'json')", "enum": ["json", "csv"], "default": "json"},
        },
        "required": ["schema"],
    },
)
def generate_mock_data(
    schema: dict,
    num_rows: int = 100,
    output_path: str | None = None,
    output_format: str = "json",
) -> str:
    num_rows = max(1, min(num_rows, 5000))
    
    first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry", "Sarah", "James", "Emily", "Michael", "Olivia"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]
    domains = ["example.com", "test.org", "company.net", "mail.edu", "cloud.io"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
    streets = ["Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Broadway", "Second St", "Cedar Ave", "Elm St", "View Rd", "Park Ln"]

    rows = []
    for idx in range(1, num_rows + 1):
        row = {}
        for col_name, gen_type in schema.items():
            g_type = str(gen_type).lower()
            
            if g_type == "id":
                row[col_name] = idx
            elif g_type == "name":
                fn = random.choice(first_names)
                ln = random.choice(last_names)
                row[col_name] = f"{fn} {ln}"
            elif g_type == "email":
                # Check if name already generated to make email match
                name_val = None
                for k, v in row.items():
                    if schema.get(k) == "name":
                        name_val = v
                        break
                if name_val:
                    clean_name = re.sub(r"\s+", ".", str(name_val).lower())
                    row[col_name] = f"{clean_name}@{random.choice(domains)}"
                else:
                    fn = random.choice(first_names).lower()
                    ln = random.choice(last_names).lower()
                    row[col_name] = f"{fn}.{ln}{random.randint(10, 99)}@{random.choice(domains)}"
            elif g_type == "phone":
                row[col_name] = f"({random.randint(200, 999)}) 555-{random.randint(1000, 9999)}"
            elif g_type == "address":
                row[col_name] = f"{random.randint(100, 9999)} {random.choice(streets)}, {random.choice(cities)}"
            elif g_type == "date":
                # Random date within last 3 years
                days_ago = random.randint(0, 1095)
                dt = datetime.now() - timedelta(days=days_ago)
                row[col_name] = dt.strftime("%Y-%m-%d")
            elif g_type == "integer":
                row[col_name] = random.randint(1, 100)
            elif g_type == "float":
                row[col_name] = round(random.uniform(1.0, 1000.0), 2)
            elif g_type == "boolean":
                row[col_name] = random.choice([True, False])
            elif g_type == "text":
                words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "sed", "do", "eiusmod", "tempor", "incididunt"]
                row[col_name] = " ".join(random.choices(words, k=5)).capitalize() + "."
            else:
                row[col_name] = f"mock_{random.randint(1000, 9999)}"
        rows.append(row)

    # Output formatting
    if output_path:
        out = Path(output_path)
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            if output_format == "csv" or out.suffix.lower() == ".csv":
                headers = list(schema.keys())
                with open(out, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(rows)
            else:
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(rows, f, indent=2, ensure_ascii=False)
            return f"Generated {num_rows} mock records and saved to '{output_path}'."
        except Exception as e:
            return f"error saving mock dataset: {e}"

    if output_format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(schema.keys()))
        writer.writeheader()
        writer.writerows(rows[:10]) # return top 10 as preview
        preview = output.getvalue()
    else:
        preview = json.dumps(rows[:5], indent=2, ensure_ascii=False)
        
    return (
        f"Generated {num_rows} mock records.\n"
        f"Preview (first few rows):\n{preview}"
    )


@tool(
    name="run_sql_on_files",
    description="Execute SQL queries directly on CSV or JSON files. Queries map tables to file paths.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "SQL query to execute (e.g. 'SELECT * FROM users JOIN orders ON users.id = orders.user_id')"},
            "file_mappings": {
                "type": "object",
                "description": "Mapping from table names used in query to their local file paths (e.g. {'users': 'data/users.csv', 'orders': 'data/orders.json'})",
            },
            "limit": {"type": "integer", "description": "Max rows to return (default 50)", "default": 50},
        },
        "required": ["query", "file_mappings"],
    },
)
def run_sql_on_files(query: str, file_mappings: dict, limit: int = 50) -> str:
    # Check if duckdb is installed
    try:
        import duckdb
        # DuckDB can query files directly
        # Let's register tables
        con = duckdb.connect(database=":memory:")
        for table_name, file_path in file_mappings.items():
            path = Path(file_path)
            if not path.is_file():
                return f"error: table file not found: {file_path}"
            
            ext = path.suffix.lower()
            if ext == ".csv":
                con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{path}')")
            elif ext == ".json":
                # DuckDB read_json
                con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_json_auto('{path}')")
            else:
                return f"error: unsupported format '{ext}' in DuckDB query."
        
        result = con.execute(query)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchmany(limit)
        con.close()
        
        if not rows:
            return "SQL query executed. 0 rows returned."
            
        lines = [f"SQL on Files (DuckDB) Query Results ({len(rows)} rows):"]
        header = " | ".join(f"{c[:15]:15s}" for c in columns)
        lines.append(f"  {header}")
        lines.append(f"  {'-' * len(header)}")
        for r in rows:
            row_str = " | ".join(f"{str(v)[:15]:15s}" for v in r)
            lines.append(f"  {row_str}")
        return "\n".join(lines)
        
    except ImportError:
        # DuckDB not installed - Fallback to SQLite in-memory
        # Parse CSV/JSON and load into sqlite memory DB, then query
        db = sqlite3.connect(":memory:")
        cursor = db.cursor()
        
        for table_name, file_path in file_mappings.items():
            path = Path(file_path)
            if not path.is_file():
                return f"error: table file not found: {file_path}"
                
            ext = path.suffix.lower()
            rows_data = []
            
            try:
                if ext == ".csv":
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        reader = csv.DictReader(f)
                        rows_data = list(reader)
                elif ext == ".json":
                    with open(path, "r", encoding="utf-8") as f:
                        rows_data = json.load(f)
                else:
                    return f"error: unsupported file extension '{ext}' in SQLite fallback query."
            except Exception as e:
                return f"error loading file '{file_path}': {e}"
                
            if not rows_data:
                # Create empty table
                cursor.execute(f"CREATE TABLE {table_name} (empty_column TEXT)")
                continue

            # Extract columns
            headers = list(rows_data[0].keys())
            
            # Clean headers for SQL compatibility (remove spaces, symbols)
            clean_headers = [re.sub(r"\W", "_", h) for h in headers]
            
            # Create Table DDL
            col_defs = [f"{h} TEXT" for h in clean_headers]
            cursor.execute(f"CREATE TABLE {table_name} ({', '.join(col_defs)})")
            
            # Insert values
            placeholders = ", ".join(["?"] * len(clean_headers))
            ins_sql = f"INSERT INTO {table_name} ({', '.join(clean_headers)}) VALUES ({placeholders})"
            
            values_to_insert = []
            for row in rows_data:
                row_val = []
                for h in headers:
                    row_val.append("" if row.get(h) is None else str(row.get(h)))
                values_to_insert.append(row_val)
                
            cursor.executemany(ins_sql, values_to_insert)
            db.commit()

        # Execute query
        try:
            cursor.execute(query)
            description = cursor.description
            if description is None:
                db.commit()
                rowcount = cursor.rowcount
                db.close()
                return f"Query executed successfully (modifying query). {rowcount} rows affected."
                
            columns = [desc[0] for desc in description]
            rows = cursor.fetchmany(limit)
            db.close()
            
            if not rows:
                return "Query executed successfully. 0 rows returned."
                
            lines = [f"SQL on Files (SQLite Fallback) Query Results ({len(rows)} rows):"]
            header = " | ".join(f"{c[:15]:15s}" for c in columns)
            lines.append(f"  {header}")
            lines.append(f"  {'-' * len(header)}")
            for r in rows:
                row_str = " | ".join(f"{str(v)[:15]:15s}" for v in r)
                lines.append(f"  {row_str}")
            return "\n".join(lines)
        except Exception as sql_err:
            db.close()
            return f"SQL Syntax/Execution error: {sql_err}"
    except Exception as e:
        return f"error executing run_sql_on_files: {e}"
