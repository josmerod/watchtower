"""Unit tests for the 💼 Mi cartera local portfolio (Markets tab, T-086).

Pure-function coverage for src/web/dashboard/components/portfolio.py
(parsing, weighted-average merge on duplicates, position/totals math,
tolerant normalization) plus render smoke tests for the section inside
markets_tab. Personal holdings never leave the browser, so these tests only
ever touch synthetic data.
"""

import json

from src.web.dashboard.components import markets_tab, portfolio

_COIN = {
    "id": "bitcoin",
    "symbol": "BTC",
    "name": "Bitcoin",
    "rank": 1,
    "price_usd": 60000,
    "market_cap_usd": 1000000,
    "volume_24h_usd": 1000,
    "change_24h_pct": 1.0,
    "change_7d_pct": -2.0,
    "ath_change_pct": -10.0,
}


# ---------- input parsing ----------


def test_parse_amount_requires_positive_number():
    assert portfolio.parse_amount("0.5") == 0.5
    assert portfolio.parse_amount(2) == 2.0
    assert portfolio.parse_amount(0) is None
    assert portfolio.parse_amount(-1) is None
    assert portfolio.parse_amount("abc") is None
    assert portfolio.parse_amount(None) is None
    assert portfolio.parse_amount(float("nan")) is None
    assert portfolio.parse_amount(float("inf")) is None


def test_parse_price_allows_zero_but_not_negative():
    assert portfolio.parse_price("0") == 0.0
    assert portfolio.parse_price("43000.5") == 43000.5
    assert portfolio.parse_price(-0.01) is None
    assert portfolio.parse_price("abc") is None
    assert portfolio.parse_price(None) is None


# ---------- add / merge / remove ----------


