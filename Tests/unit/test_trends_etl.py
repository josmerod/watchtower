"""Unit tests for the trends producer (spec 15 M5) and its dashboard consumer."""

from src.etl.analytics.trends_etl import compute_trends, tokenize_title
from src.web.dashboard.trend_utils import match_item_trend


def _item(source, title, url):
    return {"source_key": source, "title": title, "url": url, "item_id": url}


class TestTokenizeTitle:
    def test_drops_stopwords_and_short_tokens(self):
        tokens = tokenize_title("The New Way to use AI with Docker")
        assert "docker" in tokens and "ai" in tokens
        assert "the" not in tokens and "new" not in tokens and "way" not in tokens

    def test_collapses_plural(self):
        assert tokenize_title("Models") == {"model"}

    def test_handles_empty(self):
        assert tokenize_title("") == set()
        assert tokenize_title(None) == set()


class TestComputeTrends:
    def _dataset(self, size=40):
        """Build a dataset where trending terms stay under the coverage cap."""
        items = [
            _item("s1", "Docker ships release", "u1"),
            _item("s2", "Docker security fix", "u2"),
            _item("s3", "Docker trends up", "u3"),
            _item("s4", "Docker again", "u4"),
        ]
        # Unique filler titles so no other term reaches the thresholds
        for i in range(size - len(items)):
            items.append(_item(f"fill{i % 5}", f"Filler topic number {i} unique", f"f{i}"))
        return items

    def test_hot_term_detected(self):
        records, hot = compute_trends(self._dataset())
        assert "docker" in hot
        assert {r["term"] for r in records} == {"docker"}
        assert all(r["is_trending"] and r["badge"]["label"] == "🔥 docker" for r in records)

    def test_baseline_term_above_coverage_cap_excluded(self):
        # "model" in 5 of 10 items (50% coverage) is baseline vocabulary
        items = [_item(f"s{i}", f"Model update number {i}", f"m{i}") for i in range(10)]
        records, hot = compute_trends(items)
        assert "model" not in hot
        assert records == []

    def test_below_thresholds_not_hot(self):
        items = [
            _item("s1", "Kubernetes up", "u1"),
            _item("s2", "Kubernetes down", "u2"),
            _item("s3", "Kubernetes flat", "u3"),
        ]
        records, hot = compute_trends(items)
        assert hot == {} and records == []


class TestMatchItemTrend:
    MAP = {
        "u1": {"item_id": "u1", "url": "http://x/1", "term": "docker", "is_trending": True, "badge": {"label": "🔥 docker"}},
        "category:techcrunch": {"item_id": "category:techcrunch", "term": "kubernetes", "is_trending": True, "badge": {"label": "🔥 kubernetes"}},
    }

    def test_match_by_id(self):
        assert match_item_trend({"id": "u1"}, self.MAP)["term"] == "docker"

    def test_match_by_url(self):
        record = {"url": "http://x/1"}
        assert match_item_trend(record, self.MAP)["term"] == "docker"

    def test_match_by_category(self):
        assert match_item_trend({"source": "techcrunch"}, self.MAP)["term"] == "kubernetes"

    def test_match_by_title_term(self):
        assert match_item_trend({"title": "Why Docker wins"}, self.MAP)["term"] == "docker"

    def test_no_match(self):
        assert match_item_trend({"title": "Nothing here"}, self.MAP) is None
        assert match_item_trend({"title": "x"}, {}) is None
