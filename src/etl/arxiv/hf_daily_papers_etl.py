"""Hugging Face Daily Papers ETL — community-curated trending AI research.

Fetches the daily trending papers from Hugging Face's keyless API — the de
facto successor of Papers With Code (whose API now 302s to this same site).
Each paper carries upvotes, GitHub repo/stars when available, and an
AI-generated summary. Surfaces as the "🔥 HF Trending" subtab of the ArXiv
Research tab (value: papers → implementations, ranked by community vote).

Optionally enriches the top papers with CrossRef citation counts. The HF API
exposes no DOIs and arXiv DOIs (10.48550/*) are DataCite-registered, so the
lookup goes through CrossRef bibliographic title search with a strict
token-containment matcher (verified live: correct matches score >= 0.9,
noise hits on fresh preprints score well below). Failures simply leave the
additive fields (citation_count/citation_source/citation_doi) absent.
A sidecar cache (data/arxiv/hf_paper_citations.json, TTL ~7 days) keeps
repeated runs from re-querying CrossRef.

Usage:
    uv run python -m src.etl.arxiv.hf_daily_papers_etl

Output:
    data/arxiv/hf_daily_papers_latest.json (+ timestamped snapshot)
    data/arxiv/hf_paper_citations.json (citation sidecar cache)
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("HFDailyPapersETL")

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"

# --- CrossRef citation enrichment knobs -----------------------------------

CROSSREF_API_BASE = "https://api.crossref.org/works"
CROSSREF_MAILTO_ENV = "CROSSREF_MAILTO"
CROSSREF_MAILTO_DEFAULT = "watchtower@example.com"
CROSSREF_TIMEOUT_SECONDS = 30
CITATION_ENRICH_MAX_PAPERS = 30
CITATION_LOOKUP_DELAY_SECONDS = 1.1
CITATION_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
CITATION_CACHE_FILENAME = "hf_paper_citations.json"
CITATION_TITLE_MATCH_THRESHOLD = 0.9
_TITLE_STOPWORDS = frozenset({"a", "an", "the", "of", "for", "in", "on", "to", "and", "with", "from", "at", "by", "is", "are", "as", "its"})


@with_retry
def fetch_daily_papers() -> list[dict[str, Any]]:
    """Fetch and normalize today's trending papers from Hugging Face."""
    records: list[dict[str, Any]] = []
    logger.info(f"Fetching HF daily papers from {HF_DAILY_PAPERS_URL}")
    try:
        response = requests.get(HF_DAILY_PAPERS_URL, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()
        items = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.error(f"Could not fetch HF daily papers: {exc}")
        return records

    for item in items:
        paper = item.get("paper", {})
        paper_id = str(paper.get("id", "")).strip()
        if not paper_id or not paper.get("title"):
            continue
        records.append(
            {
                "source": "hf_daily_papers",
                "source_category": "trending_research",
                "id": f"https://arxiv.org/abs/{paper_id}",
                "link": f"https://huggingface.co/papers/{paper_id}",
                "title": paper.get("title", "").replace("\n", " ").strip(),
                "summary": (paper.get("summary") or paper.get("ai_summary") or "")[:800],
                "authors": [a.get("name", "") for a in paper.get("authors", []) if isinstance(a, dict)],
                "published": paper.get("publishedAt", ""),
                "upvotes": paper.get("upvotes", 0) or 0,
                "github_html_url": paper.get("githubRepo") or "",
                "github_stars": paper.get("githubStars"),
                "ai_keywords": paper.get("ai_keywords", [])[:8],
                "num_comments": item.get("numComments", 0) or 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "platform": "huggingface",
                "content_type": "research_paper",
                "language": "en",
                "region": "global",
            }
        )
    # Highest community vote first — that is the whole value of this feed
    records.sort(key=lambda r: r["upvotes"], reverse=True)
    logger.info(f"Retrieved {len(records)} trending papers ({sum(1 for r in records if r['github_html_url'])} with GitHub repos)")
    return records


def save_daily_papers(records: list[dict[str, Any]]) -> None:
    """Persist the trending papers under ``data/arxiv/``."""
    if not records:
        logger.info("No HF daily papers to save. Skipping.")
        return
    output_dir = os.path.join(get_project_root(), "data", "arxiv")
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    latest = os.path.join(output_dir, "hf_daily_papers_latest.json")
    snapshot = os.path.join(output_dir, f"hf_daily_papers_{timestamp}.json")
    for path in (snapshot, latest):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(records)} HF daily papers to {latest}")


