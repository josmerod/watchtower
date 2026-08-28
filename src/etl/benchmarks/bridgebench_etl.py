"""ETL for BridgeBench.ai — AI coding arena leaderboard (Elo).

BridgeBench restructured its site (2026): the old per-category pages
(/overall, /security, …) are gone. The reliable, server-rendered surface is
now the arena Elo leaderboard at /arena/leaderboard (rank, model, Elo, W-L,
Win%, 3-0 sweeps). This ETL scrapes that table and writes
``data/benchmarks/bridgebench_overall.json`` — the same filename the
dashboard tab already reads — so the BridgeBench section works again.

Runnable standalone: ``uv run python -m src.etl.benchmarks.bridgebench_etl``
"""

import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timezone
from html import unescape

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://bridgebench.ai"
LEADERBOARD_PATH = "/arena/leaderboard"

HEADERS = {
    "User-Agent": SCRAPER_DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_data_dir() -> str:
    """Get the data/benchmarks directory path."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data", "benchmarks")


def fetch_leaderboard_html() -> str:
    """Fetch the arena leaderboard page HTML."""
    url = f"{BASE_URL}{LEADERBOARD_PATH}"
    logger.info(f"Fetching {url}...")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _clean(cell_html: str) -> str:
    """Strip tags/entities and collapse whitespace from a table cell."""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", cell_html))).strip()


def parse_leaderboard(html: str) -> list[dict]:
    """Parse the Elo leaderboard HTML table into model records.

    Expected columns: #, Model, Elo, W-L, Win%, 3-0.
    """
    results: list[dict] = []
    for table_html in re.findall(r"<table[^>]*>(.*?)</table>", html, re.S | re.I):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.S | re.I)
        if not rows:
            continue
        header_cells = [_clean(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", rows[0], re.S | re.I)]
        if not header_cells or "Model" not in header_cells or "Elo" not in header_cells:
            continue
        for i, row in enumerate(rows[1:], start=1):
            cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
            if len(cells) < 4:
                continue
            # Cell 1 is the model name (header col 0 is '#'); cells may carry
            # badges like "Provisional" appended to the name — keep them.
            model = cells[1] if len(cells) > 1 else cells[0]
            record = {
                "rank": _try_parse_int(cells[0], default=i),
                "model": model,
                "elo": _try_parse_int(cells[2]) if len(cells) > 2 else None,
                "win_loss": cells[3] if len(cells) > 3 else "",
                "win_percentage": _try_parse_float(cells[4].rstrip("%")) if len(cells) > 4 else None,
                "sweeps_3_0": _try_parse_int(cells[5]) if len(cells) > 5 else None,
            }
            results.append(record)
        break  # only the first (main) leaderboard table
    return results


def _try_parse_int(value: str, default: int | None = None) -> int | None:
    """Best-effort int parse."""
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return default


def _try_parse_float(value: str) -> float | None:
    """Best-effort float parse."""
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def save_json(data: list[dict], filepath: str) -> None:
    """Save leaderboard data to JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    payload = {
        "source": "bridgebench.ai/arena/leaderboard",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(data),
        "models": data,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data)} models to {filepath}")


def run():
    """Fetch the BridgeBench arena leaderboard and persist it."""
    try:
        html = fetch_leaderboard_html()
        models = parse_leaderboard(html)
        if not models:
            logger.warning("No leaderboard rows parsed — site layout may have changed again.")
            return
        save_json(models, os.path.join(get_data_dir(), "bridgebench_overall.json"))
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"BridgeBench ETL failed: {e}")
        raise


if __name__ == "__main__":
    run()
