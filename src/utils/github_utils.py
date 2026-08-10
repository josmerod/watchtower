"""Utilities for interacting with GitHub repositories.

This module provides functions to extract information from GitHub URLs,
fetch repository details via the GitHub API, and find GitHub repository
links within text content.
"""

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import requests

from src.utils.logging import get_logger

logger = get_logger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com/repos"

# Safety margin: pause when fewer than this many requests remain in the rate-limit window
_RATE_LIMIT_SAFETY_THRESHOLD = 10


class _GitHubRateLimiter:
    """Thread-safe rate limiter driven by GitHub's X-RateLimit-* response headers.

    Workers call ``update(headers)`` after every API response and ``acquire()`` before
    each request. When remaining quota drops below the safety threshold, ``acquire()``
    blocks until the reset epoch so threads automatically back off.
    """

    def __init__(self, safety_threshold: int = _RATE_LIMIT_SAFETY_THRESHOLD) -> None:
        self._lock = threading.Lock()
        self._threshold = safety_threshold
        self._remaining: int | None = None
        self._reset_epoch: float | None = None

    def update(self, headers: Any) -> None:
        """Parse rate-limit headers from a ``requests.Response`` and store them."""
        try:
            remaining = headers.get("X-RateLimit-Remaining")
            reset = headers.get("X-RateLimit-Reset")
            if remaining is not None:
                self._remaining = int(remaining)
            if reset is not None:
                self._reset_epoch = float(reset)
        except (ValueError, TypeError) as e:
            logger.debug(f"Could not parse rate-limit headers: {e}")

    def acquire(self) -> None:
        """Block the calling thread until it is safe to send another request."""
        with self._lock:
            if self._remaining is not None and self._remaining < self._threshold and self._reset_epoch is not None:
                wait_seconds = max(0.0, self._reset_epoch - time.time() + 1.0)
                if wait_seconds > 0:
                    logger.warning(f"GitHub rate limit nearly exhausted ({self._remaining} remaining). Pausing for {wait_seconds:.0f}s until reset.")
                    # Release lock during sleep so other threads can also queue up and wait
                    # We release and re-acquire to avoid holding the lock during the long sleep
                    self._lock.release()
                    try:
                        time.sleep(wait_seconds)
                    finally:
                        self._lock.acquire()
                    # Reset remaining so we don't re-sleep immediately after reset
                    self._remaining = None


def extract_github_owner_repo(url: str) -> tuple[str, str] | None:
    """Extracts the owner and repository name from a GitHub URL.

    Args:
        url (str): The GitHub URL.

    Returns:
        Optional[Tuple[str, str]]: A tuple containing (owner, repo_name)
                                     or None if the URL is not a valid GitHub repo URL.
    """
    parsed_url = urlparse(url)
    if parsed_url.hostname == "github.com":
        path_parts = [part for part in parsed_url.path.split("/") if part]
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
    return None