def test_add_holding_new_coin_appends_record():
    holdings = portfolio.add_holding([], "bitcoin", "BTC", "Bitcoin", 0.5, 43000)
    assert holdings == [{"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 0.5, "avg_buy_price": 43000}]


def test_add_holding_merges_duplicate_equal_legs():
    holdings = [{"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 1, "avg_buy_price": 100}]
    merged = portfolio.add_holding(holdings, "bitcoin", "BTC", "Bitcoin", 1, 200)
    assert len(merged) == 1
    assert merged[0]["amount"] == 2
    assert merged[0]["avg_buy_price"] == 150  # (1*100 + 1*200) / 2


def test_add_holding_merges_duplicate_unequal_legs():
    merged = portfolio.add_holding(
        [{"coin_id": "ethereum", "symbol": "ETH", "name": "Ethereum", "amount": 2, "avg_buy_price": 100}],
        "ethereum",
        "ETH",
        "Ethereum",
        1,
        250,
    )
    assert merged[0]["amount"] == 3
    assert merged[0]["avg_buy_price"] == 150  # (2*100 + 1*250) / 3


def test_add_holding_does_not_touch_other_coins_or_mutate_input():
    original = [
        {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 1, "avg_buy_price": 100},
        {"coin_id": "ethereum", "symbol": "ETH", "name": "Ethereum", "amount": 2, "avg_buy_price": 200},
    ]
    merged = portfolio.add_holding(original, "bitcoin", "BTC", "Bitcoin", 1, 300)
    assert len(merged) == 2
    assert merged[1] == original[1]  # untouched sibling
    assert original[0]["amount"] == 1 and original[0]["avg_buy_price"] == 100  # input not mutated


def test_remove_holding_by_coin_id():
    holdings = [
        {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 1, "avg_buy_price": 100},
        {"coin_id": "ethereum", "symbol": "ETH", "name": "Ethereum", "amount": 2, "avg_buy_price": 200},
    ]
    assert portfolio.remove_holding(holdings, "bitcoin") == [holdings[1]]
    assert portfolio.remove_holding(holdings, "ghost") == holdings  # unknown id → unchanged copy
    assert len(holdings) == 2  # input not mutated


def test_normalize_holdings_tolerates_garbage():
    out = portfolio.normalize_holdings(
        [
            {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": "0.5", "avg_buy_price": "43000"},
            {"coin_id": "ethereum", "amount": -1, "avg_buy_price": 10},  # invalid amount → dropped
            {"amount": 1, "avg_buy_price": 2},  # no coin_id → dropped
            "nonsense",
            None,
            {"coin_id": "mined-coin", "amount": 3},  # no price → kept as costless
        ]
    )
    assert [h["coin_id"] for h in out] == ["bitcoin", "mined-coin"]
    assert out[0]["amount"] == 0.5 and out[0]["avg_buy_price"] == 43000.0
    assert out[1]["avg_buy_price"] == 0.0
    assert portfolio.normalize_holdings(None) == []
    assert portfolio.normalize_holdings({"not": "a list"}) == []


# ---------- valuation math ----------


def test_price_lookup_skips_missing_prices():
    prices = portfolio.price_lookup([{"id": "bitcoin", "price_usd": 60000}, {"id": "ghost", "price_usd": None}, {"name": "no-id", "price_usd": 1}])
    assert prices == {"bitcoin": 60000.0}


def test_compute_position_known_price():
    position = portfolio.compute_position({"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 2, "avg_buy_price": 40000}, 60000.0)
    assert position["known"] is True
    assert position["value_usd"] == 120000
    assert position["cost_usd"] == 80000
    assert position["pl_usd"] == 40000
    assert position["pl_pct"] == 50.0


def test_compute_position_unknown_price_keeps_cost():
    position = portfolio.compute_position({"coin_id": "ghost", "symbol": "GHOST", "name": "Ghost", "amount": 1, "avg_buy_price": 10}, None)
    assert position["known"] is False
    assert position["value_usd"] is None
    assert position["pl_usd"] is None and position["pl_pct"] is None
    assert position["cost_usd"] == 10


def test_compute_position_zero_cost_has_no_pct():
    position = portfolio.compute_position({"coin_id": "mined", "symbol": "MND", "name": "Mined", "amount": 1, "avg_buy_price": 0}, 25.0)
    assert position["pl_usd"] == 25.0
    assert position["pl_pct"] is None  # free coins: percentage undefined


def test_compute_totals_excludes_unknown_prices():
    holdings = [
        {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 1, "avg_buy_price": 100},
        {"coin_id": "ghost", "symbol": "GHOST", "name": "Ghost", "amount": 1, "avg_buy_price": 50},
    ]
    totals = portfolio.compute_totals(holdings, {"bitcoin": 200.0})
    assert totals["positions"] == 2
    assert totals["missing_prices"] == 1
    assert totals["value_usd"] == 200
    assert totals["cost_usd"] == 100  # ghost's cost excluded so the pct stays honest
    assert totals["pl_usd"] == 100
    assert totals["pl_pct"] == 100


def test_compute_totals_empty():
    totals = portfolio.compute_totals([], {})
    assert totals["positions"] == 0
    assert totals["value_usd"] == 0
    assert totals["pl_pct"] is None
    assert totals["missing_prices"] == 0


# ---------- formatting helpers ----------


def test_fmt_amount_trims_zeros():
    assert markets_tab._fmt_amount(0.5) == "0.5"
    assert markets_tab._fmt_amount(2) == "2"
    assert markets_tab._fmt_amount(1234567.25) == "1,234,567.25"
    assert markets_tab._fmt_amount(None) == "—"


def test_fmt_price_sub_cent_precision():
    assert markets_tab._fmt_price(0.000021) == "$0.000021"
    assert markets_tab._fmt_price(43000.5) == "$43,000.50"
    assert markets_tab._fmt_price(None) == "—"


def test_fmt_signed_usd():
    assert markets_tab._fmt_signed_usd(1234.5) == "+$1,234.50"
    assert markets_tab._fmt_signed_usd(-67.89) == "-$67.89"
    assert markets_tab._fmt_signed_usd(None) == "—"


# ---------- render smoke ----------


def test_portfolio_section_renders_with_data(tmp_path, monkeypatch):
    data_dir = tmp_path / "data" / "markets"
    data_dir.mkdir(parents=True)
    (data_dir / "coingecko_latest.json").write_text(json.dumps([_COIN]), encoding="utf-8")
    monkeypatch.setattr(markets_tab, "get_project_root", lambda: str(tmp_path))
    layout = markets_tab.render_markets_tab()
    rendered = str(layout)
    assert "Mi cartera" in rendered
    assert "markets-portfolio-store" in rendered
    assert "markets-portfolio-coin" in rendered
    assert "markets-portfolio-add" in rendered
    assert "Bitcoin" in rendered  # dropdown option fed from the snapshot
    # existing table wiring intact
    assert "Market Cap (top 50)" in rendered


def test_portfolio_section_renders_empty_state_without_data(tmp_path, monkeypatch):
    monkeypatch.setattr(markets_tab, "get_project_root", lambda: str(tmp_path))
    layout = markets_tab.render_markets_tab()
    rendered = str(layout)
    # section present even with no coins loaded, showing the friendly hint
    assert "Mi cartera" in rendered
    assert "markets-portfolio-store" in rendered
    assert "Tu cartera está vacía" in rendered


def test_portfolio_content_renders_holdings_and_totals():
    holdings = [{"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "amount": 1, "avg_buy_price": 40000}]
    content = markets_tab._render_portfolio_content(holdings, [_COIN])
    rendered = str(content)
    assert "Bitcoin" in rendered
    assert "Precio actual" in rendered
    assert "Total (1 posición)" in rendered
    assert "$60,000" in rendered  # live price cell
    assert "+50.00%" in rendered  # P/L (60000 vs 40000)


def test_portfolio_content_unknown_coin_shows_dash_but_keeps_row():
    holdings = [{"coin_id": "ghost", "symbol": "GHOST", "name": "Ghost", "amount": 1, "avg_buy_price": 10}]
    rendered = str(markets_tab._render_portfolio_content(holdings, [_COIN]))
    assert "Ghost" in rendered  # row kept
    assert "sin precio en vivo" in rendered  # muted note