def _title_tokens(title: str) -> list[str]:
    """Normalize a paper title into significant lowercase tokens.

    Strips punctuation/LaTeX noise and drops stopwords and single characters
    so that token containment is robust to "X-Bench: Long subtitle" vs the
    published short title and to minor wording differences.
    """
    cleaned = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return [t for t in cleaned.split() if len(t) > 1 and t not in _TITLE_STOPWORDS]


def title_match_confidence(query_title: str, candidate_title: str) -> float:
    """Score how plausibly two titles refer to the same work (0.0-1.0).

    Uses the max of Jaccard overlap and containment of the shorter token set
    in the longer one. Containment is what makes the matcher sane: CrossRef
    relevance reliably ranks the true record first, but its stored title is
    often just the short form ("Optuna" vs the full arXiv title), which
    exact-string similarity would wrongly reject while containment scores 1.0.
    """
    query_tokens = _title_tokens(query_title)
    candidate_tokens = _title_tokens(candidate_title)
    if not query_tokens or not candidate_tokens:
        return 0.0
    intersection = len(set(query_tokens) & set(candidate_tokens))
    if intersection == 0:
        return 0.0
    jaccard = intersection / len(set(query_tokens) | set(candidate_tokens))
    containment = intersection / min(len(query_tokens), len(candidate_tokens))
    return max(jaccard, containment)


def _crossref_mailto() -> str:
    """Return the contact email for the CrossRef polite pool (env-overridable)."""
    return os.getenv(CROSSREF_MAILTO_ENV, CROSSREF_MAILTO_DEFAULT).strip() or CROSSREF_MAILTO_DEFAULT


