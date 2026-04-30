"""AI Coding Benchmarks Tab — BridgeBench.ai rankings.

Displays model performance across 6 benchmark categories:
Overall, Security, Debugging, Refactoring, Hallucination, Reasoning.
"""

import logging
import os
from datetime import datetime, timezone

import dash_bootstrap_components as dbc
from dash import dcc, html

logger = logging.getLogger(__name__)

# ── Data Loading ──────────────────────────────────────────────

def _get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


def _load_benchmark_category(category: str) -> list[dict]:
    """Load benchmark JSON for a given category."""
    data_path = os.path.join(_get_project_root(), "data", "benchmarks", f"bridgebench_{category}.json")
    if not os.path.exists(data_path):
        logger.warning(f"Benchmark data not found: {data_path}")
        return []
    import json
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("models", [])


# ── Category Config ───────────────────────────────────────────

BENCHMARK_CATEGORIES = {
    "overall": {
        "label": "🏆 Overall",
        "description": "Composite leaderboard across all BridgeBench suites. Ranked by Quality (mean of cohort-normalized scores on 7 quality benchmarks).",
        "columns": ["rank", "model", "quality", "vibe", "coverage", "security", "debugging", "refactoring", "hallucination", "reasoning", "ui", "speed"],
        "numeric_cols": {"quality", "vibe", "security", "debugging", "refactoring", "hallucination", "reasoning", "ui"},
    },
    "security": {
        "label": "🔒 Security",
        "description": "AI Code Security Benchmark — vulnerability detection and secure coding.",
        "columns": ["rank", "model", "score"],
        "numeric_cols": {"score"},
    },
    "debugging": {
        "label": "🐛 Debugging",
        "description": "AI Debugging Benchmark — bug-fixing accuracy across codebases.",
        "columns": ["rank", "model", "score"],
        "numeric_cols": {"score"},
    },
    "refactoring": {
        "label": "♻️ Refactoring",
        "description": "AI Refactoring Benchmark — behavior-preserving code transformations.",
        "columns": ["rank", "model", "score"],
        "numeric_cols": {"score"},
    },
    "hallucination": {
        "label": "🎭 Hallucination",
        "description": "AI Hallucination Benchmark — fabrication and incorrect code generation.",
        "columns": ["rank", "model", "score"],
        "numeric_cols": {"score"},
    },
    "reasoning": {
        "label": "🧠 Reasoning",
        "description": "AI Reasoning Benchmark — logical reasoning and problem-solving in code.",
        "columns": ["rank", "model", "score"],
        "numeric_cols": {"score"},
    },
}

COLUMN_LABELS = {
    "rank": "#",
    "model": "Model",
    "quality": "Quality",
    "vibe": "Vibe",
    "coverage": "Cov",
    "security": "Sec",
    "debugging": "Debug",
    "refactoring": "Refac",
    "hallucination": "Hall",
    "reasoning": "Reason",
    "ui": "UI",
    "bs": "BS",
    "speed": "Speed",
    "score": "Score",
}


# ── Rendering Helpers ─────────────────────────────────────────

def _score_cell(value: str, col: str, is_numeric: bool) -> html.Td:
    """Style a score cell with color coding."""
    if not is_numeric or value in ("—", "", "—"):
        return html.Td(value, style={"textAlign": "center"})

    try:
        score = float(value)
    except (ValueError, TypeError):
        return html.Td(value, style={"textAlign": "center"})

    # Color gradient: green (high) → yellow (mid) → red (low)
    # For hallucination: higher is better (less hallucination)
    # Range is typically 0-100 but varies by benchmark
    if col == "coverage":
        # Coverage is X/Y format, just display
        return html.Td(value, style={"textAlign": "center"})

    if col == "speed":
        # Speed in tok/s — just display
        return html.Td(value, style={"textAlign": "center", "fontSize": "0.85rem"})

    # Normalize to 0-100 for coloring
    norm = min(max(score, 0), 100)

    if norm >= 80:
        bg = "rgba(40, 167, 69, 0.15)"  # green
        color = "#28a745"
    elif norm >= 60:
        bg = "rgba(255, 193, 7, 0.12)"  # yellow
        color = "#c69500"
    elif norm >= 40:
        bg = "rgba(255, 165, 0, 0.12)"  # orange
        color = "#cc7a00"
    else:
        bg = "rgba(220, 53, 69, 0.12)"  # red
        color = "#dc3545"

    return html.Td(
        value,
        style={
            "textAlign": "center",
            "backgroundColor": bg,
            "color": color,
            "fontWeight": "600",
            "fontSize": "0.9rem",
        },
    )


def _rank_cell(rank: int) -> html.Td:
    """Style rank cell — medals for top 3."""
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    if rank in medals:
        return html.Td(
            f"{medals[rank]} {rank}",
            style={"textAlign": "center", "fontWeight": "700", "fontSize": "1rem"},
        )
    return html.Td(str(rank), style={"textAlign": "center", "color": "#6c757d"})


