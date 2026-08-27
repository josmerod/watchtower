"""Hugging Face Daily Papers ETL — community-curated trending AI research.

Fetches the daily trending papers from Hugging Face's keyless API — the de
facto successor of Papers With Code (whose API now 302s to this same site).
Each paper carries upvotes, GitHub repo/stars when available, and an
AI-generated summary. Surfaces as the "🔥 HF Trending" subtab of the ArXiv
Research tab (value: papers → implementations, ranked by community vote).

Usage:
    uv run python -m src.etl.arxiv.hf_daily_papers_etl

Output:
    data/arxiv/hf_daily_papers_latest.json (+ timestamped snapshot)
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.utils.retry import with_retry

logger = get_logger("HFDailyPapersETL")

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


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


def main() -> None:
    """Run the HF daily papers ETL."""
    logger.info("Starting HF daily papers ETL")
    try:
        records = fetch_daily_papers()
        if not records:
            logger.warning("No records fetched from HF daily papers. Exiting.")
            return
        save_daily_papers(records)
        logger.info(f"HF daily papers ETL complete: {len(records)} papers.")
    except Exception as exc:
        logger.error(f"HF daily papers ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
