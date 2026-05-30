"""LLM module tests (mocked APIs)."""

from unittest.mock import MagicMock, patch

import pytest

from generator.llm import LLMError, generate_variation


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "key", "OPENAI_API_KEY": ""})
@patch("generator.llm._generate_anthropic")
def test_generate_variation_anthropic(mock_anthropic):
    mock_anthropic.return_value = "Post text here."
    result = generate_variation("system prompt", 1)
    assert result == "Post text here."
    mock_anthropic.assert_called_once()


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": "key"})
@patch("generator.llm._generate_anthropic", side_effect=LLMError("no anthropic"))
@patch("generator.llm._generate_openai")
def test_generate_variation_openai_fallback(mock_openai, _mock_a):
    mock_openai.return_value = "Fallback post."
    result = generate_variation("system prompt", 2)
    assert result == "Fallback post."


@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "OPENAI_API_KEY": ""})
def test_generate_variation_all_fail():
    with pytest.raises(LLMError):
        generate_variation("prompt", 1)
