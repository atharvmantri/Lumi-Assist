"""Code analysis tools — count lines, detect languages, analyze structure."""
from __future__ import annotations

from pathlib import Path

from tools import tool


# Language detection by extension
LANG_EXTENSIONS = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript (React)",
    ".jsx": "JavaScript (React)", ".java": "Java", ".c": "C", ".cpp": "C++",
    ".h": "C Header", ".hpp": "C++ Header", ".cs": "C#", ".go": "Go",
    ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".kt": "Kotlin", ".scala": "Scala", ".sh": "Shell", ".bat": "Batch",
    ".ps1": "PowerShell", ".sql": "SQL", ".html": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".xml": "XML", ".md": "Markdown", ".toml": "TOML", ".ini": "INI",
    ".env": "Environment", ".dockerfile": "Dockerfile", ".pyi": "Python (Stub)",
}

# Comment markers
COMMENT_MARKERS = {
    "Python": ["#"], "JavaScript": ["//"], "TypeScript": ["//"],
    "C": ["//", "/*"], "C++": ["//", "/*"], "Java": ["//", "/*"],
    "Go": ["//"], "Rust": ["//"], "Ruby": ["#"], "PHP": ["//", "#"],
    "Shell": ["#"], "PowerShell": ["#"], "SQL": ["--"],
    "HTML": ["<!--"], "CSS": ["/*"], "SCSS": ["//"],
}


@tool(
    name="code_stats",
    description="Analyze code in a directory: line counts, comment ratios, file counts by language.",
    parameters={
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Directory to analyze (default: current directory)",
            },
        },
        "required": [],
    },
)
def code_stats(directory: str = "") -> str:
    target = Path(directory) if directory else Path.cwd()
    if not target.exists():
        return f"error: directory not found: {directory or '.'}"

    lang_stats = {}
    total_files = 0
    total_lines = 0

    for ext, lang in LANG_EXTENSIONS.items():
        files = list(target.rglob(f"*{ext}"))
        if not files:
            continue

        lang_lines = 0
        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        for f in files:
            if not f.is_file():
                continue
            total_files += 1
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                lines = text.split("\n")
                file_lines = len(lines)
                lang_lines += file_lines

                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        blank_lines += 1
                    elif any(stripped.startswith(c) for c in COMMENT_MARKERS.get(lang, [])):
                        comment_lines += 1
                    else:
                        code_lines += 1
            except (PermissionError, OSError):
                pass

        if lang_lines > 0:
            lang_stats[lang] = {
                "files": len(files),
                "lines": lang_lines,
                "code": code_lines,
                "comments": comment_lines,
                "blank": blank_lines,
            }
            total_lines += lang_lines

    if not lang_stats:
        return f"No recognized code files found in {target}"

    lines = [f"Code Statistics for {target}:"]
    lines.append(f"\n  {'Language':<20s} {'Files':>6s} {'Lines':>8s} {'Code':>8s} {'Comments':>10s} {'Blank':>8s}")
    lines.append(f"  {'-'*60}")

    for lang in sorted(lang_stats, key=lambda l: -lang_stats[l]["lines"]):
        s = lang_stats[lang]
        lines.append(f"  {lang:<20s} {s['files']:>6d} {s['lines']:>8d} {s['code']:>8d} {s['comments']:>10d} {s['blank']:>8d}")

    lines.append(f"\n  {'TOTAL':<20s} {total_files:>6d} {total_lines:>8d}")

    if total_lines > 0:
        total_code = sum(s["code"] for s in lang_stats.values())
        total_comments = sum(s["comments"] for s in lang_stats.values())
        lines.append(f"\n  Code density: {total_code/total_lines*100:.0f}% code, {total_comments/total_lines*100:.0f}% comments")

    return "\n".join(lines)


@tool(
    name="file_types",
    description="List all file types in a directory with their counts and total sizes.",
    parameters={
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Directory to analyze (default: current directory)",
            },
        },
        "required": [],
    },
)
def file_types(directory: str = "") -> str:
    target = Path(directory) if directory else Path.cwd()
    if not target.exists():
        return f"error: directory not found: {directory or '.'}"

    type_stats = {}
    total_files = 0

    for f in target.rglob("*"):
        if not f.is_file():
            continue
        total_files += 1
        ext = f.suffix.lower() or "(no extension)"
        try:
            size = f.stat().st_size
        except (PermissionError, OSError):
            size = 0

        if ext not in type_stats:
            type_stats[ext] = {"count": 0, "size": 0}
        type_stats[ext]["count"] += 1
        type_stats[ext]["size"] += size

    lines = [f"File Types in {target} ({total_files} files):"]
    lines.append(f"\n  {'Extension':<20s} {'Count':>8s} {'Total Size':>12s}")
    lines.append(f"  {'-'*40}")

    for ext in sorted(type_stats, key=lambda e: -type_stats[e]["count"]):
        s = type_stats[ext]
        size = s["size"]
        if size > 1024**2:
            size_str = f"{size/1024**2:.1f} MB"
        elif size > 1024:
            size_str = f"{size/1024:.0f} KB"
        else:
            size_str = f"{size} B"
        lines.append(f"  {ext:<20s} {s['count']:>8d} {size_str:>12s}")

    return "\n".join(lines)
