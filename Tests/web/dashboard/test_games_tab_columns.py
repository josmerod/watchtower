"""The Games tables read the columns the ETLs write (T-155).

deals.json carries price, discount and published, and bundles.json / humblebundles.json carry the list games and
end_date. The loaders looked for other names, so the tables showed N/A and "$0.00" all over and sorted on nothing.
Fixtures only: the loaders read files written under tmp_path, never data/.
"""

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from src.web.dashboard.components import games_tab

DEALS = [
    {"title": "Cheap at 93 percent", "link": "https://example.invalid/1", "store": "Fanatical", "price": "0.47", "discount": "-93%", "published": "2026-07-22T00:06:05.000Z"},
    {"title": "Free of a discount", "link": "https://example.invalid/2", "store": "Steam", "price": "19.99", "discount": None, "published": "2026-07-21T23:30:00.000Z"},
    {"title": "Everything off", "link": "https://example.invalid/3", "store": "GOG", "price": "0", "discount": "-100%", "published": "2026-07-20T10:00:00.000Z"},
    {"title": "Undated", "link": "https://example.invalid/4", "store": "GOG", "price": "5", "discount": "-50%", "published": None},
]
BUNDLES = [
    {"title": "Bundle of two", "link": "https://example.invalid/b1", "price": "10.0", "published": "2026-07-22T10:00:00.000Z", "games": ["Alpha", "Beta"]},
    {"title": "Old bundle", "link": "https://example.invalid/b2", "price": "5.0", "published": "2026-06-01T10:00:00.000Z", "games": []},
]
HUMBLE = [
    {"title": "Humble choice", "link": "https://example.invalid/h1", "price": "Pay what you want", "end_date": "2026-12-11T14:05:39.862597+00:00", "games": ["A", "B", "C"], "type": "bundle"},
    {"title": "Humble ended", "link": "https://example.invalid/h2", "price": "Pay what you want", "end_date": "2026-07-01T17:00:00+00:00", "games": ["A", "B"], "type": "bundle"},
]
KEYS = ["deals", "bundles", "new_releases", "metacritic", "trending"]


@pytest.fixture
def fresh_games_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """The module keeps what it loaded in two dicts; each test starts without any."""
    monkeypatch.setattr(games_tab, "ALL_GAMES_DATA", {key: pd.DataFrame() for key in KEYS})
    monkeypatch.setattr(games_tab, "DATA_LOADED_SUCCESSFULLY", dict.fromkeys(KEYS, False))


