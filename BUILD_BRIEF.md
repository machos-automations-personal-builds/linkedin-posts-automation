# Build Brief: Macho's Content Engine

This document is the authoritative specification for building the LinkedIn Content Engine. It contains everything needed to implement the system. Nothing outside this document should be assumed.

---

## What This System Does

Automates the research, drafting, scheduling, and posting of LinkedIn content at a rate of 2 posts per week. The owner reviews and approves every draft before it is scheduled. Nothing is ever posted without explicit human approval.

---

## Hard Constraints

- **Every post must be approved by the owner before it is scheduled.** No auto-approve. No timeout. No fallback posting.
- **PRODUCTION_MODE defaults to false.** When false, the scheduler logs posts to a file instead of calling LinkedIn. The owner manually sets this to true after staging validation.
- **No secrets are ever committed to the repository.** All credentials live in `.env` on the server. The `.env` file is in `.gitignore`.
- **The voice guide is never committed to the repository.** It is a private config file stored only on the server.

---

## Repository Structure

```
machos-content-engine/
├── README.md
├── BUILD_BRIEF.md
├── .env.example
├── .gitignore
├── requirements.txt
├── config/
│   ├── settings.py         # posting window, LLM model, keyword list, source list
│   └── voice_guide.txt     # GITIGNORED — private, generated from owner's writing
├── db/
│   └── queue.db            # SQLite database (auto-created by init_db.py)
├── scripts/
│   └── init_db.py          # One-time database setup
├── research/
│   └── scanner.py          # Research engine
├── generator/
│   └── draft.py            # LLM draft generation
├── scheduler/
│   └── poster.py           # LinkedIn posting logic
└── tests/
    ├── test_scanner.py
    ├── test_draft.py
    └── test_poster.py
```

The UI lives in a separate repository (`machos-hub-ui`) and connects to this system's SQLite database.

---

## Database Schema

### Table: `topics`

| Field | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| text | TEXT NOT NULL | The topic text |
| source | TEXT NOT NULL | "manual" or the name of the research source |
| source_url | TEXT | Link to the source article or post (suggested topics only) |
| source_summary | TEXT | Brief summary of the source (suggested topics only) |
| status | TEXT NOT NULL | suggested / pending / drafted / scheduled / posted / skipped |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | |
| updated_at | DATETIME DEFAULT CURRENT_TIMESTAMP | Updated on every status change |
| sort_order | INTEGER DEFAULT 0 | For manual reordering in the UI |

### Table: `drafts`

| Field | Type | Description |
|---|---|---|
| id | INTEGER PRIMARY KEY AUTOINCREMENT | |
| topic_id | INTEGER NOT NULL | Foreign key → topics.id |
| draft_text | TEXT NOT NULL | The generated or edited post text |
| variation | INTEGER NOT NULL | 1 or 2 |
| status | TEXT NOT NULL | awaiting_review / approved / rejected |
| approved_at | DATETIME | Set when owner approves |
| scheduled_for | DATETIME | Randomized time within the posting window, set on approval |
| posted_at | DATETIME | Actual post time, set after successful LinkedIn API call |
| linkedin_post_id | TEXT | Returned by LinkedIn API on success |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | |

---

## Component 1: Research Engine (`research/scanner.py`)

**Trigger:** Cron. Weekly, Sunday at 6:00am CT.

**Purpose:** Pull relevant topics from external sources and insert them into the topics table as suggestions.

**Data Sources:**

| Source | Method | Notes |
|---|---|---|
| Google News RSS | RSS feed, keyword-filtered | No API key required. Use `feedparser`. |
| Reddit | Reddit JSON API (`/r/subreddit/hot.json`) | No auth required for read. Subreddits: r/entrepreneur, r/smallbusiness, r/automation, r/artificial |
| Hacker News | Algolia HN Search API (`http://hn.algolia.com/api/v1/search`) | Free. Filter by keywords. |
| Newsletter RSS | RSS feeds defined in `config/settings.py` | Owner-configured list. |

**Keyword List (defined in `config/settings.py`):**
- "AI automation"
- "small business operations"
- "entrepreneur"
- "business systems"
- "fragmented tools"
- "workflow automation"
- "AI tools for business"
- "operational efficiency"

