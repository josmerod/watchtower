from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, clientside_callback
from flask import jsonify, redirect, render_template_string

from src.web.dashboard.components.anime_tab import render_anime_tab
from src.web.dashboard.components.arxiv_research_tab import (
    register_arxiv_callbacks,
    render_arxiv_research_tab,
)

from src.web.dashboard.components.courses_tab import (
    register_courses_callbacks,
    render_courses_tab,
)

from src.web.dashboard.components.fourchan_tab import (
    register_fourchan_callbacks,
    render_fourchan_tab,
)

from src.web.dashboard.components.open_source_tab import render_open_source_tab

from src.web.dashboard.components.scavenging_tab import (
    render_scavenging_tab,
    register_scavenging_callbacks,
)
from src.web.dashboard.components.shortcuts_tab import (
    render_shortcuts_tab,
    register_shortcuts_callbacks,
    get_shortcuts_data,
)

from src.web.dashboard.components.deals_tab import (
    render_deals_tab,
    register_deals_callbacks,
)

from src.web.dashboard.components.benchmarks_tab import (
    render_benchmarks_tab,
    register_benchmarks_callbacks,
)




from src.web.dashboard.components.knowledge_garden_tab import (
    render_knowledge_garden_tab,
)



from src.web.dashboard.components.news_tab import (
    register_news_search_callbacks,
    render_news_tab,
)

# Removed notifications tab import as per UI cleanup

from src.web.dashboard.components.scavenging_tab import (
    register_scavenging_callbacks,
    render_scavenging_tab,
)


from src.web.dashboard.components.spanish_public_aid_tab import (
    register_spanish_aid_callbacks,
    render_spanish_public_aid_tab,
)

from src.web.dashboard.components.valencia_events_new_tab import (
    register_valencia_events_callbacks,
    render_valencia_events_tab,
)
from src.web.dashboard.components.videos_tab import (
    register_video_callbacks,
    render_videos_tab,
)

from src.web.dashboard.health_monitor import HealthMonitor
from src.web.api.routes import api_bp  # Import API Blueprint

# Include external JavaScript libraries. Local files under assets/ are auto-loaded by Dash.
external_scripts = [
    "https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js",
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.6/dist/js/bootstrap.bundle.min.js",
]

# Initialize the Dash application with Bootstrap styling
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    external_scripts=external_scripts,
    suppress_callback_exceptions=True,
)

# Set app title for browser tab and configure metadata
app.title = "Watchtower Dashboard"



