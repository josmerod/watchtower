"""ETL for BridgeBench.ai — cross-benchmark AI coding leaderboard.

Fetches rankings from bridgebench.ai pages and saves as JSON.
Runnable standalone: python -m src.etl.benchmarks.bridgebench_etl
"""

import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://bridgebench.ai"
PAGES = {
    "overall": "/overall",
    "security": "/security",
    "debugging": "/debugging",
    "refactoring": "/refactoring",
    "hallucination": "/hallucination",
    "reasoning": "/reasoning",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_data_dir() -> str:
    """Get the data/benchmarks directory path."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data", "benchmarks")


def fetch_page(path: str) -> str:
    """Fetch a page from bridgebench.ai."""
    url = f"{BASE_URL}{path}"
    logger.info(f"Fetching {url}...")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_markdown_tables(html: str) -> list[dict[str, str]]:
    """Parse bridgebench.ai HTML to extract table data as list of dicts.

    The site renders markdown tables inside the HTML. We look for the
    structured table data in the Next.js SSR output.
    """
    results = []

    # Strategy 1: Look for JSON data embedded in Next.js script tags
    # bridgebench.ai uses Next.js — the data might be in __NEXT_DATA__ or
    # in script tags with type="application/ld+json"
    next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if next_data_match:
        try:
            next_json = json.loads(next_data_match.group(1))
            # Check if there's table data in the props
            props = next_json.get("props", {}).get("pageProps", {})
            if props:
                # The data might be nested in various ways
                for key, val in props.items():
                    if isinstance(val, dict) and "models" in val:
                        results = val["models"]
                        logger.info(f"Found {len(results)} models from __NEXT_DATA__")
                        return results
                    elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and "model" in str(val[0]).lower():
                        results = val
                        logger.info(f"Found {len(results)} models from __NEXT_DATA__ list")
                        return results
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"Could not parse __NEXT_DATA__: {e}")

    # Strategy 2: Parse HTML table elements directly
    table_pattern = re.compile(r'<table[^>]*>(.*?)</table>', re.DOTALL)
    tables = table_pattern.findall(html)

    if not tables:
        logger.warning("No tables found in HTML")
        return results

    # Use the last/largest table (likely the main rankings)
    table_html = max(tables, key=len) if tables else ""

    # Extract rows
    row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
    rows = row_pattern.findall(table_html)

    if not rows:
        logger.warning("No rows found in table")
        return results

    # Extract headers from first row
    header_pattern = re.compile(r'<th[^>]*>(.*?)</th>', re.DOTALL)
    headers = []
    th_matches = header_pattern.findall(rows[0])
    for h in th_matches:
        clean = re.sub(r'<[^>]+>', '', h).strip().lower()
        if clean:
            headers.append(clean)

    # If no th headers, try td in first row
    if not headers:
        td_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)
        td_matches = td_pattern.findall(rows[0])
        for h in td_matches:
            clean = re.sub(r'<[^>]+>', '', h).strip().lower()
            if clean and clean != '---':
                headers.append(clean)

    logger.info(f"Table headers: {headers}")

    # Parse data rows (skip header row)
    td_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL)
    for row in rows[1:]:
        cells = td_pattern.findall(row)
        if not cells or len(cells) < 2:
            continue

        row_data = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                clean_val = re.sub(r'<[^>]+>', '', cell).strip()
                # Skip separator rows
                if clean_val and clean_val != '---':
                    row_data[headers[i]] = clean_val
            else:
                break

        # Must have at least a model name
        model = row_data.get("model", "")
        if model:
            results.append(row_data)

    logger.info(f"Parsed {len(results)} rows from HTML table")
    return results


def normalize_rank(data: list[dict]) -> list[dict]:
    """Ensure all entries have a numeric rank. Top models may have empty rank."""
    for i, entry in enumerate(data):
        rank = entry.get("rank", "")
        if rank == "" or rank is None:
            entry["rank"] = i + 1
        else:
            try:
                entry["rank"] = int(rank)
            except (ValueError, TypeError):
                entry["rank"] = i + 1
    return data


def try_parse_float(val) -> float | str:
    """Try to parse a value as float, return string if not possible."""
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    try:
        return float(s)
    except ValueError:
        return s


def normalize_scores(data: list[dict], source: str) -> list[dict]:
    """Convert score values to floats where possible."""
    # Columns that should be numeric
    if source == "overall":
        numeric_cols = ["quality", "vibe", "security", "debugging", "refactoring",
                        "hallucination", "reasoning", "ui"]
    else:
        numeric_cols = ["score", "visible", "hidden", "repro", "regress",
                        "diagnose", "intent", "accuracy", "evidence", "tasks"]

    for entry in data:
        for col in numeric_cols:
            if col in entry:
                entry[col] = try_parse_float(entry[col])

        # Standardize model name key
        for key in list(entry.keys()):
            if key.lower() in ("model", "model name", "name"):
                if "model" not in entry:
                    entry["model"] = entry.pop(key)

    return data


def save_json(data: list[dict], filepath: str):
    """Save data as JSON with metadata."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    output = {
        "source": "bridgebench.ai",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(data),
        "models": data,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(data)} models to {filepath}")


def run():
    """Main ETL runner."""
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)

    for source, path in PAGES.items():
        try:
            html = fetch_page(path)
            raw_data = parse_markdown_tables(html)

            if not raw_data:
                logger.warning(f"No data parsed for {source}, trying alternate parsing...")
                continue

            raw_data = normalize_rank(raw_data)
            raw_data = normalize_scores(raw_data, source)

            filepath = os.path.join(data_dir, f"bridgebench_{source}.json")
            save_json(raw_data, filepath)

        except Exception as e:
            logger.error(f"Failed to process {source}: {e}")
            import traceback
            traceback.print_exc()

    logger.info("BridgeBench ETL complete.")


if __name__ == "__main__":
    run()
