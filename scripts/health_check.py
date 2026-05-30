"""Daily health check."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from utils.paths import setup_repo_path

setup_repo_path()
load_dotenv()

from utils.db import get_connection, get_db_path  # noqa: E402
from utils.notify import notify  # noqa: E402


def check_database() -> str | None:
    path = get_db_path()
    if not path.exists():
        return f"database missing at {path}"
    conn = get_connection()
    conn.execute("SELECT 1")
    conn.close()
    return None


def check_env() -> str | None:
    if not os.environ.get("DB_PATH", "").strip() and not get_db_path():
        return "DB_PATH not configured"
    if not os.environ.get("MATTERMOST_WEBHOOK_URL", "").strip():
        return "MATTERMOST_WEBHOOK_URL not set"
    return None


def check_imports() -> str | None:
    try:
        import research.scanner  # noqa: F401
        import generator.draft  # noqa: F401
        import scheduler.poster  # noqa: F401
    except ImportError as exc:
        return f"component import failed: {exc}"
    return None


def main() -> int:
    checks = [
        ("database", check_database),
        ("environment", check_env),
        ("components", check_imports),
    ]

    for name, fn in checks:
        err = fn()
        if err:
            msg = f"Health check failed: {name} — {err}"
            print(msg, file=sys.stderr)
            notify(msg)
            return 1

    print("Health check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
