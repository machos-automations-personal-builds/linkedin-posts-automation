"""Topic and draft status transitions (locked lifecycle)."""

from __future__ import annotations

from datetime import datetime, timezone

import sqlite3


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _touch_topic(cursor: sqlite3.Cursor, topic_id: int) -> None:
    cursor.execute(
        "UPDATE topics SET updated_at = ? WHERE id = ?",
        (_now_iso(), topic_id),
    )


def add_manual_topic(conn: sqlite3.Connection, text: str, sort_order: int = 0) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO topics (text, source, status, sort_order, updated_at)
        VALUES (?, 'manual', 'pending', ?, ?)
        """,
        (text.strip(), sort_order, _now_iso()),
    )
    conn.commit()
    return cursor.lastrowid


def accept_topic(conn: sqlite3.Connection, topic_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE topics SET status = 'pending', updated_at = ?
        WHERE id = ? AND status = 'suggested'
        """,
        (_now_iso(), topic_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def dismiss_topic(conn: sqlite3.Connection, topic_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE topics SET status = 'skipped', updated_at = ?
        WHERE id = ? AND status = 'suggested'
        """,
        (_now_iso(), topic_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def skip_topic_review(conn: sqlite3.Connection, topic_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE topics SET status = 'pending', updated_at = ?
        WHERE id = ? AND status = 'drafted'
        """,
        (_now_iso(), topic_id),
    )
    if cursor.rowcount == 0:
        conn.commit()
        return False
    cursor.execute(
        """
        UPDATE drafts SET status = 'rejected'
        WHERE topic_id = ? AND status = 'awaiting_review'
        """,
        (topic_id,),
    )
    conn.commit()
    return True


def regenerate_topic(conn: sqlite3.Connection, topic_id: int) -> bool:
    return skip_topic_review(conn, topic_id)


def approve_draft(
    conn: sqlite3.Connection,
    draft_id: int,
    scheduled_for_iso: str,
    edited_text: str | None = None,
) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, topic_id, status FROM drafts WHERE id = ?",
        (draft_id,),
    )
    draft = cursor.fetchone()
    if not draft or draft["status"] != "awaiting_review":
        return False

    topic_id = draft["topic_id"]
    now = _now_iso()

    if edited_text is not None:
        cursor.execute(
            "UPDATE drafts SET draft_text = ? WHERE id = ?",
            (edited_text.strip(), draft_id),
        )

    cursor.execute(
        """
        UPDATE drafts SET status = 'approved', approved_at = ?, scheduled_for = ?
        WHERE id = ?
        """,
        (now, scheduled_for_iso, draft_id),
    )
    cursor.execute(
        """
        UPDATE drafts SET status = 'rejected'
        WHERE topic_id = ? AND id != ? AND status = 'awaiting_review'
        """,
        (topic_id, draft_id),
    )
    cursor.execute(
        """
        UPDATE topics SET status = 'scheduled', updated_at = ?
        WHERE id = ? AND status = 'drafted'
        """,
        (now, topic_id),
    )
    ok = cursor.rowcount > 0
    conn.commit()
    return ok


def mark_topic_drafted(
    conn: sqlite3.Connection,
    topic_id: int,
    draft_texts: tuple[str, str],
) -> None:
    cursor = conn.cursor()
    now = _now_iso()
    cursor.execute(
        """
        UPDATE topics SET status = 'drafted', updated_at = ?
        WHERE id = ? AND status = 'pending'
        """,
        (now, topic_id),
    )
    for variation, text in enumerate(draft_texts, start=1):
        cursor.execute(
            """
            INSERT INTO drafts (topic_id, draft_text, variation, status)
            VALUES (?, ?, ?, 'awaiting_review')
            """,
            (topic_id, text, variation),
        )
    conn.commit()


def mark_posted(conn: sqlite3.Connection, draft_id: int, linkedin_post_id: str | None = None) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT topic_id FROM drafts WHERE id = ? AND status = 'approved'", (draft_id,))
    row = cursor.fetchone()
    if not row:
        return False

    now = _now_iso()
    topic_id = row["topic_id"]
    cursor.execute(
        """
        UPDATE drafts SET status = 'posted', posted_at = ?, linkedin_post_id = ?
        WHERE id = ?
        """,
        (now, linkedin_post_id, draft_id),
    )
    cursor.execute(
        """
        UPDATE topics SET status = 'posted', updated_at = ?
        WHERE id = ?
        """,
        (now, topic_id),
    )
    conn.commit()
    return True


def mark_post_failed(conn: sqlite3.Connection, draft_id: int, failure_count: int) -> None:
    cursor = conn.cursor()
    now = _now_iso()
    if failure_count >= 3:
        cursor.execute(
            "UPDATE drafts SET status = 'failed', failure_count = ? WHERE id = ?",
            (failure_count, draft_id),
        )
    else:
        cursor.execute(
            "UPDATE drafts SET failure_count = ? WHERE id = ?",
            (failure_count, draft_id),
        )
    conn.commit()


def delete_or_skip_manual(conn: sqlite3.Connection, topic_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT source, status FROM topics WHERE id = ?",
        (topic_id,),
    )
    row = cursor.fetchone()
    if not row or row["source"] != "manual" or row["status"] not in ("pending",):
        return False

    cursor.execute(
        """
        UPDATE drafts SET status = 'rejected'
        WHERE topic_id = ? AND status IN ('awaiting_review', 'approved')
        """,
        (topic_id,),
    )
    cursor.execute(
        "UPDATE topics SET status = 'skipped', updated_at = ? WHERE id = ?",
        (_now_iso(), topic_id),
    )
    conn.commit()
    return True


def update_topic_text(conn: sqlite3.Connection, topic_id: int, text: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE topics SET text = ?, updated_at = ?
        WHERE id = ? AND source = 'manual' AND status = 'pending'
        """,
        (text.strip(), _now_iso(), topic_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def reorder_manual_topics(conn: sqlite3.Connection, topic_ids: list[int]) -> None:
    cursor = conn.cursor()
    for order, topic_id in enumerate(topic_ids):
        cursor.execute(
            """
            UPDATE topics SET sort_order = ?, updated_at = ?
            WHERE id = ? AND source = 'manual' AND status = 'pending'
            """,
            (order, _now_iso(), topic_id),
        )
    conn.commit()
