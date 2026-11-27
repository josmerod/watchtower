"""Mi cartera answers a click, and not the buttons its own table just rendered (T-086, T-162).

The callback is called the way the browser calls it, POST /_dash-update-component on a Dash app through Flask's
test client, so what ``dash.ctx`` holds is Dash's own and not a mock. That is how the bug showed: the guard read
a key Dash never writes (entries carry ``prop_id`` and ``value`` only), and Add and Delete answered "nothing to
change" to every click from 2026-09-10 on. Fixtures only: nothing under data/ is read or written.
"""

import json

import dash
import dash_bootstrap_components as dbc
import pytest
from dash import html

from src.web.dashboard.components import markets_tab

BITCOIN = {"coin_id": "bitcoin", "type": markets_tab.PORTFOLIO_DELETE_BTN_TYPE}
ADD = markets_tab.PORTFOLIO_ADD_BTN_ID
HOLDING = {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 1.0, "avg_buy_price": 100.0}


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
