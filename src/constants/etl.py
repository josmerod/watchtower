"""ETL constants shared across scraping modules.

Trimmed 2026-09-10 to the constants with real consumers: the two user-agent
strings used by ~50 ETL/watcher modules. Every other block this file once held
(batch sizes, circuit-breaker knobs, dashboards, feature flags…) had zero
readers — the modules that own those concerns define their own defaults.
"""

from __future__ import annotations

# --- Web Scraping Constants ---
SCRAPER_DEFAULT_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SCRAPER_BRANDED_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Watchtower/1.0"
