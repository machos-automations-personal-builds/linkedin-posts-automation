# Project Context: Macho's Content Engine

This document gives the AI assistant building this system the full context it needs to make good decisions. Read this before reading the `BUILD_BRIEF.md`.

---

## Who This Is For

This system is built for Jon Camacho, who operates under the personal brand "Macho." Jon is building a consulting business that helps small and medium-sized businesses replace fragmented tools and manual processes with custom operational systems built using AI-assisted development.

Jon is not a full-time content creator. He has deep technical and operational expertise but limited interest in spending time on social media. The entire purpose of this system is to make consistent, high-quality LinkedIn presence achievable without requiring Jon to actively manage it day to day.

---

## Why This System Exists

Jon's core thesis — the idea he is building his public reputation around — is:

> "Most small businesses are drowning in fragmented tools and manual processes that AI can replace — but only if someone builds the right architecture around their specific operation."

To be taken seriously in this space over the next 3–5 years, Jon needs a consistent, specific, and authentic presence on LinkedIn. The problem is that creating content consistently is time-consuming and mentally taxing, especially for someone who is also doing real technical work.

This system solves that by handling the research, drafting, and scheduling automatically — while keeping Jon in full control of what actually gets published. He reviews every draft. He approves every post. The system is a tool that assists him, not one that speaks for him.

---

## What This System Is

A self-hosted, Python-based automation pipeline with four components:

1. A **research engine** that scans external sources weekly for topics relevant to Jon's areas of focus.
2. A **draft generator** that uses an LLM — calibrated to Jon's voice — to produce LinkedIn post drafts from those topics.
3. A **review and approval UI** (in a separate repository, `machos-hub-ui`) where Jon reads, edits, and approves drafts.
4. A **scheduler and poster** that publishes approved posts to LinkedIn at randomized times within optimal engagement windows.

---

## What This System Is Not

- It is not a marketing automation tool for clients. It is Jon's personal system.
- It is not a fully autonomous posting bot. Jon approves every post before it goes live. This is a hard constraint, not a preference.
- It is not a SaaS product. It runs on Jon's private server for Jon's use only.
- It does not manage comments, DMs, analytics, or any LinkedIn activity beyond creating posts.

---

## Relationship to the Broader Hub

This content engine is the first component of a larger personal operational hub Jon is building for himself. The UI repository (`machos-hub-ui`) is intentionally separate because it will eventually expand to include other tools — client management, project tracking, outreach management, and more. The content engine backend is one service that feeds into that hub. It should be built as a clean, self-contained service that does one thing well.

---

## Key Design Principles

**Human review is non-negotiable.** Every architectural decision should reinforce this. The system never posts without Jon's explicit approval. There is no auto-approve path.

**Staging before production.** The `PRODUCTION_MODE` flag defaults to false. The system must be fully testable without touching Jon's real LinkedIn profile.

**Private by default.** Jon's voice guide (derived from personal writing) is never committed to the repository. Credentials are never committed. The UI is not public-facing.

**Modular and maintainable.** Each component (research, generation, scheduling) is an independent script. They share a database but do not call each other. This makes them independently testable and independently replaceable.

**No over-engineering.** Jon posts twice a week. The system runs three cron jobs. It uses SQLite. It does not need a message queue, a microservices architecture, or a cloud database. Keep it simple and reliable.

---

## Voice and Tone

Jon's posts must sound like Jon — direct, knowledgeable, entrepreneurial, and grounded in real experience. Not corporate. Not hype. Not a generic LinkedIn influencer.

The voice is calibrated via a private `config/voice_guide.txt` file that is generated from Jon's personal writing before the system goes live. This file is the most important input to the draft generator. It is stored only on the server and is never committed to version control.

Until the voice guide exists, the draft generator should not be considered production-ready.

---

## Current Status

This repository contains the full specification (`BUILD_BRIEF.md`), the database initialization script, the environment variable template, the cron schedule template, and the project structure. The four core scripts (`scanner.py`, `draft.py`, `poster.py`, `health_check.py`) and the utility module (`utils/notify.py`) need to be implemented.

The UI is in a separate repository (`machos-hub-ui`) and is partially scaffolded. The Flask routes for draft review and topic queue management need to be implemented.
