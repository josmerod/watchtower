"""Meme Economics ETL Implementation.

Tracks the rise and fall of internet memes like a stock market:
- Meme lifecycle analysis (birth, peak, death)
- Cross-platform meme migration tracking
- Meme investment recommendations
- Cultural impact scoring
- Cringe prediction algorithms

Because someone needs to bring financial rigor to meme analysis! 📈🐸
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import requests

from src.etl.base import BaseETL
from src.utils.logging import get_logger


class MemeEconomicsETL(BaseETL):
    """Meme Economics ETL for tracking internet meme market trends."""

    def __init__(self, **kwargs):
        """Initialize Meme Economics ETL."""
        super().__init__(
            name="meme_economics",
            description="Internet meme market analysis and lifecycle tracking",
            **kwargs,
        )
        self.logger = get_logger("ETL.MemeEconomics")

        # Meme data sources
        self.endpoints = {
            "reddit_memes": "https://www.reddit.com/r/memes/hot.json",
            "reddit_dankmemes": "https://www.reddit.com/r/dankmemes/hot.json",
            "reddit_memeeconomy": "https://www.reddit.com/r/MemeEconomy/hot.json",
            "knowyourmeme": "https://knowyourmeme.com/memes/trending",
        }

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/html, */*",
        }

        # Meme market indicators
        self.viral_threshold = 10000  # upvotes/likes for viral status
        self.cringe_indicators = ["ratio", "based", "sus", "no cap", "bussin"]
        self.evergreen_memes = ["rickroll", "pepe", "wojak", "chad", "doge"]

    def extract(self) -> list[dict[str, Any]]:
        """Extract meme data from various platforms."""
        self.logger.info("Starting meme market data extraction 📈")
        extracted_data = []

        try:
            # Extract Reddit meme data
            reddit_data = self._extract_reddit_memes()
            if reddit_data:
                extracted_data.extend(reddit_data)
                self.metrics.records_extracted += len(reddit_data)

            # Extract trending memes
            trending_data = self._extract_trending_memes()
            if trending_data:
                extracted_data.extend(trending_data)
                self.metrics.records_extracted += len(trending_data)

            # Generate meme market analysis
            market_data = self._generate_market_analysis()
            if market_data:
                extracted_data.extend(market_data)
                self.metrics.records_extracted += len(market_data)

            self.logger.info(f"Extracted {len(extracted_data)} meme market records 🚀")

        except Exception as e:
            self.logger.error(f"Failed to extract meme data: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def _extract_reddit_memes(self) -> list[dict[str, Any]]:
        """Extract meme data from Reddit."""
        meme_data = []

        for subreddit, url in self.endpoints.items():
            if "reddit" in subreddit:
                try:
                    self.logger.info(f"Extracting from {subreddit}")
                    response = requests.get(url, headers=self.headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get("data", {}).get("children", [])

                        for post in posts[:25]:  # Top 25 posts
                            post_data = post.get("data", {})

                            meme_record = {
                                "data_type": "meme_post",
                                "platform": "reddit",
                                "subreddit": subreddit,
                                "title": post_data.get("title", ""),
                                "author": post_data.get("author", ""),
                                "score": post_data.get("score", 0),
                                "upvotes": post_data.get("ups", 0),
                                "downvotes": post_data.get("downs", 0),
                                "upvote_ratio": post_data.get("upvote_ratio", 0.0),
                                "num_comments": post_data.get("num_comments", 0),
                                "created_utc": datetime.fromtimestamp(post_data.get("created_utc", 0)),
                                "url": f"https://reddit.com{post_data.get('permalink', '')}",
                                "image_url": post_data.get("url", ""),
                                "is_video": post_data.get("is_video", False),
                                "awards": len(post_data.get("all_awardings", [])),
                                "extracted_at": datetime.utcnow().isoformat(),
                                "published_at": datetime.utcfromtimestamp(post_data.get("created_utc", 0)).strftime("%Y-%m-%d %H:%M UTC"),
                            }

                            meme_data.append(meme_record)

                except Exception as e:
                    self.logger.error(f"Failed to extract from {subreddit}: {e}")

        return meme_data

    def _extract_trending_memes(self) -> list[dict[str, Any]]:
        """Extract trending memes (mock implementation)."""
        trending_data = []

        # Mock trending memes data
        mock_trending = [
            {
                "data_type": "trending_meme",
                "meme_name": "Distracted Boyfriend",
                "origin": "shutterstock_photo",
                "first_seen": "2017-01-02",
                "peak_date": "2017-08-25",
                "current_popularity": 6.5,
                "lifecycle_stage": "mature",
                "cultural_impact": 9.2,
                "versatility_score": 8.8,
                "normie_adoption_rate": 0.85,
                "cringe_risk": "medium",
                "investment_recommendation": "hold",
                "extracted_at": datetime.utcnow().isoformat(),
                "published_at": "2017-01-02",
            },
            {
                "data_type": "trending_meme",
                "meme_name": "Ohio",
                "origin": "tiktok_gen_z",
                "first_seen": "2022-03-15",
                "peak_date": "2023-01-10",
                "current_popularity": 4.2,
                "lifecycle_stage": "declining",
                "cultural_impact": 5.1,
                "versatility_score": 3.4,
                "normie_adoption_rate": 0.92,
                "cringe_risk": "high",
                "investment_recommendation": "sell_immediately",
                "extracted_at": datetime.utcnow().isoformat(),
                "published_at": "2022-03-15",
            },
        ]

        trending_data.extend(mock_trending)
        return trending_data

    def _generate_market_analysis(self) -> list[dict[str, Any]]:
        """Generate meme market analysis."""
        market_data = []

        # Meme market index
        market_index = {
            "data_type": "market_analysis",
            "analysis_type": "meme_market_index",
            "timestamp": datetime.utcnow().isoformat(),
            "meme_market_cap": 420690000,  # In theoretical meme coins
            "daily_volume": 69420,
            "market_sentiment": "bullish_on_frogs",
            "volatility_index": 8.5,
            "top_performers": ["pepe_variations", "chad_memes", "wojak_feels"],
            "worst_performers": [
                "minion_memes",
                "facebook_mom_content",
                "boomer_humor",
            ],
            "emerging_trends": [
                "ai_generated_memes",
                "meta_memes",
                "post_ironic_content",
            ],
            "cringe_alert_level": "moderate",
            "normification_risk": "low",
            "prediction_accuracy": 69.42,  # We're very scientific here
            "extracted_at": datetime.utcnow().isoformat(),
            "published_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        }

        market_data.append(market_index)
        return market_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform meme data with economic analysis."""
        self.logger.info(f"Transforming {len(data)} meme economic records 💰")
        transformed_data = []

        for record in data:
            try:
                if record.get("data_type") == "meme_post":
                    # Add meme economics analysis
                    transformed_record = {
                        **record,
                        "viral_status": self._calculate_viral_status(record),
                        "engagement_score": self._calculate_engagement_score(record),
                        "meme_potential": self._assess_meme_potential(record),
                        "cringe_risk": self._assess_cringe_risk(record),
                        "investment_grade": self._generate_investment_grade(record),
                        "predicted_lifespan": self._predict_meme_lifespan(record),
                        "normie_risk": self._assess_normie_risk(record),
                    }
                else:
                    transformed_record = record

                transformed_data.append(transformed_record)
                self.metrics.records_transformed += 1

            except Exception as e:
                self.logger.error(f"Failed to transform meme record: {e}")
                self.metrics.records_failed += 1

        return transformed_data

    def _calculate_viral_status(self, record: dict[str, Any]) -> str:
        """Calculate if meme has achieved viral status."""
        score = record.get("score", 0)

        if score >= 50000:
            return "mega_viral"
        elif score >= self.viral_threshold:
            return "viral"
        elif score >= 1000:
            return "trending"
        else:
            return "normie_tier"

    def _calculate_engagement_score(self, record: dict[str, Any]) -> float:
        """Calculate engagement score based on various metrics."""
        score = record.get("score", 0)
        comments = record.get("num_comments", 0)
        ratio = record.get("upvote_ratio", 0.5)
        awards = record.get("awards", 0)

        # Sophisticated meme engagement algorithm
        engagement = (score * 0.4) + (comments * 2) + (ratio * 1000) + (awards * 100)

        # Normalize to 0-10 scale
        return min(engagement / 10000, 10.0)

    def _assess_meme_potential(self, record: dict[str, Any]) -> str:
        """Assess the meme's potential for growth."""
        engagement = self._calculate_engagement_score(record)
        title = record.get("title", "").lower()

        # Look for meme potential indicators
        potential_keywords = ["oc", "original", "new format", "template"]
        has_potential = any(keyword in title for keyword in potential_keywords)

        if engagement >= 8.0 and has_potential:
            return "moon_potential"
        elif engagement >= 6.0:
            return "solid_investment"
        elif engagement >= 4.0:
            return "risky_play"
        else:
            return "penny_stock"

    def _assess_cringe_risk(self, record: dict[str, Any]) -> str:
        """Assess the cringe risk level."""
        title = record.get("title", "").lower()

        cringe_count = sum(1 for indicator in self.cringe_indicators if indicator in title)

        if cringe_count >= 3:
            return "maximum_cringe"
        elif cringe_count >= 2:
            return "high_cringe"
        elif cringe_count >= 1:
            return "moderate_cringe"
        else:
            return "acceptably_dank"

    def _generate_investment_grade(self, record: dict[str, Any]) -> str:
        """Generate investment recommendation."""
        engagement = self._calculate_engagement_score(record)
        potential = self._assess_meme_potential(record)
        cringe = self._assess_cringe_risk(record)

        if potential == "moon_potential" and cringe == "acceptably_dank":
            return "strong_buy"
        elif engagement >= 7.0 and cringe != "maximum_cringe":
            return "buy"
        elif engagement >= 5.0:
            return "hold"
        elif cringe in ["high_cringe", "maximum_cringe"]:
            return "sell"
        else:
            return "avoid"

    def _predict_meme_lifespan(self, record: dict[str, Any]) -> str:
        """Predict how long the meme will stay relevant."""
        title = record.get("title", "").lower()

        # Evergreen memes have longer lifespans
        is_evergreen = any(meme in title for meme in self.evergreen_memes)

        if is_evergreen:
            return "immortal"
        elif self._assess_meme_potential(record) == "moon_potential":
            return "6_months"
        elif self._calculate_engagement_score(record) >= 6.0:
            return "3_months"
        else:
            return "2_weeks"

    def _assess_normie_risk(self, record: dict[str, Any]) -> float:
        """Assess risk of normie adoption (which kills memes)."""
        subreddit = record.get("subreddit", "")
        score = record.get("score", 0)

        # High scores in mainstream subreddits = higher normie risk
        if "memes" in subreddit and score >= 20000:
            return 0.9
        elif score >= 10000:
            return 0.7
        elif score >= 5000:
            return 0.5
        else:
            return 0.2

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load meme economics data to storage."""
        self.logger.info(f"Loading {len(data)} meme economic records 💾")

        # Save as JSON for meme market analysis
        output_file = self.output_dir / f"meme_economics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            # Also save latest market snapshot
            latest_file = self.output_dir / "meme_economics_latest.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            self.logger.info(f"Meme economics data saved to {output_file}")
            self.metrics.records_loaded = len(data)

            # Log some fun stats
            meme_posts = [d for d in data if d.get("data_type") == "meme_post"]
            if meme_posts:
                viral_memes = [m for m in meme_posts if m.get("viral_status") in ["viral", "mega_viral"]]
                strong_buys = [m for m in meme_posts if m.get("investment_grade") == "strong_buy"]

                self.logger.info(f"Market Summary: {len(viral_memes)} viral memes, {len(strong_buys)} strong buy recommendations 📊")

        except Exception as e:
            self.logger.error(f"Failed to save meme economics data: {e}")
            raise


def run_meme_economics_etl():
    """Run the Meme Economics ETL process."""
    etl = MemeEconomicsETL()
    metrics = etl.run()
    return metrics


if __name__ == "__main__":
    run_meme_economics_etl()
