"""Hashnode GraphQL ETL using BaseETL pattern.

Part of Phase 1 ETL implementation for developer blog aggregation.
Fetches developer blogs and posts from Hashnode's GraphQL API.

Author: Phase 1 Implementation Team
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.models.hashnode import (
    HashnodeMetricsModel,
    HashnodePostModel,
    HashnodePublicationType,
)
from src.utils.logging import get_logger


class HashnodeETL(BaseETL[dict[str, Any], HashnodePostModel]):
    """ETL for Hashnode GraphQL API - Developer Blogs.

    Features:
    - GraphQL-based data fetching
    - Post discovery from publications
    - Author tracking
    - Engagement metrics (views, reactions, comments)
    - Publication and blog tracking

    Hashnode API: https://gql.hashnode.com/
    """

    def __init__(
        self,
        tags: list[str] | None = None,
        max_posts_per_tag: int = 50,
        **kwargs,
    ):
        """Initialize Hashnode ETL.

        Args:
            tags: Tags to fetch posts for
            max_posts_per_tag: Max posts to fetch per tag
            **kwargs: Additional BaseETL arguments
        """
        super().__init__(
            name="hashnode_blogs",
            description="Hashnode GraphQL ETL for developer blogs",
            **kwargs,
        )

        # Default tags for developer content
        self.tags = tags or [
            "python",
            "javascript",
            "react",
            "machine-learning",
            "web-development",
            "devops",
            "cloud",
            "ai",
            "database",
            "api",
        ]

        self.max_posts_per_tag = max_posts_per_tag
        self.graphql_url = "https://gql.hashnode.com"

        # Metrics
        self.api_metrics = HashnodeMetricsModel()

    def extract(self) -> list[dict[str, Any]]:
        """Extract posts from Hashnode GraphQL API.

        Returns:
            List of raw post dictionaries.
        """
        self.logger.info(f"Starting extraction for {len(self.tags)} tags")

        all_posts = []

        # Extract posts by tag
        for tag in self.tags:
            try:
                posts = self._fetch_posts_by_tag(tag)
                all_posts.extend(posts)
                self.logger.info(f"Fetched {len(posts)} posts for tag: {tag}")
            except Exception as e:
                self.logger.error(f"Failed to fetch tag '{tag}': {e}")
                self.metrics.add_error_detail(
                    error_message=f"Tag failed: {tag}",
                    error_type=type(e).__name__,
                    context={"tag": tag},
                )

        self.logger.info(f"Extraction complete: {len(all_posts)} total posts")
        self.api_metrics.total_posts_discovered = len(all_posts)

        return all_posts

    def _fetch_posts_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Fetch posts for a specific tag using GraphQL.

        Args:
            tag: Tag name

        Returns:
            List of post dictionaries.
        """
        # GraphQL query for posts by tag
        query = """
        query GetPostsByTag($tag: String!, $page: Int!) {
            tagPosts(tag: $tag, page: $page) {
                nodes {
                    id
                    title
                    slug
                    brief
                    content {
                        markdown
                    }
                    coverImage
                    publishedAt
                    updatedAt
                    readTimeInMinutes
                    views
                    reactionCount
                    replyCount
                    author {
                        id
                        name
                        username
                        bio
                        profilePicture
                    }
                    publication {
                        id
                        title
                        username
                        domain
                        isTeam
                    }
                    tags {
                        name
                    }
                }
                pageInfo {
                    nextPage
                    hasNextPage
                }
            }
        }
        """

        posts = []
        page = 1
        has_next = True

        while has_next and len(posts) < self.max_posts_per_tag:
            variables = {"tag": tag, "page": page}

            try:
                response = self.http_session.post(
                    self.graphql_url,
                    json={"query": query, "variables": variables},
                    timeout=30,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    self.logger.warning(f"GraphQL errors: {data['errors']}")
                    break

                nodes = data.get("data", {}).get("tagPosts", {}).get("nodes", [])
                posts.extend(nodes)

                page_info = data.get("data", {}).get("tagPosts", {}).get("pageInfo", {})
                has_next = page_info.get("hasNextPage", False)
                page = page_info.get("nextPage", page + 1)

            except Exception as e:
                self.logger.error(f"GraphQL request failed for tag '{tag}': {e}")
                break

        return posts[: self.max_posts_per_tag]

    def transform(self, raw_data: list[dict[str, Any]]) -> list[HashnodePostModel]:
        """Transform raw Hashnode data to models.

        Args:
            raw_data: List of raw post dictionaries

        Returns:
            List of HashnodePostModel instances.
        """
        transformed = []

        for raw_post in raw_data:
            try:
                model = self._transform_post(raw_post)
                if model:
                    transformed.append(model)
                    self.api_metrics.new_posts_this_run += 1
            except Exception as e:
                self.logger.warning(f"Failed to transform post: {e}")
                self.metrics.records_failed += 1

        # Update metrics
        for post in transformed:
            self.api_metrics.avg_views = (self.api_metrics.avg_views or 0) + post.views_count
            self.api_metrics.total_engagement += post.engagement_score
            if post.read_time_in_minutes:
                self.api_metrics.total_read_time_minutes += post.read_time_in_minutes

            for tag in post.tags:
                self.api_metrics.popular_tags[tag] = self.api_metrics.popular_tags.get(tag, 0) + 1

        if transformed:
            self.api_metrics.avg_views = self.api_metrics.avg_views / len(transformed)
            self.api_metrics.avg_read_time = self.api_metrics.total_read_time_minutes / len(transformed)

        self.logger.info(f"Transformed {len(transformed)} posts")
        return transformed

    def _transform_post(self, raw: dict[str, Any]) -> HashnodePostModel | None:
        """Transform single post.

        Args:
            raw: Raw post dictionary

        Returns:
            HashnodePostModel or None if transformation fails.
        """
        post_id = raw.get("id")
        title = raw.get("title")
        slug = raw.get("slug")

        if not post_id or not title:
            return None

        # Parse dates
        published_at = None
        updated_at = None
        if raw.get("publishedAt"):
            try:
                published_at = datetime.fromisoformat(raw["publishedAt"].replace("Z", "+00:00"))
            except ValueError:
                pass
        if raw.get("updatedAt"):
            try:
                updated_at = datetime.fromisoformat(raw["updatedAt"].replace("Z", "+00:00"))
            except ValueError:
                pass

        # Extract author
        author_data = raw.get("author", {})
        author_id = author_data.get("id", "unknown")
        author_name = author_data.get("name", "Unknown")
        author_username = author_data.get("username", "")

        # Extract publication
        pub_data = raw.get("publication", {})
        publication_id = pub_data.get("id")
        publication_name = pub_data.get("title")
        publication_domain = pub_data.get("domain")
        publication_type = HashnodePublicationType.ORGANIZATION if pub_data.get("isTeam") else HashnodePublicationType.BLOG

        # Extract content
        content_data = raw.get("content", {})
        content_markdown = content_data.get("markdown") if content_data else None

        # Extract tags
        tags_data = raw.get("tags", [])
        tags = [tag.get("name") for tag in tags_data if tag.get("name")]

        return HashnodePostModel(
            post_id=post_id,
            title=title,
            slug=slug,
            url=f"https://hashnode.com/{author_username}/{slug}" if publication_id is None else f"https://{publication_domain or publication_name + '.hashnode.dev'}/{slug}",
            content=content_markdown,
            excerpt=raw.get("brief"),
            author_id=author_id,
            author_name=author_name,
            author_username=author_username,
            author_bio=author_data.get("bio"),
            author_photo=author_data.get("profilePicture"),
            publication_id=publication_id,
            publication_name=publication_name,
            publication_domain=publication_domain,
            publication_type=publication_type,
            published_at=published_at,
            updated_at=updated_at,
            views_count=raw.get("views", 0),
            reactions_count=raw.get("reactionCount", 0),
            comments_count=raw.get("replyCount", 0),
            cover_image=raw.get("coverImage"),
            tags=tags,
            original_id=post_id,
            brief=raw.get("brief"),
            read_time_in_minutes=raw.get("readTimeInMinutes"),
            metadata=raw,
        )

    def load(self, data: list[HashnodePostModel]) -> None:
        """Load posts to JSON storage.

        Args:
            data: List of HashnodePostModel instances.
        """
        # Convert to dicts
        posts_data = [post.model_dump(mode="json") for post in data]

        # Generate timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save main file
        main_file = self.output_dir / f"hashnode_{timestamp}.json"
        with main_file.open("w", encoding="utf-8") as f:
            json.dump(posts_data, f, indent=2, ensure_ascii=False)

        # Save latest file
        latest_file = self.output_dir / "hashnode_latest.json"
        with latest_file.open("w", encoding="utf-8") as f:
            json.dump(posts_data, f, indent=2, ensure_ascii=False)

        # Save metrics
        metrics_file = self.output_dir / "hashnode_metrics.json"
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(self.api_metrics.model_dump(mode="json"), f, indent=2)

        self.logger.info(f"Saved {len(data)} posts to {main_file.name}")
        self.logger.info(f"Saved latest to {latest_file.name}")
        self.logger.info(f"Saved metrics to {metrics_file.name}")


def main():
    """Main entry point for Hashnode ETL."""
    logger = get_logger("HashnodeETL")
    logger.info("Starting Hashnode GraphQL ETL")

    try:
        etl = HashnodeETL()
        metrics = etl.run()

        logger.info("ETL completed successfully")
        logger.info(f"Records extracted: {metrics.records_extracted}")
        logger.info(f"Records transformed: {metrics.records_transformed}")
        logger.info(f"Records loaded: {metrics.records_loaded}")
        logger.info(f"Errors: {metrics.error_count}")
        logger.info(f"Duration: {metrics.duration_seconds:.2f}s")

    except Exception as e:
        logger.error(f"ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
