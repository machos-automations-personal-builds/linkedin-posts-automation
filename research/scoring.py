"""Topic scoring and deduplication helpers."""

from __future__ import annotations

import re
import sqlite3


def score_item(title: str, summary: str, keywords: list[str]) -> int:
    text = f"{title} {summary}".lower()
    return sum(1 for kw in keywords if kw.lower() in text)


def token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def similarity_ratio(a: str, b: str) -> float:
    sa, sb = token_set(a), token_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def is_duplicate_url(conn: sqlite3.Connection, source_url: str | None) -> bool:
    if not source_url:
        return False
    row = conn.execute(
        "SELECT 1 FROM topics WHERE source_url = ? LIMIT 1",
        (source_url,),
    ).fetchone()
    return row is not None


def is_duplicate_text(
    conn: sqlite3.Connection, text: str, threshold: float = 0.8
) -> bool:
    rows = conn.execute("SELECT text FROM topics").fetchall()
    for row in rows:
        if similarity_ratio(text, row["text"]) >= threshold:
            return True
    return False
