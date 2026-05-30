"""
Weekly research scan — inserts topics with status 'suggested'.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from utils.paths import setup_repo_path

setup_repo_path()
load_dotenv()

from config import settings  # noqa: E402
from research import fetchers  # noqa: E402
from research.scoring import (  # noqa: E402
    is_duplicate_text,
    is_duplicate_url,
    score_item,
)
from utils.db import get_connection  # noqa: E402
from utils.notify import notify  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


FETCHERS = {
    "google_news": ("google_news", fetchers.fetch_google_news),
    "reddit": ("reddit", fetchers.fetch_reddit),
    "hacker_news": ("hacker_news", fetchers.fetch_hacker_news),
    "newsletter_rss": ("newsletter_rss", fetchers.fetch_newsletters),
}


def insert_topic(
    conn,
    *,
    text: str,
    source: str,
    source_url: str | None = None,
    source_summary: str | None = None,
) -> bool:
    keywords = settings.load_keywords()
    if score_item(text, source_summary or "", keywords) < 1:
        return False
    if is_duplicate_url(conn, source_url) or is_duplicate_text(conn, text):
        return False

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO topics (text, source, source_url, source_summary, status, updated_at)
        VALUES (?, ?, ?, ?, 'suggested', ?)
        """,
        (text, source, source_url, source_summary, now),
    )
    conn.commit()
    return True


def main() -> int:
    enabled = settings.load_enabled_research_sources()
    conn = get_connection()
    total_inserted = 0
    sources_attempted = 0
    sources_failed = 0

    for source_id in enabled:
        if source_id not in FETCHERS:
            logger.warning("Unknown research source: %s", source_id)
            continue

        source_name, fetcher = FETCHERS[source_id]
        sources_attempted += 1
        try:
            items = fetcher()
            inserted = 0
            for item in items:
                if insert_topic(
                    conn,
                    text=item["text"],
                    source=source_name,
                    source_url=item.get("source_url"),
                    source_summary=item.get("source_summary"),
                ):
                    inserted += 1
            logger.info("%s: inserted %d items", source_name, inserted)
            total_inserted += inserted
        except Exception:
            logger.exception("Source failed: %s", source_name)
            sources_failed += 1

    conn.close()

    if sources_attempted > 0 and sources_failed == sources_attempted:
        notify("Research scan failed: all sources unreachable. Check logs.")
        return 1

    if total_inserted > 0:
        notify(f"Weekly research scan complete. {total_inserted} new topics added.")

    logger.info("Scan complete. %d topics inserted.", total_inserted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
