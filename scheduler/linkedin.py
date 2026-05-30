"""LinkedIn API — token validation and ugcPosts."""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

UGC_POSTS_URL = "https://api.linkedin.com/v2/ugcPosts"
ME_URL = "https://api.linkedin.com/v2/me"


class LinkedInTokenError(Exception):
    """Access token missing, expired, or invalid."""


class LinkedInPostError(Exception):
    """Post request failed."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def validate_token() -> None:
    """Raise LinkedInTokenError if token is missing or invalid."""
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not token:
        raise LinkedInTokenError("LINKEDIN_ACCESS_TOKEN not set")

    try:
        resp = requests.get(
            ME_URL,
            headers=_headers(token),
            timeout=15,
        )
    except requests.RequestException as exc:
        raise LinkedInTokenError(f"Could not reach LinkedIn API: {exc}") from exc

    if resp.status_code == 401:
        raise LinkedInTokenError("LinkedIn access token expired or invalid")
    if resp.status_code >= 400:
        raise LinkedInTokenError(
            f"LinkedIn token check failed with status {resp.status_code}"
        )


def post_to_linkedin(draft_text: str) -> tuple[str, str]:
    """
    Publish a post. Returns (post_id, post_url).
    Raises LinkedInTokenError or LinkedInPostError.
    """
    validate_token()

    token = os.environ["LINKEDIN_ACCESS_TOKEN"].strip()
    author = os.environ.get("LINKEDIN_PERSON_URN", "").strip()
    if not author:
        raise LinkedInPostError("LINKEDIN_PERSON_URN not set")

    if not author.startswith("urn:"):
        author = f"urn:li:person:{author}"

    body = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": draft_text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        resp = requests.post(
            UGC_POSTS_URL,
            headers=_headers(token),
            json=body,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise LinkedInPostError(f"Network error: {exc}") from exc

    if resp.status_code == 401:
        raise LinkedInTokenError("LinkedIn access token expired or invalid")

    if resp.status_code >= 400:
        raise LinkedInPostError(
            f"LinkedIn post failed ({resp.status_code}): {resp.text[:500]}"
        )

    post_id = resp.headers.get("X-Restli-Id") or resp.headers.get("x-restli-id")
    if not post_id and resp.text:
        try:
            data = resp.json()
            post_id = data.get("id")
        except ValueError:
            post_id = None

    if not post_id:
        raise LinkedInPostError("LinkedIn post succeeded but no post ID returned")

    post_url = f"https://www.linkedin.com/feed/update/{post_id}"
    return post_id, post_url
