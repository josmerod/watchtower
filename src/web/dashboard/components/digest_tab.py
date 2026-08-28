"""Digest Tab — weekly "last week" summary (T-054).

Renders ``data/insights/digest_latest.json`` written by
``src/etl/analytics/weekly_digest_etl.py``: top trending terms, best radar
articles and crypto market movers, plus optional context blocks (courses
watcher events, data freshness). Every section degrades to an empty state
when its data is missing — the tab never crashes on a partial digest.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import ALL, Dash, Input, Output, html

from src.utils.file_system import get_project_root
from src.web.dashboard.components.shared.table import create_refresh_button

logger = logging.getLogger(__name__)

DATA_FILE = "insights/digest_latest.json"


def _load_digest() -> dict[str, Any]:
    """Load the digest snapshot from ``data/insights/`` (empty when missing)."""
    path = Path(get_project_root()) / "data" / DATA_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as e:
        logger.warning(f"Unreadable digest file {path}: {e}")
        return {}


def _fmt_pct(value: Any) -> str:
    """Format a percentage with sign (None → em dash)."""
    if value is None:
        return "—"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_dt(raw: Any) -> str:
    """Human-friendly '28 Aug 2026 10:06' from an ISO string (fallback: raw)."""
    text = str(raw or "")
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%d %b %Y %H:%M")
    except ValueError:
        return text


def _card(title: str, body: Any, badge_text: str | None = None, color: str = "primary") -> dbc.Card:
    """Premium-minimal card shell with an optional count badge in the header."""
    header = [
        html.Span(title, className="fw-semibold"),
    ]
    if badge_text is not None:
        header.append(dbc.Badge(badge_text, color=color, pill=True, className="ms-2 align-middle"))
    return dbc.Card(
        [
            dbc.CardHeader(html.Div(header, className="d-flex align-items-center")),
            dbc.CardBody(body, className="p-0"),
        ],
        className="h-100 shadow-sm",
    )


def _terms_card(digest: dict[str, Any]) -> dbc.Card:
    """Términos 🔥 — top trending terms with mention/source counts."""
    terms = digest.get("top_terms") or []
    items = (
        dbc.ListGroup(
            [
                dbc.ListGroupItem(
                    [
                        html.Div(
                            [
                                html.Span(f"🔥 {t.get('term', '?')}", className="fw-semibold"),
                                dbc.Badge(f"{t.get('mentions', 0)} menciones · {t.get('sources', 0)} fuentes", color="danger", pill=True, className="float-end"),
                            ],
                            className="d-flex justify-content-between align-items-center w-100",
                        )
                    ],
                    className="py-2",
                )
                for t in terms
            ],
            flush=True,
        )
        if terms
        else html.P("Sin términos tendencia esta semana.", className="text-muted mb-0 p-3")
    )
    return _card("Términos 🔥", items, badge_text=str(len(terms)) if terms else None, color="danger")


def _radar_card(digest: dict[str, Any]) -> dbc.Card:
    """Mejores del Radar — top articles ranked by 🔥 mentions / recency."""
    articles = digest.get("radar_best") or []
    items = (
        dbc.ListGroup(
            [
                dbc.ListGroupItem(
                    [
                        html.A(a.get("title", "Untitled"), href=a.get("url") or "#", target="_blank", className="text-decoration-none fw-semibold"),
                        html.Div(
                            [html.Small(a.get("source", ""), className="text-muted")] + [dbc.Badge(f"🔥 {term}", color="danger", pill=True, className="ms-1") for term in a.get("trending_terms", [])],
                            className="mt-1",
                        ),
                    ],
                    className="py-2",
                )
                for a in articles
            ],
            flush=True,
        )
        if articles
        else html.P("Sin artículos del radar esta semana.", className="text-muted mb-0 p-3")
    )
    return _card("Mejores del Radar", items, badge_text=str(len(articles)) if articles else None, color="info")


def _movers_card(digest: dict[str, Any]) -> dbc.Card:
    """Movers 📈 — top 24h crypto gainers and losers."""
    movers = digest.get("market_movers") or {}
    gainers = movers.get("gainers") or []
    losers = movers.get("losers") or []

    def _rows(coins: list[dict[str, Any]], color: str) -> list[html.Div]:
        return [
            html.Div(
                [
                    html.Span(f"{c.get('name', '?')} ", className="fw-semibold"),
                    html.Small(f"({c.get('symbol', '')})", className="text-muted"),
                    dbc.Badge(_fmt_pct(c.get("change_24h_pct")), color=color, pill=True, className="float-end"),
                ],
                className="d-flex justify-content-between align-items-center px-3 py-2 border-bottom",
            )
            for c in coins
        ]

    body: html.Div | html.P
    if not gainers and not losers:
        body = html.P("Sin datos de mercado.", className="text-muted mb-0 p-3")
    else:
        body = html.Div(
            [html.Small("Top ganadores 24h", className="text-success fw-semibold px-3 pt-3")]
            + _rows(gainers, "success")
            + [html.Small("Top perdedores 24h", className="text-danger fw-semibold px-3 pt-3")]
            + _rows(losers, "danger")
        )
    return _card("Movers 📈", body, badge_text=str(len(gainers) + len(losers)) if (gainers or losers) else None, color="success")


def _context_row(digest: dict[str, Any]) -> dbc.Row:
    """Small context cards: courses-watcher events + data freshness snapshot."""
    courses = digest.get("courses_watcher")
    freshness = digest.get("freshness")

    courses_body = (
        html.Div(
            [
                html.H4(f"{courses.get('events_last_week', 0)}", className="text-primary mb-0"),
                html.P(f"eventos de cursos en 7 días · {courses.get('total_events', 0)} totales", className="text-muted small mb-0"),
                html.Small(f"Último check: {_fmt_dt(courses.get('last_check'))}", className="text-muted"),
            ],
            className="p-3",
        )
        if courses
        else html.P("Watcher de cursos sin datos.", className="text-muted mb-0 p-3")
    )

    fresh_body = (
        html.Div(
            [
                html.Div(
                    [
                        dbc.Badge(f"✓ {freshness['counts'].get('fresh', 0)} frescas", color="success", className="me-1"),
                        dbc.Badge(f"⏳ {freshness['counts'].get('stale', 0)} obsoletas", color="warning", className="me-1"),
                        dbc.Badge(f"⚠ {freshness['counts'].get('critical', 0)} críticas", color="danger"),
                    ],
                    className="mb-2",
                ),
                html.Small(f"Comprobado: {_fmt_dt(freshness.get('checked_at'))}", className="text-muted"),
            ],
            className="p-3",
        )
        if freshness
        else html.P("Watcher de frescura sin datos.", className="text-muted mb-0 p-3")
    )

    return dbc.Row(
        [
            dbc.Col(_card("🎓 Cursos (watcher)", courses_body), xs=12, lg=6, className="mb-3"),
            dbc.Col(_card("🩺 Frescura de datos", fresh_body), xs=12, lg=6, className="mb-3"),
        ],
        className="g-3",
    )


def _render_content(digest: dict[str, Any]) -> list[Any]:
    """Build the tab body (three main cards + context row + footer)."""
    if not digest:
        return [
            dbc.Alert(
                [
                    html.Div("Aún no hay digest. Genera el resumen semanal ejecutando:"),
                    html.Code("uv run python src/etl/analytics/weekly_digest_etl.py", className="d-block mt-2"),
                ],
                color="secondary",
                className="mt-2",
            )
        ]
    period = digest.get("period") or {}
    footer = html.P(
        f"Generado: {_fmt_dt(digest.get('generated_at'))} · ventana de {period.get('days', 7)} días · refresco con cada ciclo del orquestador",
        className="text-muted small mt-2 mb-0",
    )
    return [
        dbc.Row(
            [
                dbc.Col(_terms_card(digest), xs=12, lg=4, className="mb-3"),
                dbc.Col(_radar_card(digest), xs=12, lg=4, className="mb-3"),
                dbc.Col(_movers_card(digest), xs=12, lg=4, className="mb-3"),
            ],
            className="g-3",
        ),
        _context_row(digest),
        footer,
    ]


def render_digest_tab() -> html.Div:
    """Render the Digest tab: weekly summary from data/insights/digest_latest.json."""
    digest = _load_digest()
    period = digest.get("period") or {}
    subtitle = f"Semana del {_fmt_dt(period.get('start'))} al {_fmt_dt(period.get('end'))}" if period else "Resumen de la última semana"
    refresh = create_refresh_button("digest")
    return html.Div(
        [
            html.Div(
                [
                    html.H3(
                        [html.I(className="fas fa-calendar-check me-2 text-primary"), "📅 Digest"],
                        className="mb-1",
                    ),
                    html.P(subtitle, className="text-muted mb-3", style={"fontSize": "0.9rem"}),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(width="auto", className="flex-grow-1"),
                    dbc.Col(refresh, width="auto", className="align-self-end pb-1"),
                ],
                className="g-2",
            ),
            html.Div(id="digest-content", children=_render_content(digest), className="mt-2"),
        ]
    )


def register_digest_callbacks(app: Dash) -> None:
    """Wire this tab's single refresh callback on the app."""

    @app.callback(
        Output("digest-content", "children"),
        Input({"type": "digest-refresh", "tab": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _refresh_digest(_n_clicks) -> list[Any]:
        """Re-read the digest snapshot and re-render the content block."""
        try:
            return _render_content(_load_digest())
        except Exception as e:  # surface errors in the UI
            logger.error(f"Error refreshing digest: {e}")
            return [dbc.Alert(f"Error refreshing digest: {e}", color="danger")]
