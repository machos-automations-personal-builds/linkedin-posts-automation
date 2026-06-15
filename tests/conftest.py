import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def db_conn(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.executescript(
        """
        CREATE TABLE topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            source_summary TEXT,
            status TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            sort_order INTEGER DEFAULT 0,
            user_notes TEXT DEFAULT ''
        );
        CREATE TABLE drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            draft_text TEXT NOT NULL,
            variation INTEGER NOT NULL,
            status TEXT NOT NULL,
            approved_at DATETIME,
            scheduled_for DATETIME,
            posted_at DATETIME,
            linkedin_post_id TEXT,
            failure_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (topic_id) REFERENCES topics (id)
        );
        """
    )
    yield conn
    conn.close()
