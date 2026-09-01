"""Cross-source trend analysis ETL (spec 15 M5).

Scans the latest snapshots of every news-like source, counts keyword
mentions across distinct sources over the recent window and writes the
trending-item records consumed by ``src/web/dashboard/trend_utils.py``
(News and ArXiv tabs render the resulting badges).

No network access: this ETL only reads other components' JSON outputs.

Usage:
    uv run python src/etl/analytics/trends_etl.py

Output:
    - data/analytics/trends/latest_trends.json
    - data/analytics/trends/trends_<timestamp>.json
"""

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.data_loader import NEWS_SOURCES_CONFIG
from src.utils.file_system import get_project_root
from src.utils.logging import get_logger

logger = get_logger("TrendsETL")

OUTPUT_DIR = Path(get_project_root()) / "data" / "analytics" / "trends"

# A term trends when enough distinct sources and items mention it
MIN_SOURCES = 3
MIN_MENTIONS = 4
MAX_TREND_ITEMS = 100

STOPWORDS = {
    # English
    "about",
    "after",
    "again",
    "against",
    "their",
    "there",
    "these",
    "those",
    "which",
    "while",
    "with",
    "from",
    "this",
    "that",
    "will",
    "your",
    "have",
    "been",
    "more",
    "most",
    "than",
    "them",
    "they",
    "when",
    "what",
    "where",
    "how",
    "why",
    "who",
    "into",
    "over",
    "just",
    "new",
    "says",
    "said",
    "best",
    "top",
    "using",
    "use",
    "used",
    "get",
    "gets",
    "make",
    "makes",
    "way",
    "ways",
    "week",
    "weekly",
    "day",
    "daily",
    "year",
    "years",
    "time",
    "update",
    "updates",
    "report",
    "reports",
    "guide",
    "part",
    "full",
    "big",
    "all",
    "and",
    "the",
    "for",
    "are",
    "but",
    "not",
    "you",
    "can",
    "her",
    "was",
    "one",
    "our",
    "out",
    "has",
    "him",
    "his",
    "man",
    "now",
    "old",
    "see",
    "two",
    "did",
    "its",
    "let",
    "put",
    "say",
    "she",
    "too",
    "ann",
    # Spanish
    "para",
    "como",
    "este",
    "esta",
    "estos",
    "estas",
    "sobre",
    "tras",
    "entre",
    "hacia",
    "porque",
    "cuando",
    "donde",
    "quien",
    "todos",
    "todo",
    "toda",
    "todas",
    "más",
    "menos",
    "muy",
    "pero",
    "sans",
    "las",
    "los",
    "del",
    "con",
    "una",
    "uno",
    "sus",
    "sin",
    "nuevo",
    "nueva",
    "hace",
    "anos",
    "años",
    "semana",
    "día",
    "dia",
    "hoy",
    "ayer",
    "que",
    "por",
    "ser",
    "está",
    "están",
    "han",
    "hay",
    "ante",
    "según",
    "cómo",
    # Generic tech filler words — present everywhere, never a trend
    "data",
    "app",
    "user",
    "code",
    "tech",
    "web",
    "tool",
    "free",
    "video",
    "game",
    "review",
    "launch",
    "version",
    "release",
    "open",
    "online",
    "digital",
    "mejor",
}

TOKEN_RE = re.compile(r"[a-záéíóúüñ0-9][a-záéíóúüñ0-9\-\+\.]*", re.IGNORECASE)


def _strip_accents_for_key(term: str) -> str:
    """Normalize a token for aggregation while keeping the display form."""
    return "".join(c for c in unicodedata.normalize("NFD", term) if unicodedata.category(c) != "Mn").lower()


# A term trending in more than this fraction of all items is baseline
# vocabulary (e.g. "ai" in tech news), not a trend
MAX_ITEM_COVERAGE = 0.10

# Cap records per term so one hot keyword cannot fill the whole output
MAX_RECORDS_PER_TERM = 12

# Short tech terms worth trending despite the minimum token length
SHORT_ALLOWED = {"ai", "ml", "go", "js", "py", "qt", "ar", "vr", "os", "db", "ux", "ui", "3d"}


def tokenize_title(title: str) -> set[str]:
    """Extract meaningful keyword tokens from a title."""
    tokens = set()
    for match in TOKEN_RE.findall(title or ""):
        token = match.strip("-+.").lower()
        if token.isdigit():
            continue
        if len(token) < 3 and token not in SHORT_ALLOWED:
            continue
        if token in STOPWORDS or token.rstrip("s") in STOPWORDS:
            continue
        # Collapse english plural into singular for aggregation
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.add(token)
    return tokens


