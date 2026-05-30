# Macho's Content Engine (Backend)

Backend for the LinkedIn Content Engine: research, LLM drafts, scheduling, and posting. **Authoritative spec:** [BUILD_BRIEF.md](BUILD_BRIEF.md) — keep it updated when code changes.

## Architecture

This system is built around a mandatory human review constraint: **every single post must be reviewed and approved by Jon before it is scheduled for publishing. No exceptions.**

The backend consists of four core components:

1. **Topic Queue (SQLite):** The central data store. Topics: `suggested` → `pending` → `drafted` → `scheduled` → `posted` (or `skipped`). Drafts: `awaiting_review` → `approved` → `posted`.
2. **Research Engine (`scanner.py`):** Runs weekly to pull suggested topics from external sources (Google News, Reddit, Hacker News, newsletters) and inserts them into the queue.
3. **Draft Generator (`draft.py`):** Runs 2x/week. Pulls pending topics from the queue, uses an LLM (with Jon's voice guide) to generate draft variations, and alerts Jon via Mattermost.
4. **Scheduler and Poster (`poster.py`):** Runs every 30 minutes. Checks for approved posts that are due, posts them to LinkedIn, and alerts Jon via Mattermost.

*Note: The UI for reviewing drafts and managing the queue lives in a separate repository (`machos-hub-ui`).*

## Prerequisites

- Python 3.11+
- A LinkedIn Developer App with OAuth 2.0 credentials
- Anthropic API key (for Claude) or OpenAI API key (for GPT-4)
- A Mattermost incoming webhook URL for notifications
- Jon's Voice Guide document (generated from journal entries, stored locally, NOT committed to version control)

## Setup

1. Clone this repository.
2. Create a virtual environment: `python3 -m venv venv && source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your credentials.
5. Initialize the database: `python scripts/init_db.py`
6. Set up the cron jobs (see `config/crontab.example`).

## Staging vs. Production

This system has a strict staging mode. By default, `PRODUCTION_MODE=false` in your `.env` file. 

When `PRODUCTION_MODE=false`, the scheduler will process approved posts but will write them to a log file instead of calling the LinkedIn API. It will also send a Mattermost alert confirming the staging post.

You must manually set `PRODUCTION_MODE=true` only after validating the full pipeline.

## Voice Guide Calibration

The draft generator does **not** read journal files directly. You run a one-time calibration (your journals + an LLM session) to produce `config/voice_guide.txt`. That file is loaded on every draft run and prepended to the system prompt.

```bash
cp config/voice_guide.txt.example config/voice_guide.txt
# Edit voice_guide.txt with your calibrated voice (from journal work)
```

The file is gitignored and must live on the server before `generator/draft.py` will run.

## Local development

Run all commands from the repository root:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
pytest
python research/scanner.py
```

Point `machos-hub-ui` at `db/queue.db` via `DB_PATH` when running the UI alongside this repo.

## Tuning topic research

Edit files under `config/` (no code deploy needed; takes effect on the next Sunday scan):

| File | Purpose |
|------|---------|
| `keywords.txt` | Phrases for scoring and filtering |
| `reddit_subreddits.txt` | Subreddits to scan (no `r/` prefix) |
| `newsletter_rss.txt` | RSS feed URLs (one per line) |
| `research_sources.txt` | Enable/disable sources (`google_news`, `reddit`, `hacker_news`, `newsletter_rss`) |

Optional `.env` overrides: `KEYWORDS`, `REDDIT_SUBREDDITS`, `NEWSLETTER_RSS_FEEDS`, `RESEARCH_SOURCES` (comma-separated).

## Topic and draft lifecycle

- **Manual topics:** Add in the UI with `pending`; draft job picks by `sort_order`.
- **Research:** Scanner inserts `suggested`; accept in UI → `pending`.
- **Review:** Approve one of two draft versions → topic `scheduled`, draft `approved` with `scheduled_for`.
- **Post:** `poster.py` publishes due approved drafts; staging mode logs to `logs/staging_posts.log`.
