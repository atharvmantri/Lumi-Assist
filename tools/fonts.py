"""Font tools — list installed fonts, font info."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tools import tool


@tool(
    name="list_fonts",
    description="List all installed system fonts.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional filter by font name",
            },
            "limit": {
                "type": "integer",
                "description": "Max fonts to show (default 50)",
            },
        },
        "required": [],
    },
)
def list_fonts(query: str = "", limit: int = 50) -> str:
    try:
        import win32api
        fonts = win32api.EnumFonts(win32api.GetDC(0))
        font_names = sorted(set(f[2] for f in fonts))
    except ImportError:
        # Fallback: list font files
        font_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"
        if font_dir.exists():
            font_files = [f.stem for f in font_dir.glob("*.ttf")] + [f.stem for f in font_dir.glob("*.otf")]
            font_names = sorted(set(font_files))
        else:
            return "error: could not enumerate fonts"

    if query:
        font_names = [f for f in font_names if query.lower() in f.lower()]

    total = len(font_names)
    shown = font_names[:limit]

    lines = [f"Installed Fonts ({total} total, showing {len(shown)}):"]
    for f in shown:
        lines.append(f"  {f}")
    if total > limit:
        lines.append(f"  ...and {total - limit} more")

    return "\n".join(lines)


@tool(
    name="font_info",
    description="Get info about a font file.",
    parameters={
        "type": "object",
        "properties": {
            "font_path": {
                "type": "string",
                "description": "Path to the font file (.ttf, .otf)",
            },
        },
        "required": ["font_path"],
    },
)
def font_info(font_path: str) -> str:
    try:
        from PIL import ImageFont
    except ImportError:
        return "error: Pillow not installed"

    p = Path(font_path)
    if not p.exists():
        return f"error: font file not found: {font_path}"

    try:
        font = ImageFont.truetype(str(p), 16)
        size_kb = p.stat().st_size / 1024
        return (
            f"Font: {p.name}\n"
            f"  Size: {size_kb:.0f} KB\n"
            f"  Type: {p.suffix.upper()[1:]}\n"
            f"  Sample: {'The quick brown fox 0123456789'[:60]}"
        )
    except Exception as e:
        return f"error loading font: {e}"