def _load_source_items(source_key: str, path: str) -> list[dict[str, Any]]:
    """Read one source snapshot, tolerating missing/corrupt files."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Skipping {source_key}: {e}")
        return []
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        for list_key in ("articles", "items", "results"):
            if isinstance(data.get(list_key), list):
                return [d for d in data[list_key] if isinstance(d, dict)]
    return []


def extract_items() -> list[dict[str, Any]]:
    """Flatten every news source snapshot into scanned items."""
    items: list[dict[str, Any]] = []
    for source_key, config in NEWS_SOURCES_CONFIG.items():
        raw_items = _load_source_items(source_key, config.get("path", ""))
        for raw in raw_items:
            title = raw.get("title") or raw.get("name") or ""
            if not title:
                continue
            items.append(
                {
                    "source_key": source_key,
                    "title": str(title),
                    "url": raw.get("url") or raw.get("link") or raw.get("html_url"),
                    "item_id": raw.get("id") or raw.get("url") or raw.get("link"),
                }
            )
    return items


def compute_trends(items: list[dict[str, Any]], min_sources: int = MIN_SOURCES, min_mentions: int = MIN_MENTIONS) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    """Compute trending terms and the items that mention them.

    Returns:
        Tuple of (trend_item_records, term_stats). Records follow the format
        expected by ``trend_utils.get_trending_items_map``.
    """
    term_items: dict[str, set[int]] = {}
    term_sources: dict[str, set[str]] = {}
    item_tokens: list[set[str]] = []

    for idx, item in enumerate(items):
        tokens = tokenize_title(item["title"])
        item_tokens.append(tokens)
        for token in tokens:
            term_items.setdefault(token, set()).add(idx)
            term_sources.setdefault(token, set()).add(item["source_key"])

    hot_terms: dict[str, dict[str, int]] = {}
    total_items = max(1, len(items))
    for term, idxs in term_items.items():
        mentions = len(idxs)
        sources = len(term_sources[term])
        if mentions >= min_mentions and sources >= min_sources:
            if mentions / total_items > MAX_ITEM_COVERAGE:
                continue  # baseline vocabulary, not a trend
            hot_terms[term] = {"mentions": mentions, "sources": sources, "score": mentions * sources}

    records: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        best_term, best_stats = None, None
        for token in item_tokens[idx]:
            stats = hot_terms.get(token)
            if stats and (best_stats is None or stats["score"] > best_stats["score"]):
                best_term, best_stats = token, stats
        # best_stats is None exactly when best_term is unset (tuple-assigned in lockstep above)
        if not best_term or best_stats is None:
            continue
        records.append(
            {
                "item_id": item["item_id"],
                "url": item["url"],
                "source_key": item["source_key"],
                "term": best_term,
                "mentions": best_stats["mentions"],
                "sources_count": best_stats["sources"],
                "is_trending": True,
                "badge": {
                    "label": f"🔥 {best_term}",
                    "color": "danger",
                    "tooltip": f"{best_stats['mentions']} mentions across {best_stats['sources']} sources",
                },
            }
        )

    # Highest-scoring terms first, then cap per term so the file covers a
    # diverse set of trends instead of the single hottest term everywhere
    records.sort(key=lambda r: r["mentions"] * r["sources_count"], reverse=True)
    per_term_count: dict[str, int] = {}
    diversified: list[dict[str, Any]] = []
    for record in records:
        term = record["term"]
        if per_term_count.get(term, 0) >= MAX_RECORDS_PER_TERM:
            continue
        per_term_count[term] = per_term_count.get(term, 0) + 1
        diversified.append(record)
    return diversified[:MAX_TREND_ITEMS], hot_terms


def save_trends(records: list[dict[str, Any]]) -> list[Path]:
    """Persist the trending records (latest + timestamped copies)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for name in (f"trends_{stamp}.json", "latest_trends.json"):
        path = OUTPUT_DIR / name
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(path)
    return written


def run() -> dict[str, Any]:
    """Run the trends pipeline end to end."""
    items = extract_items()
    records, hot_terms = compute_trends(items)
    paths = save_trends(records)
    summary = {
        "items_scanned": len(items),
        "sources_scanned": len(NEWS_SOURCES_CONFIG),
        "trending_items": len(records),
        "hot_terms": len(hot_terms),
        "top_terms": sorted(((t, s["score"]) for t, s in hot_terms.items()), key=lambda x: -x[1])[:10],
        "outputs": [str(p) for p in paths],
    }
    logger.info(f"Trends: {summary['trending_items']} trending items from {summary['hot_terms']} hot terms ({summary['items_scanned']} items scanned)")
    return summary


if __name__ == "__main__":
    run()