**Processing Logic:**
1. Pull raw items from each source.
2. Score each item: count keyword matches in title + summary. Minimum score of 1 to pass.
3. Deduplicate: skip if `source_url` already exists in the topics table, or if text similarity to an existing topic exceeds 80% (use simple token overlap, not embeddings).
4. Insert passing items into `topics` with `status = 'suggested'` and `source` set to the source name. The owner accepts suggestions in the UI to move them to `pending` before drafting.
5. Log the number of items inserted per source.
6. On individual source failure: log the error, continue with remaining sources.
7. On all sources failing: send a Mattermost alert.

**Output:** New rows in the topics table. No notification to the owner unless all sources fail.

---

## Component 2: Draft Generator (`generator/draft.py`)

**Trigger:** Cron. Monday and Thursday at 8:00am CT.

**Purpose:** Pull the next pending topic from the queue and generate 2 draft LinkedIn post variations using an LLM.

**Topic Selection Logic:**
- Query topics table for rows where `status = 'pending'`.
- Order by `sort_order ASC`, then `created_at ASC`.
- Manual topics (source = 'manual') are interleaved naturally by sort_order. There is no separate priority override — the owner controls priority by reordering in the UI.
- If no pending topics exist: send a Mattermost alert ("Content queue is empty. Add topics to continue.") and exit without error.

**LLM Configuration:**
- Primary: Claude (Anthropic API). Model: `claude-3-5-sonnet-20241022`.
- Fallback: GPT-4o (OpenAI API) if Anthropic call fails.
- Temperature: 0.7 for variation 1, 0.85 for variation 2.

