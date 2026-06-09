"""File metadata tools — creation date, modification date, owner, etc."""
from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

from tools import tool


@tool(
    name="file_metadata",
    description="Get detailed file metadata: size, created, modified, accessed, extension info.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file or folder",
            },
        },
        "required": ["path"],
    },
)
def file_metadata(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"error: path not found: {path}"

    stat = p.stat()
    is_dir = p.is_dir()
    kind = "Directory" if is_dir else "File"

    def ts(epoch):
        return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")

    lines = [f"{kind} Metadata: {p.name}"]
    lines.append(f"  Full path: {p}")
    lines.append(f"  Extension: {p.suffix or '(none)'}")

    if is_dir:
        count = sum(1 for _ in p.iterdir())
        lines.append(f"  Items: {count}")
    else:
        size = stat.st_size
        if size > 1024**3:
            lines.append(f"  Size: {size/1024**3:.1f} GB")
        elif size > 1024**2:
            lines.append(f"  Size: {size/1024**2:.1f} MB")
        elif size > 1024:
            lines.append(f"  Size: {size/1024:.0f} KB")
        else:
            lines.append(f"  Size: {size} bytes")

    lines.append(f"  Created: {ts(stat.st_ctime)}")
    lines.append(f"  Modified: {ts(stat.st_mtime)}")
    lines.append(f"  Accessed: {ts(stat.st_atime)}")

    # Owner
    try:
        import win32security
        import ntsecuritycon as con
        sd = win32security.GetFileSecurity(str(p), con.OWNER_SECURITY_INFORMATION)
        owner = sd.GetSecurityDescriptorOwner()
        name, domain, _ = win32security.LookupAccountSid(None, owner)
        lines.append(f"  Owner: {domain}\\{name}")
    except:
        pass

    return "\n".join(lines)


@tool(
    name="rename_batch",
    description="Batch rename files in a folder with a prefix, suffix, or find-replace pattern.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder containing files to rename",
            },
            "pattern": {
                "type": "string",
                "description": "Find-replace pattern: 'old_text -> new_text'",
            },
            "prefix": {
                "type": "string",
                "description": "Prefix to add to all files",
            },
            "suffix": {
                "type": "string",
                "description": "Suffix to add before extension",
            },
        },
        "required": ["folder"],
    },
)
def rename_batch(folder: str, pattern: str = "", prefix: str = "", suffix: str = "") -> str:
    p = Path(folder)
    if not p.exists():
        return f"error: folder not found: {folder}"

    files = [f for f in p.iterdir() if f.is_file()]
    if not files:
        return f"No files in {folder}"

    renames = []
    for f in sorted(files):
        name = f.stem
        ext = f.suffix

        if pattern and "->" in pattern:
            find, replace = [x.strip() for x in pattern.split("->", 1)]
            name = name.replace(find, replace)

        if prefix:
            name = prefix + name
        if suffix:
            name = name + suffix

        new_path = f.parent / f"{name}{ext}"
        if new_path != f:
            renames.append((f, new_path))

    if not renames:
        return "No changes needed."

    # Execute renames
    lines = [f"Batch Rename ({len(renames)} files):"]
    for old, new in renames:
        try:
            old.rename(new)
            lines.append(f"  {old.name} → {new.name}")
        except Exception as e:
            lines.append(f"  FAILED: {old.name} → {e}")

    return "\n".join(lines)
