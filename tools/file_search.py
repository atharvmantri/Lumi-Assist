"""File search — fast file finder for Windows."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from tools import tool


@tool(
    name="search_files",
    description=(
        "Search for files on the PC by name or extension. "
        "Use when the user says 'find my...', 'where is...', 'search for files named...', "
        "'find all PDFs', etc. Returns matching file paths."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "File name, pattern, or extension to search for (e.g. 'report.pdf', '*.docx')",
            },
            "directory": {
                "type": "string",
                "description": "Directory to search in (default: user's home folder)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default 20)",
            },
        },
        "required": ["query"],
    },
)
def search_files(query: str, directory: str = "", max_results: int = 20) -> str:
    max_results = max(1, min(max_results, 100))
    search_dir = directory or str(Path.home())

    if not os.path.isdir(search_dir):
        return f"error: directory not found: {search_dir}"

    start_time = time.perf_counter()
    results = []

    try:
        # Use PowerShell Get-ChildItem for faster recursive search
        ps_query = query.replace("'", "''")
        ps_cmd = f"""
        Get-ChildItem -Path '{search_dir}' -Recurse -Filter '{ps_query}' -File -ErrorAction SilentlyContinue |
        Select-Object -First {max_results} -ExpandProperty FullName
        """
        result = subprocess.run(
            ["powershell", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        results = lines[:max_results]
    except subprocess.TimeoutExpired:
        return f"error: file search timed out after 30s (try a narrower directory)"
    except Exception as e:
        # Fallback: Python os.walk
        try:
            query_lower = query.lower()
            for root, dirs, files in os.walk(search_dir):
                # Skip hidden/system dirs
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    if query_lower in f.lower():
                        results.append(os.path.join(root, f))
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break
        except Exception as e2:
            return f"error searching files: {e2}"

    elapsed = time.perf_counter() - start_time

    if not results:
        return f"No files matching '{query}' found in {search_dir} ({elapsed:.1f}s)"

    lines = [f"Found {len(results)} file(s) matching '{query}' ({elapsed:.1f}s):"]
    for r in results[:max_results]:
        lines.append(f"  {r}")
    if len(results) > max_results:
        lines.append(f"  ...and {len(results) - max_results} more")

    return "\n".join(lines)
