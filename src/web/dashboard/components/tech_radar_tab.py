"""Technology Radar Tab — cloud, GenAI, AI, and self-hosting trends.

Aggregates technology news from multiple sources to track the latest trends
and updates across cloud computing, generative AI, artificial intelligence,
and self-hosted applications/tools. Consolidates sources that were previously
scattered across the News tab (Google AI Blog, KDNuggets, Cloud Updates) plus
dedicated sources: selfh.st + LinuxServer.io (self-hosting), the Hacker News
front page via Algolia (discussion), the r/SelfHosted + r/homelab community
pulse from the reddit_unified ETL, the T-070 additions: Lobsters (dev
link-aggregator), Phoronix (Linux/hardware), and the Unraid community forums
(spec 13 source table), plus the T-078 additions: GitHub Trending (open
source), ServeTheHome (server hardware) and Xataka (Spanish tech media),
and the T-082 additions: Lemmy communities (federated self-hosting pulse),
Product Hunt (product launches) and the Azure blog (cloud). The GCP blog
was probed too but all of its feed URLs now serve HTML, not RSS.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import ALL, Input, Output, dcc, html

from src.etl.github.stack_eol_etl import eol_badge
from src.utils.file_system import get_project_root
from src.web.dashboard.components import saved_items
from src.web.dashboard.components.shared.cache import TTLDataCache
from src.web.dashboard.components.shared.table import create_refresh_button
from src.web.dashboard.search_utils import create_search_input, filter_content, highlight_segments

logger = logging.getLogger(__name__)

# Source definitions: key -> (label, data file path relative to data/, icon).
# A source may read several files ("files") which are merged and de-duplicated
# — used by the community-pulse column (r/SelfHosted + r/homelab, spec 13).
RADAR_SOURCES: list[dict[str, Any]] = [
    {"key": "google_ai", "label": "🧠 Google AI Blog", "file": "news/google_ai_blog_latest.json", "category": "AI"},
    {"key": "verge_ai", "label": "⚡ The Verge AI", "file": "news/verge_ai_latest.json", "category": "AI"},
    # T-075: newest models from the public ollama.com/library (server-rendered,
    # verified stable). ETL: src/etl/ai_platforms/ollama_library_etl.py.
    {"key": "ollama", "label": "🦙 Ollama", "file": "ai_platforms/ollama_library_latest.json", "category": "Local LLM"},
    {"key": "kdnuggets", "label": "📊 KDNuggets", "file": "kdnuggets/kdnuggets.json", "category": "Data Science"},
    {"key": "cloud_updates", "label": "☁️ Cloud Updates", "file": "cloud_updates/cloud_updates_latest.json", "category": "Cloud"},
    # T-082: Azure blog — widens cloud coverage beyond the AWS-centric
    # cloud_updates aggregate (which has no Azure feed). ETL:
    # src/etl/news/news_get_azure_blog.py.
    {"key": "azure_blog", "label": "☁️ Azure Blog", "file": "news/azure_blog_latest.json", "category": "Cloud"},
    {"key": "selfhosted", "label": "🏠 Self-Hosted", "file": "selfhosted/selfhosted_latest.json", "category": "Self-Hosting"},
    {
        "key": "reddit_pulse",
        "label": "💬 r/SelfHosted + r/homelab",
        "files": ["reddit_unified/SelfHosted_latest.json", "reddit_unified/homelab_latest.json"],
        "category": "Self-Hosting",
    },
    # T-070: Unraid community threads — Invision feed from forums.unraid.net
    # (the user runs Unraid; forums.unraid.tv is dead). T-075 switched the feed
    # to the focused News & Announcements forum (/forum/7-announcements.xml/,
    # signal over noise) with the all-topics aggregate as fallback. ETL:
    # src/etl/news/news_get_unraid_forums.py.
    {"key": "unraid_forums", "label": "🟠 Unraid Announcements", "file": "news/unraid_forums_latest.json", "category": "Self-Hosting"},
    # T-082: Lemmy !selfhosted + !homelab (lemmy.world native RSS, merged in
    # one file) — federated sibling of the reddit community pulse with a
    # different, non-overlapping community. ETL: src/etl/news/news_get_lemmy.py.
    {"key": "lemmy", "label": "🍋 Lemmy", "file": "news/lemmy_latest.json", "category": "Self-Hosting"},
    {"key": "infoq", "label": "🏗️ InfoQ", "file": "infoq/infoq_news.json", "category": "Engineering"},
    {"key": "thenewstack", "label": "🧱 The New Stack", "file": "thenewstack/thenewstack_news.json", "category": "Cloud-Native"},
    # T-070: Phoronix — Linux/hardware news for the homelab angle. ETL:
    # src/etl/news/news_get_phoronix.py.
    {"key": "phoronix", "label": "🐧 Phoronix", "file": "news/phoronix_latest.json", "category": "Linux/Hardware"},
    # T-078: ServeTheHome — server/homelab hardware news next to Phoronix.
    # ETL: src/etl/news/news_get_sth.py.
    {"key": "servethehome", "label": "🔧 ServeTheHome", "file": "news/servethehome_latest.json", "category": "Linux/Hardware"},
    {"key": "changelog", "label": "🔄 Changelog", "file": "changelog/changelog_news.json", "category": "Open Source"},
    # T-078: GitHub trending repos — github.com/trending server-rendered HTML
    # (verified stable; selectors are structure-based because GitHub A/B-tests
    # utility class names). ETL: src/etl/github/github_trending_etl.py.
    {"key": "github_trending", "label": "🐙 GH Trending", "file": "github/github_trending_latest.json", "category": "Open Source"},
    # T-082: Product Hunt front-page launches (keyless Atom feed, capped 25) —
    # separate from the legacy News-tab producthunt ETL (product-shaped schema).
    # ETL: src/etl/news/news_get_producthunt_radar.py.
    {"key": "producthunt", "label": "🚀 Product Hunt", "file": "news/producthunt_radar_latest.json", "category": "Products"},
    {"key": "hn_frontpage", "label": "🗞️ Hacker News", "file": "news/hn_frontpage_latest.json", "category": "Discussion"},
    # T-070: Lobsters — dev link-aggregator (existing ETL hardened to the Wired
    # pattern): src/etl/news/news_get_lobsters.py. Also feeds the News tab.
    {"key": "lobsters", "label": "🦞 Lobsters", "file": "news/lobsters_latest.json", "category": "Engineering"},
    {"key": "wired", "label": "🔗 Wired", "file": "news/wired_latest.json", "category": "Tech Media"},
    {"key": "mit_techreview", "label": "🔬 MIT Tech Review", "file": "news/mit_techreview_latest.json", "category": "Emerging Tech"},
    # T-078: Xataka — biggest Spanish tech blog, dedicated radar column
    # (the News tab's spanish_tech ETL only mixes it into an aggregate).
    # ETL: src/etl/news/news_get_xataka.py.
    {"key": "xataka", "label": "🇪🇸 Xataka", "file": "news/xataka_latest.json", "category": "Tech Media ES"},
    # TR-F4 "Mi stack": GitHub releases of the self-hosted stack, from
    # src/etl/github/stack_releases_etl.py. ``own_tab`` keeps its column out
    # of the "Por fuente" grid (it lives on its dedicated subtab) while the
    # single controller callback still owns its output id; ``per_item_label``
    # badges each unified-feed row with the release's repo name; ``row_style``
    # renders it as release rows instead of article cards.
    {
        "key": "mi_stack",
        "label": "🧮 Mi stack",
        "file": "github/stack_releases_latest.json",
        "category": "Mi Stack",
        "own_tab": True,
        "per_item_label": "repo",
        "row_style": "release",
    },
]

MAX_ITEMS_PER_SOURCE = 25
# T-070: bumped 100 → 120 — three added sources (~75 fresh items) now compete
# for the newest-first window, so 100 starved older per-source rows.
# T-078: bumped 120 → 140 — three more sources add up to ~55 fresh items
# (trending ≤25, ServeTheHome ~6, Xataka 25) that are mostly "today" news and
# would otherwise crowd the tail of the window.
# T-082: bumped 140 → 160 — three more sources add up to ~65 fresh items
# (Lemmy ≤30, Product Hunt 25, Azure ~10) that are mostly recent-launch news
# and would otherwise crowd the tail of the window.
MAX_UNIFIED_ITEMS = 160  # cap for the TR-F3 "Todos" merged feed

# ⭐ Saved-items toggle (T-053): only the unified "🔄 Todos" feed rows get a
# star (NOT the per-source card columns). Pattern id type per tab, shared
# persistence with Knowledge Garden via data/garden/saved_items.json.
TECH_RADAR_SAVE_BTN_TYPE = "tech-radar-save-btn"

# Fields checked (with nested metadata fallback) when searching/filtering.
_SEARCHABLE_FIELDS = ["title", "summary", "description"]

# Spec 13 M4: read-through cache (5 min TTL) so the tab stops hitting disk on
# every render; the refresh button bypasses it via force_refresh.
_RADAR_CACHE = TTLDataCache(ttl_seconds=300)


def _source_files(source: dict[str, Any]) -> list[str]:
    """Return every data file a radar source reads (one or many)."""
    return list(source.get("files") or [source.get("file")])


def _read_file(file_rel: str) -> list[dict[str, Any]]:
    """Read one data file relative to the project data dir."""
    data_path = os.path.join(get_project_root(), "data", file_rel)
    if not os.path.exists(data_path):
        return []
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _load_all_source_data(force_refresh: bool = False) -> dict[str, list[dict[str, Any]]]:
    """Load every radar file once per TTL window into a {file: articles} map."""

    def _loader() -> dict[str, list[dict[str, Any]]]:
        files = {f for source in RADAR_SOURCES for f in _source_files(source) if f}
        return {file_rel: _read_file(file_rel) for file_rel in sorted(files)}

    return _RADAR_CACHE.get(_loader, force_refresh=force_refresh)


def _load_source_data(source: dict[str, Any], all_data: dict[str, list[dict[str, Any]]] | None = None) -> list[dict[str, Any]]:
    """Load a source's articles, merging + de-duplicating when it reads several files."""
    if all_data is None:
        all_data = _load_all_source_data()
    articles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for file_rel in _source_files(source):
        for raw in all_data.get(file_rel, []):
            if not isinstance(raw, dict):
                continue
            key = raw.get("link") or raw.get("url") or raw.get("title", "")
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            articles.append(raw)
    return articles


