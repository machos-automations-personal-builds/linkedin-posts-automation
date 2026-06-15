"""Update the voice guide using a newly published blog post."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config.settings import VOICE_GUIDE_PATH, VOICE_UPDATE_INSTRUCTIONS, VOICE_UPDATE_TEMPERATURE
from generator.draft import load_voice_guide
from generator.llm import generate_text

logger = logging.getLogger(__name__)

VOICE_GUIDE_HISTORY_DIR = VOICE_GUIDE_PATH.parent / "voice_guide_history"


def _backup_voice_guide(current_guide: str) -> None:
    VOICE_GUIDE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = VOICE_GUIDE_HISTORY_DIR / f"voice_guide_{timestamp}.txt"
    backup_path.write_text(current_guide, encoding="utf-8")
    logger.info("Backed up voice guide to %s", backup_path)


def update_voice_guide(post_data: dict) -> str:
    """Refine the voice guide using a newly published blog post.

    `post_data` must have `title` and `content`. Returns the updated guide
    text. Raises on any failure — callers decide how to handle this
    non-fatally (the existing guide is left untouched on error).
    """
    current_guide = load_voice_guide()
    logger.info("Loaded current voice guide (%d chars)", len(current_guide))

    _backup_voice_guide(current_guide)

    user_prompt = (
        f"Current voice guide:\n{current_guide}\n\n"
        f"New blog post titled \"{post_data['title']}\":\n{post_data['content']}"
    )

    try:
        updated_guide = generate_text(
            VOICE_UPDATE_INSTRUCTIONS,
            user_prompt,
            temperature=VOICE_UPDATE_TEMPERATURE,
        )
    except Exception:
        logger.exception("Voice guide update failed")
        raise

    VOICE_GUIDE_PATH.write_text(updated_guide, encoding="utf-8")
    logger.info("Voice guide updated (%d chars)", len(updated_guide))
    return updated_guide


if __name__ == "__main__":
    import argparse
    import json
    import sys

    from utils.paths import setup_repo_path

    setup_repo_path()

    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--post-file", required=True, help="Path to a JSON file with title/content")
    args = parser.parse_args()

    with open(args.post_file, encoding="utf-8") as f:
        data = json.load(f)

    update_voice_guide(data)
    sys.exit(0)
