# Macho's Content Engine (Backend)

This is the backend repository for the Macho's Automations Content Engine. It handles the automated research, draft generation, and scheduling of LinkedIn posts.

## Architecture

This system is built around a mandatory human review constraint: **every single post must be reviewed and approved by Jon before it is scheduled for publishing. No exceptions.**

The backend consists of four core components:

1. **Topic Queue (SQLite):** The central data store. Topics and drafts flow through statuses: pending → drafted → approved → scheduled → posted.
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

Before the draft generator can produce quality output, you must run the voice calibration session using your private journal entries. The resulting `voice_guide.txt` file must be placed in the `config/` directory. It is explicitly ignored by git.
