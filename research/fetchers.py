"""External source fetchers for the research scanner."""

from __future__ import annotations

import logging
import time
from urllib.parse import quote_plus

import feedparser
import requests

from config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "MachosContentEngine/1.0 (LinkedIn content research)"
REQUEST_TIMEOUT = 20
REDDIT_DELAY = 1.0  # polite delay between subreddit requests


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _entry_text(title: str, summary: str = "") -> str:
    title = (title or "").strip()
    if summary:
        summary = summary.strip()
        if summary and summary not in title:
            return f"{title} — {summary[:300]}"
    return title


def fetch_google_news() -> list[dict]:
    keywords = settings.load_keywords()
    if not keywords:
        return []

    session = _session()
    items: list[dict] = []
    seen_urls: set[str] = set()

    for keyword in keywords[:8]:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(keyword)}&hl=en-US&gl=US&ceid=US:en"
        )
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except requests.RequestException as exc:
            logger.warning("Google News RSS failed for %r: %s", keyword, exc)
            continue

        for entry in feed.entries[:15]:
            link = entry.get("link") or entry.get("id")
            if not link or link in seen_urls:
                continue
            seen_urls.add(link)
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            if hasattr(summary, "__len__") and len(summary) > 500:
                summary = summary[:500]
            text = _entry_text(title, summary)
            if len(text) < 10:
                continue
            items.append(
                {
                    "text": text,
                    "source_url": link,
                    "source_summary": summary[:500] if summary else None,
                }
            )

    logger.info("Google News: fetched %d raw items", len(items))
    return items


def fetch_reddit() -> list[dict]:
    subreddits = settings.load_reddit_subreddits()
    if not subreddits:
        return []

    session = _session()
    items: list[dict] = []

    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Reddit fetch failed for r/%s: %s", sub, exc)
            time.sleep(REDDIT_DELAY)
            continue

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("stickied") or post.get("over_18"):
                continue
            title = post.get("title", "")
            selftext = (post.get("selftext") or "")[:400]
            permalink = post.get("permalink", "")
            link = f"https://www.reddit.com{permalink}" if permalink else None
            text = _entry_text(title, selftext)
            items.append(
                {
                    "text": text,
                    "source_url": link,
                    "source_summary": f"r/{sub}" + (f" — {selftext[:200]}" if selftext else ""),
                }
            )

        time.sleep(REDDIT_DELAY)

    logger.info("Reddit: fetched %d raw items", len(items))
    return items


def fetch_hacker_news() -> list[dict]:
    keywords = settings.load_keywords()
    if not keywords:
        return []

    session = _session()
    items: list[dict] = []
    seen_urls: set[str] = set()

    for keyword in keywords[:8]:
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": keyword,
            "tags": "story",
            "hitsPerPage": 20,
        }
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("HN search failed for %r: %s", keyword, exc)
            continue

        for hit in data.get("hits", []):
            story_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if story_url in seen_urls:
                continue
            seen_urls.add(story_url)
            title = hit.get("title", "")
            text = _entry_text(title)
            items.append(
                {
                    "text": text,
                    "source_url": story_url,
                    "source_summary": hit.get("story_text", "")[:300] or None,
                }
            )

    logger.info("Hacker News: fetched %d raw items", len(items))
    return items


def fetch_newsletters() -> list[dict]:
    feeds = settings.load_newsletter_rss_feeds()
    if not feeds:
        logger.info("Newsletters: no feeds configured")
        return []

    items: list[dict] = []
    seen_urls: set[str] = set()

    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.warning("Newsletter RSS failed for %s: %s", feed_url, exc)
            continue

        if getattr(parsed, "bozo", False) and not parsed.entries:
            logger.warning("Newsletter feed parse error: %s", feed_url)
            continue

        for entry in parsed.entries[:20]:
            link = entry.get("link") or entry.get("id")
            if not link or link in seen_urls:
                continue
            seen_urls.add(link)
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            if isinstance(summary, str) and len(summary) > 500:
                summary = summary[:500]
            text = _entry_text(title, summary)
            if len(text) < 10:
                continue
            items.append(
                {
                    "text": text,
                    "source_url": link,
                    "source_summary": (summary[:500] if summary else None)
                    or feed_url,
                }
            )

    logger.info("Newsletters: fetched %d raw items", len(items))
    return items
