"""Security Tab — vulnerability intelligence + security news (keyless, T-050).

Aggregates the security feed (CISA KEV catalog + The Hacker News +
SecurityWeek + Krebs on Security) produced by
``src/etl/security/security_feeds_etl.py``. KEV entries (actively exploited
CVEs) surface first with ransomware-use flags; news follows. Since T-081 the
feed's ``stack_matches`` section (KEV crossed with the self-hosted stack) renders as
the "🧰 Tu stack" card plus a danger-toned match list — the CVEs actively
exploited that hit the homelab's own services. Since T-091 the same card area
also renders the OSV companion section: advisories of severity >= high from
OSV.dev/GHSA for the stack's own services (``osv_stack_latest.json`` written by
``src/etl/security/osv_stack_advisories_etl.py``), as an osv.dev-linked compact
list. Renders via the shared table builder, no callbacks — the files are
re-read each render so the 2h orchestrator cycle refreshes them.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from src.etl.security.stack_cves import total_stack_matches
from src.utils.file_system import get_project_root
from src.web.dashboard.components.shared.table import render_items_table

logger = logging.getLogger(__name__)

DATA_FILE = "security/security_latest.json"
OSV_DATA_FILE = "security/osv_stack_latest.json"
MAX_ROWS = 120


def _load_feed() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load the merged security feed plus stack matches from ``data/security/``.

    Supports both the current envelope (``{"items": [...], "stack_matches":
    [...]}``) and the legacy flat-list payload (matches default to empty), so
    a stale pre-T-081 file still renders.
    """
    path = Path(get_project_root()) / "data" / DATA_FILE
    if not path.exists():
        return [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], []
    if isinstance(data, dict):
        items = data.get("items")
        matches = data.get("stack_matches")
        return (
            items if isinstance(items, list) else [],
            matches if isinstance(matches, list) else [],
        )
    return (data if isinstance(data, list) else []), []


def _load_osv_services() -> list[dict[str, Any]]:
    """Load the OSV stack advisory groups from ``data/security/`` (T-091).

    Reads ``osv_stack_latest.json`` — ``[{"repo", "service_label",
    "advisories": [...]}, ...]``. A missing or broken file yields ``[]`` so the
    OSV section simply stays quiet until the ETL's first successful run.
    """
    path = Path(get_project_root()) / "data" / OSV_DATA_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    services = data.get("services") if isinstance(data, dict) else None
    return services if isinstance(services, list) else []


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
    ransomware = [e for e in kev if e.get("ransomware_use") == "Known"]

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


def _render_stack_section(stack_matches: list[dict[str, Any]]) -> list[Any]:
    """Render the "🧰 Tu stack" card plus, when there are hits, the match list.

    Calm state (0 matches) is a quiet success card: "0 CVEs explotados afectan
    a tu stack". Any match flips it to danger tones and appends the
    highlighted list — one row per (service, CVE) with repo badge, NVD link,
    product, dateAdded and a ransomware badge when KEV flags campaign use.
    """
    total = total_stack_matches(stack_matches)
    if total == 0:
        return [
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5([html.I(className="fas fa-toolbox me-2"), "🧰 Tu stack"], className="small text-muted mb-1"),
                        html.P(
                            [html.I(className="fas fa-check-circle me-2"), "0 CVEs explotados afectan a tu stack"],
                            className="mb-0 text-success fw-bold",
                        ),
                    ]
                ),
                outline=True,
                color="success",
                className="mb-4",
            )
        ]

    rows: list[Any] = []
    for group in stack_matches:
        label = str(group.get("service_label") or group.get("repo") or "?")
        cves = group.get("cves")
        for entry in cves if isinstance(cves, list) else []:
            if not isinstance(entry, dict):
                continue
            cve = str(entry.get("cve") or "?")
            children: list[Any] = [
                dbc.Badge(label, color="warning", pill=True, className="me-2"),
                html.A(
                    cve,
                    href=f"https://nvd.nist.gov/vuln/detail/{cve}",
                    target="_blank",
                    className="fw-bold text-decoration-none text-danger me-2",
                ),
                html.Span(str(entry.get("product") or "—"), className="text-muted me-2"),
                html.Small(f"añadido {str(entry.get('dateAdded') or '')[:10]}", className="text-muted"),
            ]
            if entry.get("ransomware") == "Known":
                children.append(dbc.Badge("🔐 Ransomware", color="danger", pill=True, className="ms-2"))
            rows.append(html.Div(children, className="d-flex flex-wrap align-items-center py-1 border-bottom border-secondary-subtle"))

    return [
        dbc.Card(
            dbc.CardBody(
                [
                    html.H5([html.I(className="fas fa-toolbox me-2"), "🧰 Tu stack"], className="small mb-1"),
                    html.H4(f"{total}", className="text-danger mb-0"),
                    html.P("CVEs explotados activamente afectan a tu stack", className="text-danger small mb-0"),
                ]
            ),
            color="danger",
            className="mb-3",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.H6([html.I(className="fas fa-bolt me-2"), "CVEs que afectan a TU stack"], className="text-danger mb-2"),
                    html.Div(rows),
                ]
            ),
            color="danger",
            outline=True,
            className="mb-4",
        ),
    ]


