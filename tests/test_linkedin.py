"""LinkedIn client tests (mocked HTTP)."""

from unittest.mock import patch

import pytest

from scheduler.linkedin import LinkedInPostError, LinkedInTokenError, post_to_linkedin


@patch.dict(
    "os.environ",
    {
        "LINKEDIN_ACCESS_TOKEN": "test-token",
        "LINKEDIN_PERSON_URN": "urn:li:person:abc123",
    },
)
@patch("scheduler.linkedin.requests.get")
@patch("scheduler.linkedin.requests.post")
def test_post_success(mock_post, mock_get):
    mock_get.return_value.status_code = 200
    mock_post.return_value.status_code = 201
    mock_post.return_value.headers = {"X-Restli-Id": "urn:li:share:999"}
    mock_post.return_value.text = ""

    post_id, url = post_to_linkedin("Hello LinkedIn")
    assert post_id == "urn:li:share:999"
    assert "999" in url


@patch.dict("os.environ", {"LINKEDIN_ACCESS_TOKEN": ""})
def test_post_missing_token():
    with pytest.raises(LinkedInTokenError):
        post_to_linkedin("text")


@patch.dict("os.environ", {"LINKEDIN_ACCESS_TOKEN": "bad"})
@patch("scheduler.linkedin.requests.get")
def test_post_token_401(mock_get):
    mock_get.return_value.status_code = 401
    with pytest.raises(LinkedInTokenError):
        post_to_linkedin("text")