def _texts(node) -> list[str]:
    """Every string and number a Dash component tree shows, in document order."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, (int, float)):
        return [str(node)]
    if isinstance(node, (list, tuple)):
        return [text for child in node for text in _texts(child)]
    children = getattr(node, "children", None)
    return _texts(children) if children is not None else []


def _bundle_files(monkeypatch: pytest.MonkeyPatch, tmp_path, names: list[str]) -> None:
    for name, rows in (("bundles.json", BUNDLES), ("humblebundles.json", HUMBLE)):
        if name in names:
            (tmp_path / name).write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(games_tab, "get_data_path", lambda domain, name: str(tmp_path / name))


def test_deals_show_the_price_the_discount_and_the_published_day(monkeypatch: pytest.MonkeyPatch, fresh_games_data) -> None:
    monkeypatch.setattr(games_tab, "deals_repo", SimpleNamespace(get=lambda: {"results": DEALS}))

    games_tab.load_deals_data()

    frame = games_tab.ALL_GAMES_DATA["deals"]
    assert frame["title"].tolist() == ["Cheap at 93 percent", "Free of a discount", "Everything off", "Undated"]  # newest first
    assert frame["price_new_numeric"].tolist() == [0.47, 19.99, 0.0, 5.0]
    assert frame["price_old_numeric"].isna().tolist() == [False, True, True, False]  # told by price and discount
    assert frame["price_old_numeric"].dropna().round(2).tolist() == [6.71, 10.0]


def test_the_deals_table_has_no_dollar_zero_where_it_knows_nothing(fresh_games_data) -> None:
    games_tab.DATA_LOADED_SUCCESSFULLY["deals"] = True
    games_tab.ALL_GAMES_DATA["deals"] = pd.DataFrame(
        {"title": ["With a discount", "Without one", "Undated"], "link": "https://example.invalid/", "store": "Steam", "price_new_numeric": [2.0, 2.0, 2.0], "price_old_numeric": [10.0, float("nan"), 10.0], "discount_numeric": [80.0, float("nan"), 50.0], "published_date": [pd.Timestamp("2026-07-21T23:30:00Z"), pd.Timestamp("2026-07-01T10:00:00Z"), pd.NaT]}
    )

    cells = _texts(games_tab.render_deals_sub_tab(games_tab.ALL_GAMES_DATA["deals"]))

    assert cells[:6] == ["Title", "Store", "New Price", "Old Price", "Discount", "Published"]
    assert cells[6:12] == ["With a discount", "Steam", "$2.00", "$10.00", "80%", "2026-07-22"]  # 23:30 UTC is already the next day in Spain
    assert cells[12:18] == ["Without one", "Steam", "$2.00", "N/A", "N/A", "2026-07-01"]
    assert cells[18:24] == ["Undated", "Steam", "$2.00", "$10.00", "50%", "N/A"]


def test_bundles_count_their_games_and_share_one_timeline(monkeypatch: pytest.MonkeyPatch, fresh_games_data, tmp_path) -> None:
    _bundle_files(monkeypatch, tmp_path, ["bundles.json", "humblebundles.json"])

    games_tab.load_bundles_data()

    frame = games_tab.ALL_GAMES_DATA["bundles"]
    assert frame["title"].tolist() == ["Humble choice", "Bundle of two", "Humble ended", "Old bundle"]  # newest end, else newest publication
    assert frame["game_count_numeric"].tolist() == [3, 2, 2, 0]
    assert frame["store"].tolist() == ["Humble Bundle", "Various/Mixed", "Humble Bundle", "Various/Mixed"]

    cells = _texts(games_tab.render_bundles_sub_tab(frame))
    assert cells[:5] == ["Title", "Store", "Price", "Games Count", "Expiry Date"]
    assert cells[5:10] == ["Humble choice", "Humble Bundle", "Pay what you want", "3", "2026-12-11"]
    assert cells[10:15] == ["Bundle of two", "Various/Mixed", "$10.00", "2", "N/A"]  # the source gives no end date


def test_one_bundle_file_is_enough(monkeypatch: pytest.MonkeyPatch, fresh_games_data, tmp_path) -> None:
    _bundle_files(monkeypatch, tmp_path, ["humblebundles.json"])

    games_tab.load_bundles_data()

    assert games_tab.ALL_GAMES_DATA["bundles"]["title"].tolist() == ["Humble choice", "Humble ended"]
    assert games_tab.DATA_LOADED_SUCCESSFULLY["bundles"] is True


def test_without_bundle_files_the_tab_says_so(monkeypatch: pytest.MonkeyPatch, fresh_games_data, tmp_path) -> None:
    _bundle_files(monkeypatch, tmp_path, [])

    games_tab.load_bundles_data()

    assert games_tab.DATA_LOADED_SUCCESSFULLY["bundles"] is False
    assert "No game bundles data" in " ".join(_texts(games_tab.render_bundles_sub_tab(games_tab.ALL_GAMES_DATA["bundles"])))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (pd.Timestamp("2026-11-26T23:30:00Z"), "2026-11-27"),
        (pd.Timestamp("2026-07-26T23:30:00Z"), "2026-07-27"),  # summer time is two hours ahead
        (pd.Timestamp("2026-11-26T12:00:00"), "2026-11-26"),  # no zone: shown as it comes
        (pd.NaT, "N/A"),
        (None, "N/A"),
    ],
)
def test_the_day_shown_is_the_one_in_spain(value, expected) -> None:
    assert games_tab.format_display_date(value) == expected