def _render_osv_section(services: list[dict[str, Any]]) -> list[Any]:
    """Render the OSV advisories companion card in the "🧰 Tu stack" area (T-091).

    A missing file (ETL not run yet) renders nothing; a calm file (0 advisories
    >= high) renders a quiet success card. Any hit flips to warning tones and
    appends the compact list — one row per advisory with service badge,
    osv.dev permalink, severity badge, CVSS score when exact, fixed-in version
    when known and the published date. The existing KEV card stays untouched.
    """
    if not services:
        return []
    total = sum(len(group.get("advisories") or []) for group in services if isinstance(group, dict))
    if total == 0:
        return [
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5([html.I(className="fas fa-shield-virus me-2"), "🛡️ OSV · Tu stack"], className="small text-muted mb-1"),
                        html.P(
                            [html.I(className="fas fa-check-circle me-2"), "OSV advisories (≥high): 0 — tu stack está en calma"],
                            className="mb-0 text-success fw-bold",
                        ),
                    ]
                ),
                outline=True,
                color="success",
                className="mb-4",
            )
        ]

    rows: list[Any] = []
    for group in services:
        label = str(group.get("service_label") or group.get("repo") or "?")
        advisories = group.get("advisories")
        for advisory in advisories if isinstance(advisories, list) else []:
            if not isinstance(advisory, dict):
                continue
            advisory_id = str(advisory.get("id") or "?")
            severity = str(advisory.get("severity") or "?")
            children: list[Any] = [
                dbc.Badge(label, color="secondary", pill=True, className="me-2"),
                html.A(
                    advisory_id,
                    href=f"https://osv.dev/vulnerability/{advisory_id}",
                    target="_blank",
                    className="fw-bold text-decoration-none text-danger me-2",
                ),
                dbc.Badge(severity, color="danger" if severity == "CRITICAL" else "warning", pill=True, className="me-2"),
            ]
            if advisory.get("cvss_score") is not None:
                children.append(html.Small(f"CVSS {advisory['cvss_score']}", className="text-muted me-2"))
            if advisory.get("fixed_in"):
                children.append(dbc.Badge(f"fixed in {advisory['fixed_in']}", color="success", pill=True, className="me-2"))
            children.append(html.Small(str(advisory.get("published") or "")[:10], className="text-muted"))
            rows.append(html.Div(children, className="d-flex flex-wrap align-items-center py-1 border-bottom border-secondary-subtle"))

    return [
        dbc.Card(
            dbc.CardBody(
                [
                    html.H5([html.I(className="fas fa-shield-virus me-2"), "🛡️ OSV · Tu stack"], className="small mb-1"),
                    html.H4(f"OSV advisories (≥high): {total}", className="text-warning mb-0"),
                    html.P("Avisos OSV/GHSA para los servicios de tu stack", className="text-warning small mb-0"),
                ]
            ),
            color="warning",
            className="mb-3",
        ),
        dbc.Card(
            dbc.CardBody(
                [
                    html.H6([html.I(className="fas fa-bug me-2"), "Avisos OSV (≥high) en TU stack"], className="text-warning mb-2"),
                    html.Div(rows),
                ]
            ),
            color="warning",
            outline=True,
            className="mb-4",
        ),
    ]


def render_security_tab() -> html.Div:
    """Render the Security tab: summary cards + severity-ordered feed table."""
    entries, stack_matches = _load_feed()
    osv_services = _load_osv_services()
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
            *_render_stack_section(stack_matches),
            *_render_osv_section(osv_services),
            html.H6("🔴 Vulnerabilidades explotadas (KEV — más recientes primero)", className="mb-2"),
            render_items_table(kev, columns, empty_message="No KEV data yet. Run the security ETL.", wrap_scroll=True),
            html.H6("📰 Noticias de seguridad", className="mt-4 mb-2"),
            render_items_table(news, columns, empty_message="No security news yet.", wrap_scroll=True),
        ]
    )
