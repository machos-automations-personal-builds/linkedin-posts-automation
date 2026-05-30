"""Load line-based config files with optional .env overrides."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _parse_lines(content: str) -> list[str]:
    items = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


def load_line_config(
    filename: str,
    env_var: str | None,
    defaults: list[str],
    *,
    normalize_lower: bool = False,
) -> list[str]:
    """Load from env (comma-separated) if set, else from config file, else defaults."""
    if env_var:
        raw = os.environ.get(env_var, "").strip()
        if raw:
            items = [p.strip() for p in raw.split(",") if p.strip()]
            if normalize_lower:
                items = [i.lower() for i in items]
            return items

    path = CONFIG_DIR / filename
    if path.exists():
        items = _parse_lines(path.read_text(encoding="utf-8"))
        if items:
            if normalize_lower:
                items = [i.lower() for i in items]
            return items

    if defaults:
        logger.warning(
            "Using defaults for %s (%s missing or empty)", filename, path
        )
    return list(defaults)
