"""Markets Tab — cryptocurrency market overview (CoinGecko, keyless).

Watchtower's first financial-capability tab (T-043 v1): top coins by market
cap with 24h/7d moves, market cap and volume. Renders via the shared table
builder; the file is re-read on every tab render so data refreshes with the
2h orchestrator cycle.

"💼 Mi cartera" (T-086): a local-only crypto portfolio on top of the same
snapshot. Holdings live in browser localStorage (dcc.Store) and are valued
client-triggered against the CoinGecko prices loaded here — personal,
keyless, data never leaves the browser.
"""

import json
import logging
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from src.utils.file_system import get_project_root
from src.web.dashboard.components import portfolio, saved_items
from src.web.dashboard.components.shared.table import render_items_table

logger = logging.getLogger(__name__)

DATA_FILE = "markets/coingecko_latest.json"

# ⭐ Saved-items toggle (T-053): every coin row gets a star. Pattern id type
# per tab, shared persistence with Knowledge Garden via
# data/garden/saved_items.json.
MARKETS_SAVE_BTN_TYPE = "markets-save-btn"

# 💼 Mi cartera (T-086): every component id is namespaced "markets-portfolio-*"
# so nothing collides with the ⭐ save buttons or other tabs. Holdings persist
# in localStorage via the store; per-row delete buttons share one pattern type.
PORTFOLIO_STORE_ID = "markets-portfolio-store"
PORTFOLIO_TOGGLE_ID = "markets-portfolio-toggle"
PORTFOLIO_COLLAPSE_ID = "markets-portfolio-collapse"
PORTFOLIO_COIN_INPUT_ID = "markets-portfolio-coin"
PORTFOLIO_AMOUNT_INPUT_ID = "markets-portfolio-amount"
PORTFOLIO_PRICE_INPUT_ID = "markets-portfolio-price"
PORTFOLIO_ADD_BTN_ID = "markets-portfolio-add"
PORTFOLIO_FEEDBACK_ID = "markets-portfolio-feedback"
PORTFOLIO_TABLE_ID = "markets-portfolio-table"
PORTFOLIO_DELETE_BTN_TYPE = "markets-portfolio-delete"


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


def _fmt_amount(value: Any) -> str:
    """Format a coin amount, trimming trailing zeros (0.50000000 → 0.5)."""
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{amount:,.8f}".rstrip("0").rstrip(".")


def _fmt_price(value: Any) -> str:
    """Format a unit price, keeping precision for sub-cent prices (SHIB-style)."""
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "—"
    if 0 < abs(amount) < 0.01:
        return f"${amount:.8f}".rstrip("0").rstrip(".")
    return _fmt_usd(amount, compact=False)


def _fmt_signed_usd(value: Any) -> str:
    """Format a signed USD delta (+$123.45 / -$67.89)."""
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{'+' if amount >= 0 else '-'}${abs(amount):,.2f}"


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


def _portfolio_feedback(message: str, ok: bool) -> html.P:
    """Small inline feedback line for add/delete/validation outcomes."""
    prefix = "✓ " if ok else "⚠ "
    color = "text-success" if ok else "text-danger"
    return html.P(f"{prefix}{message}", className=f"{color} mb-0")