# Add meta tags for better branding
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Watchtower Dashboard</title>
        <meta name="description" content="Watchtower - Real-time Intelligence & Monitoring Platform">
        <link rel="icon" type="image/svg+xml" href="/assets/watchtower_icon.svg">
        <!-- Font Awesome for mobile navigation icons -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        {%css%}
        <!-- Final visual overrides: must load after Dash auto-assets and legacy mobile CSS. -->
        <link rel="stylesheet" href="/assets/zz_visual_refresh.css?v=3">
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# Main layout with Tabs
app.layout = dbc.Container(
    [
        # Skip to content link removed

        # Hero header and operational summary
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("Live intelligence console", className="dashboard-eyebrow"),
                                html.H1("Watchtower Dashboard", className="dashboard-header-title"),
                                html.P(
                                    "Fresh feeds, deals, research, events, benchmarks, and ETL health in one place.",
                                    className="dashboard-subtitle",
                                ),
                            ],
                            className="dashboard-hero-copy",
                        ),
                        html.Div(
                            [
                                html.A("Open API", href="https://watchtower-api.josmerod.es/docs", className="btn btn-primary", target="_blank"),
                                html.A("Docs", href="/docs", className="btn btn-outline-light", target="_self"),
                                html.A("Health JSON", href="/health", className="btn btn-outline-light", target="_self"),
                            ],
                            className="dashboard-hero-actions",
                        ),
                    ],
                    className="dashboard-hero d-flex flex-column flex-lg-row justify-content-between align-items-lg-end gap-4",
                ),
                width=12,
            ),
            className="dashboard-shell",
        ),
        dcc.Interval(id="ops-summary-refresh", interval=300000, n_intervals=0),
        html.Div(id="ops-summary-cards", className="ops-summary-row"),
        # Header buttons container
        html.Div(
            className="d-none",  # Hidden container specifically for keeping mobile nav happy if it looks for header-buttons
            children=[
                 # Removed shortcuts_sidebar and customize_tabs toggles
            ]
        ),
        # Removed shortcuts sidebar
        # Removed customize tabs modal and stores
        # Mobile navigation will be inserted here by JavaScript
        # Dashboard content area
        html.Div(id="dashboard-content", className="dashboard-content"),
        # Navigation tabs
        dbc.Row(
            dbc.Col(
                dbc.Tabs(
                    id="dashboard-tabs",
                    active_tab="tab-news",  # Set a default active tab
                    className="desktop-nav-tabs",
                    children=[


                        dbc.Tab(
                            label="News",
                            tab_id="tab-news",
                            children=[render_news_tab()],
                        ),

                        dbc.Tab(
                            label="Shortcuts",
                            tab_id="tab-shortcuts",
                            children=[render_shortcuts_tab()],
                        ),

                        dbc.Tab(
                            label="🌱 Knowledge Garden",
                            tab_id="tab-knowledge-garden",
                            children=[render_knowledge_garden_tab()],
                        ),
                        # Open Source moved to Knowledge Garden subtab
                        dbc.Tab(
                            label="Videos",
                            tab_id="tab-videos",
                            children=[render_videos_tab()],
                        ),

                        # Removed Intelligence and AI Research tabs as per cleanup


                        dbc.Tab(
                            label="Courses",
                            tab_id="tab-courses",
                            children=[render_courses_tab()],
                        ),
                        dbc.Tab(
                            label="Anime",
                            tab_id="tab-anime",
                            children=[render_anime_tab()],
                        ),
                        dbc.Tab(
                            label="4chan Generals",
                            tab_id="tab-4chan",
                            children=[render_fourchan_tab()],
                        ),
                        dbc.Tab(
                            label="Scavenging",
                            tab_id="tab-scavenging",
                            children=[render_scavenging_tab()],
                        ),
                        dbc.Tab(
                            label="Valencia Events",
                            tab_id="tab-valencia",
                            children=[render_valencia_events_tab()],
                        ),

                        dbc.Tab(
                            label="🏛️ Ayudas Públicas",
                            tab_id="tab-spanish-aid",
                            children=[render_spanish_public_aid_tab()],
                        ),
                        dbc.Tab(
                            label="📄 ArXiv Research",
                            tab_id="tab-arxiv-research",
                            children=[render_arxiv_research_tab()],
                        ),
                        dbc.Tab(
                            label="🏷️ Deals",
                            tab_id="tab-deals",
                            children=[render_deals_tab()],
                        ),
                        dbc.Tab(
                            label="🏆 Benchmarks",
                            tab_id="tab-benchmarks",
                            children=[render_benchmarks_tab()],
                        ),
                    ],
                )
            )
        ),
        # Dynamic tab content container
        dbc.Row(dbc.Col(html.Div(id="tab-content", className="mt-3"))),
        # Hidden trigger for dynamic tab generation
        html.Div(
            [
                html.Button(
                    "Refresh Tabs",
                    id="dynamic-tab-trigger-0",
                    n_clicks=0,
                    style={"display": "none"},
                ),
            ],
            id="dynamic-tab-trigger-container",
            style={"display": "none"},
        ),
    ],
    fluid=True,
)

# Expose enhanced health/metrics endpoints
server = app.server

# Initialize health monitor
health_monitor = HealthMonitor()


