from utils.transitions import (
    accept_topic,
    add_manual_topic,
    approve_draft,
    dismiss_topic,
    mark_posted,
    mark_topic_drafted,
    skip_topic_review,
)


def _topic(conn, status="suggested", source="reddit"):
    cur = conn.execute(
        "INSERT INTO topics (text, source, status) VALUES ('T', ?, ?)",
        (source, status),
    )
    conn.commit()
    return cur.lastrowid


def test_accept_and_dismiss(db_conn):
    tid = _topic(db_conn)
    assert accept_topic(db_conn, tid)
    row = db_conn.execute("SELECT status FROM topics WHERE id=?", (tid,)).fetchone()
    assert row["status"] == "pending"

    tid2 = _topic(db_conn)
    assert dismiss_topic(db_conn, tid2)
    row = db_conn.execute("SELECT status FROM topics WHERE id=?", (tid2,)).fetchone()
    assert row["status"] == "skipped"


def test_approve_rejects_sibling(db_conn):
    tid = add_manual_topic(db_conn, "Post me")
    mark_topic_drafted(db_conn, tid, ("v1", "v2"))

    d1 = db_conn.execute(
        "SELECT id FROM drafts WHERE topic_id=? AND variation=1", (tid,)
    ).fetchone()[0]
    d2 = db_conn.execute(
        "SELECT id FROM drafts WHERE topic_id=? AND variation=2", (tid,)
    ).fetchone()[0]

    assert approve_draft(db_conn, d1, "2099-06-01 15:00:00")

    s1 = db_conn.execute("SELECT status FROM drafts WHERE id=?", (d1,)).fetchone()[0]
    s2 = db_conn.execute("SELECT status FROM drafts WHERE id=?", (d2,)).fetchone()[0]
    ts = db_conn.execute("SELECT status FROM topics WHERE id=?", (tid,)).fetchone()[0]

    assert s1 == "approved"
    assert s2 == "rejected"
    assert ts == "scheduled"


def test_skip_returns_pending(db_conn):
    tid = _topic(db_conn, status="pending", source="manual")
    db_conn.execute("UPDATE topics SET status='drafted' WHERE id=?", (tid,))
    mark_topic_drafted(db_conn, tid, ("a", "b"))
    assert skip_topic_review(db_conn, tid)
    assert (
        db_conn.execute("SELECT status FROM topics WHERE id=?", (tid,)).fetchone()[0]
        == "pending"
    )


def test_mark_posted_updates_both(db_conn):
    tid = add_manual_topic(db_conn, "Post me")
    db_conn.execute("UPDATE topics SET status='scheduled' WHERE id=?", (tid,))
    db_conn.execute(
        """
        INSERT INTO drafts (topic_id, draft_text, variation, status, scheduled_for)
        VALUES (?, 'text', 1, 'approved', '2020-01-01')
        """,
        (tid,),
    )
    db_conn.commit()
    did = db_conn.execute("SELECT id FROM drafts").fetchone()[0]

    assert mark_posted(db_conn, did, "urn:123")
    assert (
        db_conn.execute("SELECT status FROM drafts WHERE id=?", (did,)).fetchone()[0]
        == "posted"
    )
    assert (
        db_conn.execute("SELECT status FROM topics WHERE id=?", (tid,)).fetchone()[0]
        == "posted"
    )
