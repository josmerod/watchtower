---
name: etl-pipeline
description: Build a new Watchtower ETL pipeline the standard way, or wire an existing one into the orchestrator so it actually runs. Use whenever the user wants to add a scraper, add a data source, create an ETL, add a new feed, fetch data from a site/API/RSS, "add a pipeline", or when an ETL exists but isn't being executed. Trigger on "new etl", "scrape X", "add a data source", "fetch from", "wire up the etl", "add to the orchestrator", "it's not running".
---

# ETL Pipeline

Two styles of ETL run in production — a `BaseETL` subclass or a plain script —
and both are wired the same way. Three obligations; skip one and the pipeline
is half-built.

1. **Implement** the script: extract → transform → load, runnable on its own.
2. **Register** it in `ETL_SCRIPTS` in `run_all_etl_orchestrator.py`.
3. **Wire a consumer** — an output nobody reads is invisible.

## Obligation 1 — the pipeline

| | `BaseETL` subclass | Plain module |
| :--- | :--- | :--- |
| Registered scripts | 31 (29 direct, 2 via `SimpleETL`) | 74 (the 3 watchers and 1 miner in the list are plain scripts too) |
| Real model | `src/etl/rss_feeds/rss_feed_etl.py` | `src/etl/markets/coingecko_etl.py` |
| You write | `__init__` passing `name`; `extract`, `transform`, `load` | functions and `main()` |
| You get | stage retries, circuit breaker, checkpointing, dedup, run metrics | nothing you did not write |
| Output | `data/<name>/output/` (`self.output_dir`); file names vary | `data/<domain>/<name>_latest.json` + timestamped snapshot |
| Failure | a stage raises `ETLError` after its retries → exit 1 | whatever `main()` does — often exit 0 |
| Fits when | the source is flaky or heavy and you want that machinery | fetch → normalize → write the two JSON files tabs and the API read; no hidden state, you pick the path |

### `BaseETL` — a complete file, then its registration

```python
"""My source ETL — one-line purpose."""

import json
import logging
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL


class MySourceETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """Fetch <thing> from <source> and persist it under data/my_source/output/."""

    def __init__(self) -> None:
        super().__init__(name="my_source")

    def extract(self) -> list[dict[str, Any]]:
        """Pull raw records. fetch_json() retries transient network errors."""
        payload = self.fetch_json("https://example.com/feed.json")
        return payload["items"]

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize raw records into the output shape."""
        return [{"title": item["title"], "url": item["url"]} for item in data]

    def load(self, data: list[dict[str, Any]]) -> None:
        """Write the snapshot and the _latest copy — run() never writes data itself."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for file_name in (f"my_source_{stamp}.json", "my_source_latest.json"):
            (self.output_dir / file_name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    metrics = MySourceETL().run()
    if any(error["type"] == "CircuitBreakerOpen" for error in metrics.errors_detail):
        raise SystemExit(1)
```

Then register it — an excerpt of `ETL_SCRIPTS` in `run_all_etl_orchestrator.py`:

```python
ETL_SCRIPTS = [
    # Deals
    "src/etl/deals/lifetimo_etl.py",
    "src/etl/my_domain/my_source_etl.py",  # feeds <tab / API route>
]
```

An unregistered script never runs in production — no error, just silence.

What `run()` does (`src/etl/base.py`):

- `name` is required: it derives `data/<name>/`, its `output/` and
  `checkpoints/` subfolders and `circuit_breaker.json`, and creates the folders
  on construction.
- `extract` → `transform` → dedup → `load`, each stage attempted up to 4 times
  (5, 10, 20 s apart). Empty output from `extract` or `transform` ends the run
  without loading.
- A stage that still fails records a breaker failure and raises `ETLError` —
  the script exits non-zero. Failed or not, the run leaves
  `run_summary_latest.json` in `output_dir` and merges into
  `data/metrics/etl_runs_latest.json`.
- An **open** breaker (5 failures, 30-minute recovery) is different: `run()`
  logs a warning, returns metrics holding one `CircuitBreakerOpen` error and
  writes nothing — not even a run summary. Without the check in the guard the
  script exits 0, and the orchestrator prints SUCCESS while the data goes stale.
- Pydantic is a convention, not enforced: `run()` never validates what the
  stages return. Validate yourself with `self.validate_data(items, MyModel)` —
  invalid items are dropped and counted in `records_failed`. Only
  `TimestampedModel` instances are deduplicated; plain dicts pass through.

### Plain module — `fetch_*` → `save_*` → `main()` under a `__main__` guard

- **Fetch**: `requests` with a timeout, sending `SCRAPER_DEFAULT_USER_AGENT`
  (`src/constants/etl.py`), or `feedparser` for RSS. Retry with `@with_retry`
  or `fetch_with_retry(url, timeout=...)` from `src/utils/retry.py` — 4
  attempts, ~1/2/4 s backoff on network errors.
- **Save**: resolve the folder with `get_project_root()` and
  `ensure_directories([...])` from `src/utils/file_system.py` — never a
  hardcoded absolute path. Write `data/<domain>/<name>_YYYYMMDD_HHMMSS.json`
  and `data/<domain>/<name>_latest.json`. Keep both name parts: consumers open
  the `_latest` file, and `src/utils/snapshot_retention.py` prunes by the
  timestamp. `write_json_file(path, data, indent=...)` lives in the same
  module; no registered script uses it yet — they `json.dump` by hand.
