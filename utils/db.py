"""SQLite connection helpers."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_db_path() -> Path:
    raw = os.environ.get("DB_PATH", "db/queue.db")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")


def get_connection() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    configure_connection(conn)
    return conn