def _crossref_get(params: str) -> dict[str, Any] | None:
    """GET a CrossRef works endpoint fragment and return its JSON, or None on any failure.

    ``params`` is appended to ``CROSSREF_API_BASE`` and must already be
    URL-encoded. The mailto query parameter keeps us in the polite pool.
    """
    url = f"{CROSSREF_API_BASE}{params}"
    separator = "&" if "?" in params else "?"
    url = f"{url}{separator}mailto={_crossref_mailto()}"
    try:
        response = requests.get(url, headers={"User-Agent": f"{SCRAPER_DEFAULT_USER_AGENT} (mailto:{_crossref_mailto()})"}, timeout=CROSSREF_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except (requests.RequestException, ValueError) as exc:
        logger.debug(f"CrossRef lookup failed for {url}: {exc}")
        return None


def fetch_citation_by_doi(doi: str) -> dict[str, Any] | None:
    """Fetch the CrossRef citation count for a DOI.

    Returns:
        ``{"citation_count": int, "citation_source": "doi", "citation_doi": doi}``
        on success, otherwise ``None``.
    """
    # requests.utils.quote is literally urllib.parse.quote but untyped in the
    # requests stubs; import it directly.
    encoded = quote(doi.strip(), safe="")
    payload = _crossref_get(f"/{encoded}")
    if not payload:
        return None
    message = payload.get("message") or {}
    count = message.get("is-referenced-by-count")
    if not isinstance(count, int) or count < 0:
        return None
    return {"citation_count": count, "citation_source": "doi", "citation_doi": doi.strip()}


def fetch_citation_by_title(title: str, rows: int = 3) -> dict[str, Any] | None:
    """Find a paper in CrossRef by bibliographic title search.

    Only accepts a hit whose title tokens are a near-supset/subset of the
    query (confidence >= CITATION_TITLE_MATCH_THRESHOLD); for days-old
    preprints with no published version this correctly returns ``None``
    instead of attaching some unrelated paper's count.
    """
    query = quote(title)
    payload = _crossref_get(f"?query.bibliographic={query}&rows={rows}")
    if not payload:
        return None
    items = (payload.get("message") or {}).get("items") or []
    best: tuple[float, dict[str, Any]] | None = None
    for item in items:
        stored_titles = [t for t in (item.get("title") or []) if isinstance(t, str)]
        subtitle = [s for s in (item.get("subtitle") or []) if isinstance(s, str)]
        stored_titles += subtitle  # stored title sometimes keeps the qualifier in the subtitle
        for stored in stored_titles:
            confidence = title_match_confidence(title, stored)
            if best is None or confidence > best[0]:
                best = (confidence, item)
    if best is None or best[0] < CITATION_TITLE_MATCH_THRESHOLD:
        return None
    item = best[1]
    count = item.get("is-referenced-by-count")
    if not isinstance(count, int) or count < 0:
        return None
    return {"citation_count": count, "citation_source": "title", "citation_doi": str(item.get("DOI") or "")}


def citations_cache_path() -> str:
    """Return the path of the citation sidecar cache file."""
    return os.path.join(get_project_root(), "data", "arxiv", CITATION_CACHE_FILENAME)


def load_citation_cache() -> dict[str, dict[str, Any]]:
    """Load the citation sidecar cache; a missing or corrupt file yields an empty cache."""
    path = citations_cache_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
        return cache if isinstance(cache, dict) else {}
    except (OSError, ValueError) as exc:
        logger.warning(f"Could not read citation cache {path}: {exc}")
        return {}


def save_citation_cache(cache: dict[str, dict[str, Any]]) -> None:
    """Persist the citation sidecar cache (best-effort — never raises)."""
    path = citations_cache_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.warning(f"Could not write citation cache {path}: {exc}")


def _citation_cache_key(record: dict[str, Any]) -> str | None:
    """Return the sidecar cache key for a paper record (DOI when present, else normalized title)."""
    doi = str(record.get("doi") or record.get("citation_doi") or "").strip()
    if doi:
        return doi.lower()
    title = str(record.get("title") or "").strip()
    tokens = _title_tokens(title)
    return f"title:{' '.join(tokens)}" if tokens else None


def _cache_entry_is_fresh(entry: object, now_ts: float) -> bool:
    """Check whether a cache entry is within the TTL window."""
    if not isinstance(entry, dict):
        return False
    checked_at = entry.get("checked_at")
    try:
        checked_ts = datetime.fromisoformat(str(checked_at)).timestamp()
    except (TypeError, ValueError):
        return False
    count = entry.get("citation_count")
    return (now_ts - checked_ts) < CITATION_CACHE_TTL_SECONDS and isinstance(count, int) and not isinstance(count, bool)


def enrich_with_citations(
    records: list[dict[str, Any]],
    cache: dict[str, dict[str, Any]] | None = None,
    *,
    max_papers: int = CITATION_ENRICH_MAX_PAPERS,
    doi_fetcher=None,
    title_fetcher=None,
    sleep_fn=time.sleep,
    now_ts: float | None = None,
) -> dict[str, dict[str, Any]]:
    """Add CrossRef citation counts to the top papers by upvotes (in place).

    Only the first ``max_papers`` records are considered — they must already
    be sorted by upvotes (fetch_daily_papers sorts). Fresh cache hits are
    merged without network calls; misses query CrossRef with polite pacing.
    Failures leave the additive citation fields absent, and the updated cache
    is returned so the caller can persist it.
    """
    if cache is None:
        cache = load_citation_cache()
    doi_fetcher = doi_fetcher or fetch_citation_by_doi
    title_fetcher = title_fetcher or fetch_citation_by_title
    now_ts = now_ts if now_ts is not None else datetime.now(timezone.utc).timestamp()
    enriched = 0
    lookups = 0

    for record in records[:max_papers]:
        key = _citation_cache_key(record)
        if not key:
            continue
        entry = cache.get(key)
        if entry is not None and _cache_entry_is_fresh(entry, now_ts):
            record["citation_count"] = entry["citation_count"]
            record["citation_source"] = entry.get("citation_source", "")
            record["citation_doi"] = entry.get("citation_doi", "")
            enriched += 1
            continue

        if lookups:
            sleep_fn(CITATION_LOOKUP_DELAY_SECONDS)  # pace only between actual network lookups
        lookups += 1
        doi = str(record.get("doi") or "").strip()
        result = doi_fetcher(doi) if doi else title_fetcher(str(record.get("title") or ""))

        if result is None:
            continue
        cache[key] = {**result, "checked_at": datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat()}
        record["citation_count"] = result["citation_count"]
        record["citation_source"] = result["citation_source"]
        record["citation_doi"] = result.get("citation_doi", "")
        enriched += 1

    logger.info(f"Citation enrichment: {enriched}/{min(len(records), max_papers)} top papers carry a citation count (cache now {len(cache)} entries)")
    return cache


def main() -> None:
    """Run the HF daily papers ETL."""
    logger.info("Starting HF daily papers ETL")
    try:
        records = fetch_daily_papers()
        if not records:
            logger.warning("No records fetched from HF daily papers. Exiting.")
            return
        try:
            cache = enrich_with_citations(records)
            save_citation_cache(cache)
        except Exception as exc:  # enrichment is best-effort, never block the main save
            logger.warning(f"Citation enrichment failed; saving papers without counts: {exc}")
        save_daily_papers(records)
        logger.info(f"HF daily papers ETL complete: {len(records)} papers.")
    except Exception as exc:
        logger.error(f"HF daily papers ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