def _render_portfolio_content(holdings: list[dict[str, Any]], coins: list[dict[str, Any]]) -> Any:
    """Render the holdings table (or the empty-state hint) plus totals row.

    Server-side this initially renders the empty state; the portfolio render
    callback replaces it from the localStorage store and re-reads the
    CoinGecko snapshot for live prices.
    """
    prices = portfolio.price_lookup(coins)
    if not holdings:
        return dbc.Alert(
            [
                html.I(className="fas fa-wallet me-2"),
                "Tu cartera está vacía. ",
                html.Span(
                    "Añade tu primera posición arriba (moneda, cantidad y precio medio de compra) y se valorará con los precios en vivo de la tabla.",
                    className="text-muted",
                ),
            ],
            color="secondary",
            className="small mb-0",
        )

    positions = [(holding, portfolio.compute_position(holding, prices.get(str(holding.get("coin_id"))))) for holding in holdings]
    totals = portfolio.compute_totals(holdings, prices)

    header = html.Thead(
        html.Tr(
            [
                html.Th("Moneda"),
                html.Th("Cantidad", className="text-end"),
                html.Th("Precio compra", className="text-end"),
                html.Th("Precio actual", className="text-end"),
                html.Th("Valor", className="text-end"),
                html.Th("P/L %", className="text-end"),
                html.Th("", style={"width": "2rem"}),
            ]
        )
    )

    body_rows = []
    for holding, position in positions:
        coin_id = str(holding.get("coin_id"))
        current_price = prices.get(coin_id)
        pl_pct = position["pl_pct"]
        if pl_pct is None:
            pl_cell: Any = html.Span("—", className="text-muted")
        else:
            pl_cell = html.Span(_fmt_pct(pl_pct), className=f"fw-bold {'text-success' if pl_pct >= 0 else 'text-danger'}")
        body_rows.append(
            html.Tr(
                [
                    html.Td(
                        html.Span(
                            [
                                html.Strong(holding.get("name") or coin_id),
                                html.Span(f" {holding.get('symbol', '')}", className="text-muted ms-1"),
                            ]
                        )
                    ),
                    html.Td(_fmt_amount(holding.get("amount")), className="text-end"),
                    html.Td(_fmt_price(holding.get("avg_buy_price")), className="text-end"),
                    html.Td(_fmt_price(current_price), className="text-end"),
                    html.Td(_fmt_usd(position["value_usd"], compact=False), className="text-end"),
                    html.Td(pl_cell, className="text-end"),
                    html.Td(
                        dbc.Button(
                            "🗑",
                            id={"type": PORTFOLIO_DELETE_BTN_TYPE, "coin_id": coin_id},
                            color="link",
                            size="sm",
                            className="p-0 text-danger",
                            title="Eliminar posición",
                        ),
                        className="text-center",
                    ),
                ]
            )
        )

    if totals["pl_pct"] is None:
        pl_total_cell: Any = html.Span("—", className="text-muted")
    else:
        pl_total_cell = html.Span(
            [_fmt_pct(totals["pl_pct"]), html.Span(f" ({_fmt_signed_usd(totals['pl_usd'])})", className="text-muted ms-1")],
            className=f"fw-bold {'text-success' if totals['pl_usd'] >= 0 else 'text-danger'}",
        )
    footer = html.Tfoot(
        html.Tr(
            [
                html.Td(
                    html.Span(
                        f"Total ({totals['positions']} posición{'es' if totals['positions'] != 1 else ''})",
                        className="fw-bold",
                    )
                ),
                html.Td("", className="text-end"),
                html.Td("", className="text-end"),
                html.Td("", className="text-end"),
                html.Td(_fmt_usd(totals["value_usd"], compact=False), className="text-end fw-bold"),
                html.Td(pl_total_cell, className="text-end"),
                html.Td(""),
            ]
        )
    )

    children: list[Any] = [
        dbc.Table(
            [header, html.Tbody(body_rows), footer],
            bordered=True,
            hover=True,
            responsive=True,
            striped=True,
            size="sm",
            color="dark",
            className="mb-0",
        )
    ]
    if totals["missing_prices"]:
        children.append(
            html.P(
                f"— {totals['missing_prices']} posición(es) sin precio en vivo (fuera del top 50 actual): se conservan, pero no cuentan en el total.",
                className="text-muted small mt-2 mb-0",
            )
        )
    return html.Div(children)


