"""File organizer — auto-sort files by type."""
from __future__ import annotations

import shutil
from pathlib import Path

from tools import tool

# File type categories
FILE_CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp", ".tiff"],
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".csv", ".xlsx", ".xls", ".pptx", ".ppt"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".xml", ".sql", ".sh", ".bat"],
    "Executables": [".exe", ".msi", ".app", ".dmg"],
}


@tool(
    name="organize_folder",
    description="Organize files in a folder by sorting them into subfolders by type (Images, Documents, Videos, etc.).",
    parameters={
        "type": "object",
        "properties": {
            "folder_path": {
                "type": "string",
                "description": "Path to the folder to organize (default: user's Downloads folder)",
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, show what would happen without actually moving files (default false)",
            },
        },
        "required": [],
    },
)
def organize_folder(folder_path: str = "", dry_run: bool = False) -> str:
    folder = Path(folder_path) if folder_path else Path.home() / "Downloads"

    if not folder.exists():
        return f"error: folder not found: {folder}"
    if not folder.is_dir():
        return f"error: not a directory: {folder}"

    files = [f for f in folder.iterdir() if f.is_file()]
    if not files:
        return f"No files to organize in {folder}"

    action = "Would move" if dry_run else "Moved"
    lines = [f"{'[DRY RUN] ' if dry_run else ''}Organizing {folder}:"]
    moved_count = 0

    for f in sorted(files):
        ext = f.suffix.lower()
        category = None
        for cat, exts in FILE_CATEGORIES.items():
            if ext in exts:
                category = cat
                break

        if not category:
            continue

        dest_dir = folder / category
        if not dry_run:
            dest_dir.mkdir(exist_ok=True)

        dest = dest_dir / f.name
        # Handle name collisions
        if dest.exists():
            dest = dest_dir / f"{f.stem}_{f.suffix}"
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{f.stem}_{counter}{f.suffix}"
                counter += 1

        if not dry_run:
            shutil.move(str(f), str(dest))
        lines.append(f"  {action} {f.name} → {category}/")
        moved_count += 1

    if moved_count == 0:
        lines.append("  No files matched known categories.")

    lines.append(f"\n{moved_count} file(s) {'would be ' if dry_run else ''}organized into {len(set(FILE_CATEGORIES.keys()))} categories")
    return "\n".join(lines)


@tool(
    name="find_duplicates",
    description="Find duplicate files in a folder based on file size and content hash.",
    parameters={
        "type": "object",
        "properties": {
            "folder_path": {
                "type": "string",
                "description": "Folder to scan for duplicates (default: current directory)",
            },
        },
        "required": [],
    },
)
def find_duplicates(folder_path: str = "") -> str:
    import hashlib

    folder = Path(folder_path) if folder_path else Path.cwd()
    if not folder.exists():
        return f"error: folder not found: {folder}"

    # Group by size first (fast filter)
    size_groups: dict[int, list[Path]] = {}
    for f in folder.rglob("*"):
        if f.is_file():
            size_groups.setdefault(f.stat().st_size, []).append(f)

    # Only check files with matching sizes
    duplicates = []
    for size, files in size_groups.items():
        if len(files) < 2:
            continue

        # Hash to confirm duplicates
        hash_groups: dict[str, list[Path]] = {}
        for f in files:
            try:
                h = hashlib.md5(f.read_bytes()).hexdigest()
                hash_groups.setdefault(h, []).append(f)
            except (PermissionError, OSError):
                continue

        for h, group in hash_groups.items():
            if len(group) >= 2:
                duplicates.append((size, group))

    if not duplicates:
        return f"No duplicates found in {folder}"

    lines = [f"Found {len(duplicates)} duplicate group(s):"]
    total_waste = 0
    for size, group in duplicates:
        lines.append(f"\n  Size: {size/1024:.0f} KB ({len(group)} copies):")
        for f in group:
            lines.append(f"    {f}")
        total_waste += size * (len(group) - 1)

    lines.append(f"\nTotal wasted space: {total_waste/1024/1024:.1f} MB")
    return "\n".join(lines)
