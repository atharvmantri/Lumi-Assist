"""Configuration loading for Lumi.

Loads `config.yaml` from the project root and exposes typed accessors.
Single source of truth — every core module imports `load_config()` rather
than reading the file itself.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
CONFIG_LOCAL_PATH = PROJECT_ROOT / "config.local.yaml"
ENV_PATH = PROJECT_ROOT / ".env"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge `override` into `base`. Returns new dict."""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config() -> dict[str, Any]:
    """Read config.yaml + optional config.local.yaml overrides + load .env.

    config.local.yaml values take precedence over config.yaml (deep merge).
    This lets you change voice, model, or sensitivity without touching
    the main config that gets committed to git.
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.yaml not found at {CONFIG_PATH}. "
            "Copy from the repo or re-run the scaffold."
        )

    # .env is optional at config-load time; LLM client will error if a needed
    # secret is missing.
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Apply local overrides if present
    if CONFIG_LOCAL_PATH.exists():
        with CONFIG_LOCAL_PATH.open("r", encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, local)

    return cfg


def get_env(key: str, *, required: bool = True) -> str | None:
    """Read an env var. With required=True, raises if missing or empty."""
    val = os.environ.get(key, "").strip()
    if required and not val:
        raise RuntimeError(
            f"Environment variable {key} is not set. "
            f"Add it to {ENV_PATH} (see .env.example)."
        )
    return val or None


def read_text_file(rel_path: str) -> str:
    """Read a text file relative to the project root."""
    path = PROJECT_ROOT / rel_path
    if not path.exists():
        raise FileNotFoundError(f"Expected file at {path}")
    return path.read_text(encoding="utf-8")
