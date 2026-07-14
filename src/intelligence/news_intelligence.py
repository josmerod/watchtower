"""Intelligence engines for Developer News analysis."""

import re
from collections import Counter

from src.models.developer_news_model import DeveloperNewsItem, NewsTrend


class NewsSummarizer:
    """Heuristic-based news summarizer."""

    def summarize(self, text: str, max_sentences: int = 3) -> str:
        """Generate a heuristic summary by extracting key sentences.

        Uses simple heuristics:
        1. First sentence (often the lead).
        2. Sentences with high keyword density.
        """
        if not text:
            return ""

        # Split into sentences (naive implementation)
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]

        if len(sentences) <= max_sentences:
            return ". ".join(sentences) + "."

        # Always include the first sentence
        summary = [sentences[0]]

        # Select other sentences based on length/complexity (naive proxy for information density)
        # In a real heuristic, we'd use TF-IDF or keyword matching
        candidates = sentences[1:]
        candidates.sort(key=lambda s: len(s.split()), reverse=True)

        summary.extend(candidates[: max_sentences - 1])

        return ". ".join(summary) + "."


class TrendDetector:
    """Detects trends in developer news."""

    def detect_trends(self, items: list[DeveloperNewsItem]) -> list[NewsTrend]:
        """Detect trends based on keyword frequency in titles."""

        # flatten all titles into words
        all_words = []
        stop_words = {"the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "or", "is", "are", "with", "by", "from", "how", "why", "what", "new", "show", "hn"}

        item_map = {}  # keyword -> [item_ids]

        for item in items:
            words = re.findall(r"\w+", item.title.lower())
            for word in words:
                if word not in stop_words and len(word) > 2:
                    all_words.append(word)
                    if word not in item_map:
                        item_map[word] = []
                    item_map[word].append(item.id)

        # Count frequencies
        counter = Counter(all_words)

        trends = []
        # Threshold: keyword must appear in at least 3 items to be a "trend" in this small batch
        for keyword, count in counter.most_common(10):
            if count >= 2:
                trends.append(NewsTrend(keyword=keyword, velocity=float(count) / len(items) if items else 0.0, volume=count, related_items=item_map.get(keyword, [])))

        return trends


class RelevanceScorer:
    """Scores news items based on user preferences."""

    def __init__(self, user_tech_stack: list[str] = None):
        self.user_tech_stack = [t.lower() for t in (user_tech_stack or ["python", "ai", "cloud", "data"])]

    def score(self, item: DeveloperNewsItem) -> float:
        """Calculate relevance score (0.0 - 1.0)."""
        score = 0.1  # Base score

        text_to_check = (item.title + " " + (item.summary or "") + " " + " ".join(item.tags)).lower()

        matches = 0
        for tech in self.user_tech_stack:
            if tech in text_to_check:
                matches += 1

        # Simple sigmoid-like scaling
        if matches > 0:
            score += 0.3 * matches

        # Boost for high engagement (if available)
        if item.original_score and item.original_score > 100:
            score += 0.2

        return min(1.0, score)
