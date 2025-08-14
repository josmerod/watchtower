"""Reddit Giveaways ETL Module

This module fetches giveaways and free content from various Reddit communities
including r/FreeGameFindings, r/FreeEBOOKS, r/freebies, and more.

Usage:
    python src/etl/giveaways/reddit_giveaways_etl.py

Output:
    - JSON file: data/giveaways/reddit_giveaways.json
    - CSV file: data/giveaways/reddit_giveaways.csv
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests

# Add the project root to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.etl.base import BaseETL

# Initialize logger
logger = get_logger("RedditGiveawaysETL")


class RedditGiveawaysETL(BaseETL):
    """ETL for Reddit giveaway communities."""

    def __init__(self):
        super().__init__("reddit_giveaways")
        self.subreddits = {
            "FreeGameFindings": {
                "category": "games",
                "description": "Free games and game giveaways",
            },
            "FreeEBOOKS": {"category": "books", "description": "Free books and ebooks"},
            "freebies": {
                "category": "general",
                "description": "General freebies and giveaways",
            },
            "FREE": {"category": "general", "description": "Free stuff and giveaways"},
            "GameDeals": {
                "category": "games",
                "description": "Game deals and free games",
            },
            "udemyfreebies": {
                "category": "courses",
                "description": "Free Udemy courses",
            },
            "FreeEducation": {
                "category": "courses",
                "description": "Free educational content",
            },
            "opensignups": {
                "category": "software",
                "description": "Open signups for services",
            },
        }

    def extract(self) -> Dict[str, Any]:
        """Extract giveaway data from Reddit subreddits."""
        logger.info("Starting Reddit giveaways extraction...")

        all_posts = []

        for subreddit, config in self.subreddits.items():
            try:
                logger.info(f"Fetching from r/{subreddit} ({config['category']})...")

                # Use Reddit JSON API
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
                headers = {"User-Agent": "Watchtower/1.0 (Educational Research Bot)"}

                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()
                posts = data.get("data", {}).get("children", [])

                for post_data in posts:
                    post = post_data.get("data", {})

                    # Filter for recent posts (last 7 days)
                    created_utc = post.get("created_utc", 0)
                    post_age_days = (time.time() - created_utc) / (24 * 3600)

                    if post_age_days > 7:  # Skip posts older than 7 days
                        continue

                    # Extract post information
                    post_info = {
                        "title": post.get("title", ""),
                        "url": post.get("url", ""),
                        "reddit_url": f"https://www.reddit.com{post.get('permalink', '')}",
                        "author": post.get("author", ""),
                        "score": post.get("score", 0),
                        "upvote_ratio": post.get("upvote_ratio", 0),
                        "num_comments": post.get("num_comments", 0),
                        "created_utc": created_utc,
                        "created_date": datetime.fromtimestamp(
                            created_utc, tz=timezone.utc
                        ).isoformat(),
                        "subreddit": subreddit,
                        "category": config["category"],
                        "description": config["description"],
                        "flair_text": post.get("link_flair_text", ""),
                        "is_pinned": post.get("pinned", False),
                        "domain": post.get("domain", ""),
                        "selftext": post.get("selftext", ""),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "source": "Reddit",
                    }

                    # Only include posts that look like actual giveaways/freebies
                    title_lower = post_info["title"].lower()
                    if any(
                        keyword in title_lower
                        for keyword in [
                            "free",
                            "giveaway",
                            "bundle",
                            "gratis",
                            "100% off",
                            "limited time",
                            "ends soon",
                            "expires",
                            "coupon",
                            "deal",
                            "discount",
                            "offer",
                            "promotion",
                        ]
                    ):
                        all_posts.append(post_info)

                logger.info(
                    f"Successfully extracted {len([p for p in all_posts if p['subreddit'] == subreddit])} posts from r/{subreddit}"
                )

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit}: {e}")
                continue

        logger.info(f"Total extracted {len(all_posts)} giveaway posts from Reddit")
        return {"posts": all_posts, "total_count": len(all_posts)}

    def transform(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform Reddit giveaway data."""
        logger.info("Starting Reddit giveaways transformation...")

        posts = raw_data.get("posts", [])
        transformed_posts = []

        for post in posts:
            try:
                # Enhance title for better readability
                title = post["title"].strip()
                if len(title) > 200:
                    title = title[:197] + "..."

                # Determine giveaway type based on content
                giveaway_type = self._determine_giveaway_type(post)

                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(post)

                transformed_post = {
                    "title": title,
                    "url": post["url"],
                    "reddit_url": post["reddit_url"],
                    "author": post["author"],
                    "score": post["score"],
                    "upvote_ratio": post["upvote_ratio"],
                    "num_comments": post["num_comments"],
                    "created_date": post["created_date"],
                    "subreddit": post["subreddit"],
                    "category": post["category"],
                    "giveaway_type": giveaway_type,
                    "relevance_score": relevance_score,
                    "flair_text": post["flair_text"],
                    "domain": post["domain"],
                    "description": post.get("selftext", "")[:500],  # Limit description
                    "fetched_at": post["fetched_at"],
                    "source": post["source"],
                }

                transformed_posts.append(transformed_post)

            except Exception as e:
                logger.warning(f"Error transforming post: {e}")
                continue

        # Sort by relevance score and creation date
        transformed_posts.sort(
            key=lambda x: (x["relevance_score"], x["score"]), reverse=True
        )

        logger.info(f"Transformed {len(transformed_posts)} Reddit giveaway posts")
        return transformed_posts

    def _determine_giveaway_type(self, post: Dict[str, Any]) -> str:
        """Determine the type of giveaway based on post content."""
        title_lower = post["title"].lower()
        domain = post.get("domain", "").lower()
        category = post.get("category", "")

        # Game-related
        if category == "games" or any(
            keyword in title_lower
            for keyword in [
                "steam",
                "epic",
                "gog",
                "game",
                "gaming",
                "xbox",
                "playstation",
                "nintendo",
            ]
        ):
            return "game"

        # Book-related
        if category == "books" or any(
            keyword in title_lower
            for keyword in ["book", "ebook", "kindle", "audiobook", "pdf", "reading"]
        ):
            return "book"

        # Course-related
        if category == "courses" or any(
            keyword in title_lower
            for keyword in [
                "course",
                "udemy",
                "coursera",
                "edx",
                "tutorial",
                "learning",
                "education",
            ]
        ):
            return "course"

        # Software-related
        if any(
            keyword in title_lower
            for keyword in [
                "software",
                "app",
                "license",
                "tool",
                "program",
                "subscription",
            ]
        ):
            return "software"

        # Bundle deals
        if any(
            keyword in title_lower
            for keyword in ["bundle", "pack", "collection", "humble"]
        ):
            return "bundle"

        return "other"

    def _calculate_relevance_score(self, post: Dict[str, Any]) -> float:
        """Calculate relevance score for ranking posts."""
        score = 0.0

        # Reddit engagement metrics
        score += min(post["score"] / 100, 5.0)  # Max 5 points for upvotes
        score += min(post["upvote_ratio"] * 3, 3.0)  # Max 3 points for upvote ratio
        score += min(post["num_comments"] / 20, 2.0)  # Max 2 points for comments

        # Recency bonus (newer posts get higher scores)
        created_utc = post.get("created_utc", 0)
        hours_old = (time.time() - created_utc) / 3600
        if hours_old < 6:
            score += 2.0
        elif hours_old < 24:
            score += 1.0
        elif hours_old < 72:
            score += 0.5

        # Title quality indicators
        title_lower = post["title"].lower()
        if any(
            keyword in title_lower
            for keyword in ["limited time", "ends soon", "expires"]
        ):
            score += 1.0
        if any(keyword in title_lower for keyword in ["100% off", "free", "giveaway"]):
            score += 0.5

        return round(score, 2)

    def load(self, transformed_data: List[Dict[str, Any]]) -> bool:
        """Load transformed giveaway data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "giveaways")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "reddit_giveaways.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "reddit_giveaways.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(
                f"Successfully saved {len(transformed_data)} Reddit giveaways to {output_dir}"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving Reddit giveaways data: {e}")
            return False


def main():
    """Main function to run the Reddit Giveaways ETL."""
    etl = RedditGiveawaysETL()
    success = etl.run()

    if success:
        logger.info("Reddit Giveaways ETL completed successfully")
    else:
        logger.error("Reddit Giveaways ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
