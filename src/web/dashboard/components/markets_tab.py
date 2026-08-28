"""Markets Tab — cryptocurrency market overview (CoinGecko, keyless).

Watchtower's first financial-capability tab (T-043 v1): top coins by market
cap with 24h/7d moves, market cap and volume. Renders via the shared table
builder; the file is re-read on every tab render so data refreshes with the
2h orchestrator cycle.
"""

import json
import logging
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import html

from src.utils.file_system import get_project_root
from src.web.dashboard.components import saved_items
from src.web.dashboard.components.shared.table import render_items_table

logger = logging.getLogger(__name__)

DATA_FILE = "markets/coingecko_latest.json"

# ⭐ Saved-items toggle (T-053): every coin row gets a star. Pattern id type
# per tab, shared persistence with Knowledge Garden via
# data/garden/saved_items.json.
MARKETS_SAVE_BTN_TYPE = "markets-save-btn"


def _load_coins() -> list[dict[str, Any]]:
    """Load the CoinGecko snapshot from ``data/markets/``."""
    path = Path(get_project_root()) / "data" / DATA_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _fmt_usd(value: Any, compact: bool = True) -> str:
    """Format a USD amount, compact by default (1.2T / 340B / 12.4K)."""
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "—"
    if compact:
        for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
            if abs(amount) >= threshold:
                return f"${amount / threshold:,.2f}{suffix}"
        return f"${amount:,.2f}"
    return f"${amount:,.2f}"


def _fmt_pct(value: Any) -> str:
    """Format a percentage with sign (None → em dash)."""
    if value is None:
        return "—"
    try:
        return f"{float(value):+.2f}%"
    except (TypeError, ValueError):
        return "—"


def _pct_cell(coin: dict[str, Any], field: str) -> html.Span:
    """Color-coded percentage cell (green up / red down)."""
    value = coin.get(field)
    color = "text-success" if (value or 0) >= 0 else "text-danger"
    return html.Span(_fmt_pct(value), className=f"fw-bold {color}")


def _render_summary_cards(coins: list[dict[str, Any]]) -> dbc.Row:
    """Top-row cards: total cap, BTC dominance, best and worst 24h movers."""
    total_cap = sum(c.get("market_cap_usd") or 0 for c in coins)
    btc_cap = next((c.get("market_cap_usd") or 0 for c in coins if c.get("id") == "bitcoin"), 0)
    btc_dominance = (btc_cap / total_cap * 100) if total_cap else None
    by_change = sorted((c for c in coins if c.get("change_24h_pct") is not None), key=lambda c: c["change_24h_pct"])
    worst = by_change[0] if by_change else None
    best = by_change[-1] if by_change else None

    def card(value: str, label: str, extra: str = "") -> dbc.Col:
        return dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H4(value, className="text-primary mb-0" + (f" {extra}" if extra else "")),
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
            card(_fmt_usd(total_cap), "Market Cap (top 50)"),
            card(_fmt_pct(btc_dominance), "BTC Dominance"),
            card(
                f"{best['symbol']} {_fmt_pct(best['change_24h_pct'])}" if best else "—",
                "Mejor 24h",
                extra="text-success",
            ),
            card(
                f"{worst['symbol']} {_fmt_pct(worst['change_24h_pct'])}" if worst else "—",
                "Peor 24h",
                extra="text-danger",
            ),
        ],
        className="mb-4",
    )


def _coin_save_record(coin: dict[str, Any]) -> dict[str, Any]:
    """Saved-items record for a coin row (market rows have no article URL)."""
    name = f"{coin.get('name', '?')} ({coin.get('symbol', '')})"
    url = f"https://www.coingecko.com/en/coins/{coin['id']}" if coin.get("id") else None
    return {"title": name, "url": url, "source": "Markets (CoinGecko)"}


def _save_button(coin: dict[str, Any]):
    """⭐ toggle for one coin row (shared saved-items builder)."""
    return saved_items.save_button(_coin_save_record(coin), MARKETS_SAVE_BTN_TYPE, tab="markets")


def render_markets_tab() -> html.Div:
    """Render the Markets tab: summary cards + top-50 coins table."""
    coins = _load_coins()

    columns = [
        {
            "header": "",
            "cell": lambda c: _save_button(c),
            "td_kwargs": {"style": {"width": "2rem"}},
        },
        {"header": "#", "cell": lambda c: str(c.get("rank") or "—")},
        {
            "header": "Coin",
            "cell": lambda c: html.Span(
                [
                    html.Strong(c.get("name", "?")),
                    html.Span(f"  {c.get('symbol', '')}", className="text-muted ms-1"),
                ]
            ),
        },
        {"header": "Precio", "cell": lambda c: _fmt_usd(c.get("price_usd"), compact=False)},
        {"header": "24h", "cell": lambda c: _pct_cell(c, "change_24h_pct")},
        {"header": "7d", "cell": lambda c: _pct_cell(c, "change_7d_pct")},
        {"header": "Market Cap", "cell": lambda c: _fmt_usd(c.get("market_cap_usd"))},
        {"header": "Volumen 24h", "cell": lambda c: _fmt_usd(c.get("volume_24h_usd"))},
        {"header": "vs ATH", "cell": lambda c: _fmt_pct(c.get("ath_change_pct"))},
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.H3(
                        [html.I(className="fas fa-chart-line me-2 text-primary"), "Markets"],
                        className="mb-1",
                    ),
                    html.P(
                        "Top 50 criptomonedas por capitalización — CoinGecko (keyless), refresco cada 2h con el orquestador.",
                        className="text-muted mb-3",
                        style={"fontSize": "0.9rem"},
                    ),
                ]
            ),
            _render_summary_cards(coins),
            render_items_table(coins, columns, empty_message="No market data yet. Run the CoinGecko ETL (`uv run python -m src.etl.markets.coingecko_etl`)."),
        ]
    )


def register_markets_callbacks(app: dash.Dash) -> None:
    """Register Markets tab callbacks.

    Currently only the ⭐ saved-items toggles on coin rows (T-053): a
    pattern-matching callback on the star buttons, targeting new outputs.
    Wired from app.py alongside the other tabs' register functions.
    """
    saved_items.register_save_toggle_callback(app, MARKETS_SAVE_BTN_TYPE)
