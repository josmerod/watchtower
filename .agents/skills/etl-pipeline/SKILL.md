---
name: etl-pipeline
description: Add a data source to Watchtower the standard way — an RSS/Atom feed, a news site, an API or a page — build or fix an ETL, run one ETL on its own, or wire an existing script into the orchestrator so it actually runs in production. Use whenever the user wants to add a scraper, a feed or a source, "add a source", "scrape X", "añade un feed", "añadir fuente", "nueva fuente", "nuevo etl", "fetch from", "wire up the etl", "add to the orchestrator", "run just this etl", "probar el etl", or when an ETL is not being executed or its data is stale. Trigger on "rss", "etl", "no corre", "datos antiguos", "it's not running".
---

# ETL Pipeline

A source is done when five things are true. Skip one and it is half-built: an
unregistered script never runs (no error, just silence), an output nobody
reads is invisible, and an untested one rots.

1. **Implement** the script — or, for an RSS/Atom feed, add one dict to an
   existing list.
2. **Run it on its own**, into a temporary project root.
3. **Register** it in `ETL_SCRIPTS` in `run_all_etl_orchestrator.py`.
4. **Wire a consumer**: what reads the file, and the freshness watch.
5. **Test** it under `Tests/etl/`, with the network stubbed.

## Pick the path

| The source is | Path | Work |
| :--- | :--- | :--- |
| An RSS or Atom feed that fits inside Knowledge Garden's «RSS Feeds» | Add it to `DEFAULT_FEEDS` in `src/etl/rss_feeds/rss_feed_etl.py` | One dict; no script, nothing to register |
| A news site or feed that gets its own subtab in News | `src/etl/news/news_get_<source>.py`, a plain module | Steps 1–5 plus two News-specific edits |
| Anything else: an API, a page, a site that needs Playwright | A new script under `src/etl/<domain>/`, in either style | Steps 1–5 |

Counts were measured on 2026-11-28; re-count before quoting them:

```bash
grep -vE '^\s*#' run_all_etl_orchestrator.py | sed -n '/^ETL_SCRIPTS = \[/,/^\]/p' | grep -cE '"[^"]+\.py"'
```

### The no-code path: a feed in `DEFAULT_FEEDS`

```python
DEFAULT_FEEDS: list[dict[str, str]] = [
    ...,
    {
        "url": "https://blog.example.com/feed.xml",
        "name": "Example Engineering",
    },
]
```

`RSSFeedETL` (name `rss_feeds`) is registered, reads the list at run time and
writes every entry to `data/rss_feeds/output/latest.json` with
`source: "RSS (<name>)"`. `KNOWLEDGE_SOURCES_CONFIG["rss_feeds"]` in
`src/services/data_loader.py` serves that file to Knowledge Garden and to the
API. Know what you get:

- At most 50 entries per feed. A feed that fails is logged and skipped; the
  others still load.
- Title and description are stored as plain text, the description cut at 500
  characters.
- All the feeds share one subtab, so the feed is not a source of its own in
  the UI or in `/api/v1/sources`.

When the feed needs its own subtab, its own filters or more than 50 entries,
it is a source: take one of the two other paths.

### A news source

Steps 1–5, plus:

- **`NEWS_SOURCES_CONFIG`** in `src/services/data_loader.py`:
  `"<key>": {"path": get_data_path("<domain>", "<file>"), "name": "<Label>"}`.
  The News tab, the global search and the API (`src/api/routers.py`) all read
  this dict.
- **`NEWS_TAB_DEFINITIONS`** in `src/web/dashboard/components/news_tab.py`:
  one entry `{"label", "keys", "id"}`, or the new key added to the `keys` of an
  aggregated subtab. The tab builds its subtabs and its search callbacks from
  this list, so a key missing from it has no subtab. Keys carry no dash: the
  search callback splits its input id on `-`.
- **The article shape** the tab reads: `title`, `url`, `published_at` (ISO),
  `source`, `summary` or `description` (plain text), and optionally `author`.

## Step 1 — the script: one of two styles

| | `BaseETL` subclass | Plain module |
| :--- | :--- | :--- |
| Real model | `src/etl/rss_feeds/rss_feed_etl.py` | `src/etl/markets/coingecko_etl.py` |
| You write | `__init__` passing `name`; `extract`, `transform`, `load` | functions and `main()` |
| You get | stage retries, circuit breaker, checkpointing, dedup, run metrics | nothing you did not write |
| Output | `data/<name>/output/` (`self.output_dir`) | `data/<domain>/<name>_latest.json` and a timestamped snapshot |
| Failure | a stage raises `ETLError` after its retries, so the script exits 1 | whatever `main()` does — often exit 0 |
| Fits when | the source is flaky or heavy and you want that machinery | fetch → normalize → write the files a tab reads |

Of the 103 entries on 2026-11-28 — two watchers and one miner among them —
the 100 ETLs split into 28 in the `BaseETL` family and 72 plain. Copy a
sibling of the subpackage you are editing: its style, output path and file
name are the convention there.

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
  attempts with ~1/2/4 s backoff on network errors.
