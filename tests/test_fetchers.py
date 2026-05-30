"""Unit tests for fetcher helpers (no live network)."""

from unittest.mock import MagicMock, patch

from research.fetchers import _entry_text, fetch_google_news


def test_entry_text():
    assert "Title" in _entry_text("Title", "Summary bit")
    assert _entry_text("Only title", "") == "Only title"


@patch("research.fetchers._session")
def test_fetch_google_news_parses_feed(mock_session):
    mock_resp = MagicMock()
    mock_resp.content = b"""<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>AI automation for SMBs</title>
        <link>https://example.com/1</link>
        <description>Small business operations improve with AI tools for business.</description>
      </item>
    </channel></rss>"""
    mock_resp.raise_for_status = MagicMock()
    mock_session.return_value.get.return_value = mock_resp

    with patch("research.fetchers.settings.load_keywords", return_value=["AI automation"]):
        items = fetch_google_news()

    assert len(items) >= 1
    assert "AI automation" in items[0]["text"]
    assert items[0]["source_url"] == "https://example.com/1"
