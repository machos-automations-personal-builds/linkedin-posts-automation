"""
Post scheduler — publishes due approved drafts (staging log or LinkedIn).
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from utils.paths import setup_repo_path

setup_repo_path()
load_dotenv()

from config.settings import STAGING_LOG_PATH  # noqa: E402
from scheduler.linkedin import (  # noqa: E402
    LinkedInPostError,
    LinkedInTokenError,
    post_to_linkedin as linkedin_publish,
)
from utils.db import get_connection  # noqa: E402
from utils.notify import notify  # noqa: E402
from utils.transitions import mark_post_failed, mark_posted  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def is_production_mode() -> bool:
    return os.environ.get("PRODUCTION_MODE", "false").lower() in ("true", "1")


def get_due_drafts(conn):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return conn.execute(
        """
        SELECT d.id, d.draft_text, d.topic_id, d.failure_count
        FROM drafts d
        WHERE d.status = 'approved' AND d.scheduled_for <= ?
        ORDER BY d.scheduled_for ASC
        """,
        (now,),
    ).fetchall()


def handle_staging_post(draft_text: str) -> None:
    STAGING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(STAGING_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n--- {ts} ---\n{draft_text}\n")


def publish_production(draft_text: str) -> tuple[bool, str | None, str | None, bool]:
    """
    Returns (success, post_id, post_url, token_invalid).
    On token invalid, success is False and token_invalid is True.
    """
    try:
        post_id, post_url = linkedin_publish(draft_text)
        return True, post_id, post_url, False
    except LinkedInTokenError as exc:
        logger.error("%s", exc)
        return False, None, None, True
    except LinkedInPostError as exc:
        logger.error("%s", exc)
        notify(f"LinkedIn post failed: {exc}")
        return False, None, None, False


def main() -> int:
    conn = get_connection()
    due = get_due_drafts(conn)

    for draft in due:
        draft_id = draft["id"]
        text = draft["draft_text"]
        snippet = text[:60]

        if not is_production_mode():
            handle_staging_post(text)
            mark_posted(conn, draft_id)
            notify(f"[STAGING] Post logged (not sent to LinkedIn): {snippet}")
            logger.info("Staging post for draft id=%s", draft_id)
            continue

        ok, post_id, post_url, token_invalid = publish_production(text)

        if token_invalid:
            notify(
                "LinkedIn token expired. Re-authentication required before next post."
            )
            logger.warning(
                "Skipping draft id=%s due to invalid LinkedIn token", draft_id
            )
            continue

        if ok:
            mark_posted(conn, draft_id, post_id)
            notify(f"Post live on LinkedIn: {post_url}")
            logger.info("Posted draft id=%s", draft_id)
        else:
            failures = (draft["failure_count"] or 0) + 1
            mark_post_failed(conn, draft_id, failures)
            if failures >= 3:
                notify(
                    f"POST FAILED after 3 attempts. Manual intervention required. "
                    f"Draft ID: {draft_id}"
                )
            else:
                logger.warning(
                    "Post failed for draft id=%s (attempt %d)", draft_id, failures
                )

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
