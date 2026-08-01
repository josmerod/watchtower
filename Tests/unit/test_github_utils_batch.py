"""Unit tests for concurrent GitHub repo info batch fetching.

These tests verify the ThreadPoolExecutor-based ``get_github_repo_info_batch``
and the ``_GitHubRateLimiter`` without hitting the real GitHub API. All HTTP
calls are mocked.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.utils.github_utils import (
    _GitHubRateLimiter,
    get_github_repo_info,
    get_github_repo_info_batch,
)

# ---------------------------------------------------------------------------
# _GitHubRateLimiter
# ---------------------------------------------------------------------------


class TestGitHubRateLimiter:
    """Tests for the thread-safe rate limiter."""

    def test_update_parses_headers(self) -> None:
        """update() should parse X-RateLimit-* headers correctly."""
        limiter = _GitHubRateLimiter(safety_threshold=10)
        headers = {"X-RateLimit-Remaining": "4995", "X-RateLimit-Reset": "1700000000"}
        limiter.update(headers)
        assert limiter._remaining == 4995
        assert limiter._reset_epoch == 1700000000.0

    def test_update_ignores_garbage(self) -> None:
        """update() should silently ignore non-integer headers."""
        limiter = _GitHubRateLimiter()
        limiter.update({"X-RateLimit-Remaining": "not-a-number"})
        assert limiter._remaining is None

    def test_acquire_no_block_when_quota_available(self) -> None:
        """acquire() should return immediately when remaining > threshold."""
        limiter = _GitHubRateLimiter(safety_threshold=10)
        limiter._remaining = 100
        limiter._reset_epoch = time.time() + 3600
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Should not block

    def test_acquire_no_block_without_headers(self) -> None:
        """acquire() should be a no-op when no headers have been seen."""
        limiter = _GitHubRateLimiter()
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    def test_acquire_blocks_when_quota_exhausted(self) -> None:
        """acquire() should sleep until reset epoch when quota < threshold."""
        limiter = _GitHubRateLimiter(safety_threshold=10)
        limiter._remaining = 5  # Below threshold of 10
        limiter._reset_epoch = time.time() + 0.3  # Reset in 300ms
        start = time.monotonic()
        limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.25  # Should have slept ~0.3s


# ---------------------------------------------------------------------------
# get_github_repo_info_batch
# ---------------------------------------------------------------------------


def _make_mock_response(
    status_code: int = 200,
    stars: int = 42,
    languages: dict | None = None,
    remaining: str = "4990",
) -> MagicMock:
    """Create a mock requests.Response with GitHub-like data and headers."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = {
        "X-RateLimit-Remaining": remaining,
        "X-RateLimit-Reset": str(int(time.time()) + 3600),
    }
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} Error")
    resp.json.return_value = {
        "html_url": "https://github.com/test/repo",
        "description": "Test repo",
        "stargazers_count": stars,
        "forks_count": 3,
        "subscribers_count": 5,
        "open_issues_count": 1,
        "updated_at": "2024-01-01T00:00:00Z",
        "created_at": "2023-01-01T00:00:00Z",
        "language": "Python",
        "languages_url": "https://api.github.com/repos/test/repo/languages",
        "topics": ["ml", "ai"],
        "has_issues": True,
        "has_projects": False,
        "has_wiki": True,
        "has_pages": False,
        "default_branch": "main",
    }
    return resp


