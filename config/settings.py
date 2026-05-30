"""Application settings and editable research configuration."""

from __future__ import annotations

from pathlib import Path

from utils.config_loaders import load_line_config

CONFIG_DIR = Path(__file__).resolve().parent
REPO_ROOT = CONFIG_DIR.parent

# --- Editable research (scanner) ---

DEFAULT_KEYWORDS = [
    "AI automation",
    "small business operations",
    "entrepreneur",
    "business systems",
    "fragmented tools",
    "workflow automation",
    "AI tools for business",
    "operational efficiency",
]

DEFAULT_REDDIT_SUBREDDITS = [
    "entrepreneur",
    "smallbusiness",
    "automation",
    "artificial",
]

DEFAULT_RESEARCH_SOURCES = [
    "google_news",
    "reddit",
    "hacker_news",
    "newsletter_rss",
]


def load_keywords() -> list[str]:
    return load_line_config("keywords.txt", "KEYWORDS", DEFAULT_KEYWORDS)


def load_reddit_subreddits() -> list[str]:
    return load_line_config(
        "reddit_subreddits.txt",
        "REDDIT_SUBREDDITS",
        DEFAULT_REDDIT_SUBREDDITS,
        normalize_lower=True,
    )


def load_newsletter_rss_feeds() -> list[str]:
    return load_line_config(
        "newsletter_rss.txt",
        "NEWSLETTER_RSS_FEEDS",
        [],
    )


def load_enabled_research_sources() -> set[str]:
    sources = load_line_config(
        "research_sources.txt",
        "RESEARCH_SOURCES",
        DEFAULT_RESEARCH_SOURCES,
        normalize_lower=True,
    )
    return set(sources)


# --- Fixed runtime constants ---

ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
OPENAI_MODEL = "gpt-4o"
TEMPERATURE_VARIATION_1 = 0.7
TEMPERATURE_VARIATION_2 = 0.85

TIMEZONE = "America/Chicago"
POSTING_DAYS = (1, 3)  # Tuesday=1, Thursday=3 (weekday())
POSTING_WINDOWS = ((8, 10), (12, 14))  # hours CT, inclusive start exclusive end handled in schedule

VOICE_GUIDE_PATH = CONFIG_DIR / "voice_guide.txt"
STAGING_LOG_PATH = REPO_ROOT / "logs" / "staging_posts.log"

LINKEDIN_POST_INSTRUCTIONS = """You are writing a LinkedIn post on behalf of the account owner. Follow these rules without exception:

- Write in first person.
- Sound like a real person, not a brand or a marketer.
- Do not use phrases like "I'm excited to share", "In today's fast-paced world", "Game-changer", or any corporate filler.
- Do not use excessive hashtags. Maximum 2 hashtags per post, only if they are genuinely relevant.
- Do not use bullet-point listicles unless the topic specifically calls for a list format.
- Maximum length: 1,500 characters. Ideal length: 800–1,200 characters.
- End with a thought, question, or observation — not a call to action.
- The post must stand alone as a complete thought. It is not a teaser.
"""
