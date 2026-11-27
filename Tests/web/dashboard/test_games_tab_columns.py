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
KEYS = ["deals", "giveaways", "bundles", "new_releases", "metacritic", "trending"]
NOW = pd.Timestamp("2026-11-27 19:00", tz="UTC")


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


def _table(node):
    """The table inside what a subtab renders: a source that went quiet puts a note first."""
    return node[-1] if isinstance(node, list) else node


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
    assert frame["currency"].tolist() == ["EUR"] * 4  # the ES/EUR feed; the file predates the ETL writing the currency


def test_the_deals_table_has_no_dollar_zero_where_it_knows_nothing(fresh_games_data) -> None:
    games_tab.DATA_LOADED_SUCCESSFULLY["deals"] = True
    games_tab.ALL_GAMES_DATA["deals"] = pd.DataFrame(
        {
            "title": ["With a discount", "Without one", "Undated"],
            "link": "https://example.invalid/",
            "store": "Steam",
            "price_new_numeric": [2.0, 2.0, 2.0],
            "price_old_numeric": [10.0, float("nan"), 10.0],
            "discount_numeric": [80.0, float("nan"), 50.0],
            "published_date": [pd.Timestamp("2026-07-21T23:30:00Z"), pd.Timestamp("2026-07-01T10:00:00Z"), pd.NaT],
        }
    )

    cells = _texts(_table(games_tab.render_deals_sub_tab(games_tab.ALL_GAMES_DATA["deals"], now=NOW)))

    assert cells[:6] == ["Title", "Store", "New Price", "Old Price", "Discount", "Published"]
    assert cells[6:12] == ["With a discount", "Steam", "€2.00", "€10.00", "80%", "2026-07-22"]  # 23:30 UTC is already the next day in Spain
    assert cells[12:18] == ["Without one", "Steam", "€2.00", "N/A", "N/A", "2026-07-01"]
    assert cells[18:24] == ["Undated", "Steam", "€2.00", "€10.00", "50%", "N/A"]


def test_bundles_count_their_games_and_share_one_timeline(monkeypatch: pytest.MonkeyPatch, fresh_games_data, tmp_path) -> None:
    _bundle_files(monkeypatch, tmp_path, ["bundles.json", "humblebundles.json"])

    games_tab.load_bundles_data()

    frame = games_tab.ALL_GAMES_DATA["bundles"]
    assert frame["title"].tolist() == ["Humble choice", "Bundle of two", "Humble ended", "Old bundle"]  # newest end, else newest publication
    assert frame["game_count_numeric"].tolist() == [3, 2, 2, 0]
    assert frame["store"].tolist() == ["Humble Bundle", "Various/Mixed", "Humble Bundle", "Various/Mixed"]

    cells = _texts(_table(games_tab.render_bundles_sub_tab(frame, now=NOW)))
    assert cells[:5] == ["Title", "Store", "Price", "Games Count", "Expiry Date"]
    assert cells[5:10] == ["Humble choice", "Humble Bundle", "Pay what you want", "3", "2026-12-11"]
    assert cells[10:15] == ["Bundle of two", "Various/Mixed", "€10.00", "2", "N/A"]  # the source gives no end date


def test_prices_wear_the_currency_of_their_source(monkeypatch: pytest.MonkeyPatch, fresh_games_data, tmp_path) -> None:
    """The feeds are the ES/EUR ones ("10,80 €"): the dollar sign the tables wore was a guess."""
    rows = [
        {"title": "Priced in dollars", "link": "https://example.invalid/d", "price": "$5.99", "end_date": "2026-12-08T05:00:00.000Z", "games": ["A"], "type": "games"},
        {"title": "Euro bundle", "link": "https://example.invalid/e", "price": 10.0, "published": "2026-11-27T10:00:00Z", "games": ["A"], "currency": "EUR"},
    ]
    (tmp_path / "bundles.json").write_text(json.dumps(rows[1:]), encoding="utf-8")
    (tmp_path / "humblebundles.json").write_text(json.dumps(rows[:1]), encoding="utf-8")
    monkeypatch.setattr(games_tab, "get_data_path", lambda domain, name: str(tmp_path / name))

    games_tab.load_bundles_data()

    frame = games_tab.ALL_GAMES_DATA["bundles"].set_index("title")
    priced = _texts(games_tab.render_bundles_sub_tab(frame.loc[["Priced in dollars"]].reset_index(), now=NOW))
    euro = _texts(games_tab.render_bundles_sub_tab(frame.loc[["Euro bundle"]].reset_index(), now=NOW))
    assert priced[5:10] == ["Priced in dollars", "Humble Bundle", "$5.99", "1", "2026-12-08"]  # the date the page states
    assert euro[5:10] == ["Euro bundle", "Various/Mixed", "€10.00", "1", "N/A"]