def _make_lang_response(status_code: int = 200) -> MagicMock:
    """Create a mock response for the languages endpoint."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = {"X-RateLimit-Remaining": "4988", "X-RateLimit-Reset": str(int(time.time()) + 3600)}
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"Python": 1000, "Shell": 50}
    return resp


class TestGetGitHubRepoInfoBatch:
    """Tests for the concurrent batch fetch function."""

    def test_empty_input_returns_empty(self) -> None:
        """Empty URL list should return empty dict without any HTTP calls."""
        result = get_github_repo_info_batch([])
        assert result == {}

    def test_single_url_success(self) -> None:
        """A single URL should fetch and return structured data."""
        repo_url = "https://github.com/test/repo"
        mock_resp = _make_mock_response(stars=99)
        mock_lang = _make_lang_response()

        with patch("src.utils.github_utils.requests.get", side_effect=[mock_resp, mock_lang]):
            result = get_github_repo_info_batch([repo_url])

        assert repo_url in result
        info = result[repo_url]
        assert info is not None
        assert info["github_stars"] == 99
        assert info["github_language"] == "Python"
        assert info["github_languages"] == {"Python": 1000, "Shell": 50}

    def test_multiple_urls_concurrent(self) -> None:
        """Multiple URLs should all appear in the result mapping."""
        urls = [
            "https://github.com/a/repo1",
            "https://github.com/b/repo2",
            "https://github.com/c/repo3",
        ]
        # Each repo needs 2 requests (repo info + languages)
        responses = []
        for i, _ in enumerate(urls):
            responses.append(_make_mock_response(stars=i * 10))
            responses.append(_make_lang_response())

        with patch("src.utils.github_utils.requests.get", side_effect=responses):
            result = get_github_repo_info_batch(urls)

        assert len(result) == 3
        assert result[urls[0]] is not None
        assert result[urls[0]]["github_stars"] == 0  # type: ignore[index]
        assert result[urls[1]] is not None
        assert result[urls[1]]["github_stars"] == 10  # type: ignore[index]
        assert result[urls[2]] is not None
        assert result[urls[2]]["github_stars"] == 20  # type: ignore[index]

    def test_duplicate_urls_deduplicated(self) -> None:
        """Duplicate URLs should be fetched only once and share results."""
        url = "https://github.com/test/repo"
        urls = [url, url, url]
        mock_resp = _make_mock_response(stars=77)
        mock_lang = _make_lang_response()

        with patch("src.utils.github_utils.requests.get", side_effect=[mock_resp, mock_lang]) as mock_get:
            result = get_github_repo_info_batch(urls)

        # Only 2 HTTP calls for 3 duplicate URLs (1 repo + 1 languages)
        assert mock_get.call_count == 2
        # Dict keys are unique, so 1 entry — but the result is correct
        assert len(result) == 1
        assert url in result
        assert result[url] is not None
        assert result[url]["github_stars"] == 77  # type: ignore[index]

    def test_failed_fetch_returns_none(self) -> None:
        """A 404 or network error should map to None, not crash."""
        url = "https://github.com/nonexistent/repo"
        error_resp = _make_mock_response(status_code=404)

        with patch("src.utils.github_utils.requests.get", return_value=error_resp):
            result = get_github_repo_info_batch([url])

        assert result[url] is None

    def test_partial_failure(self) -> None:
        """Mix of successful and failed fetches should not break the batch."""
        urls = ["https://github.com/ok/repo", "https://github.com/bad/repo"]
        ok_resp = _make_mock_response(stars=10)
        ok_lang = _make_lang_response()
        bad_resp = _make_mock_response(status_code=500)

        # The execution order depends on ThreadPoolExecutor scheduling, so we
        # use a flexible side_effect that returns responses per URL path
        def side_effect(url, **kwargs):
            if "ok" in url:
                # Alternate between repo info and languages based on call context
                if "languages" in url:
                    return ok_lang
                return ok_resp
            return bad_resp

        with patch("src.utils.github_utils.requests.get", side_effect=side_effect):
            result = get_github_repo_info_batch(urls)

        assert result[urls[0]] is not None
        assert result[urls[0]]["github_stars"] == 10  # type: ignore[index]
        assert result[urls[1]] is None

    def test_rate_limiter_integration(self) -> None:
        """The shared rate limiter should see updated headers after requests."""
        url = "https://github.com/test/repo"
        mock_resp = _make_mock_response(remaining="3500")
        mock_lang = _make_lang_response()

        with (
            patch("src.utils.github_utils.requests.get", side_effect=[mock_resp, mock_lang]),
            patch.object(_GitHubRateLimiter, "acquire") as mock_acquire,
            patch.object(_GitHubRateLimiter, "update") as mock_update,
        ):
            get_github_repo_info_batch([url])

        # acquire() should be called before each request
        assert mock_acquire.call_count == 2
        # update() should be called after each response
        assert mock_update.call_count == 2


# ---------------------------------------------------------------------------
# get_github_repo_info (single fetch with rate_limiter param)
# ---------------------------------------------------------------------------


class TestGetGitHubRepoInfoWithLimiter:
    """Verify the rate_limiter parameter on the single-fetch function."""

    def test_passes_rate_limiter(self) -> None:
        """When rate_limiter is provided, acquire/update should be called."""
        url = "https://github.com/test/repo"
        mock_resp = _make_mock_response()
        mock_lang = _make_lang_response()
        limiter = MagicMock(spec=_GitHubRateLimiter)

        with patch("src.utils.github_utils.requests.get", side_effect=[mock_resp, mock_lang]):
            get_github_repo_info(url, rate_limiter=limiter)

        assert limiter.acquire.call_count == 2
        assert limiter.update.call_count == 2

    def test_works_without_rate_limiter(self) -> None:
        """Backward compatibility: works fine without a rate_limiter."""
        url = "https://github.com/test/repo"
        mock_resp = _make_mock_response(stars=5)
        mock_lang = _make_lang_response()

        with patch("src.utils.github_utils.requests.get", side_effect=[mock_resp, mock_lang]):
            info = get_github_repo_info(url)

        assert info is not None
        assert info["github_stars"] == 5