def _render_portfolio_section(coins: list[dict[str, Any]]) -> html.Div:
    """💼 Mi cartera: collapsible local-only portfolio above the coins table.

    Holds the localStorage store, the add form and the holdings table
    container (initially the server-rendered empty state).
    """
    options = [{"label": f"{coin.get('name', '?')} ({coin.get('symbol', '')})", "value": coin["id"]} for coin in coins if coin.get("id")]
    return html.Div(
        [
            dbc.Button(
                "💼 Mi cartera",
                id=PORTFOLIO_TOGGLE_ID,
                color="primary",
                outline=True,
                size="sm",
                className="mb-2",
                title="Tu cartera personal: vive solo en este navegador",
            ),
            dbc.Collapse(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.P(
                                "🔒 100% local — tus posiciones se guardan solo en este navegador (localStorage), sin cuentas ni claves, y se valoran con los precios CoinGecko que ya carga la pestaña.",
                                className="text-muted small mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dcc.Dropdown(id=PORTFOLIO_COIN_INPUT_ID, options=options, placeholder="Moneda…", clearable=True),
                                        xs=12,
                                        md=4,
                                        className="mb-2",
                                    ),
                                    dbc.Col(
                                        dbc.Input(id=PORTFOLIO_AMOUNT_INPUT_ID, type="number", min=0, step="any", placeholder="Cantidad (p. ej. 0.5)"),
                                        xs=6,
                                        md=3,
                                        className="mb-2",
                                    ),
                                    dbc.Col(
                                        dbc.Input(id=PORTFOLIO_PRICE_INPUT_ID, type="number", min=0, step="any", placeholder="Precio medio compra (USD)"),
                                        xs=6,
                                        md=3,
                                        className="mb-2",
                                    ),
                                    dbc.Col(
                                        dbc.Button("➕ Añadir", id=PORTFOLIO_ADD_BTN_ID, color="primary", size="sm", n_clicks=0),
                                        xs=6,
                                        md=2,
                                        className="mb-2",
                                    ),
                                ],
                                className="g-2",
                            ),
                            html.Div(id=PORTFOLIO_FEEDBACK_ID, className="small mb-2"),
                            html.Div(_render_portfolio_content([], coins), id=PORTFOLIO_TABLE_ID),
                        ]
                    ),
                    className="shadow-sm",
                ),
                id=PORTFOLIO_COLLAPSE_ID,
                is_open=False,
            ),
            dcc.Store(id=PORTFOLIO_STORE_ID, storage_type="local", data=[]),
        ],
        className="mb-4",
    )


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
            _render_portfolio_section(coins),
            render_items_table(coins, columns, empty_message="No market data yet. Run the CoinGecko ETL (`uv run python -m src.etl.markets.coingecko_etl`)."),
        ]
    )