def get_github_repo_info(
    repo_url: str,
    github_token: str | None = None,
    rate_limiter: _GitHubRateLimiter | None = None,
) -> dict[str, Any] | None:
    """Fetches information about a GitHub repository using its URL.

    Args:
        repo_url (str): The full URL of the GitHub repository.
        github_token (str, optional): A GitHub personal access token for authenticated requests.
                                      Defaults to None (unauthenticated request).
        rate_limiter (optional): Shared rate limiter. When provided, each request
            first calls ``acquire()`` to respect GitHub quota, then updates the
            limiter with response headers. Defaults to None (no rate-limit coordination).

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing repository information
                                  (stars, forks, description, last_updated, languages, html_url)
                                  or None if an error occurs or the URL is invalid.
    """
    owner_repo = extract_github_owner_repo(repo_url)
    if not owner_repo:
        logger.warning(f"Invalid GitHub URL format: {repo_url}")
        return None

    owner, repo = owner_repo
    api_url = f"{GITHUB_API_BASE_URL}/{owner}/{repo}"

    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        if rate_limiter:
            rate_limiter.acquire()
        response = requests.get(api_url, headers=headers, timeout=10)
        if rate_limiter:
            rate_limiter.update(response.headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()

        # Fetch languages separately
        languages_url = data.get("languages_url")
        languages_data = {}
        if languages_url:
            if rate_limiter:
                rate_limiter.acquire()
            lang_response = requests.get(languages_url, headers=headers, timeout=5)
            if rate_limiter:
                rate_limiter.update(lang_response.headers)
            if lang_response.status_code == 200:
                languages_data = lang_response.json()
            else:
                logger.warning(f"Failed to fetch languages for {owner}/{repo}: {lang_response.status_code}")

        return {
            "github_html_url": data.get("html_url"),
            "github_description": data.get("description"),
            "github_stars": data.get("stargazers_count"),
            "github_forks": data.get("forks_count"),
            "github_watchers": data.get("subscribers_count"),  # 'subscribers_count' is often referred to as watchers
            "github_open_issues": data.get("open_issues_count"),
            "github_last_updated": data.get("updated_at"),
            "github_created_at": data.get("created_at"),
            "github_language": data.get("language"),  # Primary language
            "github_languages": languages_data,  # Detailed language breakdown
            "github_topics": data.get("topics", []),
            "github_has_issues": data.get("has_issues"),
            "github_has_projects": data.get("has_projects"),
            "github_has_wiki": data.get("has_wiki"),
            "github_has_pages": data.get("has_pages"),
            "github_default_branch": data.get("default_branch"),
        }

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching GitHub repo {owner}/{repo}: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching GitHub repo {owner}/{repo}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching GitHub repo {owner}/{repo}: {e}")

    return None


def find_github_links_in_text(text: str) -> list[str]:
    """Finds all GitHub repository URLs in a given text.

    Args:
        text (str): The text to search for GitHub links.

    Returns:
        list[str]: A list of unique GitHub repository URLs found.
    """
    # Regex to find GitHub URLs (http or https)
    # It looks for github.com followed by two path segments (owner/repo)
    # and ensures it doesn't pick up URLs with further subpaths like /issues or /pulls directly
    regex = r'https?://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)(?![^\s\'"`<>])'

    found_urls = re.findall(regex, text)

    # Reconstruct the full URLs and ensure uniqueness
    unique_urls = sorted({f"https://github.com/{owner}/{repo}" for owner, repo in found_urls})

    return unique_urls


def get_github_repo_info_batch(
    repo_urls: list[str],
    github_token: str | None = None,
    max_workers: int = 5,
) -> dict[str, dict[str, Any] | None]:
    """Fetch GitHub repository info for multiple URLs concurrently.

    Uses a :class:`ThreadPoolExecutor` with a shared :class:`_GitHubRateLimiter`
    so that requests run in parallel while respecting GitHub's secondary rate
    limits. Each URL is fetched at most once; duplicate URLs share a single result.

    Args:
        repo_urls: List of GitHub repository URLs to fetch.
        github_token: Optional GitHub PAT for authenticated requests (higher rate limits).
        max_workers: Maximum number of concurrent worker threads. Defaults to 5,
            which is safe for unauthenticated use (60 req/h) and well within
            the 5000 req/h authenticated limit.

    Returns:
        A mapping ``{repo_url: repo_info_dict_or_None}`` for every URL in the
        input list, including duplicates.
    """
    if not repo_urls:
        return {}

    # De-duplicate URLs to avoid redundant API calls
    unique_urls: list[str] = list(dict.fromkeys(repo_urls))

    rate_limiter = _GitHubRateLimiter()
    results: dict[str, dict[str, Any] | None] = {}

    logger.info(f"Fetching GitHub info for {len(unique_urls)} unique repos with {max_workers} workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url: dict[Any, str] = {executor.submit(get_github_repo_info, url, github_token, rate_limiter): url for url in unique_urls}

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results[url] = future.result()
            except Exception as e:
                logger.error(f"Worker error fetching {url}: {e}")
                results[url] = None

    # Expand results back to all input URLs (including duplicates)
    return {url: results.get(url) for url in repo_urls}


if __name__ == "__main__":
    # Example Usage
    logger.info("Starting GitHub Utils example")

    # Test link extraction
    sample_text_with_links = """
    Check out this project: https://github.com/user1/repo1.
    Also, see https://github.com/user2/repo2/issues/1 for an issue.
    Another one is http://github.com/user3/repo3/.
    And https://github.com/user4/repo4_with_underscores.
    A more complex one: https://github.com/tensorflow/tensorflow
    This should not match: https://github.com/blog
    This is just github.com.
    This has a trailing quote: "https://github.com/user5/repo5"
    This has a trailing parenthesis: (https://github.com/user6/repo6)
    This is embedded: `https://github.com/user7/repo7`
    """
    extracted_links = find_github_links_in_text(sample_text_with_links)
    logger.info(f"Extracted GitHub links: {extracted_links}")

    test_repo_urls = [
        "https://github.com/psf/requests",
        "https://github.com/fastapi/fastapi",
        "https://github.com/nonexistent/repo",  # Test non-existent repo
        "http://github.com/polars/polars",
    ]

    if extracted_links:
        test_repo_urls.append(extracted_links[0])  # Add one from extracted for testing

    for url in test_repo_urls:
        logger.info(f"Fetching info for: {url}")
        # Note: For real use, you might want to pass a GITHUB_TOKEN from an environment variable
        # repo_info = get_github_repo_info(url, github_token=os.getenv("GITHUB_TOKEN"))
        repo_info = get_github_repo_info(url)
        if repo_info:
            logger.info(f"Repository: {repo_info.get('github_html_url')}")
            logger.info(f"  Stars: {repo_info.get('github_stars')}, Forks: {repo_info.get('github_forks')}")
            logger.info(f"  Description: {repo_info.get('github_description')}")
            logger.info(f"  Last Updated: {repo_info.get('github_last_updated')}")
            logger.info(f"  Primary Language: {repo_info.get('github_language')}")
            logger.info(f"  Languages: {repo_info.get('github_languages')}")
            logger.info(f"  Topics: {repo_info.get('github_topics')}")
        else:
            logger.warning(f"Could not fetch info for {url}")

    logger.info("GitHub Utils example finished")
