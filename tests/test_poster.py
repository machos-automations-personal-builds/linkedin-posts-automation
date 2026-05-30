from datetime import datetime, timezone

from scheduler.poster import get_due_drafts


def test_get_due_drafts(db_conn):
    past = "2020-01-01 12:00:00"
    future = "2099-01-01 12:00:00"

    db_conn.execute(
        "INSERT INTO topics (text, source, status) VALUES ('t', 'manual', 'scheduled')"
    )
    topic_id = db_conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    db_conn.execute(
        """
        INSERT INTO drafts (topic_id, draft_text, variation, status, scheduled_for)
        VALUES (?, 'due', 1, 'approved', ?)
        """,
        (topic_id, past),
    )
    db_conn.execute(
        """
        INSERT INTO drafts (topic_id, draft_text, variation, status, scheduled_for)
        VALUES (?, 'future', 1, 'approved', ?)
        """,
        (topic_id, future),
    )
    db_conn.commit()

    due = get_due_drafts(db_conn)
    assert len(due) == 1
    assert due[0]["draft_text"] == "due"
