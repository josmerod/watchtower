"""Security Tab — vulnerability intelligence + security news (keyless, T-050).

Aggregates the security feed (CISA KEV catalog + The Hacker News +
SecurityWeek + Krebs on Security) produced by
``src/etl/security/security_feeds_etl.py``. KEV entries (actively exploited
CVEs) surface first with ransomware-use flags; news follows. Renders via the
shared table builder, no callbacks — the file is re-read each render so the
2h orchestrator cycle refreshes it.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from src.utils.file_system import get_project_root
from src.web.dashboard.components.shared.table import render_items_table

logger = logging.getLogger(__name__)

DATA_FILE = "security/security_latest.json"
MAX_ROWS = 120


def _load_entries() -> list[dict[str, Any]]:
    """Load the merged security feed from ``data/security/``."""
    path = Path(get_project_root()) / "data" / DATA_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _parse_date(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    # KEV dateAdded is date-only → naive; make it comparable with UTC "now"
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _render_summary_cards(entries: list[dict[str, Any]]) -> dbc.Row:
    """Top-row cards: KEV shown, KEV last 7 days, ransomware-linked, news count."""
    kev = [e for e in entries if e.get("source") == "cisa_kev"]
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    recent = [e for e in kev if (d := _parse_date(e.get("published", ""))) and d >= week_ago]
    ransomware = [e for e in kev if "known" in str(e.get("summary", "")).lower().replace("known ransomware campaign use: unknown", "")]

    def card(value: str, label: str, extra: str = "") -> dbc.Col:
        return dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4(value, className=f"mb-0 {extra}" if extra else "text-danger mb-0"),
                        html.P(label, className="text-muted small mb-0"),
                    ]
                )
            ),
            xs=12,
            sm=6,
            md=3,
        )

    return dbc.Row(
        [
            card(str(len(kev)), "CVEs explotados (catálogo activo)"),
            card(str(len(recent)), "KEV añadidos últimos 7d", extra="text-warning"),
            card(str(len(ransomware)), "Con uso ransomware", extra="text-danger"),
            card(str(len(entries) - len(kev)), "Noticias de seguridad", extra="text-info"),
        ],
        className="mb-4",
    )


def render_security_tab() -> html.Div:
    """Render the Security tab: summary cards + severity-ordered feed table."""
    entries = _load_entries()
    kev = [e for e in entries if e.get("source") == "cisa_kev"]
    news = [e for e in entries if e.get("source") != "cisa_kev"]

    columns = [
        {
            "header": "Severidad",
            "cell": lambda e: dbc.Badge("🔴 Exploitado" if e.get("source") == "cisa_kev" else "📰 Noticia", color="danger" if e.get("source") == "cisa_kev" else "info", pill=True),
        },
        {
            "header": "Título",
            "cell": lambda e: html.A(
                e.get("title", "?"),
                href=e.get("link") or "#",
                target="_blank",
                className="text-decoration-none fw-bold" if e.get("source") == "cisa_kev" else "text-decoration-none",
            ),
        },
        {"header": "Fuente", "cell": lambda e: e.get("source", "?")},
        {"header": "Fecha", "cell": lambda e: str(e.get("published", ""))[:10]},
        {"header": "Resumen", "cell": lambda e: html.Small((e.get("summary") or "")[:140], className="text-muted")},
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.H3(
                        [html.I(className="fas fa-shield-alt me-2 text-primary"), "Security"],
                        className="mb-1",
                    ),
                    html.P(
                        "CISA KEV (CVEs explotados activamente) + The Hacker News, SecurityWeek y Krebs on Security — keyless, refresco cada 2h.",
                        className="text-muted mb-3",
                        style={"fontSize": "0.9rem"},
                    ),
                ]
            ),
            _render_summary_cards(entries),
            html.H6("🔴 Vulnerabilidades explotadas (KEV — más recientes primero)", className="mb-2"),
            render_items_table(kev, columns, empty_message="No KEV data yet. Run the security ETL.", wrap_scroll=True),
            html.H6("📰 Noticias de seguridad", className="mt-4 mb-2"),
            render_items_table(news, columns, empty_message="No security news yet.", wrap_scroll=True),
        ]
    )
