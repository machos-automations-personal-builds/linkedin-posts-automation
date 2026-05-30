from config.settings import (
    load_enabled_research_sources,
    load_keywords,
    load_reddit_subreddits,
)
from research.scoring import score_item, similarity_ratio


def test_score_item():
    keywords = ["AI automation", "entrepreneur"]
    assert score_item("AI automation for SMBs", "", keywords) >= 1
    assert score_item("unrelated cats", "", keywords) == 0


def test_similarity_ratio():
    assert similarity_ratio("hello world foo", "hello world bar") >= 0.5


def test_load_keywords_non_empty():
    assert len(load_keywords()) >= 1


def test_load_reddit_subreddits():
    subs = load_reddit_subreddits()
    assert "entrepreneur" in subs


def test_load_enabled_sources():
    assert "google_news" in load_enabled_research_sources()