def _build_table(models: list[dict], category: str) -> html.Table:
    """Build a styled table for benchmark data."""
    if not models:
        return html.Div("No data available.", className="text-muted p-3")

    config = BENCHMARK_CATEGORIES[category]
    columns = config["columns"]
    numeric_cols = config["numeric_cols"]

    # Header
    header_cells = [
        html.Th(
            COLUMN_LABELS.get(c, c.title()),
            style={"textAlign": "center" if c != "model" else "left", "fontSize": "0.85rem", "textTransform": "uppercase"},
        )
        for c in columns
    ]
    thead = html.Thead(html.Tr(header_cells))

    # Rows
    rows = []
    for model in models:
        cells = []
        for col in columns:
            val = str(model.get(col, ""))
            if col == "rank":
                try:
                    cells.append(_rank_cell(int(val)))
                except ValueError:
                    cells.append(html.Td(val))
            elif col == "model":
                cells.append(html.Td(
                    val,
                    style={"fontWeight": "600", "fontSize": "0.9rem"},
                ))
            else:
                cells.append(_score_cell(val, col, col in numeric_cols))
        rows.append(html.Tr(cells))

    tbody = html.Tbody(rows)

    return html.Table(
        [thead, tbody],
        className="table table-sm table-hover",
        style={
            "fontSize": "0.9rem",
            "marginBottom": "0",
            "borderCollapse": "separate",
            "borderSpacing": "0",
        },
    )


def _build_category_tab(category: str) -> html.Div:
    """Build content for a single benchmark category tab."""
    config = BENCHMARK_CATEGORIES[category]
    models = _load_benchmark_category(category)

    if not models:
        return html.Div([
            html.H5(f"{config['label']} — No Data", className="text-muted"),
            html.P("Benchmark data file not found. Run the ETL to generate it."),
        ], className="p-3")

    # Metadata
    meta_items = []
    data_path = os.path.join(_get_project_root(), "data", "benchmarks", f"bridgebench_{category}.json")
    if os.path.exists(data_path):
        import json
        with open(data_path) as f:
            meta = json.load(f)
        fetched = meta.get("fetched_at", "")
        if fetched:
            try:
                dt = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
                meta_items.append(f"Updated: {dt.strftime('%Y-%m-%d %H:%M')}")
            except:
                pass
        meta_items.append(f"Models: {len(models)}")

    meta_text = " · ".join(meta_items)
    source_link = html.A(
        "BridgeBench.ai",
        href=f"https://bridgebench.ai/{category}",
        target="_blank",
        rel="noopener noreferrer",
        style={"color": "#6c757d"},
    )

    return html.Div([
        html.Div([
            html.H5(config["label"], className="mb-1", style={"fontWeight": "700"}),
            html.P(config["description"], className="mb-1 text-muted", style={"fontSize": "0.85rem"}),
            html.Small([
                source_link,
                " · ",
                meta_text,
            ], className="text-muted"),
        ], className="mb-3"),
        html.Div(
            _build_table(models, category),
            style={"overflowX": "auto", "borderRadius": "8px", "border": "1px solid #dee2e6"},
        ),
    ])


# ── Main Render Function ──────────────────────────────────────

def render_benchmarks_tab() -> html.Div:
    """Render the full benchmarks tab with sub-tabs."""
    # Load overall data for the summary
    overall_models = _load_benchmark_category("overall")

    # Top model info
    top_quality = overall_models[0] if overall_models else None
    # Find vibe leader (max vibe score)
    vibe_leader = max(overall_models, key=lambda m: _safe_float(m.get("vibe"))) if overall_models else None

    summary_cards = []
    if top_quality:
        summary_cards.extend([
            dbc.Card([
                dbc.CardBody([
                    html.Small("Models Ranked", className="text-muted"),
                    html.H3(str(len(overall_models)), className="mb-0", style={"color": "#007bff"}),
                ], className="text-center py-2"),
            ], className="col-md-3 col-6 mb-2"),
            dbc.Card([
                dbc.CardBody([
                    html.Small("Quality Leader", className="text-muted"),
                    html.H6(top_quality.get("model", "—"), className="mb-0", style={"fontWeight": "700"}),
                    html.Span(f"{top_quality.get('quality', '—')} pts", className="badge bg-success"),
                ], className="text-center py-2"),
            ], className="col-md-3 col-6 mb-2"),
            dbc.Card([
                dbc.CardBody([
                    html.Small("Vibe Leader", className="text-muted"),
                    html.H6(vibe_leader.get("model", "—") if vibe_leader else "—", className="mb-0", style={"fontWeight": "700", "fontSize": "0.85rem"}),
                    html.Span(f"{vibe_leader.get('vibe', '—') if vibe_leader else '—'} pts", className="badge bg-info"),
                ], className="text-center py-2"),
            ], className="col-md-3 col-6 mb-2"),
            dbc.Card([
                dbc.CardBody([
                    html.Small("Source", className="text-muted"),
                    html.H6(html.A("BridgeBench.ai", href="https://bridgebench.ai", target="_blank"), className="mb-0"),
                    html.Span("AI Coding Benchmarks", className="text-muted", style={"fontSize": "0.75rem"}),
                ], className="text-center py-2"),
            ], className="col-md-3 col-6 mb-2"),
        ])

    # Sub-tabs content
    tab_children = []
    for cat_key, cat_config in BENCHMARK_CATEGORIES.items():
        tab_children.append(
            dbc.Tab(
                label=cat_config["label"],
                tab_id=f"benchmark-{cat_key}",
                children=[_build_category_tab(cat_key)],
            )
        )

    return html.Div([
        # Summary cards
        html.Div([
            html.H4("🏆 AI Coding Benchmarks", className="mb-3", style={"fontWeight": "700"}),
            dbc.Row(summary_cards) if summary_cards else None,
        ], className="mb-3"),

        # Sub-tabs for categories
        dbc.Tabs(
            tab_children,
            id="benchmark-category-tabs",
            active_tab="benchmark-overall",
            className="nav-justified",
        ),
    ])


def register_benchmarks_callbacks(app):
    """Register callbacks for the benchmarks tab (if needed)."""
    # Benchmarks tab is mostly static (data loaded from JSON files).
    # No dynamic callbacks needed unless we add live-refresh.
    pass


def _safe_float(val) -> float:
    """Safely convert a value to float."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return -1.0
