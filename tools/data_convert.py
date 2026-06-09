"""JSON and data format conversion tools."""
from __future__ import annotations

import json
import csv
import io

from tools import tool


@tool(
    name="json_format",
    description="Format, validate, or minify JSON text.",
    parameters={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "JSON text to format or validate",
            },
            "operation": {
                "type": "string",
                "description": "Operation: 'format' (pretty print), 'minify', 'validate' (default 'format')",
                "enum": ["format", "minify", "validate"],
            },
        },
        "required": ["text"],
    },
)
def json_format(text: str, operation: str = "format") -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return f"error: invalid JSON: {e}"

    if operation == "format":
        return json.dumps(data, indent=2, ensure_ascii=False)
    elif operation == "minify":
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    elif operation == "validate":
        keys = list(data.keys()) if isinstance(data, dict) else f"array with {len(data)} items"
        return f"Valid JSON. Type: {'object' if isinstance(data, dict) else 'array'}, {keys if isinstance(data, dict) else ''}"
    return f"error: unknown operation '{operation}'"


@tool(
    name="csv_to_json",
    description="Convert CSV text to JSON format.",
    parameters={
        "type": "object",
        "properties": {
            "csv_text": {
                "type": "string",
                "description": "CSV text to convert",
            },
            "delimiter": {
                "type": "string",
                "description": "CSV delimiter (default comma)",
            },
        },
        "required": ["csv_text"],
    },
)
def csv_to_json(csv_text: str, delimiter: str = ",") -> str:
    try:
        reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
        rows = list(reader)
        return json.dumps(rows, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"error converting CSV to JSON: {e}"


@tool(
    name="json_to_csv",
    description="Convert a JSON array of objects to CSV format.",
    parameters={
        "type": "object",
        "properties": {
            "json_text": {
                "type": "string",
                "description": "JSON array text to convert",
            },
        },
        "required": ["json_text"],
    },
)
def json_to_csv(json_text: str) -> str:
    try:
        data = json.loads(json_text)
        if not isinstance(data, list):
            return "error: JSON must be an array of objects"
        if not data:
            return "error: empty JSON array"

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    except Exception as e:
        return f"error converting JSON to CSV: {e}"


@tool(
    name="yaml_to_json",
    description="Convert YAML text to JSON format.",
    parameters={
        "type": "object",
        "properties": {
            "yaml_text": {
                "type": "string",
                "description": "YAML text to convert",
            },
        },
        "required": ["yaml_text"],
    },
)
def yaml_to_json(yaml_text: str) -> str:
    try:
        import yaml
        data = yaml.safe_load(yaml_text)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except ImportError:
        return "error: PyYAML not installed"
    except Exception as e:
        return f"error converting YAML to JSON: {e}"
