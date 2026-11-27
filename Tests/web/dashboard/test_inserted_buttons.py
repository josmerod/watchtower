"""Buttons a callback has just inserted change nothing, and a real click still acts (T-162, T-086).

Dash runs a pattern-matching callback again, prevent_initial_call=True or not, when another callback inserts its
buttons: the request lists each one in ``changedPropIds`` with ``n_clicks=None``. Each callback here is called the
way the browser calls it, POST /_dash-update-component on a Dash app through Flask's test client, so what
``dash.ctx`` holds is Dash's own and not a mock. That is how the portfolio bug showed: its guard read a key Dash
never writes, and Add and Delete answered "nothing to change" to every click from 2026-09-10 on.
Fixtures only: nothing under data/ is read or written.
"""

import json

import dash
import dash_bootstrap_components as dbc
import pytest
from dash import html

from src.web.dashboard.components import arxiv_research_tab, digest_tab, markets_tab, news_tab, shortcuts_tab

BITCOIN = {"coin_id": "bitcoin", "type": markets_tab.PORTFOLIO_DELETE_BTN_TYPE}
ADD = markets_tab.PORTFOLIO_ADD_BTN_ID
HOLDING = {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 1.0, "avg_buy_price": 100.0}
EXPANDER = {"index": "h1", "type": arxiv_research_tab.ARXIV_EXPAND_BTN_TYPE}
DETAIL = {"index": "h1", "type": arxiv_research_tab.ARXIV_DETAIL_COLLAPSE_TYPE}
REFRESH = {"tab": "daily", "type": "digest-refresh"}
EXPORT = {"keys": "techcrunch", "type": "news-export"}
TOP_TECH = news_tab.TOP_TECH_COMPONENT_ID
OPEN = {"action": "add", "category": "AI", "index": -1, "type": "shortcut-open"}


def sid(ident) -> str:
    """A pattern id as the renderer stringifies it: JSON, keys sorted, no spaces."""
    return ident if isinstance(ident, str) else json.dumps(ident, sort_keys=True, separators=(",", ":"))


def entry(ident, prop, value) -> dict:
    return {"id": sid(ident), "property": prop, "value": value}


