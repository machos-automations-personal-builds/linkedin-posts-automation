import sqlite3
from pathlib import Path

# Topic statuses: suggested, pending, drafted, scheduled, posted, skipped
# Draft statuses: awaiting_review, approved, rejected, posted, failed

def init_db():
    db_dir = Path(__file__).parent.parent / "db"
    db_dir.mkdir(exist_ok=True)

    db_path = db_dir / "queue.db"

    print(f"Initializing database at {db_path}...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        source TEXT NOT NULL,
        source_url TEXT,
        source_summary TEXT,
        status TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        sort_order INTEGER DEFAULT 0
    )
    """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS drafts (
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
    )
    """
    )

    # Migration for existing DBs without failure_count
    cursor.execute("PRAGMA table_info(drafts)")
    columns = {row[1] for row in cursor.fetchall()}
    if "failure_count" not in columns:
        cursor.execute(
            "ALTER TABLE drafts ADD COLUMN failure_count INTEGER DEFAULT 0"
        )

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
