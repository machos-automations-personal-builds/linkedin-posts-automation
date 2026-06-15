"""Generate LinkedIn promo drafts for a newly published blog post."""

from __future__ import annotations

import logging
import sqlite3
import time

from config.settings import BLOG_PROMO_INSTRUCTIONS, BLOG_PROMO_VARIATION_COUNT
from generator.llm import LLMError, generate_variation

logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 60


def build_system_prompt(voice_guide: str, post_data: dict) -> str:
    parts = [
        voice_guide,
        BLOG_PROMO_INSTRUCTIONS,
        f"Blog post title: {post_data['title']}",
    ]
    if post_data.get("description"):
        parts.append(f"Description: {post_data['description']}")
    parts.append(f"Blog post content:\n{post_data['content']}")
    parts.append(
        f"Blog post URL: {post_data['url']}\n"
        "Include this bare URL on its own line somewhere in the post (not as a markdown link)."
    )
    return "\n\n".join(parts)


def generate_promo_drafts(post_data: dict, voice_guide_text: str) -> list[str]:
    """Generate BLOG_PROMO_VARIATION_COUNT promo drafts; retry once after 60s on failure."""
    system_prompt = build_system_prompt(voice_guide_text, post_data)
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            drafts: list[str] = []
            for variation in range(1, BLOG_PROMO_VARIATION_COUNT + 1):
                text = generate_variation(system_prompt, variation)
                logger.info("Generated promo draft variation %d (%d chars)", variation, len(text))
                drafts.append(text)
            return drafts
        except (LLMError, Exception) as exc:
            last_error = exc
            logger.exception("Blog promo draft generation failed (attempt %d/2)", attempt + 1)
            if attempt == 0:
                logger.info("Retrying in %d seconds...", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)

    logger.exception("Blog promo draft generation failed after retry")
    raise last_error or LLMError("Blog promo draft generation failed")


def insert_topic_and_drafts(conn: sqlite3.Connection, post_data: dict, draft_texts: list[str]) -> int:
    """Insert a 'website' topic in 'drafted' status with awaiting_review drafts."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO topics (text, source, source_url, status)
            VALUES (?, 'website', ?, 'drafted')
            """,
            (f"Promote blog post: {post_data['title']}", post_data["url"]),
        )
        topic_id = cursor.lastrowid
        for variation, text in enumerate(draft_texts, start=1):
            cursor.execute(
                """
                INSERT INTO drafts (topic_id, draft_text, variation, status)
                VALUES (?, ?, ?, 'awaiting_review')
                """,
                (topic_id, text, variation),
            )
        conn.commit()
    except Exception:
        logger.exception("Failed to insert topic/drafts for blog promo")
        raise

    logger.info("Inserted topic_id=%s with %d drafts", topic_id, len(draft_texts))
    return topic_id