def find(app, marker) -> dict:
    """The callback whose output spec contains ``marker``, as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if marker in cb["output"])


def call(app, cb, inputs, changed, states=None, output_id=None) -> dict:
    """POST the callback as the browser would and return only the outputs it changed.

    ``inputs`` has one slot per Input of the callback: a component's value where the id is literal or MATCH, the
    list of every matching component where it is ALL (same for ``states``). ``changed`` are the ``id.prop`` keys
    the renderer reports. ``output_id`` is the concrete id when the output is pattern-matching.
    """
    if cb["output"].startswith(".."):
        outputs = [dict(zip(("id", "property"), part.rsplit(".", 1))) for part in cb["output"][2:-2].split("...")]
    else:
        ident = output_id if output_id is not None else cb["output"].rsplit(".", 1)[0]
        outputs = {"id": ident, "property": cb["output"].rsplit(".", 1)[1]}
    body = {
        "output": cb["output"],
        "outputs": outputs,
        "inputs": inputs,
        "changedPropIds": [key for key in changed],
        "state": states if states is not None else [{**spec, "value": None} for spec in cb["state"]],
    }
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code in (200, 204), response.get_data(as_text=True)[-800:]  # 204: a callback that prevented the update
    if response.status_code == 204:
        return {}
    return {name: value for name, value in response.get_json()["response"].items() if value is not None}


def _app(*register) -> dash.Dash:
    app = dash.Dash("test-inserted-buttons", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = html.Div(id="root")
    for register_callbacks in register:
        register_callbacks(app)
    return app


def _top_tech_inputs(search="", per_page=50, show_duplicates=False, clicks=(None, None)) -> list:
    pager = {"type": f"{TOP_TECH}-page-btn"}
    return [
        entry(news_tab.TOP_TECH_SEARCH_ID, "value", search),
        entry(f"{TOP_TECH}-items-per-page", "value", per_page),
        entry(f"{TOP_TECH}-show-duplicates", "value", show_duplicates),
        [entry({"dir": "prev", **pager}, "n_clicks", clicks[0]), entry({"dir": "next", **pager}, "n_clicks", clicks[1])],
    ]


def _shortcut_inputs(search="", **clicks) -> list:
    return [
        entry("search-shortcuts-input", "value", search),
        [entry(OPEN, "n_clicks", clicks.get("open"))],
        entry("shortcut-modal-close", "n_clicks", clicks.get("close")),
        entry("shortcut-save-btn", "n_clicks", clicks.get("save")),
        entry("shortcut-delete-btn", "n_clicks", clicks.get("delete")),
    ]


INSERTED = [
    pytest.param(arxiv_research_tab.register_arxiv_callbacks, "arxiv-detail-collapse", [entry(EXPANDER, "n_clicks", None)], [f"{sid(EXPANDER)}.n_clicks"], DETAIL, id="arxiv-expander"),
    pytest.param(digest_tab.register_digest_callbacks, "digest-content.children", [[entry(REFRESH, "n_clicks", None)]], [f"{sid(REFRESH)}.n_clicks"], None, id="digest-refresh"),
    pytest.param(news_tab.register_news_search_callbacks, "news-export-download.data", [[entry(EXPORT, "n_clicks", None)]], [f"{sid(EXPORT)}.n_clicks"], None, id="news-export"),
    pytest.param(
        news_tab.register_news_search_callbacks,
        f"{news_tab.TOP_TECH_SEARCH_ID}-results.children",
        _top_tech_inputs(),
        [f"{sid({'dir': 'prev', 'type': f'{TOP_TECH}-page-btn'})}.n_clicks", f"{sid({'dir': 'next', 'type': f'{TOP_TECH}-page-btn'})}.n_clicks"],
        None,
        id="news-toptech-pager",
    ),
    pytest.param(
        shortcuts_tab.register_shortcuts_callbacks,
        "shortcuts-cards-container.children",
        _shortcut_inputs(),
        [f"{sid(OPEN)}.n_clicks"],
        None,
        id="shortcuts-open",
    ),
]


@pytest.mark.parametrize(("register", "marker", "inputs", "changed", "output_id"), INSERTED)
def test_buttons_just_inserted_change_nothing(register, marker, inputs, changed, output_id) -> None:
    assert call(_app(register), find(_app(register), marker), inputs, changed, output_id=output_id) == {}


def test_a_click_on_the_expander_opens_the_detail() -> None:
    app = _app(arxiv_research_tab.register_arxiv_callbacks)

    opened = call(app, find(app, "arxiv-detail-collapse"), [entry(EXPANDER, "n_clicks", 1)], [f"{sid(EXPANDER)}.n_clicks"], output_id=DETAIL)
    closed = call(app, find(app, "arxiv-detail-collapse"), [entry(EXPANDER, "n_clicks", 2)], [f"{sid(EXPANDER)}.n_clicks"], output_id=DETAIL)

    assert opened == {sid(DETAIL): {"is_open": True}}
    assert closed == {sid(DETAIL): {"is_open": False}}


def test_a_refresh_click_renders_the_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(digest_tab, "_load_digest", lambda: {})
    app = _app(digest_tab.register_digest_callbacks)

    changed = call(app, find(app, "digest-content.children"), [[entry(REFRESH, "n_clicks", 1)]], [f"{sid(REFRESH)}.n_clicks"])

    assert "Aún no hay digest" in json.dumps(changed["digest-content"], ensure_ascii=False)


def test_a_search_still_moves_the_top_tech_view(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(news_tab, "get_all_news_data", lambda: {})
    app = _app(news_tab.register_news_search_callbacks)

    changed = call(app, find(app, f"{news_tab.TOP_TECH_SEARCH_ID}-results.children"), _top_tech_inputs(search="model"), [f"{news_tab.TOP_TECH_SEARCH_ID}.value"])

    assert "No data available" in json.dumps(changed, ensure_ascii=False)
    assert changed[f"{TOP_TECH}-page"] == {"data": 1}


def test_a_search_still_filters_the_shortcuts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shortcuts_tab, "get_shortcuts_data", lambda: {"AI": [{"name": "Hugging Face", "url": "https://example.invalid/hf"}]})
    monkeypatch.setattr(shortcuts_tab, "_load_custom_raw", lambda: {})
    app = _app(shortcuts_tab.register_shortcuts_callbacks)

    changed = call(app, find(app, "shortcuts-cards-container.children"), _shortcut_inputs(search="hugging"), ["search-shortcuts-input.value"])

    assert "Hugging Face" in json.dumps(changed["shortcuts-cards-container"], ensure_ascii=False)
    assert "shortcut-modal" not in changed


# --- Mi cartera: the click is in ctx.triggered, which carries prop_id and value only ---
@pytest.fixture
def portfolio(monkeypatch: pytest.MonkeyPatch) -> dash.Dash:
    app = _app(markets_tab.register_markets_callbacks)
    monkeypatch.setattr(markets_tab, "_load_coins", lambda: [{"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"}])
    return app


def _portfolio_call(app, *, clicked, add=None, delete=None, coin=None, amount=None, price=None, store=None) -> dict:
    inputs = [entry(ADD, "n_clicks", add), [entry(BITCOIN, "n_clicks", delete)]]
    states = [entry("markets-portfolio-coin", "value", coin), entry("markets-portfolio-amount", "value", amount), entry("markets-portfolio-price", "value", price), entry("markets-portfolio-store", "data", store)]
    return call(app, find(app, "markets-portfolio-store.data"), inputs, [f"{sid(clicked)}.n_clicks"], states)


def test_a_delete_button_the_table_just_rendered_changes_nothing(portfolio) -> None:
    assert _portfolio_call(portfolio, clicked=BITCOIN, delete=None, store=[HOLDING]) == {}


def test_a_delete_click_removes_the_position(portfolio) -> None:
    changed = _portfolio_call(portfolio, clicked=BITCOIN, delete=1, store=[HOLDING])

    assert changed["markets-portfolio-store"] == {"data": []}
    assert "eliminada" in json.dumps(changed["markets-portfolio-feedback"], ensure_ascii=False)


def test_an_add_click_records_the_buy(portfolio) -> None:
    changed = _portfolio_call(portfolio, clicked=ADD, add=1, coin="bitcoin", amount="0.5", price="20000", store=[])

    assert changed["markets-portfolio-store"] == {"data": [{"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 0.5, "avg_buy_price": 20000.0}]}
    assert "Añadido BTC" in json.dumps(changed["markets-portfolio-feedback"], ensure_ascii=False)


def test_an_add_click_without_a_coin_says_so(portfolio, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(markets_tab, "_load_coins", lambda: [])

    changed = _portfolio_call(portfolio, clicked=ADD, add=1, coin=None, amount="1", price="1", store=[])

    assert "markets-portfolio-store" not in changed
    assert "Selecciona una moneda" in json.dumps(changed["markets-portfolio-feedback"], ensure_ascii=False)
