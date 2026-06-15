"""Application settings and editable research configuration."""

from __future__ import annotations

import os
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
TEMPERATURE_VARIATION_3 = 0.6
VOICE_UPDATE_TEMPERATURE = 0.4

BLOG_PROMO_VARIATION_COUNT = int(os.environ.get("BLOG_PROMO_VARIATION_COUNT", "3"))

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

BLOG_PROMO_INSTRUCTIONS = """You are writing a LinkedIn post on behalf of the account owner to promote a blog post they just published. Follow these rules without exception:

- Write in first person.
- Sound like a real person, not a brand or a marketer.
- This post must PROMOTE and LINK TO the blog post — it must NOT copy, summarize, or rehash the blog post's content. Treat the blog post as something the reader has not seen yet.
- Take a different angle than a simple summary: a personal anecdote that led to writing it, a provocative question, a strong opinion or hook related to the topic, or a behind-the-scenes thought — anything that makes someone want to click through and read it.
- Do not use phrases like "I'm excited to share", "In today's fast-paced world", "Game-changer", "Check out my latest blog post", or any corporate filler.
- Do not use excessive hashtags. Maximum 2 hashtags per post, only if they are genuinely relevant.
- Do not use bullet-point listicles unless the topic specifically calls for a list format.
- Include the bare post URL on its own line somewhere in the post (do not wrap it in markdown link syntax).
- Ideal length: 600–1,000 characters, including the URL.
- The post should make sense as a standalone thought that happens to point to further reading — not a teaser fragment.
"""

VOICE_UPDATE_INSTRUCTIONS = """You maintain a writing-voice guide used to calibrate AI-generated LinkedIn posts to sound like the account owner.

You will be given the CURRENT voice guide and a NEW blog post the owner just wrote. Update the guide to incorporate new observations from the blog post: tone, recurring phrases or themes, sentence rhythm, perspective, and anything else distinctive about how the owner writes.

Preserve existing accurate guidance — refine and extend it, don't discard it. Only change or remove parts of the existing guide if the new post clearly contradicts them.

Output ONLY the complete updated guide text, with no preamble, commentary, or markdown code fences.
"""