def test_humble_rows_show_their_own_count_and_no_invented_date(monkeypatch: pytest.MonkeyPatch, fresh_games_data, tmp_path) -> None:
    """Humble lists its first eleven items and states the count; a date the page did not give stays empty."""
    rows = [
        {"title": "Twenty-two items", "link": "https://example.invalid/a", "price": "Pay what you want", "end_date": None, "items_count": 22, "games": [f"Game {i}" for i in range(11)], "type": "games"},
        {"title": "Counted by the list", "link": "https://example.invalid/b", "price": "Pay what you want", "end_date": "2026-12-03T05:00:00.000Z", "items_count": None, "games": ["A", "B"], "type": "books"},
    ]
    (tmp_path / "humblebundles.json").write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(games_tab, "get_data_path", lambda domain, name: str(tmp_path / name))

    games_tab.load_bundles_data()

    frame = games_tab.ALL_GAMES_DATA["bundles"].set_index("title")
    cells = {title: _texts(games_tab.render_bundles_sub_tab(frame.loc[[title]].reset_index(), now=NOW))[5:10] for title in frame.index}
    assert cells["Twenty-two items"] == ["Twenty-two items", "Humble Bundle", "Pay what you want", "22", "N/A"]
    assert cells["Counted by the list"] == ["Counted by the list", "Humble Bundle", "Pay what you want", "2", "2026-12-03"]


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


def test_a_hundred_bundles_fit_in_the_table(fresh_games_data) -> None:
    """Fifty rows hid the IsThereAnyDeal bundles behind Humble's 58 dated ones."""
    games_tab.DATA_LOADED_SUCCESSFULLY["bundles"] = True
    frame = pd.DataFrame({"title": [f"Bundle {i}" for i in range(96)], "store": "Humble Bundle", "game_count_numeric": 1, "expiry_date": pd.NaT, "published_date": NOW})

    rows = _texts(_table(games_tab.render_bundles_sub_tab(frame, now=NOW)))

    assert "Bundle 95" in rows
    assert len([text for text in rows if text.startswith("Bundle ")]) == 96


# --- Giveaways: the ETL keeps the live ones in giveaways.json and nothing read them ---


GIVEAWAYS = [
    {"title": "Dead Age 2 on GOG", "link": "https://example.invalid/g2", "published": "2026-11-27T16:39:24.000Z", "expires": "2026-11-30T14:00:23Z"},
    {"title": "Vertical Drop Heroes HD on Fanatical", "link": "https://example.invalid/g1", "published": "2026-11-27T16:45:12.000Z", "expires": "2026-11-28T23:59:00Z"},
]


def test_giveaways_list_the_soonest_to_end_first(monkeypatch: pytest.MonkeyPatch, fresh_games_data) -> None:
    monkeypatch.setattr(games_tab, "giveaways_repo", SimpleNamespace(get=lambda: {"results": GIVEAWAYS}))

    games_tab.load_giveaways_data()

    assert _texts(games_tab.render_giveaways_sub_tab(games_tab.ALL_GAMES_DATA["giveaways"])) == [
        "Game",
        "Expires",
        "Vertical Drop Heroes HD on Fanatical",
        "2026-11-29",  # 23:59 UTC is already the next day in Spain
        "Dead Age 2 on GOG",
        "2026-11-30",
    ]


def test_no_giveaway_is_a_quiet_state_not_an_error(monkeypatch: pytest.MonkeyPatch, fresh_games_data) -> None:
    monkeypatch.setattr(games_tab, "giveaways_repo", SimpleNamespace(get=lambda: {"results": []}))

    games_tab.load_giveaways_data()

    assert games_tab.DATA_LOADED_SUCCESSFULLY["giveaways"] is True
    assert "No free game to claim right now." in _texts(games_tab.render_giveaways_sub_tab(games_tab.ALL_GAMES_DATA["giveaways"]))


# --- A source that went quiet says so (the July deals shown as current for four months) ---


def _one_deal(published) -> pd.DataFrame:
    games_tab.DATA_LOADED_SUCCESSFULLY["deals"] = True
    return pd.DataFrame({"title": ["A deal"], "published_date": [published], "discount_numeric": [float("nan")]})


def test_a_source_that_went_quiet_is_said_above_the_table(fresh_games_data) -> None:
    rendered = games_tab.render_deals_sub_tab(_one_deal(pd.Timestamp("2026-07-22T04:16:43Z")), now=NOW)

    assert isinstance(rendered, list) and len(rendered) == 2
    assert "Newest deal is from 2026-07-22 (128 days ago): the source has gone quiet." in _texts(rendered[0])[0]
    assert _texts(rendered[1])[:6] == ["Title", "Store", "New Price", "Old Price", "Discount", "Published"]


def test_a_live_source_gets_no_note(fresh_games_data) -> None:
    rendered = games_tab.render_deals_sub_tab(_one_deal(NOW - pd.Timedelta(days=1, hours=23)), now=NOW)

    assert not isinstance(rendered, list)


def test_nothing_is_said_without_a_dated_item(fresh_games_data) -> None:
    assert not isinstance(games_tab.render_deals_sub_tab(_one_deal(pd.NaT), now=NOW), list)


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
