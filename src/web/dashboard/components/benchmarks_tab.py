"""AI Benchmarks Tab — BridgeBench.ai rankings + Artificial Analysis leaderboard.

Displays model performance across multiple benchmark sources:
- BridgeBench.ai: AI coding benchmarks (Overall, Security, Debugging, etc.)
- Artificial Analysis: LLM benchmarks (intelligence, coding, math, pricing, speed)
  and Image Model Arena (ELO ratings from text-to-image evaluations)
"""

import json
import logging
import os
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html

logger = logging.getLogger(__name__)

# ── Project Root ──────────────────────────────────────────────


def _get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


# ═══════════════════════════════════════════════════════════════
# SECTION 1: BridgeBench.ai (unchanged from original)
# ═══════════════════════════════════════════════════════════════


def _load_benchmark_category(category: str) -> list[dict]:
    """Load benchmark JSON for a given category."""
    data_path = os.path.join(_get_project_root(), "data", "benchmarks", f"bridgebench_{category}.json")
    if not os.path.exists(data_path):
        logger.warning(f"Benchmark data not found: {data_path}")
        return []
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("models", [])


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


def _score_cell(value: str, col: str, is_numeric: bool) -> html.Td:
    """Style a score cell with color coding."""
    if not is_numeric or value in ("—", "", "—"):
        return html.Td(value, style={"textAlign": "center"})

    try:
        score = float(value)
    except (ValueError, TypeError):
        return html.Td(value, style={"textAlign": "center"})

    if col == "coverage":
        return html.Td(value, style={"textAlign": "center"})
    if col == "speed":
        return html.Td(value, style={"textAlign": "center", "fontSize": "0.85rem"})

    norm = min(max(score, 0), 100)

    if norm >= 80:
        bg, color = "rgba(40, 167, 69, 0.15)", "#28a745"
    elif norm >= 60:
        bg, color = "rgba(255, 193, 7, 0.12)", "#c69500"
    elif norm >= 40:
        bg, color = "rgba(255, 165, 0, 0.12)", "#cc7a00"
    else:
        bg, color = "rgba(220, 53, 69, 0.12)", "#dc3545"

    return html.Td(
        value,
        style={"textAlign": "center", "backgroundColor": bg, "color": color, "fontWeight": "600", "fontSize": "0.9rem"},
    )


def _rank_cell(rank: int) -> html.Td:
    """Style rank cell — medals for top 3."""
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    if rank in medals:
        return html.Td(f"{medals[rank]} {rank}", style={"textAlign": "center", "fontWeight": "700", "fontSize": "1rem"})
    return html.Td(str(rank), style={"textAlign": "center", "color": "#6c757d"})


def _build_table(models: list[dict], category: str) -> html.Table:
    """Build a styled table for benchmark data."""
    if not models:
        return html.Div("No data available.", className="text-muted p-3")

    config = BENCHMARK_CATEGORIES[category]
    columns = config["columns"]
    numeric_cols = config["numeric_cols"]

    header_cells = [html.Th(COLUMN_LABELS.get(c, c.title()), style={"textAlign": "center" if c != "model" else "left", "fontSize": "0.85rem", "textTransform": "uppercase"}) for c in columns]
    thead = html.Thead(html.Tr(header_cells))

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
                cells.append(html.Td(val, style={"fontWeight": "600", "fontSize": "0.9rem"}))
            else:
                cells.append(_score_cell(val, col, col in numeric_cols))
        rows.append(html.Tr(cells))

    tbody = html.Tbody(rows)

    return html.Table(
        [thead, tbody],
        className="table table-sm table-hover",
        style={"fontSize": "0.9rem", "marginBottom": "0", "borderCollapse": "separate", "borderSpacing": "0"},
    )


