"""Zip archive tools — create, extract, list contents."""
from __future__ import annotations

import zipfile
from pathlib import Path

from tools import tool


@tool(
    name="zip_create",
    description="Create a zip archive from a file or folder.",
    parameters={
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": "File or folder to zip",
            },
            "output": {
                "type": "string",
                "description": "Output zip file path (default: source.zip)",
            },
        },
        "required": ["source"],
    },
)
def zip_create(source: str, output: str = "") -> str:
    p = Path(source)
    if not p.exists():
        return f"error: path not found: {source}"

    if not output:
        output = str(p.parent / f"{p.stem}.zip")

    try:
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
            if p.is_file():
                zf.write(p, p.name)
            else:
                for fp in p.rglob("*"):
                    if fp.is_file():
                        arcname = str(fp.relative_to(p.parent))
                        zf.write(fp, arcname)

        zip_size = Path(output).stat().st_size / 1024
        return f"Created: {output} ({zip_size:.0f} KB)"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="zip_list",
    description="List the contents of a zip file without extracting.",
    parameters={
        "type": "object",
        "properties": {
            "zip_path": {
                "type": "string",
                "description": "Path to the zip file",
            },
        },
        "required": ["zip_path"],
    },
)
def zip_list(zip_path: str) -> str:
    p = Path(zip_path)
    if not p.exists():
        return f"error: zip file not found: {zip_path}"

    try:
        with zipfile.ZipFile(p, "r") as zf:
            infos = zf.infolist()
            total_size = sum(i.file_size for i in infos)
            lines = [f"Zip Contents ({len(infos)} files, {total_size/1024/1024:.1f} MB uncompressed):"]
            for i in infos[:50]:
                size = i.file_size / 1024
                size_str = f"{size:.0f} KB" if size > 1 else f"{size*1024:.0f} B"
                lines.append(f"  {i.filename} ({size_str})")
            if len(infos) > 50:
                lines.append(f"  ...and {len(infos) - 50} more")
            return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="zip_extract",
    description="Extract files from a zip archive.",
    parameters={
        "type": "object",
        "properties": {
            "zip_path": {
                "type": "string",
                "description": "Path to the zip file",
            },
            "output_dir": {
                "type": "string",
                "description": "Directory to extract to (default: same directory as zip)",
            },
        },
        "required": ["zip_path"],
    },
)
def zip_extract(zip_path: str, output_dir: str = "") -> str:
    p = Path(zip_path)
    if not p.exists():
        return f"error: zip file not found: {zip_path}"

    dest = Path(output_dir) if output_dir else p.parent
    dest.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(p, "r") as zf:
            zf.extractall(dest)
            file_count = len(zf.namelist())
        return f"Extracted {file_count} file(s) to: {dest}"
    except Exception as e:
        return f"error: {e}"