- **Save**: resolve the folder with `get_project_root()` and
  `ensure_directories([...])` from `src/utils/file_system.py` — never a
  hardcoded absolute path, and never a path derived from `__file__`: that one
  escapes the temporary root of step 2. Write
  `data/<domain>/<name>_YYYYMMDD_HHMMSS.json` and
  `data/<domain>/<name>_latest.json`. Keep both name parts: consumers open the
  `_latest` file, and `src/utils/snapshot_retention.py` prunes by the
  timestamp.
- **Store plain text.** Titles and summaries go through
  `html_to_text()` and `plain_excerpt(text, 500)` from `src/utils/text.py`.
  Feeds hand over HTML: stored raw it bloats the file (one Kagi feed went from
  546,787 to 76,960 bytes), shows tags in the cards and makes the search match
  markup instead of words. One limit to know: anything shaped like a tag is
  removed, including a literal `<Suspense>` in a title.
- **Fail loudly.** This is where plain modules are weak: most catch the network
  error inside the fetch and return what they have, then exit 0, and the
  orchestrator prints SUCCESS although nothing was written. When the fetch
  fails entirely, log and `raise`.
- **Pydantic**: plain modules emit dicts. Validate with a `src/models/` model
  when the shape is new.

### Conventions

- **File name**: lowercase snake_case under `src/etl/<domain>/`. `<source>_etl.py`
  is the default; `news/` uses `news_get_<source>.py` and `games/`
  `games_get_<source>.py`. The suffix does not indicate the style.
- **Subpackage**: 22 domain folders under `src/etl/` hold code. Add one (with
  an `__init__.py`) only for a genuinely new domain.
- **HTTP**: `requests` for APIs, `feedparser` for RSS, Playwright only for
  JS-rendered pages — it is heavy.
- **`if __name__ == "__main__":` is mandatory**: the orchestrator runs each
  entry as `uv run python <script>` from the repository root.
- **No API key** unless the user opts in: RSS feeds and public endpoints
  first. A key that is needed goes on `CONTAINER_ENV_KEYS` in
  `deployment/deploy.py` and in `.env.example`, or it never reaches the
  container (`unraid-deploy` skill).

## Step 2 — run one ETL, without touching the checkout's `data/`

`data/` is historical, gitignored and never clobbered, and a check that runs
an ETL "just to see" writes into it. Two different helpers decide where it
is, and both have to be redirected:

- plain modules ask `get_project_root()` in `src/utils/file_system.py`;
- `BaseETL` asks `Settings.project_root` (`src/config/settings.py`), which
  reads the environment variable `WATCHTOWER_PROJECT_ROOT`, and derives from it
  `data/`, `logs/` and the log file.

The bundled script does both before anything under `src/` is imported:

```bash
uv run python .agents/skills/etl-pipeline/scripts/run_etl_temp_root.py src/etl/news/news_get_devto.py
uv run python .agents/skills/etl-pipeline/scripts/run_etl_temp_root.py src.etl.news.news_get_devto --any-flag 1
uv run python .agents/skills/etl-pipeline/scripts/run_etl_temp_root.py --seed-data <a data dir> src/etl/courses/ms_applied_skills_etl.py
```

Run it from the root of the checkout you are working in, so it is that tree's
code that runs. It creates a temporary project root, prints its path and, at
the end, the files written under it; the root stays for inspection. It copies
nothing in: an ETL that merges with a file already under `data/` sees none.

An ETL that keeps state in its output — stamps of first detection,
checkpoints, a file it merges into — does not show what it really does on an
empty root. Pass `--seed-data <a data dir>`: that `data/` is copied into the
root before the ETL starts (`metrics/` is left out) and only read. The run is
then the next production cycle in miniature. `ms_applied_skills_etl.py` on a
copy of production `data/` kept 121 of its 122 `first_detected_at` stamps and
stamped one new credential — the fact that proved the change was safe to
deploy, and one an empty root cannot show.

Do not run `uv run python src/etl/...` directly. Redirecting only the first
helper once left `data/` and `logs/` inside a worktree, and a `logs/` file held
open by a running process cannot be deleted on Windows.

## Step 3 — register it

```python
ETL_SCRIPTS = [
    # Deals
    "src/etl/deals/lifetimo_etl.py",
    "src/etl/my_domain/my_source_etl.py",  # feeds <tab / API route>
]
```

What the orchestrator then does (`run_all_etl_orchestrator.py`):

