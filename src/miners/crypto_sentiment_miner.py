"""Cryptocurrency Sentiment Miner

This mining tool monitors cryptocurrency sentiment across multiple platforms
including social media, news sources, and forums to track market sentiment and trends.

Usage:
    python src/miners/crypto_sentiment_miner.py

Output:
    - JSON file: data/crypto_sentiment/sentiment_data.json
    - CSV file: data/crypto_sentiment/sentiment_data.csv
"""

import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

import requests

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("CryptoSentimentMiner")


class CryptoSentimentMiner:
    """Cryptocurrency sentiment analysis and tracking system."""

    def __init__(self):
        """Initialize the crypto sentiment miner."""
        self.cryptocurrencies = {
            "bitcoin": ["bitcoin", "btc", "$btc"],
            "ethereum": ["ethereum", "eth", "$eth", "ether"],
            "cardano": ["cardano", "ada", "$ada"],
            "solana": ["solana", "sol", "$sol"],
            "polkadot": ["polkadot", "dot", "$dot"],
            "chainlink": ["chainlink", "link", "$link"],
            "polygon": ["polygon", "matic", "$matic"],
            "avalanche": ["avalanche", "avax", "$avax"],
            "cosmos": ["cosmos", "atom", "$atom"],
            "algorand": ["algorand", "algo", "$algo"],
            "near": ["near", "near protocol", "$near"],
            "terra": ["terra", "luna", "$luna"],
            "binance": ["binance", "bnb", "$bnb"],
            "ripple": ["ripple", "xrp", "$xrp"],
            "dogecoin": ["dogecoin", "doge", "$doge"],
            "shiba": ["shiba inu", "shib", "$shib"],
        }

        self.sentiment_keywords = {
            "very_positive": [
                "moon",
                "mooning",
                "bullish",
                "rocket",
                "lambo",
                "diamond hands",
                "hodl",
                "to the moon",
                "all time high",
                "ath",
                "pump",
                "surge",
                "breakout",
                "rally",
                "explosion",
                "massive gains",
            ],
            "positive": [
                "buy",
                "buying",
                "accumulate",
                "long",
                "support",
                "uptrend",
                "green",
                "profit",
                "gains",
                "rise",
                "increase",
                "growth",
                "potential",
                "promising",
                "strong",
                "solid",
            ],
            "neutral": [
                "hold",
                "stable",
                "sideways",
                "consolidation",
                "range",
                "watching",
                "monitoring",
                "analysis",
                "chart",
                "technical",
            ],
            "negative": [
                "sell",
                "selling",
                "short",
                "dump",
                "drop",
                "fall",
                "decline",
                "red",
                "loss",
                "weak",
                "resistance",
                "bear",
                "correction",
                "pullback",
            ],
            "very_negative": [
                "crash",
                "collapse",
                "plummet",
                "dump",
                "panic",
                "fear",
                "dead",
                "scam",
                "rugpull",
                "worthless",
                "disaster",
                "panic selling",
                "bloodbath",
                "capitulation",
            ],
        }

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Watchtower-CryptoMiner/1.0 (Data Collection Bot)",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def mine_reddit_sentiment(
        self, subreddits: list[str] = None
    ) -> list[dict[str, Any]]:
        """Mine cryptocurrency sentiment from Reddit.

        Args:
            subreddits: List of subreddits to monitor

        Returns:
            List of sentiment data
        """
        if subreddits is None:
            subreddits = [
                "cryptocurrency",
                "bitcoin",
                "ethereum",
                "cardano",
                "solana",
                "cryptomoonshots",
                "altcoin",
                "defi",
                "satoshistreetbets",
                "ethtrader",
            ]

        logger.info(f"Mining Reddit sentiment from subreddits: {subreddits}")
        sentiment_data = []

        for subreddit in subreddits:
            try:
                # Fetch hot posts from subreddit
                url = f"https://www.reddit.com/r/{subreddit}/hot.json"
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                data = response.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts[:20]:  # Limit to top 20 posts
                    post_data = post.get("data", {})

                    # Extract and analyze post
                    sentiment_item = self._analyze_reddit_post(post_data, subreddit)
                    if sentiment_item:
                        sentiment_data.append(sentiment_item)

                # Rate limiting
                time.sleep(2)

            except requests.RequestException as e:
                logger.error(f"Error fetching Reddit data for r/{subreddit}: {e}")
                continue

        return sentiment_data

    def mine_news_sentiment(
        self, news_sources: list[str] = None
    ) -> list[dict[str, Any]]:
        """Mine cryptocurrency sentiment from news sources.

        Args:
            news_sources: List of news sources to check

        Returns:
            List of sentiment data
        """
        if news_sources is None:
            news_sources = [
                "coindesk.com",
                "cointelegraph.com",
                "decrypt.co",
                "cryptonews.com",
                "bitcoinist.com",
                "newsbtc.com",
            ]

        logger.info(f"Mining news sentiment from sources: {news_sources}")
        sentiment_data = []

        # This would typically involve RSS feeds or news APIs
        # For demonstration, we'll simulate news sentiment analysis

        for source in news_sources:
            try:
                # Simulate fetching news articles
                # In practice, you'd use RSS feeds or news APIs
                articles = self._simulate_news_articles(source)

                for article in articles:
                    sentiment_item = self._analyze_news_article(article, source)
                    if sentiment_item:
                        sentiment_data.append(sentiment_item)

            except Exception as e:
                logger.error(f"Error processing news from {source}: {e}")
                continue

        return sentiment_data

    def mine_social_media_sentiment(self) -> list[dict[str, Any]]:
        """Mine cryptocurrency sentiment from social media platforms.

        Returns:
            List of sentiment data
        """
        logger.info("Mining social media sentiment")
        sentiment_data = []

        # This would integrate with Twitter API, Telegram channels, etc.
        # For demonstration, we'll simulate social media sentiment

        platforms = ["twitter", "telegram", "discord"]

        for platform in platforms:
            try:
                # Simulate social media posts
                posts = self._simulate_social_media_posts(platform)

                for post in posts:
                    sentiment_item = self._analyze_social_media_post(post, platform)
                    if sentiment_item:
                        sentiment_data.append(sentiment_item)

            except Exception as e:
                logger.error(f"Error processing {platform} data: {e}")
                continue

        return sentiment_data

    def _analyze_reddit_post(
        self, post_data: dict[str, Any], subreddit: str
    ) -> dict[str, Any] | None:
        """Analyze sentiment of a Reddit post.

        Args:
            post_data: Reddit post data
            subreddit: Subreddit name

        Returns:
            Sentiment analysis result
        """
        title = post_data.get("title", "").lower()
        text = post_data.get("selftext", "").lower()
        combined_text = f"{title} {text}"

        # Detect mentioned cryptocurrencies
        detected_cryptos = self._detect_cryptocurrencies(combined_text)

        if not detected_cryptos:
            return None

        # Analyze sentiment
        sentiment_score, sentiment_label = self._calculate_sentiment(combined_text)

        return {
            "id": f"reddit_{post_data.get('id', 'unknown')}",
            "platform": "reddit",
            "source": f"r/{subreddit}",
            "title": post_data.get("title", ""),
            "content": post_data.get("selftext", "")[:500],  # Limit content length
            "url": f"https://reddit.com{post_data.get('permalink', '')}",
            "author": post_data.get("author", ""),
            "score": post_data.get("score", 0),
            "comments_count": post_data.get("num_comments", 0),
            "created_utc": post_data.get("created_utc", 0),
            "detected_cryptos": detected_cryptos,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "engagement_score": post_data.get("score", 0)
            + post_data.get("num_comments", 0),
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def _analyze_news_article(
        self, article: dict[str, Any], source: str
    ) -> dict[str, Any] | None:
        """Analyze sentiment of a news article.

        Args:
            article: News article data
            source: News source

        Returns:
            Sentiment analysis result
        """
        title = article.get("title", "").lower()
        content = article.get("content", "").lower()
        combined_text = f"{title} {content}"

        # Detect mentioned cryptocurrencies
        detected_cryptos = self._detect_cryptocurrencies(combined_text)

        if not detected_cryptos:
            return None

        # Analyze sentiment
        sentiment_score, sentiment_label = self._calculate_sentiment(combined_text)

        return {
            "id": f"news_{hashlib.md5(article.get('url', '').encode()).hexdigest()[:8]}",
            "platform": "news",
            "source": source,
            "title": article.get("title", ""),
            "content": article.get("content", "")[:500],
            "url": article.get("url", ""),
            "author": article.get("author", ""),
            "published_at": article.get("published_at", ""),
            "detected_cryptos": detected_cryptos,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "credibility_score": self._calculate_news_credibility(source),
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def _analyze_social_media_post(
        self, post: dict[str, Any], platform: str
    ) -> dict[str, Any] | None:
        """Analyze sentiment of a social media post.

        Args:
            post: Social media post data
            platform: Platform name

        Returns:
            Sentiment analysis result
        """
        content = post.get("content", "").lower()

        # Detect mentioned cryptocurrencies
        detected_cryptos = self._detect_cryptocurrencies(content)

        if not detected_cryptos:
            return None

        # Analyze sentiment
        sentiment_score, sentiment_label = self._calculate_sentiment(content)

        return {
            "id": f"{platform}_{post.get('id', 'unknown')}",
            "platform": platform,
            "source": platform,
            "content": post.get("content", "")[:500],
            "author": post.get("author", ""),
            "followers_count": post.get("followers_count", 0),
            "likes_count": post.get("likes_count", 0),
            "retweets_count": post.get("retweets_count", 0),
            "created_at": post.get("created_at", ""),
            "detected_cryptos": detected_cryptos,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "influence_score": self._calculate_influence_score(post),
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def _detect_cryptocurrencies(self, text: str) -> list[str]:
        """Detect mentioned cryptocurrencies in text.

        Args:
            text: Text to analyze

        Returns:
            List of detected cryptocurrency names
        """
        detected = []

        for crypto, keywords in self.cryptocurrencies.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    detected.append(crypto)
                    break

        return list(set(detected))  # Remove duplicates

    def _calculate_sentiment(self, text: str) -> tuple[float, str]:
        """Calculate sentiment score and label for text.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (sentiment_score, sentiment_label)
        """
        sentiment_score = 0
        word_count = 0

        # Score based on sentiment keywords
        for sentiment_type, keywords in self.sentiment_keywords.items():
            multiplier = {
                "very_positive": 2.0,
                "positive": 1.0,
                "neutral": 0.0,
                "negative": -1.0,
                "very_negative": -2.0,
            }[sentiment_type]

            for keyword in keywords:
                if keyword in text:
                    sentiment_score += multiplier
                    word_count += 1

        # Normalize score
        if word_count > 0:
            sentiment_score = sentiment_score / word_count

        # Determine label
        if sentiment_score >= 1.5:
            label = "very_positive"
        elif sentiment_score >= 0.5:
            label = "positive"
        elif sentiment_score >= -0.5:
            label = "neutral"
        elif sentiment_score >= -1.5:
            label = "negative"
        else:
            label = "very_negative"

        return round(sentiment_score, 2), label

    def _calculate_news_credibility(self, source: str) -> float:
        """Calculate credibility score for news source.

        Args:
            source: News source domain

        Returns:
            Credibility score (0-10)
        """
        credibility_scores = {
            "coindesk.com": 9.0,
            "cointelegraph.com": 8.5,
            "decrypt.co": 8.0,
            "cryptonews.com": 7.5,
            "bitcoinist.com": 7.0,
            "newsbtc.com": 7.0,
            "coinmarketcap.com": 8.5,
            "coingecko.com": 8.0,
        }

        return credibility_scores.get(source, 6.0)

    def _calculate_influence_score(self, post: dict[str, Any]) -> float:
        """Calculate influence score for social media post.

        Args:
            post: Post data

        Returns:
            Influence score
        """
        followers = post.get("followers_count", 0)
        likes = post.get("likes_count", 0)
        shares = post.get("retweets_count", 0)

        # Weighted calculation
        influence = (followers * 0.3 + likes * 0.4 + shares * 0.3) / 100

        return round(min(influence, 10.0), 2)

    def _simulate_news_articles(self, source: str) -> list[dict[str, Any]]:
        """Simulate news articles for demonstration.

        Args:
            source: News source

        Returns:
            List of simulated articles
        """
        # This is just for demonstration - replace with actual news fetching
        sample_articles = [
            {
                "title": "Bitcoin Reaches New All-Time High as Institutional Adoption Grows",
                "content": "Bitcoin has surged to a new all-time high following increased institutional adoption...",
                "url": f"https://{source}/bitcoin-ath-institutional-adoption",
                "author": "Crypto Reporter",
                "published_at": datetime.utcnow().isoformat(),
            },
            {
                "title": "Ethereum 2.0 Upgrade Shows Promising Results for Scalability",
                "content": "The Ethereum 2.0 upgrade continues to show positive results for network scalability...",
                "url": f"https://{source}/ethereum-2-upgrade-scalability",
                "author": "Tech Analyst",
                "published_at": datetime.utcnow().isoformat(),
            },
        ]

        return sample_articles

    def _simulate_social_media_posts(self, platform: str) -> list[dict[str, Any]]:
        """Simulate social media posts for demonstration.

        Args:
            platform: Platform name

        Returns:
            List of simulated posts
        """
        # This is just for demonstration - replace with actual social media APIs
        sample_posts = [
            {
                "id": f"{platform}_001",
                "content": "Bitcoin is mooning! 🚀 Diamond hands hodling strong! #BTC #ToTheMoon",
                "author": "CryptoEnthusiast",
                "followers_count": 10000,
                "likes_count": 150,
                "retweets_count": 75,
                "created_at": datetime.utcnow().isoformat(),
            },
            {
                "id": f"{platform}_002",
                "content": "Ethereum smart contracts are revolutionizing DeFi. Bullish on ETH long term.",
                "author": "DeFiExpert",
                "followers_count": 25000,
                "likes_count": 200,
                "retweets_count": 120,
                "created_at": datetime.utcnow().isoformat(),
            },
        ]

        return sample_posts

    def aggregate_sentiment_data(
        self, sentiment_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Aggregate sentiment data for analysis.

        Args:
            sentiment_data: List of sentiment items

        Returns:
            Aggregated sentiment analysis
        """
        logger.info("Aggregating sentiment data")

        # Group by cryptocurrency
        crypto_sentiment = defaultdict(
            lambda: {
                "total_mentions": 0,
                "sentiment_scores": [],
                "platform_breakdown": defaultdict(int),
                "sentiment_labels": defaultdict(int),
                "average_engagement": 0,
                "total_engagement": 0,
            }
        )

        for item in sentiment_data:
            for crypto in item.get("detected_cryptos", []):
                crypto_data = crypto_sentiment[crypto]
                crypto_data["total_mentions"] += 1
                crypto_data["sentiment_scores"].append(item.get("sentiment_score", 0))
                crypto_data["platform_breakdown"][item.get("platform", "unknown")] += 1
                crypto_data["sentiment_labels"][
                    item.get("sentiment_label", "neutral")
                ] += 1

                # Add engagement metrics
                engagement = item.get("engagement_score", 0) or item.get("score", 0)
                crypto_data["total_engagement"] += engagement

        # Calculate aggregated metrics
        aggregated_data = {}
        for crypto, data in crypto_sentiment.items():
            if data["sentiment_scores"]:
                avg_sentiment = sum(data["sentiment_scores"]) / len(
                    data["sentiment_scores"]
                )
                avg_engagement = data["total_engagement"] / data["total_mentions"]

                # Determine overall sentiment trend
                positive_count = (
                    data["sentiment_labels"]["positive"]
                    + data["sentiment_labels"]["very_positive"]
                )
                negative_count = (
                    data["sentiment_labels"]["negative"]
                    + data["sentiment_labels"]["very_negative"]
                )

                if positive_count > negative_count:
                    trend = "bullish"
                elif negative_count > positive_count:
                    trend = "bearish"
                else:
                    trend = "neutral"

                aggregated_data[crypto] = {
                    "total_mentions": data["total_mentions"],
                    "average_sentiment": round(avg_sentiment, 2),
                    "average_engagement": round(avg_engagement, 2),
                    "sentiment_trend": trend,
                    "platform_breakdown": dict(data["platform_breakdown"]),
                    "sentiment_distribution": dict(data["sentiment_labels"]),
                    "bullish_ratio": round(positive_count / data["total_mentions"], 2),
                    "bearish_ratio": round(negative_count / data["total_mentions"], 2),
                }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_items_analyzed": len(sentiment_data),
            "cryptocurrencies_mentioned": len(aggregated_data),
            "crypto_sentiment": aggregated_data,
            "overall_market_sentiment": self._calculate_overall_sentiment(
                aggregated_data
            ),
        }

    def _calculate_overall_sentiment(
        self, crypto_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate overall market sentiment.

        Args:
            crypto_data: Aggregated cryptocurrency sentiment data

        Returns:
            Overall market sentiment metrics
        """
        if not crypto_data:
            return {"trend": "neutral", "confidence": 0}

        total_mentions = sum(data["total_mentions"] for data in crypto_data.values())
        weighted_sentiment = (
            sum(
                data["average_sentiment"] * data["total_mentions"]
                for data in crypto_data.values()
            )
            / total_mentions
            if total_mentions > 0
            else 0
        )

        bullish_cryptos = sum(
            1 for data in crypto_data.values() if data["sentiment_trend"] == "bullish"
        )
        bearish_cryptos = sum(
            1 for data in crypto_data.values() if data["sentiment_trend"] == "bearish"
        )

        if bullish_cryptos > bearish_cryptos:
            trend = "bullish"
        elif bearish_cryptos > bullish_cryptos:
            trend = "bearish"
        else:
            trend = "neutral"

        confidence = min(abs(weighted_sentiment) * 10, 10)

        return {
            "trend": trend,
            "weighted_sentiment_score": round(weighted_sentiment, 2),
            "confidence": round(confidence, 1),
            "bullish_cryptos": bullish_cryptos,
            "bearish_cryptos": bearish_cryptos,
            "neutral_cryptos": len(crypto_data) - bullish_cryptos - bearish_cryptos,
        }


def main():
    """Main execution function for crypto sentiment mining."""
    logger.info("Starting cryptocurrency sentiment mining")

    try:
        # Create output directory
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "crypto_sentiment")
        ensure_directories([output_dir])

        # Initialize miner
        miner = CryptoSentimentMiner()

        # Collect sentiment data from various sources
        all_sentiment_data = []

        # Mine Reddit sentiment
        logger.info("Mining Reddit sentiment...")
        reddit_data = miner.mine_reddit_sentiment()
        all_sentiment_data.extend(reddit_data)

        # Mine news sentiment
        logger.info("Mining news sentiment...")
        news_data = miner.mine_news_sentiment()
        all_sentiment_data.extend(news_data)

        # Mine social media sentiment
        logger.info("Mining social media sentiment...")
        social_data = miner.mine_social_media_sentiment()
        all_sentiment_data.extend(social_data)

        if not all_sentiment_data:
            logger.warning("No sentiment data collected")
            return

        # Aggregate sentiment data
        aggregated_data = miner.aggregate_sentiment_data(all_sentiment_data)

        # Save data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Raw sentiment data
        raw_json_file = os.path.join(
            output_dir, f"crypto_sentiment_raw_{timestamp}.json"
        )
        with open(raw_json_file, "w", encoding="utf-8") as f:
            json.dump(all_sentiment_data, f, indent=2, ensure_ascii=False)

        # Aggregated data
        agg_json_file = os.path.join(
            output_dir, f"crypto_sentiment_aggregated_{timestamp}.json"
        )
        with open(agg_json_file, "w", encoding="utf-8") as f:
            json.dump(aggregated_data, f, indent=2, ensure_ascii=False)

        # CSV output for raw data
        csv_file = os.path.join(output_dir, f"crypto_sentiment_raw_{timestamp}.csv")
        import pandas as pd

        # Flatten data for CSV
        csv_data = []
        for item in all_sentiment_data:
            csv_row = item.copy()
            csv_row["detected_cryptos"] = ", ".join(item.get("detected_cryptos", []))
            csv_data.append(csv_row)

        df = pd.DataFrame(csv_data)
        df.to_csv(csv_file, index=False, encoding="utf-8")

        # Create latest files
        latest_raw_json = os.path.join(output_dir, "crypto_sentiment_raw_latest.json")
        latest_agg_json = os.path.join(
            output_dir, "crypto_sentiment_aggregated_latest.json"
        )
        latest_csv = os.path.join(output_dir, "crypto_sentiment_raw_latest.csv")

        # Remove existing files
        for latest_file in [latest_raw_json, latest_agg_json, latest_csv]:
            if os.path.exists(latest_file):
                os.unlink(latest_file)

        # Create new files (copy instead of symlink for better compatibility)
        import shutil

        shutil.copy2(raw_json_file, latest_raw_json)
        shutil.copy2(agg_json_file, latest_agg_json)
        shutil.copy2(csv_file, latest_csv)

        logger.info(f"Successfully processed {len(all_sentiment_data)} sentiment items")
        logger.info(f"Raw data: {raw_json_file}")
        logger.info(f"Aggregated data: {agg_json_file}")
        logger.info(f"CSV data: {csv_file}")

        # Print summary
        print("\n=== Cryptocurrency Sentiment Mining Summary ===")
        print(f"Total sentiment items: {len(all_sentiment_data)}")
        print(
            f"Cryptocurrencies mentioned: {aggregated_data['cryptocurrencies_mentioned']}"
        )
        print(
            f"Overall market sentiment: {aggregated_data['overall_market_sentiment']['trend']}"
        )
        print(
            f"Market confidence: {aggregated_data['overall_market_sentiment']['confidence']}/10"
        )

        # Print top cryptocurrencies by mention count
        crypto_mentions = [
            (crypto, data["total_mentions"])
            for crypto, data in aggregated_data["crypto_sentiment"].items()
        ]
        crypto_mentions.sort(key=lambda x: x[1], reverse=True)

        print("\nTop mentioned cryptocurrencies:")
        for crypto, mentions in crypto_mentions[:10]:
            sentiment_data = aggregated_data["crypto_sentiment"][crypto]
            print(
                f"  {crypto.title()}: {mentions} mentions, "
                f"sentiment: {sentiment_data['sentiment_trend']} "
                f"({sentiment_data['average_sentiment']:+.2f})"
            )

    except Exception as e:
        logger.error(f"Error in cryptocurrency sentiment mining: {e}")
        raise


if __name__ == "__main__":
    main()
