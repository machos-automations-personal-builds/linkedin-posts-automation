"""Tests for generator/blog_promo.py"""

from unittest.mock import patch

import pytest

from generator.blog_promo import generate_promo_drafts, insert_topic_and_drafts
from generator.llm import LLMError

POST_DATA = {
    "title": "How I Automated My Lawn Care Business",
    "description": "A case study",
    "content": "Full post content here.",
    "url": "https://joncamacho.com/writing/lawn-care-automation",
}


@patch("generator.blog_promo.generate_variation")
def test_generate_promo_drafts_success(mock_generate):
    mock_generate.side_effect = ["Draft 1", "Draft 2", "Draft 3"]

    drafts = generate_promo_drafts(POST_DATA, "voice guide text")

    assert drafts == ["Draft 1", "Draft 2", "Draft 3"]
    assert mock_generate.call_count == 3


@patch("generator.blog_promo.time.sleep")
@patch("generator.blog_promo.generate_variation")
def test_generate_promo_drafts_retries_then_succeeds(mock_generate, mock_sleep):
    mock_generate.side_effect = [LLMError("fail"), "Draft 1", "Draft 2", "Draft 3"]

    drafts = generate_promo_drafts(POST_DATA, "voice guide text")

    assert drafts == ["Draft 1", "Draft 2", "Draft 3"]
    mock_sleep.assert_called_once()


@patch("generator.blog_promo.time.sleep")
@patch("generator.blog_promo.generate_variation", side_effect=LLMError("fail"))
def test_generate_promo_drafts_raises_after_retry(mock_generate, mock_sleep):
    with pytest.raises(LLMError):
        generate_promo_drafts(POST_DATA, "voice guide text")

    assert mock_generate.call_count == 2


def test_insert_topic_and_drafts(db_conn):
    topic_id = insert_topic_and_drafts(db_conn, POST_DATA, ["Draft 1", "Draft 2", "Draft 3"])

    topic = db_conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    assert topic["source"] == "website"
    assert topic["status"] == "drafted"
    assert topic["source_url"] == POST_DATA["url"]

    drafts = db_conn.execute(
        "SELECT * FROM drafts WHERE topic_id = ? ORDER BY variation", (topic_id,)
    ).fetchall()
    assert [d["status"] for d in drafts] == ["awaiting_review"] * 3
    assert [d["variation"] for d in drafts] == [1, 2, 3]
    assert [d["draft_text"] for d in drafts] == ["Draft 1", "Draft 2", "Draft 3"]
