# Build Brief: Macho's Content Engine

This document is the authoritative specification for the LinkedIn Content Engine (backend + hub UI). It describes **what is implemented** in the repositories under [machos-automations-personal-builds](https://github.com/machos-automations-personal-builds).

**Spec maintenance:** When implementation changes, update this file in the same change (or immediately after). `PROJECT_CONTEXT.md` is background only; this brief is the source of truth for behavior and layout.

**Repositories:**
- Backend: `linkedin-posts-automation` (GitHub repo of the same name)
- UI: `machos-hub-ui`

---

## What This System Does

Automates research, drafting, scheduling, and posting of LinkedIn content at ~2 posts per week. The owner reviews and approves every draft before it is scheduled. Nothing is posted without explicit human approval.

**Manual-first:** Topics can be added in the UI without using the research scanner. Research suggestions require **Accept** before entering the draft queue.

---

## Hard Constraints

- **Every post must be approved by the owner before it is scheduled.** No auto-approve. No timeout. No fallback posting.
- **`PRODUCTION_MODE` defaults to false.** When false, the scheduler logs posts to a file instead of calling LinkedIn. Set to true only after staging validation.
- **No secrets in git.** Credentials live in `.env` on the server (gitignored).
- **Voice guide is not in git.** `config/voice_guide.txt` is generated from the owner's writing (e.g. journal calibration) and loaded at draft time. The app does not ingest journal files automatically.

---

## Repository Structure (backend: `linkedin-posts-automation`)

```
linkedin-posts-automation/
├── README.md
├── BUILD_BRIEF.md              # This file
├── PROJECT_CONTEXT.md          # Background for builders (not behavioral spec)
├── .env.example
├── .gitignore
├── requirements.txt
├── pytest.ini
├── config/
│   ├── settings.py             # Fixed constants + loaders for research config
│   ├── keywords.txt            # Editable keyword list (committed defaults)
│   ├── reddit_subreddits.txt   # Editable subreddit list
│   ├── newsletter_rss.txt      # Editable RSS URLs (may start empty)
│   ├── research_sources.txt    # Enable/disable sources (one per line)
│   ├── crontab.example
│   ├── voice_guide.txt         # GITIGNORED — private, from owner calibration
│   └── voice_guide.txt.example
├── db/
│   └── queue.db                # GITIGNORED — created by init_db.py
├── logs/                       # GITIGNORED — staging_posts.log, cron logs
├── scripts/
│   ├── init_db.py
│   └── health_check.py
├── research/
│   ├── scanner.py              # Cron entrypoint
│   ├── fetchers.py             # Google News, Reddit, HN, newsletters
│   └── scoring.py              # Keyword score + deduplication
├── generator/
│   ├── draft.py                # Cron entrypoint
│   └── llm.py                  # Anthropic primary, OpenAI fallback
├── scheduler/
│   ├── poster.py               # Cron entrypoint
│   └── linkedin.py             # Token check + ugcPosts
├── utils/
│   ├── db.py                   # Connection + WAL
│   ├── notify.py               # Mattermost webhook
│   ├── transitions.py          # Topic/draft status changes (backend)
│   ├── config_loaders.py       # Line-based config + env overrides
│   └── paths.py                # Repo root on sys.path for scripts
└── tests/
    ├── conftest.py
    ├── test_scanner.py
    ├── test_fetchers.py
    ├── test_draft.py
    ├── test_llm.py
    ├── test_poster.py
    ├── test_linkedin.py
    └── test_transitions.py
```

Run cron scripts from the **repository root** (or ensure repo root is on `PYTHONPATH`; `utils/paths.py` handles this for script entrypoints).

---

## Hub UI (`machos-hub-ui`)

```
machos-hub-ui/
├── README.md
├── .env.example
├── app.py                      # Flask app + routes
├── lib/
│   ├── schedule.py             # scheduled_for (Tue/Thu windows, America/Chicago)
│   └── transitions.py          # Same lifecycle rules as backend utils/transitions.py
├── templates/
│   ├── base.html               # Nav: Review | Queue with counts
│   ├── review.html             # One drafted topic, two variations
│   └── queue.html              # Your queue + Suggestions
├── static/style.css
└── tests/test_schedule.py
```

**Connection:** Reads/writes the same SQLite file as the backend via `DB_PATH` (absolute path on server). Uses `PRAGMA journal_mode=WAL` and `busy_timeout=5000` for concurrent cron + UI access.

**Auth:** HTTP Basic Auth (`UI_USERNAME`, `UI_PASSWORD`). Not for public internet without TLS and a strong password or fronting proxy (Tailscale, Cloudflare Access, nginx).

### Routes

| Route | Method | Behavior |
|-------|--------|----------|
| `/` | GET | Redirect to `/review` if drafted topics await review; else `/queue` |
| `/review` | GET | Oldest `drafted` topic with `awaiting_review` drafts; Version 1 & 2 cards |
| `/review/<draft_id>/approve` | POST | Optional edited `draft_text`; sets `scheduled_for`; topic → `scheduled`; sibling draft → `rejected` |
| `/review/<topic_id>/skip` | POST | Topic → `pending`; `awaiting_review` drafts → `rejected` |
| `/review/<topic_id>/regenerate` | POST | Same as skip; owner waits for next `draft.py` cron (no inline LLM) |
| `/queue` | GET | Manual `pending` topics + `suggested` topics |
| `/queue/add` | POST | New manual topic → `pending` |
| `/queue/<id>/edit` | POST | Edit manual pending topic text |
| `/queue/<id>/delete` | POST | Manual pending → `skipped` |
| `/queue/reorder` | POST | Comma-separated topic IDs → `sort_order` |
| `/queue/<id>/accept` | POST | `suggested` → `pending` |
| `/queue/<id>/dismiss` | POST | `suggested` → `skipped` |

**UI copy:** End users see labels like "In your queue" and "Suggestion", not raw DB status strings on drafts (shown as Version 1 / Version 2).

---

## Topic and Draft Lifecycle (implemented)

### Topics (`topics.status`)

| Status | Meaning |
|--------|---------|
| `suggested` | Inserted by scanner; not drafted until accepted |
| `pending` | In queue for `draft.py` (manual or accepted suggestion) |
| `drafted` | Draft job ran; awaiting review in UI |
| `scheduled` | Owner approved one variation; waiting for post time |
| `posted` | Parent topic published (poster success) |
| `skipped` | Dismissed suggestion or removed manual topic |

There is **no** `approved` status on topics (approval is tracked on drafts).

```text
manual add ──► pending
scanner ──► suggested ──accept──► pending ──draft.py──► drafted
                                              └──skip/regenerate──► pending
drafted ──approve in UI──► scheduled ──poster──► posted
suggested ──dismiss──► skipped
```

### Drafts (`drafts.status`)

| Status | Meaning |
|--------|---------|
| `awaiting_review` | Generated; shown as Version 1 / 2 |
| `approved` | Chosen variation; has `scheduled_for` |
| `rejected` | Sibling variation or skip/regenerate |
| `posted` | Published (staging log or LinkedIn) |
| `failed` | Production post failed 3 times |

On **approve:** one draft → `approved` + `scheduled_for`; other `awaiting_review` on same topic → `rejected`; topic → `scheduled`.

On **post success (staging or production):** draft → `posted`; **topic** → `posted`.

On **LinkedIn token invalid:** skip post, Mattermost alert, draft stays `approved`, `failure_count` unchanged.

On **post error (not token):** increment `failure_count`; at 3 → draft `failed`, Mattermost escalation.

---

## Database Schema

### Table: `topics`

| Field | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| text | TEXT NOT NULL | Topic text |
| source | TEXT NOT NULL | `manual` or source id (`google_news`, `reddit`, etc.) |
| source_url | TEXT | Link (suggested topics) |
| source_summary | TEXT | Short context (suggested topics) |
| status | TEXT NOT NULL | See lifecycle above |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | |
| updated_at | DATETIME DEFAULT CURRENT_TIMESTAMP | Updated on status changes |
| sort_order | INTEGER DEFAULT 0 | Manual queue ordering (lower first) |

### Table: `drafts`

| Field | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| topic_id | INTEGER NOT NULL | FK → topics.id |
| draft_text | TEXT NOT NULL | Post body (editable on approve) |
| variation | INTEGER NOT NULL | 1 or 2 |
| status | TEXT NOT NULL | See lifecycle above |
| approved_at | DATETIME | Set on approve |
| scheduled_for | DATETIME | UTC; set on approve by UI |
| posted_at | DATETIME | Set on successful post |
| linkedin_post_id | TEXT | From LinkedIn `X-Restli-Id` or response |
| failure_count | INTEGER DEFAULT 0 | Production post retries |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | |

---

## Editable Research Configuration

Research inputs are **owner-editable without code changes**. Optional `.env` comma-separated values **override** the file when set.

| File / env | Purpose | Default |
|------------|---------|---------|
| `config/keywords.txt` / `KEYWORDS` | Scoring + Google News queries + HN search | 8 phrases in BUILD_BRIEF history |
| `config/reddit_subreddits.txt` / `REDDIT_SUBREDDITS` | Subreddits (no `r/` prefix) | entrepreneur, smallbusiness, automation, artificial |
| `config/newsletter_rss.txt` / `NEWSLETTER_RSS_FEEDS` | RSS URLs | Empty until owner adds |
| `config/research_sources.txt` / `RESEARCH_SOURCES` | Enabled sources | google_news, reddit, hacker_news, newsletter_rss |

Loaders: `config/settings.py` → `load_keywords()`, `load_reddit_subreddits()`, `load_newsletter_rss_feeds()`, `load_enabled_research_sources()`.

---

## Component 1: Research Engine

**Entrypoint:** `research/scanner.py`  
**Trigger:** Cron Sunday 6:00am CT (`config/crontab.example`)

**Fetchers (`research/fetchers.py`):**

| Source id | Implementation |
|-----------|----------------|
| `google_news` | Google News RSS per keyword (`feedparser`) |
| `reddit` | `https://www.reddit.com/r/{sub}/hot.json` per `reddit_subreddits.txt` |
| `hacker_news` | Algolia `https://hn.algolia.com/api/v1/search` per keyword |
| `newsletter_rss` | `feedparser` on each URL in `newsletter_rss.txt` |

**Processing (`research/scoring.py` + `scanner.insert_topic`):**
1. Pull items from each **enabled** source (see `research_sources.txt`).
2. Score: keyword match count in title + summary; minimum 1.
3. Dedupe: existing `source_url`, or text similarity ≥ 80% (token overlap).
4. Insert with `status = 'suggested'`, `source` = source id.
5. Log inserts per source; continue on per-source errors.
6. If **all** enabled sources fail → Mattermost alert.
7. If any inserts → Mattermost: `Weekly research scan complete. [N] new topics added.`

---

## Component 2: Draft Generator

**Entrypoints:** `generator/draft.py`, `generator/llm.py`  
**Trigger:** Cron Monday and Thursday 8:00am CT

**Voice guide:** `config/voice_guide.txt` (not journals). One-time calibration produces this file; `draft.py` calls `load_voice_guide()` each run. Missing file → error exit + Mattermost.

**Topic selection:** `status = 'pending'` only, `ORDER BY sort_order ASC, created_at ASC LIMIT 1`.

**LLM:**
- Primary: Anthropic `claude-3-5-sonnet-20241022` (`ANTHROPIC_API_KEY`)
- Fallback per variation: OpenAI `gpt-4o` (`OPENAI_API_KEY`)
- Temperature: 0.7 (v1), 0.85 (v2)

**Prompt:** `voice_guide` + `LINKEDIN_POST_INSTRUCTIONS` (in `settings.py`) + topic text + optional `source_summary` / `source_url`.

**Success:** Two drafts `awaiting_review`; topic → `drafted`; Mattermost with `UI_URL`.

**Failure:** Wait 60s, retry once; if still failing → Mattermost, topic stays `pending`, no drafts committed.

---

## Component 3: Scheduler and Poster

**Entrypoints:** `scheduler/poster.py`, `scheduler/linkedin.py`  
**Trigger:** Cron every 30 minutes

**Due drafts:** `status = 'approved'` AND `scheduled_for <= now` (UTC).

**Staging (`PRODUCTION_MODE` false):** Append to `logs/staging_posts.log`; draft + topic → `posted`; Mattermost staging message.

**Production (`PRODUCTION_MODE` true):**
1. `linkedin.validate_token()` via `GET https://api.linkedin.com/v2/me`
2. `POST https://api.linkedin.com/v2/ugcPosts` (see JSON below)
3. Success: `linkedin_post_id` from `X-Restli-Id`; draft + topic → `posted`
4. Token invalid: alert, skip (draft stays `approved`)
5. Other failure: `failure_count++`; at 3 → `failed` + escalation Mattermost

**Posting window (UI on approve):** Implemented in `machos-hub-ui/lib/schedule.py` — Tuesday/Thursday, 8–10 or 12–14 America/Chicago, random minute, avoid double-booking same week, store UTC in `scheduled_for`.

---

## LinkedIn API Integration

**Env:** `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` (full `urn:li:person:…` or bare id normalized in code)

**Post body:**
```json
{
  "author": "urn:li:person:{LINKEDIN_PERSON_URN}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": { "text": "{POST_TEXT}" },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

**Headers:** `Authorization: Bearer …`, `Content-Type: application/json`, `X-Restli-Protocol-Version: 2.0.0`

OAuth refresh is **manual** (re-auth, update `.env`). No automated token refresh script in repo.

---

## Component 4: Health Check

**Entrypoint:** `scripts/health_check.py`  
**Trigger:** Cron daily 7:00am CT

Checks: database reachable; `MATTERMOST_WEBHOOK_URL` set; imports for scanner, draft, poster. Failure → Mattermost `Health check failed: …`.

---

## Cron Schedule

`TZ=America/Chicago`. Commands run from repo root (see `config/crontab.example`):

| Job | Command | Schedule |
|-----|---------|----------|
| Research | `python research/scanner.py` | `0 6 * * 0` |
| Draft | `python generator/draft.py` | `0 8 * * 1,4` |
| Post | `python scheduler/poster.py` | `*/30 * * * *` |
| Health | `python scripts/health_check.py` | `0 7 * * *` |

---

## Environment Variables (backend `.env`)

| Variable | Required | Notes |
|----------|----------|-------|
| `PRODUCTION_MODE` | No | Default false |
| `ANTHROPIC_API_KEY` | For drafts | Primary LLM |
| `OPENAI_API_KEY` | No | Fallback LLM |
| `LINKEDIN_ACCESS_TOKEN` | Production post | |
| `LINKEDIN_PERSON_URN` | Production post | |
| `MATTERMOST_WEBHOOK_URL` | Yes for alerts | Health check expects it |
| `UI_URL` | No | Draft-ready links (default localhost) |
| `DB_PATH` | No | Default `db/queue.db` |
| `KEYWORDS`, `REDDIT_SUBREDDITS`, etc. | No | Override config files |

Hub UI `.env`: `DB_PATH`, `UI_USERNAME`, `UI_PASSWORD`, `SECRET_KEY`, optional `FLASK_*`.

---

## Mattermost Notifications

Via `utils/notify.py` → `MATTERMOST_WEBHOOK_URL`. If unset, logs to stderr (no crash).

| Event | Message pattern |
|-------|-----------------|
| New draft ready | `New draft ready for review: [topic] — [UI_URL]` |
| Post live | `Post live on LinkedIn: [url]` |
| Staging post | `[STAGING] Post logged (not sent to LinkedIn): [snippet]` |
| Post failed 3× | `POST FAILED after 3 attempts… Draft ID: [id]` |
| LinkedIn token | `LinkedIn token expired. Re-authentication required…` |
| Queue empty | `Content queue is empty. Add topics to continue.` |
| Scan complete | `Weekly research scan complete. [N] new topics added.` |
| All sources failed | `Research scan failed: all sources unreachable. Check logs.` |
| Health check | `Health check failed: [component] — [detail]` |
| Draft / voice failure | As implemented in `draft.py` |

---

## Staging Validation Checklist

Before `PRODUCTION_MODE=true`:

- [ ] `init_db.py` creates schema including `failure_count`
- [ ] Manual topic in UI → `pending` in DB
- [ ] `scanner.py` inserts `suggested` topics
- [ ] Accept in UI → `pending`
- [ ] `voice_guide.txt` present; `draft.py` creates two real drafts
- [ ] Mattermost on draft ready
- [ ] Approve in UI → `scheduled_for` on Tue/Thu window
- [ ] `poster.py` staging → `logs/staging_posts.log`, topic + draft `posted`
- [ ] LLM retry behavior verified
- [ ] LinkedIn failure / token behavior verified in production dry runs
- [ ] `PRODUCTION_MODE=false` for all of the above

---

## `.gitignore` (backend)

```
.env
config/voice_guide.txt
db/queue.db
db/*.db-shm
db/*.db-wal
logs/
venv/
__pycache__/
*.pyc
*.pyo
.DS_Store
```