**System Prompt Construction:**
The system prompt is assembled from three parts, in this order:
1. The contents of `config/voice_guide.txt` (the owner's private voice guide).
2. A fixed LinkedIn post instruction block (see below).
3. The topic text and any source context.

**Fixed LinkedIn Post Instruction Block:**
```
You are writing a LinkedIn post on behalf of the account owner. Follow these rules without exception:

- Write in first person.
- Sound like a real person, not a brand or a marketer.
- Do not use phrases like "I'm excited to share", "In today's fast-paced world", "Game-changer", or any corporate filler.
- Do not use excessive hashtags. Maximum 2 hashtags per post, only if they are genuinely relevant.
- Do not use bullet-point listicles unless the topic specifically calls for a list format.
- Maximum length: 1,500 characters. Ideal length: 800–1,200 characters.
- End with a thought, question, or observation — not a call to action.
- The post must stand alone as a complete thought. It is not a teaser.
```

**Draft Generation Process:**
1. Construct the full prompt.
2. Call the LLM API twice (two separate calls with different temperatures) to produce 2 variations.
3. Insert both drafts into the `drafts` table with `status = 'awaiting_review'`.
4. Update the topic's `status` to `'drafted'` and `updated_at` to now.
5. Send a Mattermost notification: `"New draft ready for review: [topic text truncated to 60 chars] — [UI URL]"`

**Failure Handling:**
- On LLM API failure: wait 60 seconds, retry once.
- If retry fails: send Mattermost alert, leave topic status as `'pending'`, exit.
- Log all errors with full traceback.

---

## Component 3: Scheduler and Poster (`scheduler/poster.py`)

**Trigger:** Cron. Every 30 minutes.

**Purpose:** Check for approved drafts that are due and post them to LinkedIn.

**Posting Logic:**
1. Query drafts table for rows where `status = 'approved'` AND `scheduled_for <= now (UTC)`.
2. For each due draft:
   a. Read `PRODUCTION_MODE` from environment.
   b. **If `PRODUCTION_MODE=false`:** Write post text to `logs/staging_posts.log` with timestamp. Update draft `status` to `'posted'`, set `posted_at` to now. Send Mattermost notification: `"[STAGING] Post logged (not sent to LinkedIn): [first 60 chars]"`
   c. **If `PRODUCTION_MODE=true`:** Call LinkedIn API (see LinkedIn API section below). On success: update `status` to `'posted'`, set `posted_at` and `linkedin_post_id`. Send Mattermost notification: `"Post live on LinkedIn: [linkedin post URL]"`. On failure: log error, send Mattermost alert, leave `status` as `'approved'` for retry on next run.
3. After 3 consecutive failures on the same draft (track with a `failure_count` field or a separate log): escalate Mattermost alert, set `status` to `'failed'`, stop retrying automatically.

**Posting Window and Randomization:**
- Timezone: `America/Chicago` (use Python `zoneinfo` module, not hardcoded UTC offsets).
- Allowed posting days: Tuesday and Thursday.
- Allowed time windows: 8:00am–10:00am CT or 12:00pm–2:00pm CT.
- When a draft is approved via the UI, `scheduled_for` is calculated as follows:
  - Find the next occurrence of Tuesday or Thursday from today.
  - Pick one of the two time windows at random.
  - Pick a random minute within that window.
  - Convert to UTC and store in `scheduled_for`.
- If both Tuesday and Thursday of the current week already have a post scheduled, push to the following week.

---

## LinkedIn API Integration

**Authentication:** OAuth 2.0. The owner authenticates once via the LinkedIn Developer App. The resulting access token is stored in the `.env` file as `LINKEDIN_ACCESS_TOKEN`.

**Token Expiry:** LinkedIn access tokens expire after approximately 60 days. The system must check token validity before each post attempt. If the token is expired or invalid, skip the post, send a Mattermost alert ("LinkedIn token expired. Re-authentication required."), and set the draft back to `'approved'` status.

**Posting Endpoint:** `POST https://api.linkedin.com/v2/ugcPosts`

**Request Body:**
```json
{
  "author": "urn:li:person:{LINKEDIN_PERSON_URN}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "{POST_TEXT}"
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

**Required Headers:**
```
Authorization: Bearer {LINKEDIN_ACCESS_TOKEN}
Content-Type: application/json
X-Restli-Protocol-Version: 2.0.0
```

---

## Cron Schedule

All times are in CT. The server crontab should use the `TZ=America/Chicago` environment variable or equivalent.

| Job | Command | Schedule |
|---|---|---|
| Research scan | `python research/scanner.py` | `0 6 * * 0` (Sunday 6am) |
| Draft generation | `python generator/draft.py` | `0 8 * * 1,4` (Mon + Thu 8am) |
| Post scheduler | `python scheduler/poster.py` | `*/30 * * * *` (every 30 min) |
| Health check | `python scripts/health_check.py` | `0 7 * * *` (daily 7am) |

A `config/crontab.example` file should be included in the repo with these entries pre-filled.

---

## Mattermost Notifications

All notifications are sent via an incoming webhook. The webhook URL is stored in `.env` as `MATTERMOST_WEBHOOK_URL`.

A shared utility function `notify(message: str)` should live in `utils/notify.py` and be imported by all components.

| Event | Message |
|---|---|
| New draft ready | `"New draft ready for review: [topic] — [UI_URL]"` |
| Post live (production) | `"Post live on LinkedIn: [post URL]"` |
| Post logged (staging) | `"[STAGING] Post logged (not sent to LinkedIn): [first 60 chars]"` |
| Post failed (after 3 retries) | `"POST FAILED after 3 attempts. Manual intervention required. Draft ID: [id]"` |
| LinkedIn token expired | `"LinkedIn token expired. Re-authentication required before next post."` |
| Queue empty | `"Content queue is empty. Add topics to continue."` |
| Research scan complete | `"Weekly research scan complete. [N] new topics added."` |
| All research sources failed | `"Research scan failed: all sources unreachable. Check logs."` |
| Health check failure | `"Health check failed: [component] is not responding."` |

---

## Staging Validation Checklist

Before setting `PRODUCTION_MODE=true`, the following must be verified:

- [ ] `init_db.py` runs without error and creates the correct schema.
- [ ] A manual topic can be added via the UI and appears in the database.
- [ ] `scanner.py` runs and inserts suggested topics into the database.
- [ ] A suggested topic can be accepted via the UI and moves to pending status.
- [ ] `draft.py` runs and generates 2 draft variations for a pending topic.
- [ ] Mattermost notification is received when a draft is ready.
- [ ] Draft can be reviewed and approved in the UI.
- [ ] `scheduled_for` is set to a valid Tuesday or Thursday within the posting window.
- [ ] `poster.py` detects the approved draft and writes it to the staging log.
- [ ] Mattermost staging notification is received.
- [ ] Failure handling: manually break the LLM API call and confirm the retry + alert behavior.
- [ ] Failure handling: manually break the LinkedIn API call and confirm the 3-retry escalation.
- [ ] `PRODUCTION_MODE` is confirmed as `false` throughout all of the above.

---

## `.gitignore` Contents

```
.env
config/voice_guide.txt
db/queue.db
logs/
venv/
__pycache__/
*.pyc
*.pyo
.DS_Store
```
