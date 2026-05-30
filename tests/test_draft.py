from generator.draft import select_next_topic


def _insert(conn, text, status, sort_order=0, source="manual"):
    conn.execute(
        """
        INSERT INTO topics (text, source, status, sort_order)
        VALUES (?, ?, ?, ?)
        """,
        (text, source, status, sort_order),
    )
    conn.commit()


def test_select_next_topic_pending_only(db_conn):
    _insert(db_conn, "suggested one", "suggested")
    _insert(db_conn, "pending second", "pending", sort_order=1)
    _insert(db_conn, "pending first", "pending", sort_order=0)

    row = select_next_topic(db_conn)
    assert row["text"] == "pending first"


def test_select_ignores_suggested(db_conn):
    _insert(db_conn, "only suggested", "suggested")
    assert select_next_topic(db_conn) is None
