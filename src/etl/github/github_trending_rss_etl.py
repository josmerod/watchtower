"""GitHub Trending RSS ETL Module

This module fetches GitHub trending repository data from RSS feeds and processes
them into structured format for the dashboard. Supports multiple time periods
and programming languages.

Usage:
    python src/etl/github/github_trending_rss_etl.py

Output:
    - JSON files in data/github_trending/ for each feed
    - Combined latest data for dashboard consumption
"""

import json
import re
from datetime import datetime
from typing import Any, List
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.etl.base import BaseETL
from src.models.github import (
    GitHubRepositoryModel,
    GitHubRepositoryOwner,
    GitHubTrendingFeed,
    RepositoryLanguage,
    TrendingPeriod,
)
from src.utils.logging import get_logger

logger = get_logger("GitHubTrendingRSSETL")


class GitHubTrendingRSSETL(BaseETL[GitHubTrendingFeed, GitHubRepositoryModel]):
    """ETL for GitHub trending repository RSS feeds."""

    # RSS feed configurations
    TRENDING_FEEDS: List[GitHubTrendingFeed] = [
        # All languages
        GitHubTrendingFeed(
            name="Daily Trending - All Languages",
            url="https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml",
            period=TrendingPeriod.DAILY,
            language=RepositoryLanguage.ALL,
            description="GitHub trending repositories for the day across all programming languages",
        ),
        GitHubTrendingFeed(
            name="Weekly Trending - All Languages",
            url="https://mshibanami.github.io/GitHubTrendingRSS/weekly/all.xml",
            period=TrendingPeriod.WEEKLY,
            language=RepositoryLanguage.ALL,
            description="GitHub trending repositories for the week across all programming languages",
        ),
        GitHubTrendingFeed(
            name="Monthly Trending - All Languages",
            url="https://mshibanami.github.io/GitHubTrendingRSS/monthly/all.xml",
            period=TrendingPeriod.MONTHLY,
            language=RepositoryLanguage.ALL,
            description="GitHub trending repositories for the month across all programming languages",
        ),
        # Python specific
        GitHubTrendingFeed(
            name="Daily Trending - Python",
            url="https://mshibanami.github.io/GitHubTrendingRSS/daily/python.xml",
            period=TrendingPeriod.DAILY,
            language=RepositoryLanguage.PYTHON,
            description="GitHub trending Python repositories for the day",
        ),
        GitHubTrendingFeed(
            name="Weekly Trending - Python",
            url="https://mshibanami.github.io/GitHubTrendingRSS/weekly/python.xml",
            period=TrendingPeriod.WEEKLY,
            language=RepositoryLanguage.PYTHON,
            description="GitHub trending Python repositories for the week",
        ),
        GitHubTrendingFeed(
            name="Monthly Trending - Python",
            url="https://mshibanami.github.io/GitHubTrendingRSS/monthly/python.xml",
            period=TrendingPeriod.MONTHLY,
            language=RepositoryLanguage.PYTHON,
            description="GitHub trending Python repositories for the month",
        ),
        # Jupyter Notebook
        GitHubTrendingFeed(
            name="Weekly Trending - Jupyter Notebook",
            url="https://mshibanami.github.io/GitHubTrendingRSS/weekly/jupyter-notebook.xml",
            period=TrendingPeriod.WEEKLY,
            language=RepositoryLanguage.JUPYTER_NOTEBOOK,
            description="GitHub trending Jupyter Notebook repositories for the week",
        ),
        GitHubTrendingFeed(
            name="Monthly Trending - Jupyter Notebook",
            url="https://mshibanami.github.io/GitHubTrendingRSS/monthly/jupyter-notebook.xml",
            period=TrendingPeriod.MONTHLY,
            language=RepositoryLanguage.JUPYTER_NOTEBOOK,
            description="GitHub trending Jupyter Notebook repositories for the month",
        ),
        # CUDA
        GitHubTrendingFeed(
            name="Monthly Trending - CUDA",
            url="https://mshibanami.github.io/GitHubTrendingRSS/monthly/cuda.xml",
            period=TrendingPeriod.MONTHLY,
            language=RepositoryLanguage.CUDA,
            description="GitHub trending CUDA repositories for the month",
        ),
        # Terraform (HCL)
        GitHubTrendingFeed(
            name="Monthly Trending - Terraform (HCL)",
            url="https://mshibanami.github.io/GitHubTrendingRSS/monthly/hcl.xml",
            period=TrendingPeriod.MONTHLY,
            language=RepositoryLanguage.HCL,
            description="GitHub trending Terraform (HCL) repositories for the month",
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(
            name="github_trending_rss",
            description="GitHub Trending RSS Feed ETL",
            **kwargs,
        )
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update(
            {
                "User-Agent": "Watchtower-GitHubTrending-ETL/1.0",
                "Accept": "application/rss+xml, application/xml, text/xml",
            }
        )

        return session

    def extract(self) -> List[GitHubTrendingFeed]:
        """Extract feed configurations."""
        self.logger.info(
            f"Extracting {len(self.TRENDING_FEEDS)} GitHub trending RSS feeds"
        )
        self.metrics.records_extracted = len(self.TRENDING_FEEDS)
        return self.TRENDING_FEEDS

    def transform(self, feeds: List[GitHubTrendingFeed]) -> List[GitHubRepositoryModel]:
        """Transform RSS feed data into repository models."""
        all_repositories = []

        for feed in feeds:
            try:
                self.logger.info(f"Processing feed: {feed.name}")
                repositories = self._process_feed(feed)
                all_repositories.extend(repositories)
                self.logger.info(
                    f"Processed {len(repositories)} repositories from {feed.name}"
                )

            except Exception as e:
                self.logger.error(f"Error processing feed {feed.name}: {e}")
                self.metrics.error_count += 1
                continue

        self.metrics.records_transformed = len(all_repositories)
        self.logger.info(f"Total repositories processed: {len(all_repositories)}")
        return all_repositories

    def _process_feed(self, feed: GitHubTrendingFeed) -> List[GitHubRepositoryModel]:
        """Process a single RSS feed."""
        try:
            # Fetch RSS feed
            self.logger.debug(f"Fetching RSS feed: {feed.url}")
            response = self.session.get(feed.url, timeout=30, verify=False)
            response.raise_for_status()

            # Parse RSS feed
            parsed_feed = feedparser.parse(response.content)

            if parsed_feed.bozo:
                self.logger.warning(
                    f"RSS feed parsing warning for {feed.url}: {parsed_feed.bozo_exception}"
                )

            repositories = []

            for entry in parsed_feed.entries:
                try:
                    repo = self._parse_rss_entry(entry, feed)
                    if repo:
                        repositories.append(repo)

                except Exception as e:
                    self.logger.warning(f"Error parsing RSS entry: {e}")
                    self.metrics.records_failed += 1
                    continue

            return repositories

        except requests.RequestException as e:
            self.logger.error(f"Error fetching RSS feed {feed.url}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error processing RSS feed {feed.url}: {e}")
            raise

    def _parse_rss_entry(
        self, entry: Any, feed: GitHubTrendingFeed
    ) -> GitHubRepositoryModel | None:
        """Parse individual RSS entry into repository model."""
        try:
            # Extract basic RSS information
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "")
            published = getattr(entry, "published", "")

            if not link or not title:
                self.logger.warning("RSS entry missing required fields (title or link)")
                return None

            # Parse GitHub repository information from RSS data
            repo_info = self._extract_repo_info_from_rss(title, link, summary)

            if not repo_info:
                self.logger.warning(
                    f"Could not extract repository info from RSS entry: {title}"
                )
                return None

            # Parse published date
            published_date = None
            if published:
                try:
                    published_date = datetime(
                        *feedparser.parse(published).published_parsed[:6]
                    )
                except:
                    try:
                        published_date = datetime.fromisoformat(
                            published.replace("Z", "+00:00")
                        )
                    except:
                        self.logger.warning(
                            f"Could not parse published date: {published}"
                        )

            # Set language from feed context if not detected in content
            language = repo_info.get("language") or (
                feed.language if feed.language != RepositoryLanguage.ALL else None
            )

            # Create repository model
            repository = GitHubRepositoryModel(
                name=repo_info["name"],
                full_name=repo_info["full_name"],
                description=repo_info.get("description"),
                html_url=repo_info["html_url"],
                language=language,
                stars_count=repo_info.get("stars_count", 0),
                forks_count=repo_info.get("forks_count", 0),
                owner=(
                    GitHubRepositoryOwner(
                        login=repo_info["owner_login"],
                        type=repo_info.get("owner_type", "User"),
                        html_url=repo_info.get("owner_html_url"),
                    )
                    if repo_info.get("owner_login")
                    else None
                ),
                trending_period=feed.period,
                trending_language=feed.language,
                rss_title=title,
                rss_link=link,
                rss_published=published_date,
                rss_summary=summary,
                source_url=feed.url,
            )

            return repository

        except Exception as e:
            self.logger.error(f"Error parsing RSS entry: {e}")
            return None

    def _extract_repo_info_from_rss(
        self, title: str, link: str, summary: str
    ) -> dict[str, Any] | None:
        """Extract repository information from RSS entry data."""
        try:
            # Parse GitHub URL to get owner and repo name
            github_url_pattern = r"https://github\.com/([^/]+)/([^/\?#]+)"
            match = re.search(github_url_pattern, link)

            if not match:
                return None

            owner_login = match.group(1)
            repo_name = match.group(2)
            full_name = f"{owner_login}/{repo_name}"

            # Extract description from HTML summary using improved HTML parsing
            description = self._extract_description_from_html(summary)

            # Debug logging for description extraction
            if not description:
                self.logger.debug(
                    f"No description extracted for {full_name}, summary length: {len(summary) if summary else 0}"
                )

            # Language will be set from the feed context in _parse_rss_entry
            language = None

            # Extract additional metadata if available in summary
            stars_count = 0
            forks_count = 0

            # Look for GitHub-style stat patterns in HTML
            stars_match = re.search(r"(\d+(?:,\d+)*)\s*stars?", summary, re.IGNORECASE)
            if stars_match:
                stars_count = int(stars_match.group(1).replace(",", ""))

            forks_match = re.search(r"(\d+(?:,\d+)*)\s*forks?", summary, re.IGNORECASE)
            if forks_match:
                forks_count = int(forks_match.group(1).replace(",", ""))

            return {
                "name": repo_name,
                "full_name": full_name,
                "description": description,
                "html_url": link,
                "language": language,
                "stars_count": stars_count,
                "forks_count": forks_count,
                "owner_login": owner_login,
                "owner_type": "User",  # Default, could be Organization
                "owner_html_url": f"https://github.com/{owner_login}",
            }

        except Exception as e:
            self.logger.error(f"Error extracting repo info from RSS: {e}")
            return None

    def _extract_description_from_html(self, html_content: str) -> str | None:
        """Extract a clean description from HTML content."""
        if not html_content:
            return None

        try:
            import html

            # First decode HTML entities properly
            decoded_content = html.unescape(html_content)

            # Strategy 1: Look for the first meaningful paragraph
            # Try multiple paragraph patterns
            paragraph_patterns = [
                r"<p[^>]*>(.*?)</p>",  # Standard paragraph
                r"<p>(.*?)</p>",  # Simple paragraph
                r"<div[^>]*class[^>]*description[^>]*>(.*?)</div>",  # Description div
            ]

            for pattern in paragraph_patterns:
                p_match = re.search(pattern, decoded_content, re.IGNORECASE | re.DOTALL)
                if p_match:
                    description = p_match.group(1)
                    # Clean HTML tags
                    description = re.sub(r"<[^>]+>", "", description)
                    # Clean up whitespace
                    description = " ".join(description.split())

                    # Check if we have meaningful content (not just symbols or very short text)
                    if (
                        description
                        and len(description) > 15
                        and not description.isspace()
                    ):
                        # Remove common HTML artifacts
                        description = description.replace("&nbsp;", " ").strip()
                        if description:
                            return (
                                description[:200] + "..."
                                if len(description) > 200
                                else description
                            )

            # Strategy 2: Extract text from the beginning, skipping HTML structure elements
            # Remove script and style tags first
            clean_content = re.sub(
                r"<(script|style)[^>]*>.*?</\1>",
                "",
                decoded_content,
                flags=re.IGNORECASE | re.DOTALL,
            )

            # Remove all HTML tags but preserve text content
            clean_text = re.sub(r"<[^>]+>", " ", clean_content)

            # Clean up whitespace and common artifacts
            clean_text = re.sub(r"\s+", " ", clean_text)
            clean_text = clean_text.replace("&nbsp;", " ").strip()

            # Look for the first meaningful sentence (ending with . ! or ?)
            sentences = re.split(r"[.!?]+", clean_text)
            for sentence in sentences[:3]:  # Check first 3 sentences
                sentence = sentence.strip()
                if len(sentence) > 20 and not sentence.startswith("http"):  # Skip URLs
                    return sentence[:200] + "..." if len(sentence) > 200 else sentence

            # Strategy 3: If we still don't have anything, take first meaningful chunk
            if clean_text and len(clean_text) > 15:
                # Split by common separators and take first meaningful part
                parts = re.split(r"[|\-—]+", clean_text)
                for part in parts[:2]:
                    part = part.strip()
                    if len(part) > 20:
                        return part[:200] + "..." if len(part) > 200 else part

            return None

        except Exception as e:
            self.logger.warning(f"Error extracting description from HTML: {e}")
            return None

    def load(self, repositories: List[GitHubRepositoryModel] | List[dict]) -> None:
        """Load data into JSON files.

        Args:
            repositories: List of GitHubRepositoryModel objects or dicts
        """
        if not repositories:
            self.logger.warning("No data to load")
            return

        # Convert dicts back to models if necessary
        models = []
        for repo in repositories:
            if isinstance(repo, dict):
                try:
                    models.append(GitHubRepositoryModel(**repo))
                except Exception as e:
                    self.logger.error(f"Failed to convert dict to model: {e}")
            else:
                models.append(repo)
        
        repositories = models

        # Create output directory
        output_dir = self.output_dir / "github_trending"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Group repositories by feed configuration
        feed_groups = {}
        for repo in repositories:
            key = f"{repo.trending_period}_{repo.trending_language}"
            if key not in feed_groups:
                feed_groups[key] = []
            feed_groups[key].append(repo)

        # Save individual feed files
        all_files = []
        for group_key, group_repos in feed_groups.items():
            filename = f"github_trending_{group_key}.json"
            file_path = output_dir / filename

            # Convert to dashboard format
            dashboard_data = [repo.to_dashboard_dict() for repo in group_repos]

            # Save to file
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)

            all_files.append(str(file_path))
            self.logger.info(f"Saved {len(group_repos)} repositories to {filename}")

        # Save combined latest file for dashboard
        latest_file = output_dir / "github_trending_latest.json"
        all_dashboard_data = [repo.to_dashboard_dict() for repo in repositories]

        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(all_dashboard_data, f, indent=2, ensure_ascii=False, default=str)

        all_files.append(str(latest_file))

        # Save metadata
        metadata = {
            "total_repositories": len(repositories),
            "feeds_processed": len(feed_groups),
            "last_updated": datetime.utcnow().isoformat(),
            "feed_summary": {key: len(repos) for key, repos in feed_groups.items()},
        }

        metadata_file = output_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        all_files.append(str(metadata_file))

        self.metrics.records_loaded = len(repositories)
        self.logger.info(
            f"Successfully loaded {len(repositories)} repositories to {len(all_files)} files"
        )


def main():
    """Main function to run the GitHub Trending RSS ETL."""
    logger.info("Starting GitHub Trending RSS ETL")

    try:
        etl = GitHubTrendingRSSETL()
        etl.run()

        logger.info("GitHub Trending RSS ETL completed successfully")
        logger.info(f"Metrics: {etl.metrics}")

    except Exception as e:
        logger.error(f"GitHub Trending RSS ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
