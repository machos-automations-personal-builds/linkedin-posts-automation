"""
Draft generator — picks pending topics, generates two LLM draft variations.
"""

from __future__ import annotations

import logging
import os
import sys
import time

from dotenv import load_dotenv

from utils.paths import setup_repo_path

setup_repo_path()
load_dotenv()

from config.settings import VOICE_GUIDE_PATH  # noqa: E402
from generator.llm import LLMError, generate_variation  # noqa: E402
from utils.db import get_connection  # noqa: E402
from utils.notify import notify  # noqa: E402
from utils.transitions import mark_topic_drafted  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 60


def select_next_topic(conn):
    return conn.execute(
        """
        SELECT id, text, source, source_url, source_summary
        FROM topics
        WHERE status = 'pending'
        ORDER BY sort_order ASC, created_at ASC
        LIMIT 1
        """
    ).fetchone()


def load_voice_guide() -> str:
    if not VOICE_GUIDE_PATH.exists():
        raise FileNotFoundError(
            f"Voice guide missing at {VOICE_GUIDE_PATH}. "
            "Copy config/voice_guide.txt.example to config/voice_guide.txt"
        )
    return VOICE_GUIDE_PATH.read_text(encoding="utf-8")


def build_system_prompt(voice_guide: str, topic_row) -> str:
    from config.settings import LINKEDIN_POST_INSTRUCTIONS

    parts = [voice_guide, LINKEDIN_POST_INSTRUCTIONS, f"Topic: {topic_row['text']}"]
    if topic_row["source_summary"]:
        parts.append(f"Context: {topic_row['source_summary']}")
    if topic_row["source_url"]:
        parts.append(f"Source URL: {topic_row['source_url']}")
    return "\n\n".join(parts)


def generate_both_variations(system_prompt: str) -> tuple[str, str]:
    """Generate two variations; retry once after 60s on failure."""
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            text1 = generate_variation(system_prompt, 1)
            text2 = generate_variation(system_prompt, 2)
            return text1, text2
        except (LLMError, Exception) as exc:
            last_error = exc
            logger.exception(
                "LLM generation failed (attempt %d/2)", attempt + 1
            )
            if attempt == 0:
                logger.info("Retrying in %d seconds...", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                break

    raise last_error or LLMError("Draft generation failed")


def select_topic_by_id(conn, topic_id: int):
    return conn.execute(
        """
        SELECT id, text, source, source_url, source_summary
        FROM topics
        WHERE id = ? AND status = 'pending'
        """,
        (topic_id,),
    ).fetchone()


def main(topic_id: int | None = None) -> int:
    conn = get_connection()
    topic = select_topic_by_id(conn, topic_id) if topic_id else select_next_topic(conn)

    if not topic:
        notify("Content queue is empty. Add topics to continue.")
        conn.close()
        logger.info("No pending topics.")
        return 0

    try:
        voice = load_voice_guide()
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        notify(str(exc))
        conn.close()
        return 1

    system_prompt = build_system_prompt(voice, topic)

    try:
        text1, text2 = generate_both_variations(system_prompt)
    except Exception:
        notify(
            f"Draft generation failed for topic id={topic['id']}. "
            "Topic left pending. Check logs."
        )
        conn.close()
        return 1

    mark_topic_drafted(conn, topic["id"], (text1, text2))

    ui_url = os.environ.get("UI_URL", "http://localhost:5000/review")
    snippet = topic["text"][:60]
    notify(f"New draft ready for review: {snippet} — {ui_url}")

    logger.info("Drafted topic id=%s", topic["id"])
    conn.close()
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic-id", type=int, default=None)
    args = parser.parse_args()
    sys.exit(main(topic_id=args.topic_id))