def _build_category_tab(category: str) -> html.Div:
    """Build content for a single benchmark category tab."""
    config = BENCHMARK_CATEGORIES[category]
    models = _load_benchmark_category(category)

    if not models:
        return html.Div(
            [
                html.H5(f"{config['label']} — No Data", className="text-muted"),
                html.P("Benchmark data file not found. Run the ETL to generate it."),
            ],
            className="p-3",
        )

    meta_items = []
    data_path = os.path.join(_get_project_root(), "data", "benchmarks", f"bridgebench_{category}.json")
    if os.path.exists(data_path):
        with open(data_path) as f:
            meta = json.load(f)
        fetched = meta.get("fetched_at", "")
        if fetched:
            try:
                dt = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
                meta_items.append(f"Updated: {dt.strftime('%Y-%m-%d %H:%M')}")
            except Exception:
                pass
        meta_items.append(f"Models: {len(models)}")

    meta_text = " · ".join(meta_items)
    source_link = html.A("BridgeBench.ai", href=f"https://bridgebench.ai/{category}", target="_blank", rel="noopener noreferrer", style={"color": "#6c757d"})

    return html.Div(
        [
            html.Div(
                [
                    html.H5(config["label"], className="mb-1", style={"fontWeight": "700"}),
                    html.P(config["description"], className="mb-1 text-muted", style={"fontSize": "0.85rem"}),
                    html.Small([source_link, " · ", meta_text], className="text-muted"),
                ],
                className="mb-3",
            ),
            html.Div(_build_table(models, category), style={"overflowX": "auto", "borderRadius": "8px", "border": "1px solid #dee2e6"}),
        ]
    )


