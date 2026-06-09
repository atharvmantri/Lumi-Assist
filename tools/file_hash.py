"""File hash and integrity tools."""
from __future__ import annotations

import hashlib
from pathlib import Path

from tools import tool


def _file_hash(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@tool(
    name="file_hash",
    description="Compute file hash (MD5, SHA1, SHA256).",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file",
            },
            "algorithm": {
                "type": "string",
                "description": "Hash algorithm: 'md5', 'sha1', 'sha256' (default 'sha256')",
                "enum": ["md5", "sha1", "sha256"],
            },
        },
        "required": ["path"],
    },
)
def file_hash(path: str, algorithm: str = "sha256") -> str:
    p = Path(path)
    if not p.exists():
        return f"error: file not found: {path}"
    if not p.is_file():
        return f"error: not a file: {path}"

    try:
        digest = _file_hash(p, algorithm)
        size_mb = p.stat().st_size / (1024 * 1024)
        return f"{algorithm.upper()}({p.name}) [{size_mb:.1f}MB] = {digest}"
    except Exception as e:
        return f"error: {e}"


@tool(
    name="file_hash_all",
    description="Compute all three hashes (MD5, SHA1, SHA256) for a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file",
            },
        },
        "required": ["path"],
    },
)
def file_hash_all(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"error: file not found: {path}"

    try:
        lines = [f"File Hashes for {p.name}:"]
        for algo in ["md5", "sha1", "sha256"]:
            digest = _file_hash(p, algo)
            lines.append(f"  {algo.upper()}: {digest}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"


@tool(
    name="verify_hash",
    description="Verify a file's hash matches an expected value.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file",
            },
            "expected_hash": {
                "type": "string",
                "description": "Expected hash value",
            },
            "algorithm": {
                "type": "string",
                "description": "Hash algorithm (auto-detected by hash length if not specified)",
            },
        },
        "required": ["path", "expected_hash"],
    },
)
def verify_hash(path: str, expected_hash: str, algorithm: str = "") -> str:
    p = Path(path)
    if not p.exists():
        return f"error: file not found: {path}"

    # Auto-detect algorithm
    if not algorithm:
        hash_len = len(expected_hash)
        algo_map = {32: "md5", 40: "sha1", 64: "sha256"}
        algorithm = algo_map.get(hash_len, "sha256")

    expected_hash = expected_hash.lower().strip()
    actual = _file_hash(p, algorithm).lower()

    if actual == expected_hash:
        return f"✓ HASH MATCH: {algorithm.upper()} verified for {p.name}"
    else:
        return f"✗ HASH MISMATCH for {p.name}:\n  Expected: {expected_hash}\n  Actual:   {actual}"
