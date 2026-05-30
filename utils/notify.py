"""Mattermost webhook notifications."""

from __future__ import annotations

import logging
import os
import sys

import requests

logger = logging.getLogger(__name__)


def notify(message: str) -> bool:
    url = os.environ.get("MATTERMOST_WEBHOOK_URL", "").strip()
    if not url:
        logger.warning("MATTERMOST_WEBHOOK_URL not set; notification skipped: %s", message)
        print(f"[notify] {message}", file=sys.stderr)
        return False

    try:
        resp = requests.post(url, json={"text": message}, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.exception("Failed to send Mattermost notification: %s", exc)
        print(f"[notify failed] {message}", file=sys.stderr)
        return False
