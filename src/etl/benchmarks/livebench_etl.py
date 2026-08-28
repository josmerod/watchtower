"""ETL for the LiveBench LLM leaderboard (livebench.ai).

LiveBench is a contamination-free LLM benchmark with per-category scores
(reasoning, coding, agentic coding, mathematics, data analysis, language,
instruction following) refreshed roughly every six months.

Transport note: the leaderboard data files (``table_<release>.csv`` etc.) are
served keyless, but the origin 404s plain ``requests`` clients (TLS/HTTP2
fingerprint filtering) while real browsers always succeed. The ETL therefore
renders the site in the shared browserless Chrome instance (same pattern as
``src.etl.news.news_get_uneed`` / ``src.etl.opensource.opensource_projects_etl``:
``BROWSERLESS_ENDPOINT`` env var with localhost fallback) and reads the
leaderboard straight from the rendered DOM. The raw CSV observed on the wire is
persisted alongside the output for provenance when available.

Output (under ``data/benchmarks/``):
- ``livebench_latest.json`` — parsed leaderboard (per-model category scores).
- ``livebench_<timestamp>.json`` — timestamped copy.
- ``livebench_scores.csv`` — raw scores CSV captured from the page load.

Failure policy: when scraping fails after retries the existing files are left
untouched (last-good data wins).

Runnable standalone: ``uv run python -m src.etl.benchmarks.livebench_etl``
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.utils.file_system import get_project_root

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LIVEBENCH_URL = "https://livebench.ai/"
OUTPUT_LATEST = "livebench_latest.json"
RAW_CSV_NAME = "livebench_scores.csv"
REQUEST_TIMEOUT = 90
RETRY_DELAYS: tuple[int, ...] = (5, 15)
COST_KEY = "cost_per_successful_task"

# JS executed in the page: grab the release shown in the header plus the rows
# of the largest table (the leaderboard). Kept as a module constant so tests
# can assert it stays in sync with the extraction contract.
EXTRACT_JS = """() => {
    const tables = [...document.querySelectorAll('table')];
    const t = tables.sort((a, b) => b.querySelectorAll('tr').length - a.querySelectorAll('tr').length)[0];
    if (!t) return null;
    const rows = [...t.querySelectorAll('tr')].map(tr => [...tr.querySelectorAll('td,th')].map(td => td.innerText.trim()));
    const release = document.body.innerText.match(/Showing LiveBench-([0-9-]+)/);
    return {release: release ? release[1] : null, rows};
}"""


def get_data_dir() -> Path:
    """Return the ``data/benchmarks`` directory, creating it if needed."""
    data_dir = Path(get_project_root()) / "data" / "benchmarks"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _norm_category(label: str) -> str:
    """Normalize a leaderboard column header into a snake_case key.

    Strips sort arrows (``▼``), newlines and spaces, e.g.
    ``"COST PER\\nSUCCESSFUL TASK"`` -> ``"cost_per_successful_task"``.
    """
    cleaned = label.replace("▼", "").replace("\n", " ").strip().lower()
    return "_".join(part for part in cleaned.split() if part)


def parse_score(value: str | None) -> float | None:
    """Best-effort parse of a score cell to float."""
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_cost(value: str | None) -> float | None:
    """Parse a dollar cost cell (``"$1.439"``) to float."""
    if value is None:
        return None
    try:
        return float(str(value).strip().removeprefix("$").replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_leaderboard(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Convert the raw DOM payload into the persisted leaderboard schema.

    Args:
        payload: ``{"release": str | None, "rows": list[list[str]]}`` — the
            raw table rows scraped from the rendered page (header included).

    Returns:
        The leaderboard dict (see module docstring) or ``None`` when the
        payload has no usable rows.
    """
    rows = payload.get("rows") or []
    if len(rows) < 2:
        return None

    header = rows[0]
    # Column layout: [expander, MODEL, ...category scores..., cost]. Skip
    # leading empty/expander cells and locate the model column by header.
    model_idx = next((i for i, cell in enumerate(header) if _norm_category(cell) == "model"), 1)
    score_keys: list[tuple[int, str]] = []
    for i, cell in enumerate(header):
        if i == model_idx:
            continue
        key = _norm_category(cell)
        if key:
            score_keys.append((i, key))

    categories = [key for _, key in score_keys if key != COST_KEY]

    models: list[dict[str, Any]] = []
    for row in rows[1:]:
        if len(row) <= model_idx:
            continue
        name = row[model_idx].strip()
        if not name or name.lower() == "model":
            continue
        entry: dict[str, Any] = {"rank": len(models) + 1, "model": name}
        for idx, key in score_keys:
            value = row[idx] if idx < len(row) else None
            entry[key] = parse_cost(value) if key == COST_KEY else parse_score(value)
        if entry.get("overall") is None:
            logger.debug(f"Row without overall score skipped: {name!r}")
            continue
        models.append(entry)

    if not models:
        return None

    return {
        "source": "livebench.ai",
        "source_url": LIVEBENCH_URL,
        "release": payload.get("release"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "categories": categories,
        "cost_key": COST_KEY,
        "models_count": len(models),
        "models": models,
    }


def _wait_for_table(page, timeout_s: int = 30) -> None:
    """Poll until the leaderboard table has data rows (or timeout)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if page.evaluate("document.querySelectorAll('table tr').length") > 1:
                return
        except Exception:
            pass
        time.sleep(1)


def scrape_leaderboard() -> dict[str, Any] | None:
    """Render livebench.ai in browserless and extract the leaderboard.

    Returns:
        ``{"release": ..., "rows": ..., "raw_csv": ...}`` on success, ``None``
        on any failure (logged, never raised).
    """
    from playwright.sync_api import sync_playwright

    raw_csv: str | None = None

    def _capture_csv(response) -> None:
        """Capture the raw leaderboard CSV seen on the wire, for provenance."""
        nonlocal raw_csv
        if raw_csv is None and "table_" in response.url and ".csv" in response.url:
            try:
                body = response.text()
                if body.lstrip().startswith("model,"):
                    raw_csv = body
            except Exception:
                pass

    try:
        with sync_playwright() as p:
            browserless_ws = os.getenv("BROWSERLESS_ENDPOINT", "ws://localhost:3000")
            try:
                logger.info(f"Connecting to remote browser at {browserless_ws}")
                browser = p.chromium.connect_over_cdp(browserless_ws)
                context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=SCRAPER_DEFAULT_USER_AGENT)
            except Exception as e:
                logger.warning(f"Could not connect to remote browser: {e}. Falling back to local launch.")
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=SCRAPER_DEFAULT_USER_AGENT)

            page = context.new_page()
            page.on("response", _capture_csv)
            try:
                logger.info(f"Navigating to {LIVEBENCH_URL}")
                page.goto(LIVEBENCH_URL, timeout=REQUEST_TIMEOUT * 1000, wait_until="load")
                _wait_for_table(page)
                payload = page.evaluate(EXTRACT_JS)
            finally:
                context.close()
                browser.close()
    except Exception as e:
        logger.error(f"LiveBench scrape failed: {type(e).__name__}: {e}")
        return None

    if not payload or not payload.get("rows"):
        logger.warning("LiveBench page rendered no leaderboard rows.")
        return None
    payload["raw_csv"] = raw_csv
    return payload


def fetch_livebench_data(max_retries: int = 3) -> dict[str, Any] | None:
    """Scrape the leaderboard with retries and return the parsed payload."""
    delays = (0, *RETRY_DELAYS)[:max_retries]
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            logger.info(f"Retrying in {delay}s (attempt {attempt}/{max_retries})...")
            time.sleep(delay)
        payload = scrape_leaderboard()
        if payload:
            logger.info(f"Scrape succeeded on attempt {attempt}/{max_retries} (release={payload.get('release')}, rows={len(payload.get('rows', []))}).")
            return payload
        logger.warning(f"Scrape attempt {attempt}/{max_retries} returned no data.")
    return None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write ``data`` as pretty JSON to ``path``."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def save_json(data: dict[str, Any], filename: str) -> Path:
    """Write ``data`` to ``data/benchmarks/<filename>`` and return the path."""
    out_path = get_data_dir() / filename
    _write_json(out_path, data)
    logger.info(f"Saved {data.get('models_count', '?')} models to {out_path}")
    return out_path


def run() -> None:
    """Scrape LiveBench and persist latest + timestamped outputs.

    On failure the previous outputs are kept untouched (last-good wins).
    """
    logger.info("Starting LiveBench leaderboard fetch...")
    payload = fetch_livebench_data()
    data = parse_leaderboard(payload) if payload else None
    if data is None:
        logger.warning("No LiveBench data fetched — keeping existing files untouched.")
        return

    save_json(data, OUTPUT_LATEST)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_json(data, f"livebench_{timestamp}.json")

    raw_csv = payload.get("raw_csv") if payload else None
    if raw_csv:
        csv_path = get_data_dir() / RAW_CSV_NAME
        csv_path.write_text(raw_csv, encoding="utf-8")
        logger.info(f"Saved raw CSV snapshot to {csv_path}")

    logger.info(f"Done: release={data['release']}, {data['models_count']} models.")


if __name__ == "__main__":
    run()