- **Fail loudly**: this is where plain modules are weak. Most catch the network
  error inside the fetch and return what they have — `coingecko_etl.py` and
  `news_get_techcrunch.py` then exit 0, and the orchestrator prints SUCCESS
  although nothing was written. When the fetch fails entirely, log and `raise`.
- **Pydantic**: plain modules emit dicts. Validate with a `src/models/` model
  when the shape is new.

### Conventions

- **File name**: lowercase snake_case under `src/etl/<domain>/`. `<source>_etl.py`
  is the default (54 registered scripts); `news/` uses `news_get_<source>.py`
  (41) and `games/` `games_get_<source>.py` (6). The suffix does not indicate
  the style.
- **Subpackage**: 23 domain folders under `src/etl/` hold code. Add one (with
  an `__init__.py`) only for a genuinely new domain.
- **HTTP**: `requests` for APIs, `feedparser` for RSS, Playwright only for
  JS-rendered pages — it is heavy.
- **`if __name__ == "__main__":` is mandatory**: the orchestrator runs each
  entry as `uv run python <script>` from the repo root.

## Obligation 2 — register it; what the orchestrator then does

`run_script` in `run_all_etl_orchestrator.py`:

| Fact | Value |
| :--- | :--- |
| Command | `uv run python <script>` from the repo root; stdout + stderr go to `logs/<name>.log` (`coingecko_etl.py` → `logs/coingecko_etl.log`), overwritten each run. No flag runs a single entry — run the script directly |
| Concurrency | `--workers N`, default 4 (`run_all_etl.sh` passes 4). List order is only the start order: scripts wait for nothing |
| `--exclude NAME` | repeatable; matches the basename or any substring of the path — `--exclude news` skips all of `news/` |
| Timeout | 1800 s per script; 4500 s for `reddit_unified_etl.py` and `goldigging_youtube_posts.py`. On timeout the process tree is killed, `TIMEOUT:` is printed and the script counts as failed |
| Result lines | `SUCCESS:` · `ERROR: ... failed with code N` · `Warning: Script ... does not exist. Skipping.` (a missing file counts as failed) |
| Exit code | always 0 — read the `Successful:` and `Failed:` counts in its output |
| After the pool | `src.utils.snapshot_retention --keep-last 30 --apply` keeps the newest 30 timestamped `.json`/`.csv` files per name and never touches `*latest*`, state files or `data/watchers/`. Then `run_backup.py` — only if the file exists, and it is not shipped, so production runs no backup |

## Obligation 3 — wire a consumer

A new `_latest.json` is invisible until something reads it. Update what applies:

- **`src/services/data_loader.py`** — add the source to its `*_SOURCES_CONFIG`
  dict (`NEWS_SOURCES_CONFIG`, `GAMES_SOURCES_CONFIG`,
  `BENCHMARKS_SOURCES_CONFIG`, …) as
  `"<key>": {"path": get_data_path("<domain>", "<file>"), "name": "<Label>"}`.
  The dashboard tabs **and** the API (`src/api/routers.py`) read these dicts.
- **Tab-local lists**, for sources outside those dicts — among others
  `RADAR_SOURCES` in `tech_radar_tab.py` and `DATA_FILE` in
  `security_tab.py`, `markets_tab.py`, `digest_tab.py`, `fourchan_tab.py`.
- **`src/watchers/data_freshness_watcher.py`** — a `SOURCE_FILES` entry
  `{"key", "label", "path" (relative to `data/`), "warn_hours", "critical_hours"}`
  puts the source on the stale-data watch (the Metrics card).
- **`src/services/content_search.py`** — `ARTICLE_COLLECTIONS` and the
  `RELEASES_FILE`, `MARKETS_FILE`, `PAPERS_FILE`, `VIDEOS_GLOB` constants feed
  the search API (`src/api/search.py`).

## Definition of done

- [ ] `uv run python src/etl/<domain>/<my_etl>.py` runs from the repo root and
      writes `<name>_latest.json` where the consumer looks for it.
- [ ] A forced failure exits non-zero — and so does an open circuit breaker.
- [ ] The path is in `ETL_SCRIPTS`; a consumer reads the file; `SOURCE_FILES`
      lists it.
- [ ] `uv run ruff check` is clean on the new file; if a model was added,
      `uv run mypy` is clean on it.
- [ ] Any new dependency is in `pyproject.toml` and `uv.lock`.

## When an ETL "isn't running" or its data is stale

1. Not in `ETL_SCRIPTS` → add it.
2. `Warning: Script ... does not exist. Skipping.` → wrong or renamed path.
3. `SUCCESS:` but no new file → a swallowed exception (plain module) or an open
   circuit breaker (`data/<name>/circuit_breaker.json`).
4. `ERROR:` or `TIMEOUT:` → the detail is in `logs/<name>.log`
   (`/mnt/user/appdata/watchtower/logs/` on the server — `unraid-deploy` skill).
