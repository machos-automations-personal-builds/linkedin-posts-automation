"""Orchestrator triggered by the Hub when a blog post is published.

Reads a post (title/description/content/url) from a JSON handoff file,
updates the voice guide, generates LinkedIn promo drafts that link to the
post, and inserts them into the review queue.
"""

from __future__ import annotations

import json
import logging
import os
import sys

from utils.paths import setup_repo_path

setup_repo_path()

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from generator.blog_promo import generate_promo_drafts, insert_topic_and_drafts  # noqa: E402
from generator.draft import load_voice_guide  # noqa: E402
from generator.voice_update import update_voice_guide  # noqa: E402
from utils.db import get_connection  # noqa: E402
from utils.notify import notify  # noqa: E402


def main(post_file: str) -> int:
    logger.info("Starting on_publish for post-file=%s", post_file)
    with open(post_file, encoding="utf-8") as f:
        post_data = json.load(f)
    os.remove(post_file)
    logger.info("Loaded post '%s' (%s)", post_data["title"], post_data["url"])

    conn = get_connection()

    try:
        voice = update_voice_guide(post_data)
    except Exception:
        logger.exception("Voice guide update failed — continuing with existing guide")
        notify(f"Voice guide update failed for '{post_data['title']}' — check logs/on_publish.log.")
        voice = load_voice_guide()

    try:
        draft_texts = generate_promo_drafts(post_data, voice)
    except Exception:
        logger.exception("LinkedIn promo draft generation failed")
        notify(f"LinkedIn promo draft generation failed for '{post_data['title']}' — check logs/on_publish.log.")
        conn.close()
        return 1

    topic_id = insert_topic_and_drafts(conn, post_data, draft_texts)
    logger.info("Done. topic_id=%s, drafts=%d", topic_id, len(draft_texts))

    ui_url = os.environ.get("UI_URL", "http://localhost:5000/review")
    notify(f"Published '{post_data['title']}' — {len(draft_texts)} LinkedIn drafts ready for review: {ui_url}")

    conn.close()
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--post-file", required=True, help="Path to a JSON file with title/description/content/url")
    args = parser.parse_args()
    sys.exit(main(args.post_file))
