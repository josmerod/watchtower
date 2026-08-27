"""Unit tests for the CoinGecko markets ETL + Markets tab (T-043)."""

from src.etl.markets import coingecko_etl
from src.web.dashboard.components import markets_tab


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


_COIN = {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "market_cap_rank": 1,
    "current_price": 79868,
    "market_cap": 1602656104942,
    "total_volume": 30509341580,
    "price_change_percentage_24h_in_currency": 2.105,
    "price_change_percentage_7d_in_currency": -1.2,
    "high_24h": 80475,
    "low_24h": 77648,
    "ath": 126080,
    "ath_change_percentage": -36.65,
}


def test_normalization(monkeypatch):
    monkeypatch.setattr(coingecko_etl.requests, "get", lambda *a, **kw: _FakeResponse([_COIN]))
    records = coingecko_etl.fetch_markets()
    r = records[0]
    assert r["rank"] == 1 and r["symbol"] == "BTC"
    assert r["change_24h_pct"] == 2.105 and r["change_7d_pct"] == -1.2
    assert r["price_usd"] == 79868


def test_skips_coin_without_id(monkeypatch):
    monkeypatch.setattr(coingecko_etl.requests, "get", lambda *a, **kw: _FakeResponse([_COIN, {"name": "ghost"}]))
    assert len(coingecko_etl.fetch_markets()) == 1


def test_fmt_usd_compact():
    assert markets_tab._fmt_usd(1602656104942) == "$1.60T"
    assert markets_tab._fmt_usd(30509341580) == "$30.51B"
    assert markets_tab._fmt_usd(79868.5, compact=False) == "$79,868.50"
    assert markets_tab._fmt_usd(None) == "—"


def test_fmt_pct_signed():
    assert markets_tab._fmt_pct(2.105) == "+2.10%"  # float repr of 2.105 rounds down
    assert markets_tab._fmt_pct(-1.2) == "-1.20%"
    assert markets_tab._fmt_pct(None) == "—"


def test_tab_renders_with_data(tmp_path, monkeypatch):
    import json

    data_dir = tmp_path / "data" / "markets"
    data_dir.mkdir(parents=True)
    (data_dir / "coingecko_latest.json").write_text(json.dumps([_COIN]), encoding="utf-8")
    monkeypatch.setattr(markets_tab, "get_project_root", lambda: str(tmp_path))
    layout = markets_tab.render_markets_tab()
    assert "Market Cap (top 50)" in str(layout)
    assert "Bitcoin" in str(layout)


def test_tab_registered_in_app():
    from src.web.dashboard.app import _TAB_RENDERERS

    assert _TAB_RENDERERS.get("tab-markets") is markets_tab.render_markets_tab