def _safe_float(val) -> float:
    """Safely convert a value to float."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return -1.0


def _render_bridgebench_section() -> html.Div:
    """Render the BridgeBench.ai section with summary cards and sub-tabs."""
    overall_models = _load_benchmark_category("overall")

    top_quality = overall_models[0] if overall_models else None
    vibe_leader = max(overall_models, key=lambda m: _safe_float(m.get("vibe"))) if overall_models else None

    summary_cards = []
    if top_quality:
        summary_cards.extend(
            [
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Small("Models Ranked", className="text-muted"),
                                html.H3(str(len(overall_models)), className="mb-0", style={"color": "#007bff"}),
                            ],
                            className="text-center py-2",
                        ),
                    ],
                    className="col-md-3 col-6 mb-2",
                ),
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Small("Quality Leader", className="text-muted"),
                                html.H6(top_quality.get("model", "—"), className="mb-0", style={"fontWeight": "700"}),
                                html.Span(f"{top_quality.get('quality', '—')} pts", className="badge bg-success"),
                            ],
                            className="text-center py-2",
                        ),
                    ],
                    className="col-md-3 col-6 mb-2",
                ),
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Small("Vibe Leader", className="text-muted"),
                                html.H6(vibe_leader.get("model", "—") if vibe_leader else "—", className="mb-0", style={"fontWeight": "700", "fontSize": "0.85rem"}),
                                html.Span(f"{vibe_leader.get('vibe', '—') if vibe_leader else '—'} pts", className="badge bg-info"),
                            ],
                            className="text-center py-2",
                        ),
                    ],
                    className="col-md-3 col-6 mb-2",
                ),
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Small("Source", className="text-muted"),
                                html.H6(html.A("BridgeBench.ai", href="https://bridgebench.ai", target="_blank"), className="mb-0"),
                                html.Span("AI Coding Benchmarks", className="text-muted", style={"fontSize": "0.75rem"}),
                            ],
                            className="text-center py-2",
                        ),
                    ],
                    className="col-md-3 col-6 mb-2",
                ),
            ]
        )

    tab_children = []
    for cat_key, cat_config in BENCHMARK_CATEGORIES.items():
        tab_children.append(dbc.Tab(label=cat_config["label"], tab_id=f"benchmark-{cat_key}", children=[_build_category_tab(cat_key)]))

    return html.Div(
        [
            html.Div(
                [
                    html.H4("🏆 AI Coding Benchmarks", className="mb-3", style={"fontWeight": "700"}),
                    dbc.Row(summary_cards) if summary_cards else None,
                ],
                className="mb-3",
            ),
            dbc.Tabs(tab_children, id="benchmark-category-tabs", active_tab="benchmark-overall", className="nav-justified"),
        ]
    )


# ═══════════════════════════════════════════════════════════════
# SECTION 2: Artificial Analysis
# ═══════════════════════════════════════════════════════════════


def _load_aa_data(filename: str) -> tuple[list[dict], dict]:
    """Load Artificial Analysis JSON. Returns (models_list, metadata_dict)."""
    data_path = os.path.join(_get_project_root(), "data", "benchmarks", filename)
    if not os.path.exists(data_path):
        return [], {}
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    models = data.get("models", [])
    meta = {k: v for k, v in data.items() if k != "models"}
    return models, meta


def _fmt_score(val) -> str:
    """Format a benchmark score for display."""
    if val is None:
        return "—"
    try:
        f = float(val)
        if f == int(f):
            return str(int(f))
        return f"{f:.1f}"
    except (ValueError, TypeError):
        return "—"


def _fmt_price(val) -> str:
    """Format a price per 1M tokens for display."""
    if val is None:
        return "—"
    try:
        f = float(val)
        if f == 0:
            return "Free"
        if f >= 100:
            return f"${f:.0f}"
        if f >= 1:
            return f"${f:.2f}"
        return f"${f:.4f}"
    except (ValueError, TypeError):
        return "—"


def _fmt_speed(val) -> str:
    """Format tokens per second."""
    if val is None:
        return "—"
    try:
        f = float(val)
        return f"{f:.0f}"
    except (ValueError, TypeError):
        return "—"


def _fmt_ttft(val) -> str:
    """Format time to first token in seconds."""
    if val is None:
        return "—"
    try:
        f = float(val)
        return f"{f:.2f}s"
    except (ValueError, TypeError):
        return "—"


def _aa_score_cell(value: str, is_benchmark: bool = True) -> html.Td:
    """Style an Artificial Analysis score cell."""
    if value == "—" or value == "Free":
        return html.Td(value, style={"textAlign": "center", "fontSize": "0.85rem", "color": "#6c757d"})

    if not is_benchmark:
        return html.Td(value, style={"textAlign": "center", "fontSize": "0.85rem"})

    try:
        score = float(value)
    except (ValueError, TypeError):
        return html.Td(value, style={"textAlign": "center", "fontSize": "0.85rem"})

    # For indices that are 0-100 scale
    if score > 0:
        norm = min(max(score, 0), 100)
        if norm >= 85:
            bg, color = "rgba(40, 167, 69, 0.15)", "#28a745"
        elif norm >= 70:
            bg, color = "rgba(255, 193, 7, 0.12)", "#c69500"
        elif norm >= 50:
            bg, color = "rgba(255, 165, 0, 0.12)", "#cc7a00"
        else:
            bg, color = "rgba(220, 53, 69, 0.12)", "#dc3545"
    else:
        bg, color = "transparent", "#495057"

    return html.Td(value, style={"textAlign": "center", "backgroundColor": bg, "color": color, "fontWeight": "600", "fontSize": "0.85rem"})


def _build_aa_llm_table(models: list[dict], filter_open: str = "all", sort_by: str = "intelligence_index") -> html.Div:
    """Build the LLM leaderboard table with sorting and filtering."""

    # Filter
    filtered = models
    if filter_open == "open":
        filtered = [m for m in filtered if m.get("open_weights")]
    elif filter_open == "proprietary":
        filtered = [m for m in filtered if not m.get("open_weights")]

    # Sort
    reverse = True
    sort_key = sort_by

    if sort_by in ("price_input_per_1m", "price_output_per_1m", "price_blended_3_to_1", "median_ttft"):
        # Lower is better for price and TTFT
        reverse = False
        filtered.sort(key=lambda m: m.get(sort_key) if m.get(sort_key) is not None else float("inf"), reverse=reverse)
    elif sort_by == "name":
        filtered.sort(key=lambda m: m.get("name", "").lower())
        reverse = False
    else:
        filtered.sort(key=lambda m: m.get(sort_key) if m.get(sort_key) is not None else float("-inf"), reverse=True)

    if not filtered:
        return html.Div("No models match the current filter.", className="text-muted p-3")

    # Limit to top 100 for performance
    display = filtered[:100]

    # Header
    cols = ["#", "Model", "Creator", "Type", "Intelligence", "Coding", "Math", "MMLU-Pro", "GPQA", "Price In", "Price Out", "Speed", "TTFT"]
    header = html.Thead(html.Tr([html.Th(c, style={"textAlign": "center", "fontSize": "0.78rem", "textTransform": "uppercase", "whiteSpace": "nowrap"}) for c in cols]))

    rows = []
    for i, m in enumerate(display):
        badge_class = "badge bg-success" if m.get("open_weights") else "badge bg-secondary"
        badge_text = "Open" if m.get("open_weights") else "Prop"
        row = html.Tr(
            [
                html.Td(str(i + 1), style={"textAlign": "center", "color": "#6c757d", "fontSize": "0.85rem"}),
                html.Td(m.get("name", "—"), style={"fontWeight": "600", "fontSize": "0.85rem", "whiteSpace": "nowrap"}),
                html.Td(m.get("creator", "—"), style={"fontSize": "0.8rem", "color": "#495057"}),
                html.Td(html.Span(badge_text, className=badge_class, style={"fontSize": "0.7rem"}), style={"textAlign": "center"}),
                _aa_score_cell(_fmt_score(m.get("intelligence_index"))),
                _aa_score_cell(_fmt_score(m.get("coding_index"))),
                _aa_score_cell(_fmt_score(m.get("math_index"))),
                _aa_score_cell(_fmt_score(m.get("mmlu_pro"))),
                _aa_score_cell(_fmt_score(m.get("gpqa"))),
                _aa_score_cell(_fmt_price(m.get("price_input_per_1m")), is_benchmark=False),
                _aa_score_cell(_fmt_price(m.get("price_output_per_1m")), is_benchmark=False),
                _aa_score_cell(_fmt_speed(m.get("median_output_tps")), is_benchmark=False),
                _aa_score_cell(_fmt_ttft(m.get("median_ttft")), is_benchmark=False),
            ]
        )
        rows.append(row)

    tbody = html.Tbody(rows)

    table = html.Table(
        [header, tbody],
        className="table table-sm table-hover",
        style={"fontSize": "0.85rem", "marginBottom": "0", "borderCollapse": "separate", "borderSpacing": "0"},
    )

    return html.Div(table, style={"overflowX": "auto", "borderRadius": "8px", "border": "1px solid #dee2e6"})


def _build_aa_image_table(models: list[dict]) -> html.Div:
    """Build the Image Model Arena table with ELO ratings."""
    if not models:
        return html.Div("No image model data available.", className="text-muted p-3")

    display = models[:50]  # Top 50

    cols = ["#", "Model", "Creator", "Type", "Arena ELO", "Votes", "Quality #", "Alignment #"]
    header = html.Thead(html.Tr([html.Th(c, style={"textAlign": "center", "fontSize": "0.78rem", "textTransform": "uppercase", "whiteSpace": "nowrap"}) for c in cols]))

    rows = []
    for i, m in enumerate(display):
        badge_class = "badge bg-success" if m.get("open_weights") else "badge bg-secondary"
        badge_text = "Open" if m.get("open_weights") else "Prop"
        row = html.Tr(
            [
                html.Td(str(i + 1), style={"textAlign": "center", "color": "#6c757d", "fontSize": "0.85rem"}),
                html.Td(m.get("name", "—"), style={"fontWeight": "600", "fontSize": "0.85rem", "whiteSpace": "nowrap"}),
                html.Td(m.get("creator", "—"), style={"fontSize": "0.8rem", "color": "#495057"}),
                html.Td(html.Span(badge_text, className=badge_class, style={"fontSize": "0.7rem"}), style={"textAlign": "center"}),
                _aa_score_cell(_fmt_score(m.get("arena_elo"))),
                html.Td(_fmt_score(m.get("arena_votes")), style={"textAlign": "center", "fontSize": "0.85rem", "color": "#6c757d"}),
                html.Td(_fmt_score(m.get("quality_ranking")), style={"textAlign": "center", "fontSize": "0.85rem"}),
                html.Td(_fmt_score(m.get("alignment_ranking")), style={"textAlign": "center", "fontSize": "0.85rem"}),
            ]
        )
        rows.append(row)

    tbody = html.Tbody(rows)

    table = html.Table(
        [header, tbody],
        className="table table-sm table-hover",
        style={"fontSize": "0.85rem", "marginBottom": "0", "borderCollapse": "separate", "borderSpacing": "0"},
    )

    return html.Div(table, style={"overflowX": "auto", "borderRadius": "8px", "border": "1px solid #dee2e6"})


def _get_aa_meta_text(meta: dict, filename: str) -> str:
    """Get metadata text for display."""
    items = []
    fetched = meta.get("fetched_at", "")
    if fetched:
        try:
            dt = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
            items.append(f"Updated: {dt.strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            pass
    count = meta.get("count", 0)
    if count:
        items.append(f"Models: {count}")
    return " · ".join(items)


def _render_aa_no_data() -> html.Div:
    """Render placeholder when no AA data is available."""
    return html.Div(
        [
            html.Div(
                [
                    html.H5("📊 Artificial Analysis — No Data", className="text-muted"),
                    html.P("Benchmark data not found. Run the ETL to fetch data:"),
                    html.Code("python -m src.etl.benchmarks.artificial_analysis_etl", style={"fontSize": "0.85rem"}),
                    html.P(
                        [
                            "Set ",
                            html.Code("ARTIFICIAL_ANALYSIS_API_KEY", style={"fontSize": "0.85rem"}),
                            " in your environment or .env file. Get a free key at ",
                            html.A("artificialanalysis.ai", href="https://artificialanalysis.ai/", target="_blank"),
                            ".",
                        ],
                        className="text-muted mt-2",
                        style={"fontSize": "0.85rem"},
                    ),
                ],
                className="p-3",
            ),
        ]
    )


def _render_aa_llm_section() -> html.Div:
    """Render the LLM leaderboard section."""
    models, meta = _load_aa_data("artificial_analysis_llms.json")

    if not models:
        return _render_aa_no_data()

    meta_text = _get_aa_meta_text(meta, "artificial_analysis_llms.json")
    source_link = html.A("Artificial Analysis", href="https://artificialanalysis.ai/llms", target="_blank", rel="noopener noreferrer", style={"color": "#6c757d"})

    # Summary stats
    with_evals = [m for m in models if m.get("intelligence_index") is not None]
    open_count = sum(1 for m in models if m.get("open_weights"))
    prop_count = len(models) - open_count

    summary_cards = [
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Small("Total Models", className="text-muted"),
                        html.H3(str(len(models)), className="mb-0", style={"color": "#6f42c1"}),
                    ],
                    className="text-center py-2",
                ),
            ],
            className="col-md-2 col-4 mb-2",
        ),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Small("With Scores", className="text-muted"),
                        html.H3(str(len(with_evals)), className="mb-0", style={"color": "#007bff"}),
                    ],
                    className="text-center py-2",
                ),
            ],
            className="col-md-2 col-4 mb-2",
        ),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Small("Open Weights", className="text-muted"),
                        html.H3(str(open_count), className="mb-0", style={"color": "#28a745"}),
                    ],
                    className="text-center py-2",
                ),
            ],
            className="col-md-2 col-4 mb-2",
        ),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Small("Proprietary", className="text-muted"),
                        html.H3(str(prop_count), className="mb-0", style={"color": "#6c757d"}),
                    ],
                    className="text-center py-2",
                ),
            ],
            className="col-md-2 col-4 mb-2",
        ),
    ]

    # Top models quick stats
    if with_evals:
        best_intel = max(with_evals, key=lambda m: m.get("intelligence_index") or 0)
        best_coding = max(with_evals, key=lambda m: m.get("coding_index") or 0)
        max(with_evals, key=lambda m: m.get("math_index") or 0)

        summary_cards.extend(
            [
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Small("Best Intelligence", className="text-muted"),
                                html.H6(best_intel.get("name", "—"), className="mb-0", style={"fontWeight": "700", "fontSize": "0.8rem"}),
                                html.Span(f"{_fmt_score(best_intel.get('intelligence_index'))}", className="badge bg-primary"),
                            ],
                            className="text-center py-2",
                        ),
                    ],
                    className="col-md-2 col-4 mb-2",
                ),
                dbc.Card(
                    [
                        dbc.CardBody(
                            [
                                html.Small("Best Coding", className="text-muted"),
                                html.H6(best_coding.get("name", "—"), className="mb-0", style={"fontWeight": "700", "fontSize": "0.8rem"}),
                                html.Span(f"{_fmt_score(best_coding.get('coding_index'))}", className="badge bg-warning"),
                            ],
                            className="text-center py-2",
                        ),
                    ],
                    className="col-md-2 col-4 mb-2",
                ),
            ]
        )

    # Sort/filter controls (static — Dash callbacks could make these dynamic)
    filter_info = html.Div(
        [
            html.Small(
                [
                    "💡 Showing top 100. Data is sorted by Intelligence Index by default. Use the API endpoint for custom filtering: ",
                    html.Code("/api/v1/benchmarks/artificial-analysis?model_type=llm", style={"fontSize": "0.75rem"}),
                ],
                className="text-muted",
                style={"fontSize": "0.8rem"},
            ),
        ],
        className="mb-2",
    )

    return html.Div(
        [
            html.Div(
                [
                    html.H5("🤖 LLM Leaderboard", className="mb-1", style={"fontWeight": "700"}),
                    html.P("Comprehensive benchmarks across intelligence, coding, math, pricing, and speed.", className="mb-1 text-muted", style={"fontSize": "0.85rem"}),
                    html.Small([source_link, " · ", meta_text], className="text-muted"),
                ],
                className="mb-3",
            ),
            dbc.Row(summary_cards),
            filter_info,
            _build_aa_llm_table(models),
        ]
    )


def _render_aa_image_section() -> html.Div:
    """Render the Image Model Arena section."""
    models, meta = _load_aa_data("artificial_analysis_image.json")

    if not models:
        return html.Div(
            [
                html.Div(
                    [
                        html.H5("🎨 Image Models Arena — No Data", className="text-muted"),
                        html.P("Run the ETL with the text-to-image endpoint to fetch arena data."),
                        html.Code("python -m src.etl.benchmarks.artificial_analysis_etl", style={"fontSize": "0.85rem"}),
                    ],
                    className="p-3",
                ),
            ]
        )

    meta_text = _get_aa_meta_text(meta, "artificial_analysis_image.json")
    source_link = html.A("Artificial Analysis", href="https://artificialanalysis.ai/text-to-image", target="_blank", rel="noopener noreferrer", style={"color": "#6c757d"})

    open_count = sum(1 for m in models if m.get("open_weights"))

    summary_cards = [
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Small("Total Models", className="text-muted"),
                        html.H3(str(len(models)), className="mb-0", style={"color": "#6f42c1"}),
                    ],
                    className="text-center py-2",
                ),
            ],
            className="col-md-3 col-6 mb-2",
        ),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.Small("Open Weights", className="text-muted"),
                        html.H3(str(open_count), className="mb-0", style={"color": "#28a745"}),
                    ],
                    className="text-center py-2",
                ),
            ],
            className="col-md-3 col-6 mb-2",
        ),
    ]

    if models:
        top_elo = models[0]
        summary_cards.append(
            dbc.Card(
                [
                    dbc.CardBody(
                        [
                            html.Small("Arena Leader", className="text-muted"),
                            html.H6(top_elo.get("name", "—"), className="mb-0", style={"fontWeight": "700", "fontSize": "0.8rem"}),
                            html.Span(f"ELO: {_fmt_score(top_elo.get('arena_elo'))}", className="badge bg-primary"),
                        ],
                        className="text-center py-2",
                    ),
                ],
                className="col-md-3 col-6 mb-2",
            ),
        )

    return html.Div(
        [
            html.Div(
                [
                    html.H5("🎨 Image Models Arena", className="mb-1", style={"fontWeight": "700"}),
                    html.P("ELO ratings from the Artificial Analysis text-to-image arena.", className="mb-1 text-muted", style={"fontSize": "0.85rem"}),
                    html.Small([source_link, " · ", meta_text], className="text-muted"),
                ],
                className="mb-3",
            ),
            dbc.Row(summary_cards),
            _build_aa_image_table(models),
        ]
    )


def _render_artificial_analysis_section() -> html.Div:
    """Render the complete Artificial Analysis section with sub-tabs."""
    aa_tabs = [
        dbc.Tab(label="🤖 LLM Leaderboard", tab_id="aa-llm", children=[_render_aa_llm_section()]),
        dbc.Tab(label="🎨 Image Arena", tab_id="aa-image", children=[_render_aa_image_section()]),
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.H4("📊 Artificial Analysis", className="mb-1", style={"fontWeight": "700"}),
                    html.P(
                        "Comprehensive AI model benchmarks — intelligence, coding, math, pricing, speed, and image generation arena ratings.",
                        className="text-muted mb-3",
                        style={"fontSize": "0.9rem"},
                    ),
                ]
            ),
            dbc.Tabs(aa_tabs, id="aa-category-tabs", active_tab="aa-llm", className="nav-justified"),
        ]
    )


# ═══════════════════════════════════════════════════════════════
# MAIN: Combined Benchmarks Tab
# ═══════════════════════════════════════════════════════════════


def render_benchmarks_tab() -> html.Div:
    """Render the full benchmarks tab with top-level source tabs."""
    # Top-level tabs: BridgeBench | Artificial Analysis
    top_tabs = [
        dbc.Tab(
            label="🏆 BridgeBench.ai",
            tab_id="benchmarks-bridgebench",
            children=[_render_bridgebench_section()],
        ),
        dbc.Tab(
            label="📊 Artificial Analysis",
            tab_id="benchmarks-artificial-analysis",
            children=[_render_artificial_analysis_section()],
        ),
    ]

    return html.Div(
        [
            dbc.Tabs(
                top_tabs,
                id="benchmarks-source-tabs",
                active_tab="benchmarks-bridgebench",
                className="nav-fill mb-4",
                style={"fontSize": "1.1rem"},
            ),
        ]
    )


def register_benchmarks_callbacks(app):
    """Register callbacks for the benchmarks tab (if needed)."""
    # Benchmarks tab is mostly static (data loaded from JSON files).
    # No dynamic callbacks needed unless we add live-refresh.
    pass
