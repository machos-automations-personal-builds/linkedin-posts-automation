"""Tests for generator/on_publish.py orchestration."""

import json
from unittest.mock import MagicMock, patch

from generator.on_publish import main

POST_DATA = {
    "title": "How I Automated My Lawn Care Business",
    "description": "A case study",
    "content": "Full post content here.",
    "url": "https://joncamacho.com/writing/lawn-care-automation",
}


def _write_post_file(tmp_path):
    post_file = tmp_path / "post.json"
    post_file.write_text(json.dumps(POST_DATA), encoding="utf-8")
    return post_file


@patch("generator.on_publish.notify")
@patch("generator.on_publish.insert_topic_and_drafts", return_value=42)
@patch("generator.on_publish.generate_promo_drafts", return_value=["d1", "d2", "d3"])
@patch("generator.on_publish.update_voice_guide", return_value="updated voice guide")
@patch("generator.on_publish.get_connection")
def test_main_success(mock_conn, mock_update_voice, mock_gen_drafts, mock_insert, mock_notify, tmp_path):
    post_file = _write_post_file(tmp_path)
    conn = MagicMock()
    mock_conn.return_value = conn

    result = main(str(post_file))

    assert result == 0
    assert not post_file.exists()
    mock_update_voice.assert_called_once_with(POST_DATA)
    mock_gen_drafts.assert_called_once_with(POST_DATA, "updated voice guide")
    mock_insert.assert_called_once_with(conn, POST_DATA, ["d1", "d2", "d3"])
    conn.close.assert_called_once()
    mock_notify.assert_called_once()
    assert "3 LinkedIn drafts" in mock_notify.call_args[0][0]


@patch("generator.on_publish.notify")
@patch("generator.on_publish.insert_topic_and_drafts", return_value=42)
@patch("generator.on_publish.generate_promo_drafts", return_value=["d1", "d2", "d3"])
@patch("generator.on_publish.load_voice_guide", return_value="existing voice guide")
@patch("generator.on_publish.update_voice_guide", side_effect=Exception("voice update failed"))
@patch("generator.on_publish.get_connection")
def test_main_voice_update_failure_is_non_fatal(
    mock_conn, mock_update_voice, mock_load_voice, mock_gen_drafts, mock_insert, mock_notify, tmp_path
):
    post_file = _write_post_file(tmp_path)
    conn = MagicMock()
    mock_conn.return_value = conn

    result = main(str(post_file))

    assert result == 0
    assert not post_file.exists()
    mock_load_voice.assert_called_once()
    mock_gen_drafts.assert_called_once_with(POST_DATA, "existing voice guide")
    assert mock_notify.call_count == 2


@patch("generator.on_publish.notify")
@patch("generator.on_publish.generate_promo_drafts", side_effect=Exception("draft generation failed"))
@patch("generator.on_publish.update_voice_guide", return_value="updated voice guide")
@patch("generator.on_publish.get_connection")
def test_main_draft_generation_failure_returns_1(mock_conn, mock_update_voice, mock_gen_drafts, mock_notify, tmp_path):
    post_file = _write_post_file(tmp_path)
    conn = MagicMock()
    mock_conn.return_value = conn

    result = main(str(post_file))

    assert result == 1
    assert not post_file.exists()
    conn.close.assert_called_once()
    mock_notify.assert_called_once()
    assert "failed" in mock_notify.call_args[0][0].lower()