def register_markets_callbacks(app: dash.Dash) -> None:
    """Register Markets tab callbacks.

    ⭐ saved-items toggles on coin rows (T-053) plus the 💼 Mi cartera
    portfolio callbacks (T-086): section toggle, the single store-mutating
    callback (add + delete), and the store-driven table render. All wired
    from app.py alongside the other tabs' register functions.
    """
    saved_items.register_save_toggle_callback(app, MARKETS_SAVE_BTN_TYPE)

    @app.callback(
        Output(PORTFOLIO_COLLAPSE_ID, "is_open"),
        Input(PORTFOLIO_TOGGLE_ID, "n_clicks"),
        prevent_initial_call=True,
    )
    def _toggle_portfolio_section(n_clicks: int) -> bool:
        """Abrir/cerrar la sección Mi cartera (impar abre)."""
        return bool(n_clicks and n_clicks % 2)

    @app.callback(
        Output(PORTFOLIO_STORE_ID, "data"),
        Output(PORTFOLIO_FEEDBACK_ID, "children"),
        Output(PORTFOLIO_COIN_INPUT_ID, "value"),
        Output(PORTFOLIO_AMOUNT_INPUT_ID, "value"),
        Output(PORTFOLIO_PRICE_INPUT_ID, "value"),
        Input(PORTFOLIO_ADD_BTN_ID, "n_clicks"),
        Input({"type": PORTFOLIO_DELETE_BTN_TYPE, "coin_id": dash.ALL}, "n_clicks"),
        State(PORTFOLIO_COIN_INPUT_ID, "value"),
        State(PORTFOLIO_AMOUNT_INPUT_ID, "value"),
        State(PORTFOLIO_PRICE_INPUT_ID, "value"),
        State(PORTFOLIO_STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _mutate_portfolio(add_clicks, delete_clicks, coin_id, amount_raw, price_raw, store_data):
        """Añadir/eliminar posiciones — única escritora del store (T-086).

        Add validates (moneda seleccionada, cantidad > 0, precio >= 0) and
        merges duplicates by coin_id at a weighted-average price; delete
        removes by the coin_id carried on the row's pattern id. The n_clicks
        guard ignores the fires that lazily-rendered/refreshed components
        emit on mount (fresh buttons report None/0).
        """
        no_change = (dash.no_update,) * 5
        try:
            triggered = dash.ctx.triggered_id
            clicks = next((entry.get("value") for entry in dash.ctx.triggered if entry.get("id") == triggered), None)
            if triggered is None or not clicks:
                return no_change

            holdings = portfolio.normalize_holdings(store_data)

            if isinstance(triggered, dict):  # a 🗑 delete button fired
                target = str(triggered.get("coin_id") or "")
                removed = next((h for h in holdings if str(h.get("coin_id")) == target), None)
                label = (removed or {}).get("symbol") or (removed or {}).get("name") or target
                new_holdings = portfolio.remove_holding(holdings, target)
                return new_holdings, _portfolio_feedback(f"Posición {label} eliminada.", True), dash.no_update, dash.no_update, dash.no_update

            coin = next((c for c in _load_coins() if str(c.get("id")) == str(coin_id)), None)
            if coin is None:
                return dash.no_update, _portfolio_feedback("Selecciona una moneda de la lista.", False), dash.no_update, dash.no_update, dash.no_update
            amount = portfolio.parse_amount(amount_raw)
            if amount is None:
                return dash.no_update, _portfolio_feedback("La cantidad debe ser un número mayor que 0.", False), dash.no_update, dash.no_update, dash.no_update
            price = portfolio.parse_price(price_raw)
            if price is None:
                return dash.no_update, _portfolio_feedback("El precio de compra debe ser un número mayor o igual que 0.", False), dash.no_update, dash.no_update, dash.no_update

            merged = any(str(h.get("coin_id")) == str(coin["id"]) for h in holdings)
            new_holdings = portfolio.add_holding(holdings, str(coin["id"]), str(coin.get("symbol") or ""), str(coin.get("name") or ""), amount, price)
            verb = "Actualizado" if merged else "Añadido"
            message = f"{verb} {coin.get('symbol') or coin.get('name')}: {_fmt_amount(amount)} @ {_fmt_price(price)}."
            return new_holdings, _portfolio_feedback(message, True), None, None, None
        except Exception:
            logger.exception("Error mutating Mi cartera store")
            return dash.no_update, _portfolio_feedback("No se pudo actualizar la cartera (revisa el log del dashboard).", False), dash.no_update, dash.no_update, dash.no_update

    @app.callback(
        Output(PORTFOLIO_TABLE_ID, "children"),
        Input(PORTFOLIO_STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _render_portfolio(store_data):
        """Repintar la tabla de posiciones al cambiar el store.

        Also fires when the local store hydrates from localStorage on page
        load, so persisted holdings show without any server round-trip of
        personal data. Prices come from the same CoinGecko snapshot the tab
        loads; coins without a live quote render "—" but keep their row.
        """
        try:
            holdings = portfolio.normalize_holdings(store_data)
            return _render_portfolio_content(holdings, _load_coins())
        except Exception:
            logger.exception("Error rendering Mi cartera table")
            return dbc.Alert("No se pudo renderizar la cartera (revisa el log del dashboard).", color="danger", className="small mb-0")
