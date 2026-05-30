"""LLM draft generation — Anthropic primary, OpenAI fallback."""

from __future__ import annotations

import logging
import os

from config.settings import (
    ANTHROPIC_MODEL,
    OPENAI_MODEL,
    TEMPERATURE_VARIATION_1,
    TEMPERATURE_VARIATION_2,
)

logger = logging.getLogger(__name__)

VARIATION_TEMPS = {
    1: TEMPERATURE_VARIATION_1,
    2: TEMPERATURE_VARIATION_2,
}


class LLMError(Exception):
    """All LLM providers failed."""


def _generate_anthropic(system_prompt: str, variation: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY not set")

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    temperature = VARIATION_TEMPS.get(variation, TEMPERATURE_VARIATION_1)

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write LinkedIn post variation {variation} for the topic above. "
                    "Output only the post text, no preamble or labels."
                ),
            }
        ],
    )

    parts = []
    for block in message.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    text = "".join(parts).strip()
    if not text:
        raise LLMError("Anthropic returned empty content")
    if len(text) > 1500:
        text = text[:1500]
    return text


def _generate_openai(system_prompt: str, variation: int) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise LLMError("OPENAI_API_KEY not set")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    temperature = VARIATION_TEMPS.get(variation, TEMPERATURE_VARIATION_1)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=2048,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Write LinkedIn post variation {variation} for the topic above. "
                    "Output only the post text, no preamble or labels."
                ),
            },
        ],
    )

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise LLMError("OpenAI returned empty content")
    if len(text) > 1500:
        text = text[:1500]
    return text


def generate_variation(system_prompt: str, variation: int) -> str:
    """Try Anthropic, then OpenAI on failure."""
    errors: list[str] = []

    try:
        return _generate_anthropic(system_prompt, variation)
    except Exception as exc:
        logger.warning("Anthropic failed for variation %d: %s", variation, exc)
        errors.append(f"Anthropic: {exc}")

    try:
        return _generate_openai(system_prompt, variation)
    except Exception as exc:
        logger.warning("OpenAI failed for variation %d: %s", variation, exc)
        errors.append(f"OpenAI: {exc}")

    raise LLMError("; ".join(errors))
