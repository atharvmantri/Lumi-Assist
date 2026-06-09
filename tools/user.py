"""User account and profile tools."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tools import tool


@tool(
    name="whoami",
    description="Show current user information: username, domain, groups.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def whoami() -> str:
    try:
        username = os.environ.get("USERNAME", "unknown")
        userdomain = os.environ.get("USERDOMAIN", "")
        userprofile = os.environ.get("USERPROFILE", "")
        computername = os.environ.get("COMPUTERNAME", "")

        lines = [
            f"Current User:",
            f"  Username: {username}",
            f"  Domain: {userdomain}",
            f"  Computer: {computername}",
            f"  Profile: {userprofile}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="user_groups",
    description="Show which groups the current user belongs to.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def user_groups() -> str:
    try:
        result = subprocess.run(
            ["net", "user", os.environ.get("USERNAME", "")],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = []
        capture = False
        for line in result.stdout.split("\n"):
            if "Global Group" in line or "Local Group" in line:
                capture = True
                continue
            if capture and line.strip():
                groups = [g.strip() for g in line.split() if g.strip()]
                lines.extend(groups)

        if lines:
            return f"User Groups ({len(lines)}):\n" + "\n".join(f"  {g}" for g in lines)
        return "No group information found."
    except Exception as e:
        return f"error: {e}"


@tool(
    name="open_user_folder",
    description="Open a user folder: Desktop, Documents, Downloads, Pictures, Music, Videos, or AppData.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder to open: 'desktop', 'documents', 'downloads', 'pictures', 'music', 'videos', 'appdata'",
                "enum": ["desktop", "documents", "downloads", "pictures", "music", "videos", "appdata"],
            },
        },
        "required": ["folder"],
    },
)
def open_user_folder(folder: str) -> str:
    folders = {
        "desktop": Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
        "downloads": Path.home() / "Downloads",
        "pictures": Path.home() / "Pictures",
        "music": Path.home() / "Music",
        "videos": Path.home() / "Videos",
        "appdata": Path(os.environ.get("APPDATA", "")),
    }

    target = folders.get(folder.lower())
    if not target or not target.exists():
        return f"error: folder '{folder}' not found"

    try:
        os.startfile(str(target))
        return f"Opened {folder} folder: {target}"
    except Exception as e:
        return f"error opening {folder}: {e}"


@tool(
    name="get_recent_files",
    description="List recently modified files in a user folder.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder to scan: 'desktop', 'documents', 'downloads', 'pictures' (default 'downloads')",
                "enum": ["desktop", "documents", "downloads", "pictures"],
            },
            "limit": {
                "type": "integer",
                "description": "Max files to show (default 15)",
            },
        },
        "required": [],
    },
)
def get_recent_files(folder: str = "downloads", limit: int = 15) -> str:
    folder_map = {
        "desktop": Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
        "downloads": Path.home() / "Downloads",
        "pictures": Path.home() / "Pictures",
    }
    target = folder_map.get(folder.lower())
    if not target or not target.exists():
        return f"error: folder '{folder}' not found"

    try:
        files = [f for f in target.iterdir() if f.is_file()]
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        lines = [f"Recent Files in {folder} ({len(files)} total):"]
        for f in files[:limit]:
            mtime = f.stat().st_mtime
            from datetime import datetime
            ts = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            size = f.stat().st_size
            size_str = f"{size/1024/1024:.1f}MB" if size > 1024*1024 else f"{size/1024:.0f}KB"
            lines.append(f"  [{ts}] {f.name} ({size_str})")

        if len(files) > limit:
            lines.append(f"  ...and {len(files) - limit} more")

        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"