WATCHTOWER_DOCS_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Watchtower Docs</title>
  <meta name="description" content="Public documentation for Watchtower, the data aggregation and monitoring platform.">
  <link rel="icon" type="image/svg+xml" href="/assets/watchtower_icon.svg">
  <style>
    :root {
      color-scheme: dark;
      --bg: #08111f;
      --panel: #101b2d;
      --panel-2: #0c1626;
      --text: #ecf3ff;
      --muted: #a7b4c7;
      --accent: #69d2ff;
      --accent-2: #98f5c4;
      --border: rgba(255,255,255,.12);
      --code: #07101d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #183154 0, var(--bg) 40%, #050912 100%);
      color: var(--text);
      line-height: 1.6;
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .wrap { max-width: 1120px; margin: 0 auto; padding: 40px 22px 64px; }
    header { padding: 44px 0 30px; border-bottom: 1px solid var(--border); }
    .eyebrow { color: var(--accent-2); text-transform: uppercase; letter-spacing: .14em; font-size: .78rem; font-weight: 700; }
    h1 { font-size: clamp(2.2rem, 6vw, 4.6rem); line-height: 1; margin: 10px 0 18px; }
    h2 { margin-top: 42px; padding-top: 10px; font-size: 1.8rem; }
    h3 { margin-top: 28px; color: var(--accent-2); }
    p, li { color: var(--muted); }
    .lead { max-width: 820px; font-size: 1.15rem; color: #d8e5f8; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 24px 0; }
    .card { background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid var(--border); border-radius: 18px; padding: 20px; box-shadow: 0 18px 40px rgba(0,0,0,.24); }
    .card strong { display: block; color: var(--text); margin-bottom: 6px; }
    .pillrow { display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0; }
    .pill { border: 1px solid var(--border); border-radius: 999px; padding: 8px 12px; color: #dce9fb; background: rgba(255,255,255,.05); }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }
    code { background: rgba(105,210,255,.12); color: #dff6ff; padding: 2px 6px; border-radius: 7px; }
    pre { background: var(--code); border: 1px solid var(--border); border-radius: 14px; padding: 16px; overflow-x: auto; color: #dce9fb; }
    table { width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 14px; border: 1px solid var(--border); }
    th, td { padding: 12px 14px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
    th { color: var(--text); background: rgba(255,255,255,.06); }
    td { color: var(--muted); }
    .actions { display: flex; flex-wrap: wrap; gap: 12px; margin: 28px 0; }
    .button { display: inline-block; padding: 11px 16px; border-radius: 12px; border: 1px solid var(--border); background: rgba(105,210,255,.14); color: var(--text); font-weight: 700; }
    .button.secondary { background: rgba(255,255,255,.06); }
    .note { border-left: 4px solid var(--accent-2); background: rgba(152,245,196,.08); padding: 14px 16px; border-radius: 12px; }
    footer { margin-top: 52px; padding-top: 24px; border-top: 1px solid var(--border); color: var(--muted); }
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <div class="eyebrow">Watchtower public docs</div>
      <h1>Data aggregation, monitoring, and intelligence feeds.</h1>
      <p class="lead">Watchtower collects useful data from public sources, normalizes it into category feeds, exposes a JSON API, and renders a dashboard for browsing news, deals, courses, research, events, public aid, benchmarks, and more.</p>
      <div class="actions">
        <a class="button" href="/">Open dashboard</a>
        <a class="button secondary" href="https://watchtower-api.josmerod.es/docs">Interactive API docs</a>
        <a class="button secondary" href="https://watchtower-api.josmerod.es/api/v1/sources">Source list JSON</a>
      </div>
    </header>

    <section>
      <h2>Public endpoints</h2>
      <div class="grid">
        <div class="card"><strong>Dashboard</strong><a href="https://watchtower.josmerod.es">watchtower.josmerod.es</a><p>Human-facing Dash UI with tabs for each content area.</p></div>
        <div class="card"><strong>API</strong><a href="https://watchtower-api.josmerod.es">watchtower-api.josmerod.es</a><p>FastAPI service serving normalized JSON feeds.</p></div>
        <div class="card"><strong>Health</strong><a href="/health">/health</a><p>Dashboard health endpoint. API health is at <code>https://watchtower-api.josmerod.es/health</code>.</p></div>
        <div class="card"><strong>Metrics</strong><a href="/metrics">/metrics</a><p>Dashboard-side ETL and source metrics where available.</p></div>
      </div>
    </section>

    <section>
      <h2>How the system works</h2>
      <ol>
        <li><strong>ETLs run on a schedule.</strong> Scripts fetch public feeds, APIs, and pages, then write normalized JSON files under Watchtower data directories.</li>
        <li><strong>The API serves category feeds.</strong> FastAPI reads the generated files and exposes them under <code>/api/v1/*</code>.</li>
        <li><strong>The dashboard renders the same data.</strong> The UI groups sources into tabs and adds search/filter/table views.</li>
        <li><strong>Hermes crons consume the API.</strong> Daily and weekly summaries pull directly from the API host, not from the dashboard host.</li>
      </ol>
      <p class="note"><strong>Important:</strong> the dashboard host and API host are intentionally split. Use <code>watchtower.josmerod.es</code> for humans and <code>watchtower-api.josmerod.es</code> for integrations.</p>
    </section>

    <section>
      <h2>API quick start</h2>
      <pre><code># Health
curl -s https://watchtower-api.josmerod.es/health

# Latest news item
curl -s "https://watchtower-api.josmerod.es/api/v1/news?limit=1"

# Available source keys by category
curl -s https://watchtower-api.josmerod.es/api/v1/sources

# Filter one category by source
curl -s "https://watchtower-api.josmerod.es/api/v1/ecommerce?source=gumroad_scraper&amp;limit=5"</code></pre>
    </section>

    <section>
      <h2>Core API routes</h2>
      <table>
        <thead><tr><th>Route</th><th>Use it for</th><th>Parameters</th></tr></thead>
        <tbody>
          <tr><td><code>/api/v1/news</code></td><td>Tech/news feeds such as Hacker News, TechCrunch, Ben's Bites, Product Hunt, and similar sources.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/knowledge-garden</code></td><td>Longer-lived knowledge items, open-source discoveries, references, and learning material.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/ecommerce</code></td><td>Digital products, marketplace items, and deal feeds.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/games</code></td><td>Game deals and free/discounted game opportunities.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/travel</code></td><td>Travel deals and destination opportunities.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/research</code></td><td>Academic/research feeds such as arXiv and ADHD/publication data.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/intelligence</code></td><td>Security and intelligence feeds such as CVEs and SEC-style signals.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/museums</code></td><td>Museum/culture data.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/entertainment</code></td><td>Movies, anime, and entertainment feeds.</td><td><code>limit</code>, <code>source</code></td></tr>
          <tr><td><code>/api/v1/benchmarks</code></td><td>AI coding benchmark data.</td><td><code>source</code></td></tr>
          <tr><td><code>/api/v1/sources</code></td><td>Machine-readable list of available source keys for filtering.</td><td>None</td></tr>
        </tbody>
      </table>
      <p>The full OpenAPI/Swagger reference is available at <a href="https://watchtower-api.josmerod.es/docs">watchtower-api.josmerod.es/docs</a>.</p>
    </section>

    <section>
      <h2>Freshness and staleness model</h2>
      <p>Watchtower data freshness depends on the ETL source. Most sources are refreshed by the scheduled ETL runner; browser-backed sources can fail if Playwright browser binaries or source-site access change. The API can be healthy while one source is stale, so check freshness per source rather than treating health as a complete data-quality signal.</p>
      <div class="pillrow">
        <span class="pill">API up ≠ every source fresh</span>
        <span class="pill">Check item timestamps</span>
        <span class="pill">Check <code>/api/v1/sources</code></span>
        <span class="pill">Use dashboard <code>/metrics</code> when debugging</span>
      </div>
    </section>

    <section>
      <h2>Common integration pattern</h2>
      <pre><code>import requests

base = "https://watchtower-api.josmerod.es/api/v1"
items = requests.get(f"{base}/news", params={"limit": 10}, timeout=20).json()
for item in items:
    print(item["published_at"], item["source"], item["title"])</code></pre>
    </section>

    <footer>
      <p>Watchtower docs are served from the dashboard app at <code>/docs</code>. API OpenAPI docs are served by the API app at <code>watchtower-api.josmerod.es/docs</code>.</p>
    </footer>
  </main>
</body>
</html>
"""


@server.route("/docs")
@server.route("/docs/")
def docs():
    """Public human-readable Watchtower documentation."""
    return render_template_string(WATCHTOWER_DOCS_HTML)


@server.route("/api-docs")
def api_docs_redirect():
    """Convenience redirect to the public FastAPI Swagger UI."""
    return redirect("https://watchtower-api.josmerod.es/docs", code=302)


@server.route("/health")
def health():
    """Enhanced health endpoint with status calculation and caching."""
    try:
        # Try to get cached response first
        cached_response = health_monitor.get_cached_response("health")
        if cached_response:
            return jsonify(cached_response)

        # Calculate health status
        health_status = health_monitor.calculate_overall_health()

        # Convert to dict for JSON response
        response_data = health_status.model_dump()

        # Cache for 5 minutes
        health_monitor.set_cached_response("health", response_data, ttl_minutes=5)

        return jsonify(response_data)

    except Exception as e:
        # Fallback response on error
        return (
            jsonify(
                {
                    "status": "down",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0.0",
                    "error": str(e),
                }
            ),
            500,
        )


@server.route("/metrics")
def metrics():
    """Enhanced metrics endpoint with comprehensive ETL metrics and caching."""
    try:
        # Try to get cached response first
        cached_response = health_monitor.get_cached_response("metrics")
        if cached_response:
            return jsonify(cached_response)

        # Generate comprehensive metrics summary
        metrics_summary = health_monitor.generate_metrics_summary()

        # Convert to dict for JSON response
        response_data = metrics_summary.model_dump()

        # Cache for 5 minutes
        health_monitor.set_cached_response("metrics", response_data, ttl_minutes=5)

        return jsonify(response_data)

    except Exception as e:
        # Fallback response on error
        return (
            jsonify(
                {
                    "generated_at": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "total_sources": 0,
                    "total_items": 0,
                    "last_etl_run_times": {},
                    "error_rates_per_source": {},
                }
            ),
            500,
        )


# Register callbacks for the main app
# Callback for updating shortcuts in the Shortcuts Tab





# Callback for dynamic tab content loading
# Remove legacy dynamic loader with dead branches to avoid confusion
# (Tabs are rendered directly above per component.)




def _format_uptime(seconds: float | None) -> str:
    """Human-friendly uptime for the dashboard summary strip."""
    if seconds is None:
        return "unknown"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h {minutes % 60}m"
    days = hours // 24
    return f"{days}d {hours % 24}h"


def _summary_card(label: str, value, hint: str = "") -> dbc.Col:
    """Build a compact operational summary card."""
    return dbc.Col(
        html.Div(
            [
                html.Div(label, className="ops-summary-card__label"),
                html.Div(value, className="ops-summary-card__value"),
                html.Div(hint, className="ops-summary-card__hint") if hint else None,
            ],
            className="ops-summary-card",
        ),
        xs=6,
        sm=6,
        lg=3,
    )


@app.callback(Output("ops-summary-cards", "children"), Input("ops-summary-refresh", "n_intervals"))
def update_ops_summary(_n_intervals):
    """Refresh the top-of-dashboard health cards without requiring a page reload."""
    try:
        health_status = health_monitor.calculate_overall_health()
        details = health_status.details or {}
        status = health_status.status or "unknown"
        failed_sources = details.get("failed_sources") or []
        degraded_sources = details.get("degraded_sources") or []
        failure_percentage = details.get("failure_percentage", 0) or 0
        total_runs = details.get("total_etl_runs", 0) or 0
        failed_runs = details.get("failed_runs", 0) or 0

        status_value = html.Span(status, className=f"status-pill status-pill--{status}")
        failed_hint = ", ".join(failed_sources[:3]) if failed_sources else "No failing sources reported"
        if len(failed_sources) > 3:
            failed_hint += f" +{len(failed_sources) - 3} more"

        return dbc.Row(
            [
                _summary_card("System status", status_value, f"{failure_percentage:.1f}% source failure rate"),
                _summary_card("ETL sources", total_runs, f"{failed_runs} failing / {len(degraded_sources)} degraded"),
                _summary_card("Failed sources", len(failed_sources), failed_hint),
                _summary_card("Dashboard uptime", _format_uptime(health_status.uptime_seconds), "Auto-refreshes every 5 minutes"),
            ],
            className="g-3",
        )
    except Exception as exc:
        return dbc.Row(
            [
                _summary_card(
                    "System status",
                    html.Span("down", className="status-pill status-pill--down"),
                    f"Health summary failed: {exc}",
                )
            ],
            className="g-3",
        )


# Register callbacks from other modules
register_video_callbacks(app)
register_courses_callbacks(app)
register_spanish_aid_callbacks(app)
register_arxiv_callbacks(app)

register_news_search_callbacks(app)
register_scavenging_callbacks(app)
register_valencia_events_callbacks(app)
register_shortcuts_callbacks(app)
register_deals_callbacks(app)
register_benchmarks_callbacks(app)









if __name__ == "__main__":
    # Note on data loading:
    # - Shortcuts data (ALL_SHORTCUTS_DATA) is loaded when shortcuts_tab.py is imported.
    # - News data (ALL_NEWS_DATA) is loaded when news_tab.py is imported.
    # - Videos data (ALL_VIDEOS_DATA) is loaded when videos_tab.py is imported.
    # These imports happen when app.py itself is imported (e.g., by run_watchtower_dashboard.py).
    # The relative paths within each component (e.g., '../../../data/...') are resolved
    # based on the Current Working Directory (CWD) when the Python interpreter loads those modules.
    # If run_watchtower_dashboard.py is at project root, CWD is project root, so paths should be correct.

    print("Verifying data loaded for Watchtower Dashboard:")
    # Simple check, more detailed checks are in individual tab's __main__ blocks
    if get_shortcuts_data():
        print("  Shortcuts data loaded successfully.")
    else:
        print("  Warning: Shortcuts data might be missing.")

    # Accessing ALL_NEWS_DATA and ALL_VIDEOS_DATA directly here would require importing them into app.py
    # For now, we assume their respective tabs handle their data loading messages.
    # If this script (app.py) is run directly, ensure CWD allows components to find their data.
    # Typically, one would run `run_watchtower_dashboard.py` from the project root.

    app.run(debug=False, port=8050)  # Default Dash port for direct app run
