import sys
import os
import json
import sqlite3
import csv
from pathlib import Path

# Configure UTF-8 encoding for stdout on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.database import query_database, database_schema_inspect, database_migrate, backup_database, sync_databases
from tools.data_processing import parse_csv_excel, convert_data_format, data_cleanse, generate_mock_data, run_sql_on_files

def test_database_operations():
    print("Testing Database Operations...")
    db1_path = "data/test_db1.db"
    db2_path = "data/test_db2.db"
    
    # Remove previous test databases
    for db_p in (db1_path, db2_path):
        p = Path(db_p)
        if p.exists():
            try:
                os.remove(p)
            except Exception:
                pass
                
    # 1. query_database (CREATE and INSERT)
    print("  Testing query_database (write)...")
    create_res = query_database(db1_path, "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT)")
    print(f"    Create table: {create_res}")
    insert_res = query_database(db1_path, "INSERT INTO users (name, email, phone) VALUES (?, ?, ?)", ["Alice", "alice@example.com", "1234567890"])
    print(f"    Insert row: {insert_res}")
    
    # 2. query_database (SELECT)
    print("  Testing query_database (read)...")
    select_res = query_database(db1_path, "SELECT * FROM users")
    print(f"    Select: {select_res}")
    
    # 3. database_schema_inspect
    print("  Testing database_schema_inspect...")
    schema_res = database_schema_inspect(db1_path)
    print(f"    Schema:\n{schema_res}")
    
    # 4. database_migrate
    print("  Testing database_migrate (run)...")
    mig_res = database_migrate(
        db1_path, 
        action="run", 
        migration_name="add_posts", 
        up_sql="CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, body TEXT);",
        down_sql="DROP TABLE posts;"
    )
    print(f"    Migrate up: {mig_res}")
    
    print("  Testing database_migrate (status)...")
    status_res = database_migrate(db1_path, action="status")
    print(f"    Migrate status:\n{status_res}")
    
    print("  Testing database_migrate (rollback)...")
    rollback_res = database_migrate(db1_path, action="rollback")
    print(f"    Migrate rollback: {rollback_res}")
    
    # 5. backup_database
    print("  Testing backup_database...")
    backup_res = backup_database(db1_path, backup_dir="data/backups")
    print(f"    Backup: {backup_res}")
    
    # 6. sync_databases
    print("  Testing sync_databases...")
    # Add a post table back to sync it
    query_database(db1_path, "CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT)")
    query_database(db1_path, "INSERT INTO posts (title) VALUES (?)", ["My Post"])
    
    sync_res = sync_databases(db1_path, db2_path)
    print(f"    Sync databases: {sync_res}")
    
    sync_check = query_database(db2_path, "SELECT * FROM posts")
    print(f"    Sync verify: {sync_check}")


def test_data_processing():
    print("\n" + "="*50 + "\n")
    print("Testing Data Processing...")
    
    csv_path = "data/mock_test.csv"
    json_path = "data/mock_test.json"
    xml_path = "data/mock_test.xml"
    yaml_path = "data/mock_test.yaml"
    
    # Cleanup previous mock files
    for p in (csv_path, json_path, xml_path, yaml_path):
        path_p = Path(p)
        if path_p.exists():
            try:
                os.remove(path_p)
            except Exception:
                pass

    # 1. generate_mock_data
    print("  Testing generate_mock_data...")
    schema = {
        "id": "id",
        "name": "name",
        "email": "email",
        "phone": "phone",
        "address": "address",
        "created_at": "date"
    }
    mock_res = generate_mock_data(schema, num_rows=10, output_path=csv_path, output_format="csv")
    print(f"    CSV Gen: {mock_res}")
    mock_res_json = generate_mock_data(schema, num_rows=5, output_path=json_path, output_format="json")
    print(f"    JSON Gen: {mock_res_json}")

    # 2. parse_csv_excel
    print("  Testing parse_csv_excel...")
    parse_res = parse_csv_excel(csv_path, columns=["id", "name", "email"], limit=3)
    print(f"    Parsed: {parse_res}")

    # 3. convert_data_format
    print("  Testing convert_data_format (JSON to YAML)...")
    conv_yaml = convert_data_format(json_path, yaml_path)
    print(f"    JSON to YAML: {conv_yaml}")
    
    print("  Testing convert_data_format (CSV to XML)...")
    conv_xml = convert_data_format(csv_path, xml_path)
    print(f"    CSV to XML: {conv_xml}")
    
    # 4. data_cleanse
    print("  Testing data_cleanse...")
    # Create a dirty CSV to clean
    dirty_csv = "data/dirty_test.csv"
    cleaned_csv = "data/cleaned_test.csv"
    with open(dirty_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Phone", "Address"])
        writer.writerow([" Alice Smith ", " 1234567890 ", " 123 Main Street "])
        writer.writerow([" Bob Jones ", " (555) 019-2834 ", " 456 Oak Avenue "])
        writer.writerow([" Alice Smith ", " 1234567890 ", " 123 Main Street "]) # duplicate
        
    clean_res = data_cleanse(dirty_csv, output_path=cleaned_csv)
    print(f"    Cleanse: {clean_res}")
    
    with open(cleaned_csv, "r", encoding="utf-8") as f:
        print(f"    Cleaned CSV contents:\n{f.read().strip()}")

    # 5. run_sql_on_files
    print("  Testing run_sql_on_files...")
    sql_query = "SELECT Name, Phone FROM people WHERE Name LIKE '%Alice%'"
    sql_res = run_sql_on_files(sql_query, file_mappings={"people": cleaned_csv})
    print(f"    SQL on Files result:\n{sql_res}")


if __name__ == "__main__":
    test_database_operations()
    test_data_processing()