| Fact | Value |
| :--- | :--- |
| Command | `uv run python <script>` from the repo root; stdout + stderr go to `logs/<name>.log` (`coingecko_etl.py` → `logs/coingecko_etl.log`), overwritten each run. No flag runs a single entry — run the script itself (step 2) |
| Concurrency | `--workers N`, default 4 (`run_all_etl.sh` passes 4). List order is only the start order |
| `--exclude NAME` | repeatable; matches the basename or any substring of the path — `--exclude news` skips all of `news/` |
| Timeout | 1800 s per script; 4500 s for `reddit_unified_etl.py` and `goldigging_youtube_posts.py`. On timeout the process tree is killed, `TIMEOUT:` is printed and the script counts as failed |
| Result lines | `SUCCESS:` · `ERROR: ... failed with code N` · `Warning: Script ... does not exist. Skipping.` (a missing file counts as failed) |
| Exit code | always 0 — read the `Successful:` and `Failed:` counts in its output |
| After the pool | The data-freshness watcher runs alone and counts in the summary. Then `src.utils.snapshot_retention --keep-last 30 --apply` keeps the newest 30 timestamped files per name (`*latest*`, state files and `data/watchers/` are never touched). Then `run_backup.py --max-age-hours 20`: one verified archive of `data/` and `logs/` a day, 7 kept (`unraid-deploy` skill) |

`Tests/unit/test_deploy.py` guards what the container ships: run it after
touching the script list.

## Step 4 — wire a consumer

A new file is invisible until something reads it. Update what applies, in the
same change as the registration:

- **`src/services/data_loader.py`** — the source's `*_SOURCES_CONFIG` dict
  (`NEWS_SOURCES_CONFIG`, `KNOWLEDGE_SOURCES_CONFIG`, `GAMES_SOURCES_CONFIG`,
  `BENCHMARKS_SOURCES_CONFIG`, …) as
  `"<key>": {"path": get_data_path("<domain>", "<file>"), "name": "<Label>"}`.
  The dashboard tabs **and** the API (`src/api/routers.py`) read these dicts.
- **Tab-local lists**, for sources outside those dicts — among others
  `RADAR_SOURCES` in `tech_radar_tab.py` and `DATA_FILE` in
  `security_tab.py`, `markets_tab.py`, `digest_tab.py`, `fourchan_tab.py`.
- **`src/watchers/data_freshness_watcher.py`** — a `SOURCE_FILES` entry
  `{"key", "label", "path" (relative to `data/`), "warn_hours", "critical_hours"}`
  puts the source on the stale-data watch (the Metrics card). Without it a
  source that stops updating is counted as good forever.
- **`src/services/content_search.py`** — `ARTICLE_COLLECTIONS` and the
  `RELEASES_FILE`, `MARKETS_FILE`, `PAPERS_FILE`, `VIDEOS_GLOB` constants feed
  the search API (`src/api/search.py`).

## Step 5 — the test

- `Tests/etl/test_<source>.py`, next to the ETL's siblings in that directory.
  A `BaseETL` subclass is built with `MyETL.__new__(MyETL)` and only the
  attributes the stage under test reads; a plain module's fetch is replaced
  with `monkeypatch.setattr(module.requests, "get", fake_get)`.
- Never reach a real service, and never read or write the real `data/`:
  fixtures and `tmp_path` only.
- Feed fixtures are well-formed XML **bytes** (`<img ... />` self-closed,
  accented characters as numeric entities such as `&#225;`). `feedparser`
  decodes titles once but hands summaries over with their HTML re-escaped, so
  the fixture holds `&amp;amp;` where the wire had `&amp;`.
- Run the file while iterating and the whole directory before reporting:
  `uv run pytest Tests/etl/test_<source>.py -q`.

## Definition of done

- [ ] Step 2's script runs it from the repository root, writes
      `<name>_latest.json` under the printed temporary root, and nothing
      appeared under the checkout's `data/` or `logs/`.
- [ ] It ran for real after the last change to it. A test with the network
      stubbed proves the code against the fixture you wrote, not against the
      source: the output the real source gives is the one production gets.
- [ ] For an ETL that keeps state, a run with `--seed-data` on a copy of
      production `data/` keeps what it must keep (stamps, checkpoints).
- [ ] A forced failure exits non-zero — and so does an open circuit breaker.
- [ ] The path is in `ETL_SCRIPTS`; a consumer reads the file; `SOURCE_FILES`
      lists it.
- [ ] The test passes: `uv run pytest Tests/etl/test_<source>.py`.
- [ ] `uv run ruff check` and `uv run ruff format --check` are clean on the
      new files; if a model was added, `uv run mypy src` is clean.
- [ ] Any new dependency is in `pyproject.toml` and `uv.lock`.
- [ ] After the deploy, the file on the server is from today and the tab shows
      the new source (`unraid-deploy` skill).

## When an ETL "isn't running" or its data is stale

1. Not in `ETL_SCRIPTS` → add it.
2. `Warning: Script ... does not exist. Skipping.` → wrong or renamed path.
3. `SUCCESS:` but no new file → a swallowed exception (plain module) or an open
   circuit breaker (`data/<name>/circuit_breaker.json`).
4. `ERROR:` or `TIMEOUT:` → the detail is in `logs/<name>.log`
   (`/mnt/user/appdata/watchtower/logs/` on the server — `unraid-deploy` skill).
5. The file is new but the tab shows old data → the tab reads another path, or
   its repository cached the previous file for up to an hour
   (`dashboard-tab` skill).