def _sortable_date(article: dict[str, Any]) -> float:
    """Best-effort epoch for date-desc sorting; undated articles sort last."""
    raw = str(article.get("published") or article.get("published_at") or article.get("fetched_at") or "")
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _normalize_article(article: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested metadata so heterogeneous ETL outputs render uniformly.

    The KDNuggets ETL nests summary/tags inside ``metadata`` and uses
    ``published_at`` instead of ``published``; other ETLs use top-level keys.
    Reddit posts (community-pulse column) carry score/comments instead of a
    summary, so one is synthesized for the cards.
    """
    if not isinstance(article, dict):
        return {}
    metadata = article.get("metadata") or {}
    if not article.get("summary"):
        article["summary"] = metadata.get("summary", "") or metadata.get("description", "")
    if not article.get("summary") and ("score" in article or "num_comments" in article):
        article["summary"] = f"⬆ {article.get('score', 0)} · 💬 {article.get('num_comments', 0)} · r/{article.get('subreddit', '')}"
    if article.get("summary"):
        # Reddit/atom summaries arrive as HTML fragments — show plain text.
        article["summary"] = re.sub(r"<[^>]+>", "", article["summary"]).strip()
    if not article.get("description"):
        article["description"] = article.get("summary", "")
    if not article.get("published"):
        article["published"] = article.get("published_at", "") or article.get("fetched_at", "")
    if not article.get("link"):
        article["link"] = article.get("url", "")
    return article


def _build_article_card(article: dict[str, Any]) -> dbc.Card:
    """Build a card for a single article."""
    title = article.get("title", "Untitled")
    link = article.get("link", article.get("url", "#"))
    summary = article.get("summary", article.get("description", ""))
    published = article.get("published", article.get("fetched_at", ""))
    if summary:
        summary = summary[:200] + "…" if len(summary) > 200 else summary
    return dbc.Card(
        dbc.CardBody(
            [
                html.H6(
                    html.A(title, href=link, target="_blank", className="text-decoration-none"),
                    className="mb-1",
                ),
                html.Small(published[:10] if published else "", className="text-muted") if published else None,
                html.P(summary, className="small text-muted mt-1 mb-0") if summary else None,
            ]
        ),
        className="mb-2 shadow-sm",
    )


def _render_source_section(source: dict[str, Any], search_term: str | None = None, all_data: dict[str, list[dict[str, Any]]] | None = None) -> list:
    """Render one source's articles as a column of cards, optionally filtered."""
    if source.get("row_style") == "release":
        return _render_stack_section(source, search_term=search_term, all_data=all_data)
    articles = [_normalize_article(a) for a in _load_source_data(source, all_data)]
    if not articles:
        return [
            html.H6(source["label"], className="mb-2"),
            dbc.Alert(f"No data yet. Run the ETL for {source['label'].split(' ', 1)[-1]}.", color="light", className="small"),
        ]
    if search_term:
        articles = filter_content(search_term, articles, _SEARCHABLE_FIELDS)
        if not articles:
            return [
                html.H6(source["label"], className="mb-2"),
                dbc.Alert(f"No articles matching '{search_term}'.", color="light", className="small"),
            ]
    # Spec 13 M4: newest first regardless of file order; undated last.
    articles.sort(key=_sortable_date, reverse=True)
    articles = articles[:MAX_ITEMS_PER_SOURCE]
    return [
        html.H6(source["label"], className="mb-2"),
        html.Small(f"{len(articles)} articles", className="text-muted mb-2 d-block"),
        *[_build_article_card(a) for a in articles],
    ]


def _render_stack_section(source: dict[str, Any], search_term: str | None = None, all_data: dict[str, list[dict[str, Any]]] | None = None) -> list:
    """Render the TR-F4 "Mi stack" releases as unified-style rows (one row per release).

    Each row badges the repo name (the "service I run") and the release
    category, reusing the unified-feed row style; newest release first.
    """
    releases = [_normalize_article(a) for a in _load_source_data(source, all_data)]
    if not releases:
        return [
            html.H6(source["label"], className="mb-2"),
            dbc.Alert(f"No data yet. Run the ETL for {source['label'].split(' ', 1)[-1]} (src/etl/github/stack_releases_etl.py).", color="light", className="small"),
            *_render_stack_eol_section(),
        ]
    if search_term:
        releases = filter_content(search_term, releases, _SEARCHABLE_FIELDS)
        if not releases:
            return [
                html.H6(source["label"], className="mb-2"),
                dbc.Alert(f"No releases matching '{search_term}'.", color="light", className="small"),
            ]
    releases.sort(key=_sortable_date, reverse=True)
    releases = releases[:MAX_ITEMS_PER_SOURCE]
    repos = sorted({str(r.get("repo")) for r in releases if r.get("repo")})
    rows = [_render_unified_row(release, str(release.get("repo") or source["label"]), "release", search_term) for release in releases]
    return [
        html.H6(source["label"], className="mb-2"),
        html.Small(f"{len(releases)} releases · {', '.join(repos)}", className="text-muted mb-2 d-block"),
        html.Ul(rows, className="mb-0"),
        *_render_stack_eol_section(),
    ]


# T-092: support-cycle awareness from src/etl/github/stack_eol_etl.py — the
# third stack-health pillar (releases + CVEs + EOL). Keyed by product label
# so the badge can also reach the per-service rows if coverage ever lands.
STACK_EOL_FILE = "stack/eol_latest.json"


def _load_stack_eol() -> dict[str, Any] | None:
    """Load the EOL envelope; missing or corrupt file → None (no section)."""
    data_path = os.path.join(get_project_root(), "data", STACK_EOL_FILE)
    if not os.path.exists(data_path):
        return None
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _render_stack_eol_section() -> list:
    """Render the "⏳ EOL" badge card for every mapped stack product (T-092).

    One row per product from ``data/stack/eol_latest.json`` with the tier
    badge from :func:`src.etl.github.stack_eol_etl.eol_badge`: red EOL within
    90 days or past, orange within 180 days, white fine or no date, dash not
    covered by endoflife.date. Returns ``[]`` (no section at all) until the
    ETL has run.
    """
    data = _load_stack_eol()
    if not data:
        return []
    products = [p for p in data.get("products", []) if isinstance(p, dict)]
    if not products:
        return []
    rows = []
    for product in products:
        symbol, _tier = eol_badge(product)
        if product.get("tracked") and product.get("nearest_eol"):
            days = product.get("days_to_eol")
            horizon = f"{days}d" if days is not None and days >= 0 else (f"{-days}d ago" if days is not None else "")
            detail = f"EOL {product['nearest_eol']}" + (f" ({horizon})" if horizon else "")
        elif product.get("tracked"):
            detail = "no EOL date published"
        else:
            detail = "not tracked by endoflife.date"
        cycles = product.get("cycles") or []
        newest = str(cycles[0].get("latest_release") or cycles[0].get("cycle") or "") if cycles else ""
        rows.append(
            html.Li(
                [
                    html.Span(f"{symbol} ", className="me-1"),
                    html.Strong(str(product.get("label") or product.get("product") or "?")),
                    (f" · {newest}" if newest else ""),
                    f" · {detail}",
                ],
                className="mb-1 small",
            )
        )
    return [
        dbc.Card(
            [
                dbc.CardHeader(html.H6("⏳ EOL & support cycles — endoflife.date", className="mb-0")),
                dbc.CardBody(html.Ul(rows, className="mb-0 list-unstyled")),
            ],
            className="mt-3 shadow-sm",
        ),
    ]


# Curated technology dictionary (spec 13 TR-F1 v1): canonical name -> quadrant.
# Quadrants follow the ThoughtWorks vocabulary: Techniques / Tools / Platforms / Languages & Frameworks.
TECH_DICTIONARY: dict[str, str] = {
    # Languages & frameworks
    "python": "Languages & Frameworks",
    "rust": "Languages & Frameworks",
    "golang": "Languages & Frameworks",
    "typescript": "Languages & Frameworks",
    "javascript": "Languages & Frameworks",
    "java": "Languages & Frameworks",
    "react": "Languages & Frameworks",
    "vue": "Languages & Frameworks",
    "svelte": "Languages & Frameworks",
    "next.js": "Languages & Frameworks",
    "django": "Languages & Frameworks",
    "flask": "Languages & Frameworks",
    "fastapi": "Languages & Frameworks",
    "spring": "Languages & Frameworks",
    "tailwind": "Languages & Frameworks",
    "flutter": "Languages & Frameworks",
    "swift": "Languages & Frameworks",
    "kotlin": "Languages & Frameworks",
    # Platforms
    "kubernetes": "Platforms",
    "k8s": "Platforms",
    "docker": "Platforms",
    "aws": "Platforms",
    "gcp": "Platforms",
    "azure": "Platforms",
    "cloudflare": "Platforms",
    "vercel": "Platforms",
    "github": "Platforms",
    "gitlab": "Platforms",
    "linux": "Platforms",
    "nginx": "Platforms",
    "home assistant": "Platforms",
    "raspberry pi": "Platforms",
    "unraid": "Platforms",
    "proxmox": "Platforms",
    "steam": "Platforms",
    # Tools
    "terraform": "Tools",
    "ansible": "Tools",
    "postgres": "Tools",
    "postgresql": "Tools",
    "mysql": "Tools",
    "redis": "Tools",
    "sqlite": "Tools",
    "mongodb": "Tools",
    "grafana": "Tools",
    "prometheus": "Tools",
    "n8n": "Tools",
    "hugging face": "Tools",
    "ollama": "Tools",
    "vscode": "Tools",
    "neovim": "Tools",
    "obsidian": "Tools",
    "docker compose": "Tools",
    "traefik": "Tools",
    # Techniques
    "rag": "Techniques",
    "fine-tuning": "Techniques",
    "rlhf": "Techniques",
    "distillation": "Techniques",
    "quantization": "Techniques",
    "mlops": "Techniques",
    "ci/cd": "Techniques",
    "tdd": "Techniques",
    "microservices": "Techniques",
    "serverless": "Techniques",
    "edge computing": "Techniques",
    "vector database": "Techniques",
    "agent": "Techniques",
    "agents": "Techniques",
    # AI models treated as Tools (bubbles sized by mentions)
    "llama": "Tools",
    "gpt": "Tools",
    "claude": "Tools",
    "gemini": "Tools",
    "mistral": "Tools",
    "deepseek": "Tools",
    "qwen": "Tools",
}

_QUADRANT_ORDER = ["Techniques", "Tools", "Platforms", "Languages & Frameworks"]
_RING_ORDER = ["Adopt", "Trial", "Assess", "Hold"]


def _extract_tech_mentions(all_data: dict[str, list[dict[str, Any]]] | None = None) -> list[dict[str, Any]]:
    """Scan every radar source for dictionary-tech mentions.

    Returns one record per detected technology with mention counts, the
    sources that mentioned it and example articles for the hover.
    """
    if all_data is None:
        all_data = _load_all_source_data()
    combined: dict[str, dict[str, Any]] = {}
    for source in RADAR_SOURCES:
        for raw in _load_source_data(source, all_data):
            article = _normalize_article(raw)
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            for tech, quadrant in TECH_DICTIONARY.items():
                if re.search(rf"\b{re.escape(tech)}\b", text):
                    entry = combined.setdefault(
                        tech,
                        {"tech": tech, "quadrant": quadrant, "mentions": 0, "sources": set(), "examples": []},
                    )
                    entry["mentions"] += 1
                    entry["sources"].add(source["label"])
                    if len(entry["examples"]) < 3:
                        entry["examples"].append(article.get("title", "")[:80])

    records = []
    for entry in combined.values():
        if entry["mentions"] >= 2:  # noise floor: single mentions skipped
            ring = _RING_ORDER[min(3, entry["mentions"] // 3)]  # 2-2 Assess, 3-5 Trial, 6-8 Adopt, 9+ Hold cap
            if entry["mentions"] >= 6:
                ring = "Adopt"
            elif entry["mentions"] >= 3:
                ring = "Trial"
            else:
                ring = "Assess"
            records.append({**entry, "sources": sorted(entry["sources"]), "ring": ring})
    records.sort(key=lambda r: r["mentions"], reverse=True)
    return records[:40]


def _build_radar_figure(records: list[dict[str, Any]]) -> go.Figure:
    """Plotly scatter: quadrant columns x ring rows, bubble size by mentions."""
    if not records:
        fig = go.Figure()
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper", text="No tech mentions detected yet — run the radar ETLs", showarrow=False)
        return fig

    fig = go.Figure()
    for quadrant in _QUADRANT_ORDER:
        subset = [r for r in records if r["quadrant"] == quadrant]
        if not subset:
            continue
        fig.add_trace(
            go.Scatter(
                x=[quadrant] * len(subset),
                y=[r["ring"] for r in subset],
                text=[r["tech"] for r in subset],
                customdata=list(subset),
                mode="markers+text",
                textposition="bottom center",
                marker={
                    "size": [min(60, 10 + r["mentions"] * 4) for r in subset],
                    "sizemode": "diameter",
                    "opacity": 0.75,
                    "color": [len(r["sources"]) for r in subset],
                    "colorscale": "Viridis",
                    "showscale": quadrant == _QUADRANT_ORDER[-1],
                    "colorbar": {"title": "Fuentes"} if quadrant == _QUADRANT_ORDER[-1] else None,
                },
                name=quadrant,
                hovertemplate="<b>%{text}</b><br>Ring: %{y}<br>Quadrant: %{x}<br>Menciones: %{customdata[2]}<br>Fuentes: %{customdata[4]}<extra></extra>",
            )
        )

    fig.update_layout(
        title="📡 Radar tecnológico — menciones cruzadas por cuadrante y madurez",
        xaxis_title="Cuadrante",
        yaxis_title="Anillo (madurez estimada por menciones)",
        xaxis={"categoryorder": "array", "categoryarray": _QUADRANT_ORDER},
        yaxis={"categoryorder": "array", "categoryarray": list(reversed(_RING_ORDER))},
        height=560,
        template="plotly_white",
        legend={"orientation": "h", "yanchor": "bottom"},
        margin={"l": 60, "r": 30, "t": 60, "b": 40},
    )
    return fig


def _render_radar_plot() -> dbc.Card:
    """Radar visualization card (spec 13 TR-F1)."""
    records = _extract_tech_mentions()
    return dbc.Card(
        [
            dbc.CardHeader(html.H6("📡 Radar — Tecnologías detectadas en las últimas publicaciones", className="mb-0")),
            dbc.CardBody(dcc.Graph(id="tech-radar-plot", figure=_build_radar_figure(records), style={"height": "560px"})),
            dbc.CardFooter(
                html.Small(
                    f"{len(records)} tecnologías detectadas (diccionario curado v1, ≥2 menciones). Tamaño = menciones; color = numero de fuentes.",
                    className="text-muted",
                )
            ),
        ],
        className="mb-3",
    )


def _render_unified_row(article: dict[str, Any], source_label: str, category: str, search_term: str | None, with_save: bool = False) -> html.Li:
    """One row of the TR-F3 merged feed: source badge + date + linked title.

    ``with_save`` prepends the shared ⭐ toggle — enabled for the unified
    "🔄 Todos" feed (T-053); the per-source columns render plain rows.
    """
    title = article.get("title", "Untitled")
    link = article.get("link") or article.get("url") or "#"
    published = str(article.get("published") or "")[:10]
    highlighted = highlight_segments(title, search_term) if search_term else title
    children: list[Any] = []
    if with_save:
        record = {**article, "source_display_name": article.get("source_display_name") or article.get("source") or source_label}
        children.append(saved_items.save_button(record, TECH_RADAR_SAVE_BTN_TYPE, tab="tech_radar", class_name="me-1 p-0 border-0"))
    children.extend(
        [
            dbc.Badge(source_label, color="info", className="me-2", pill=True),
            html.Small(f"{published} · {category}", className="text-muted me-2"),
            html.A(highlighted if isinstance(highlighted, list) else title, href=link, target="_blank", className="text-decoration-none"),
        ]
    )
    return html.Li(children, className="mb-2")


def _render_unified_feed(search_term: str | None = None, source_filter: str = "all", category_filter: str = "all", all_data: dict[str, list[dict[str, Any]]] | None = None) -> html.Div:
    """TR-F3: chronological merge of every radar source with filters."""
    if all_data is None:
        all_data = _load_all_source_data()
    rows: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for source in RADAR_SOURCES:
        if source_filter != "all" and source["key"] != source_filter:
            continue
        if category_filter != "all" and source["category"] != category_filter:
            continue
        for raw in _load_source_data(source, all_data):
            article = _normalize_article(raw)
            if search_term:
                title = str(article.get("title", ""))
                summary = str(article.get("summary") or article.get("description") or "")
                term = search_term.lower()
                if term not in title.lower() and term not in summary.lower():
                    continue
            rows.append((_sortable_date(article), article, source))
    rows.sort(key=lambda r: r[0], reverse=True)

    if not rows:
        return dbc.Alert("Nada que mostrar con estos filtros.", color="info", className="mt-3")

    items = html.Ul(
        [_render_unified_row(article, _row_label(article, source), source["category"], search_term, with_save=True) for _, article, source in rows[:MAX_UNIFIED_ITEMS]],
        className="mb-0",
    )
    return html.Div(
        [
            html.Small(f"{len(rows)} artículos ({min(len(rows), MAX_UNIFIED_ITEMS)} mostrados) — todas las fuentes, orden cronológico.", className="text-muted d-block mb-2"),
            items,
        ]
    )


def _row_label(article: dict[str, Any], source: dict[str, Any]) -> str:
    """Badge label for a unified-feed row.

    Sources may opt into a per-item label field (``per_item_label``) — the
    "Mi stack" source badges each row with its release's ``repo`` name so
    n8n/Immich/Jellyfin updates are distinguishable in the merged feed.
    """
    field = source.get("per_item_label")
    if field and article.get(field):
        return str(article[field])
    return source["label"]


def _unified_source_options() -> list[dict[str, str]]:
    """Dropdown options for the TR-F3 source filter."""
    return [{"label": "📋 Todas las fuentes", "value": "all"}, *[{"label": s["label"], "value": s["key"]} for s in RADAR_SOURCES]]


def _unified_category_options() -> list[dict[str, str]]:
    """Dropdown options for the TR-F3 category filter (distinct RADAR_SOURCES categories)."""
    categories = sorted({s["category"] for s in RADAR_SOURCES})
    return [{"label": f"🏷️ {c}", "value": c} for c in categories]


def render_tech_radar_tab() -> html.Div:
    """Render the Technology Radar tab: unified feed (TR-F3) + per-source columns."""
    search = create_search_input("tech-radar-search", placeholder="Search tech radar…", clear_button=True)
    refresh = create_refresh_button("tech-radar")

    # Build a responsive grid of source sections ("Por fuente"); sources with
    # ``own_tab`` render their column on their dedicated subtab instead — the
    # controller callback still owns every tech-radar-col-* output id.
    source_cols = [dbc.Col(_render_source_section(source), id=f"tech-radar-col-{source['key']}", width=12, lg=6, xl=3, className="mb-3") for source in RADAR_SOURCES if not source.get("own_tab")]
    stack_sources = [source for source in RADAR_SOURCES if source.get("own_tab")]

    return html.Div(
        [
            html.Div(
                [
                    html.H3(
                        [html.I(className="fas fa-satellite-dish me-2 text-primary"), "Technology Radar"],
                        className="mb-1",
                    ),
                    html.P(
                        "Latest trends and updates across Cloud, Generative AI, Artificial Intelligence, and Self-Hosting.",
                        className="text-muted mb-3",
                        style={"fontSize": "0.9rem"},
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(search, width="auto", className="flex-grow-1"),
                    dbc.Col(refresh, width="auto", className="align-self-end pb-1"),
                ],
                className="g-2",
            ),
            dbc.Tabs(
                [
                    dbc.Tab(
                        [
                            _render_radar_plot(),
                            dbc.Row(
                                [
                                    dbc.Col(dcc.Dropdown(id="tech-radar-source-filter", options=_unified_source_options(), value="all", clearable=False, placeholder="Fuente…"), width=12, md=4),
                                    dbc.Col(dcc.Dropdown(id="tech-radar-category-filter", options=_unified_category_options(), value="all", clearable=False, placeholder="Categoría…"), width=12, md=4),
                                ],
                                className="mb-1 mt-2",
                            ),
                            html.Div(id="tech-radar-unified-feed", children=_render_unified_feed()),
                        ],
                        label="🔄 Todos",
                        tab_id="tech-radar-tab-all",
                    ),
                    dbc.Tab(
                        html.Div(dbc.Row(source_cols, className="mt-2")),
                        label="🗂️ Por fuente",
                        tab_id="tech-radar-tab-sources",
                    ),
                    # TR-F4: releases of the self-hosted stack ("Mi stack").
                    dbc.Tab(
                        html.Div(
                            [
                                dbc.Row(
                                    dbc.Col(_render_source_section(source), id=f"tech-radar-col-{source['key']}", width=12, lg=8, className="mb-3"),
                                    className="mt-2",
                                )
                                for source in stack_sources
                            ]
                        ),
                        label="🧮 Mi stack",
                        tab_id="tech-radar-tab-stack",
                    ),
                ],
                id="tech-radar-view-tabs",
                active_tab="tech-radar-tab-all",
            ),
        ]
    )


def register_tech_radar_callbacks(app):
    """Register callbacks for the Technology Radar tab."""

    @app.callback(
        [Output(f"tech-radar-col-{source['key']}", "children") for source in RADAR_SOURCES] + [Output("tech-radar-plot", "figure"), Output("tech-radar-unified-feed", "children")],
        [
            Input("tech-radar-search", "value"),
            Input({"type": "tech-radar-refresh", "tab": ALL}, "n_clicks"),
            Input("tech-radar-source-filter", "value"),
            Input("tech-radar-category-filter", "value"),
        ],
        prevent_initial_call=True,
    )
    def update_radar(search_term, refresh_clicks, source_filter, category_filter):
        """Single controller (spec 15 pattern) for search, filters and refresh.

        Search filters the per-source columns; the source/category dropdowns
        drive the TR-F3 unified feed; a refresh click bypasses the TTL cache
        and re-renders everything.
        """
        try:
            is_refresh = dash.callback_context.triggered_id and getattr(dash.callback_context.triggered_id, "get", lambda _k: None)("type") == "tech-radar-refresh"
            all_data = _load_all_source_data(force_refresh=bool(is_refresh))
            term = (search_term or "").strip() or None
            sections = [_render_source_section(source, search_term=term, all_data=all_data) for source in RADAR_SOURCES]
            figure = _build_radar_figure(_extract_tech_mentions(all_data))
            feed = _render_unified_feed(
                search_term=term,
                source_filter=source_filter or "all",
                category_filter=category_filter or "all",
                all_data=all_data,
            )
            return sections + [figure, feed]
        except Exception as e:
            logger.error(f"Error in tech radar update: {e}")
            return [[dbc.Alert(f"Error searching: {e}", color="danger")] for _ in RADAR_SOURCES] + [dash.no_update, dash.no_update]

    @app.callback(
        Output("tech-radar-search", "value", allow_duplicate=True),
        Input("tech-radar-search-clear", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_radar_search(n_clicks):
        """Clear the search input."""
        if n_clicks:
            return ""
        return dash.no_update

    # ⭐ Save/unsave toggles for the unified "🔄 Todos" feed rows (T-053):
    # pattern-matching callback on the star buttons only; targets new outputs
    # so the radar controller above is untouched.
    saved_items.register_save_toggle_callback(app, TECH_RADAR_SAVE_BTN_TYPE)
