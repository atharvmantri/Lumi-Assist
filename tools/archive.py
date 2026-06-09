"""Zip / extract file operations."""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

from tools import tool


@tool(
    name="compress_folder",
    description=(
        "Compress a folder into a .zip file. Default output sits next to the source folder "
        "with the same name + .zip extension. Confirm before compressing large folders."
    ),
    parameters={
        "type": "object",
        "properties": {
            "source_path": {"type": "string", "description": "Folder to compress"},
            "output_path": {"type": "string", "description": "Optional output .zip path; defaults to source_path + .zip"},
        },
        "required": ["source_path"],
    },
)
def compress_folder(source_path: str, output_path: str | None = None) -> str:
    src = Path(os.path.expandvars(os.path.expanduser(source_path))).resolve()
    if not src.is_dir():
        return f"error: {src} is not a directory"
    out = Path(os.path.expandvars(os.path.expanduser(output_path))).resolve() if output_path else src.with_suffix(".zip")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            count = 0
            for root, _, files in os.walk(src):
                for f in files:
                    p = Path(root) / f
                    zf.write(p, p.relative_to(src.parent))
                    count += 1
        return f"compressed {count} files from {src} into {out} ({out.stat().st_size} bytes)"
    except Exception as e:  # noqa: BLE001
        return f"error compressing: {e}"


@tool(
    name="extract_zip",
    description=(
        "Extract a .zip file. Default destination is a sibling folder with the same name. "
        "Will refuse to overwrite without confirm: pass overwrite=True to allow."
    ),
    parameters={
        "type": "object",
        "properties": {
            "zip_path": {"type": "string", "description": "Path to the .zip file"},
            "dest_path": {"type": "string", "description": "Optional extraction destination"},
            "overwrite": {"type": "boolean", "description": "Overwrite files in dest if they exist (default false)"},
        },
        "required": ["zip_path"],
    },
)
def extract_zip(zip_path: str, dest_path: str | None = None, overwrite: bool = False) -> str:
    zpath = Path(os.path.expandvars(os.path.expanduser(zip_path))).resolve()
    if not zpath.is_file() or not zipfile.is_zipfile(zpath):
        return f"error: {zpath} is not a valid .zip file"
    dest = Path(os.path.expandvars(os.path.expanduser(dest_path))).resolve() if dest_path else zpath.with_suffix("")
    try:
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath, "r") as zf:
            existing = [n for n in zf.namelist() if (dest / n).exists()]
            if existing and not overwrite:
                return (
                    f"refused: {len(existing)} files already exist in {dest}. "
                    "Pass overwrite=True to allow extraction over them."
                )
            zf.extractall(dest)
        return f"extracted {zpath} to {dest}"
    except Exception as e:  # noqa: BLE001
        return f"error extracting: {e}"
