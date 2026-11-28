"""The Games tab's three price trackers (T-139 and T-140): lazy subtabs with a minimum-discount filter.

``Nintendo eShop JP``, ``Key Shops`` and ``Gift Cards`` are shells until they are opened: nothing of their files is
read when the tab renders, and their controllers run for the request that opens a subtab or changes one of its
filters. The callbacks are called the way the browser calls them, POST /_dash-update-component through Flask's
test client, so ``dash.ctx`` is Dash's own. Every table shows the base price beside the sale price and a discount
the ETL computed from the two.

The records are the ones the ETLs build from the real pages saved under Tests/etl/fixtures, so the tab reads the
shape the ETLs write. Fixtures only: every file lives under tmp_path, never data/.
"""

import json
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
import pytest

from src.etl.games import games_get_eshop_jp as eshop
from src.etl.games import games_get_gift_cards as gift_cards
from src.etl.games import games_get_key_shops as key_shops
from src.etl.games import games_tracker_common as trackers
from src.web.dashboard.components import games_tab

FIXTURES = Path(__file__).parents[2] / "etl" / "fixtures"
NOW = "2026-11-28T06:00:00+00:00"
BAR = "games-sub-tabs"
EXISTING_TABS = ["subtab-deals", "subtab-giveaways", "subtab-bundles", "subtab-trending", "subtab-metacritic"]
TRACKER_TABS = {"eshop_jp": "subtab-eshop-jp", "key_shops": "subtab-key-shops", "gift_cards": "subtab-gift-cards"}
OVERCOOKED = "Overcooked!® - オーバークック 王国のフルコース"
BOMBERMAN = "スーパーボンバーマン コレクション Nintendo Switch 2 Edition"
SYBERIA_URL = "https://www.instant-gaming.com/es/1245-comprar-syberia-2-pc-mac-juego-steam/"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- The records, as the three ETLs build them from the saved pages ---
def _eshop_records() -> list[dict]:
    tiles = eshop.parse_listing_page(_fixture("eshop_jp_sale_listing.html"))
    prices = eshop.parse_prices(json.loads(_fixture("eshop_jp_price_api.json")))
    return trackers.stamp_records(eshop.build_records(tiles, prices), "nsuid", [], NOW)


def _key_shop_records() -> list[dict]:
    pages = {
        "instant_gaming_daily_deal_product.html": "comprar-syberia-2",
        "instant_gaming_daily_deal_product_little_nightmares.html": "comprar-little-nightmares-iii",
        "instant_gaming_daily_deal_product_fc_points.html": "comprar-ea-sports-fc-24",
    }
    records = []
    for tile in trackers.parse_ig_tiles(_fixture("instant_gaming_daily_deals.html")):
        page = next(name for name, marker in pages.items() if marker in tile["url"])
        record = key_shops.build_record(tile, trackers.parse_ig_product(_fixture(page)))
        assert record is not None
        records.append(record)
    return trackers.stamp_records(records, "deal_id", [], NOW)


def _gift_card_records() -> list[dict]:
    records = []
    for page in ("eneba_gift_cards_page.html", "eneba_gift_cards_last_page.html"):
        page_cards, _next = gift_cards.parse_eneba_page(_fixture(page))
        records.extend(page_cards)
    for tile in trackers.parse_ig_tiles(_fixture("instant_gaming_gift_cards_shelf.html")):
        face_value = gift_cards.face_value_eur(tile["title"])
        if face_value is None or tile.get("price") is None:
            continue
        product = trackers.parse_ig_product(_fixture("instant_gaming_card_product_15.html" if "-15eur-" in tile["url"] else "instant_gaming_card_product.html"))
        card = gift_cards.build_ig_card(tile, product, face_value, "Nintendo eShop")
        assert card is not None
        records.append(card)
    return trackers.stamp_records(records, "card_id", [], NOW)


RECORDS = {"eshop_jp": _eshop_records, "key_shops": _key_shop_records, "gift_cards": _gift_card_records}


# --- Component trees, before and after serialization ---
def _walk(node):
    """Yield every node of a Dash component tree, strings included."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)


def _by_id(root, component_id: str) -> list:
    return [node for node in _walk(root) if getattr(node, "id", None) == component_id]


def _ids(root) -> set[str]:
    return {node.id for node in _walk(root) if isinstance(getattr(node, "id", None), str)}


def _shown(node) -> list[str]:
    """Every string a component tree shows, in document order, from the tree or from its JSON."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return _shown(node.get("props", {}).get("children"))
    if isinstance(node, (list, tuple)):
        return [text for child in node for text in _shown(child)]
    if node is None or not hasattr(node, "children"):
        return []
    return _shown(node.children)


def _of_type(node, kind: str) -> list[dict]:
    """Every serialized component of one Dash type below ``node``."""
    if isinstance(node, dict):
        return ([node] if node.get("type") == kind else []) + _of_type(node.get("props", {}).get("children"), kind)
    if isinstance(node, list):
        return [found for child in node for found in _of_type(child, kind)]
    return []


def _rows(table: dict) -> list[list[list[str]]]:
    """The body of a serialized table, row by row, each row as the texts of its cells."""
    body = _of_type(table, "Tbody")[0]
    return [_shown(row["props"]["children"]) for row in body["props"]["children"]]


def _links(node) -> list[str]:
    return [link["props"].get("href") for link in _of_type(node, "A")]


def _ident(key: str) -> str:
    return f"games-{key.replace('_', '-')}"


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    """The three tracker files under tmp_path, built from the saved pages; every other source finds no file."""
    monkeypatch.setattr(games_tab, "get_data_path", lambda domain, name: str(tmp_path / name))
    for key, tracker in games_tab.GAME_TRACKERS.items():
        file_name = tracker["file"]
        (tmp_path / file_name).write_text(json.dumps(RECORDS[key](), ensure_ascii=False), encoding="utf-8")
        monkeypatch.setitem(tracker, "repo", games_tab.GamesRepository(str(tmp_path / file_name)))
    for name in ("deals_repo", "giveaways_repo", "trending_repo"):
        monkeypatch.setattr(games_tab, name, games_tab.GamesRepository(str(tmp_path / f"{name}.json")))
    return tmp_path


def _app(layout=None) -> dash.Dash:
    app = dash.Dash("test-games-trackers", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = layout if layout is not None else games_tab.render_games_tab()
    games_tab.register_games_callbacks(app)
    return app


# --- Calling a controller as the browser does ---
def _controller(app: dash.Dash, key: str) -> dict:
    """The callback that fills a tracker subtab, as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if f"{_ident(key)}-content.children" in cb["output"])


def _call(app: dash.Dash, key: str, values: dict[str, Any], changed=(), rendered: bool = False) -> dict:
    """POST to the controller of ``key`` with its inputs; ``values`` holds what each input holds, by id."""
    cb = _controller(app, key)
    state_value = {"-rendered": rendered}

    def slot(spec: dict) -> dict:
        suffix = next((ending for ending in state_value if spec["id"].endswith(ending)), None)
        return {"id": spec["id"], "property": spec["property"], "value": values.get(spec["id"], state_value[suffix] if suffix else None)}

    outputs = [dict(zip(("id", "property"), part.rsplit(".", 1), strict=True)) for part in cb["output"][2:-2].split("...")]
    body = {"output": cb["output"], "outputs": outputs, "inputs": [slot(spec) for spec in cb["inputs"]], "changedPropIds": list(changed), "state": [slot(spec) for spec in cb["state"]]}
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code in (200, 204), response.get_data(as_text=True)[-800:]  # 204: every output was no_update
    return {} if response.status_code == 204 else response.get_json()["response"]


def _open(app: dash.Dash, key: str) -> dict:
    """The browser telling the bar that the subtab of ``key`` is now the one in view."""
    return _call(app, key, {BAR: TRACKER_TABS[key]}, [f"{BAR}.active_tab"])


# --- The layout ---
def test_the_bar_opens_on_deals_and_ends_with_three_shells(root, monkeypatch) -> None:
    for tracker in games_tab.GAME_TRACKERS.values():
        monkeypatch.setattr(tracker["repo"], "get", lambda **_kw: pytest.fail("a tracker file was read while the tab rendered"))

    layout = games_tab.render_games_tab()

    bar = _by_id(layout, BAR)[0]
    assert bar.active_tab == "subtab-deals"  # set in the layout: unset, the bar sets it on mount and that fires the controllers
    assert [tab.tab_id for tab in bar.children] == EXISTING_TABS + list(TRACKER_TABS.values())
    assert [tab.label for tab in bar.children][len(EXISTING_TABS) :] == ["Nintendo eShop JP", "Key Shops", "Gift Cards"]
    for key in TRACKER_TABS:
        assert _shown(_by_id(layout, f"{_ident(key)}-content")[0]) == ["Loading…"]  # its controller has not run yet
        discount_filter = _by_id(layout, f"{_ident(key)}-min-discount")[0]
        assert [option["value"] for option in discount_filter.options] == [0, 10, 25, 50, 75, 90]
        assert discount_filter.value == 0  # every discount until the user asks for less


def test_every_id_each_controller_uses_is_in_the_layout(root) -> None:
    """The renderer skips a callback while one of its ids is missing, and with suppress_callback_exceptions nothing says so."""
    app = _app()
    layout_ids = _ids(app.layout)
    controllers = [_controller(app, key) for key in TRACKER_TABS]
    outputs = [part for cb in controllers for part in cb["output"][2:-2].split("...")]

    assert len(set(outputs)) == len(outputs) == 9  # one writer per Output id: the Single Callback Pattern
    for key in TRACKER_TABS:
        cb = _controller(app, key)
        ident = _ident(key)
        assert cb["prevent_initial_call"] is True
        assert [spec["id"] for spec in cb["inputs"]] == [BAR, f"{ident}-min-discount", f"{ident}-platform"]
        assert [spec["id"] for spec in cb["state"]] == [f"{ident}-rendered"]
        assert [part.rsplit(".", 1)[0] for part in cb["output"][2:-2].split("...")] == [f"{ident}-content", f"{ident}-platform", f"{ident}-rendered"]
        for spec in cb["inputs"] + cb["state"]:
            assert spec["id"] in layout_ids
        for part in cb["output"][2:-2].split("..."):
            assert part.rsplit(".", 1)[0] in layout_ids


def test_with_only_a_tracker_file_the_tab_shows_its_subtabs(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(games_tab, "get_data_path", lambda domain, name: str(tmp_path / name))
    for key, tracker in games_tab.GAME_TRACKERS.items():
        monkeypatch.setitem(tracker, "repo", games_tab.GamesRepository(str(tmp_path / tracker["file"])))
    for name in ("deals_repo", "giveaways_repo", "trending_repo"):
        monkeypatch.setattr(games_tab, name, games_tab.GamesRepository(str(tmp_path / f"{name}.json")))
    (tmp_path / "key_shop_deals.json").write_text(json.dumps(RECORDS["key_shops"]()), encoding="utf-8")

    layout = games_tab.render_games_tab()

    texts = _shown(layout)
    assert "games-sub-tabs" in _ids(layout)
    assert "All game data files are missing" not in texts and "Could not load game data" not in texts
    assert "No game deals data currently available or failed to load." in texts  # the eager subtabs say what they could not load


# --- Opening a tracker subtab ---
def test_opening_the_eshop_subtab_builds_its_table_in_whole_yen(root) -> None:
    response = _open(_app(), "eshop_jp")

    content = response[f"{_ident('eshop_jp')}-content"]["children"]
    assert _shown(content[0]) == ["3 titles on sale · best discount first"]
    table = _of_type(content[1], "Table")[0]
    assert _shown(table["props"]["children"][0]) == ["Title", "Platform", "Base price", "Sale price", "Discount", "Ends"]
    assert _rows(table) == [
        [OVERCOOKED, "Nintendo Switch", "¥4,100", "¥1,230", "70%", "2026-12-02"],
        ["モンスターハンターワイルズ", "Nintendo Switch 2", "¥4,990", "¥3,742", "25%", "2027-01-07"],
        [BOMBERMAN, "Nintendo Switch 2 Edition", "¥3,300", "¥2,640", "20%", "2026-12-06"],
    ]
    assert _links(table) == [
        "https://store-jp.nintendo.com/item/software/D70010000038868",
        "https://store-jp.nintendo.com/item/software/D70010000102604",
        "https://store-jp.nintendo.com/item/software/D70010000113450",
    ]
    assert "Prices in yen (¥)" in _shown(content[2])[0]  # the currency is the store's own: nothing converts it
    assert {option["value"] for option in response[f"{_ident('eshop_jp')}-platform"]["options"]} == {"Nintendo Switch", "Nintendo Switch 2", "Nintendo Switch 2 Edition"}
    assert response[f"{_ident('eshop_jp')}-rendered"]["data"] is True


def test_the_sale_price_is_bold_and_the_base_price_is_beside_it(root) -> None:
    table = _of_type(_open(_app(), "key_shops")[f"{_ident('key_shops')}-content"]["children"][1], "Table")[0]

    assert _shown(table["props"]["children"][0]) == ["Title", "Platform", "Store", "Region", "Base price", "Sale price", "Discount", "Ends"]
    first = _of_type(table, "Tbody")[0]["props"]["children"][0]["props"]["children"]
    assert [(cell["type"], _shown(cell), cell["props"].get("className")) for cell in first[4:6]] == [("Td", ["€13.00"], None), ("Td", ["€0.99"], "fw-bold")]
    assert _rows(table) == [
        ["Syberia 2", "PC & Mac", "Steam", "N/A", "€13.00", "€0.99", "92%", "2026-11-28"],  # 13 -> 0.99
        ["EA Sports FC 24 - 12000 FC Points", "PC", "EA App", "N/A", "€100.00", "€15.99", "84%", "2026-11-28"],
        ["Little Nightmares III Deluxe Edition", "PC", "Steam", "Europe", "€60.00", "€24.99", "58%", "2026-11-28"],
    ]
    assert _links(table)[0] == SYBERIA_URL


def test_the_gift_card_table_shows_the_face_value_beside_the_price(root) -> None:
    content = _open(_app(), "gift_cards")[f"{_ident('gift_cards')}-content"]["children"]
    table = _of_type(content[1], "Table")[0]

    assert _shown(content[0]) == ["8 gift cards under their face value · best discount first"]
    assert _shown(table["props"]["children"][0]) == ["Card", "Shop", "Platform", "Region", "Face value", "Price", "Discount"]
    rows = _rows(table)
    assert rows[0] == ["Tarjeta Playstation Network 80 EUR (ES) PSN Key SPAIN", "Eneba", "PlayStation Store", "Spain", "€80.00", "€67.97", "15%"]
    assert ["Tarjeta Nintendo eShop 50€", "Instant Gaming", "Nintendo eShop", "Europe", "€50.00", "€45.39", "9%"] in rows
    assert [row[-1] for row in rows] == ["15%", "15%", "15%", "13%", "10%", "9%", "7%", "5%"]  # the best discount first; 45.39 out of 50 is 9%, 13.89 out of 15 is 7%
    assert _links(table)[0] == "https://www.eneba.com/es/psn-playstation-network-card-80-eur-es-psn-key-spain"


def test_another_subtab_leaves_the_trackers_alone(root) -> None:
    app = _app()

    assert _call(app, "eshop_jp", {BAR: "subtab-deals"}, [f"{BAR}.active_tab"]) == {}  # back on Deals
    assert _call(app, "key_shops", {BAR: "subtab-deals"}) == {}  # a call without a change (a tab left open across a deploy)
    assert _call(app, "gift_cards", {BAR: "subtab-eshop-jp"}, [f"{BAR}.active_tab"]) == {}  # the subtab next door


def test_a_hundred_rows_fit_and_the_line_says_so(root) -> None:
    tiled = [dict(record, nsuid=f"{record['nsuid']}{n:02d}", title=f"{record['title']} #{n}") for n in range(40) for record in _eshop_records()]
    (root / "eshop_jp_deals.json").write_text(json.dumps(tiled, ensure_ascii=False), encoding="utf-8")

    content = _open(_app(), "eshop_jp")[f"{_ident('eshop_jp')}-content"]["children"]

    assert _shown(content[0]) == ["120 titles on sale · best discount first, showing 100"]
    assert len(_rows(_of_type(content[1], "Table")[0])) == 100


# --- The filters ---
def test_the_minimum_discount_filter_narrows_the_table(root) -> None:
    response = _call(_app(), "key_shops", {BAR: "subtab-key-shops", f"{_ident('key_shops')}-min-discount": 90}, [f"{_ident('key_shops')}-min-discount.value"], rendered=True)
    content = response[f"{_ident('key_shops')}-content"]["children"]

    assert _shown(content[0]) == ["1 of 3 deals of the day · at 90% off or more · best discount first"]
    assert _rows(_of_type(content[1], "Table")[0]) == [["Syberia 2", "PC & Mac", "Steam", "N/A", "€13.00", "€0.99", "92%", "2026-11-28"]]


def test_the_platform_filter_narrows_the_table(root) -> None:
    response = _call(_app(), "eshop_jp", {BAR: "subtab-eshop-jp", f"{_ident('eshop_jp')}-platform": "Nintendo Switch 2"}, [f"{_ident('eshop_jp')}-platform.value"], rendered=True)
    content = response[f"{_ident('eshop_jp')}-content"]["children"]

    assert _shown(content[0]) == ["1 of 3 titles on sale · on Nintendo Switch 2 · best discount first"]
    assert _rows(_of_type(content[1], "Table")[0]) == [["モンスターハンターワイルズ", "Nintendo Switch 2", "¥4,990", "¥3,742", "25%", "2027-01-07"]]


def test_both_filters_together_and_nothing_left(root) -> None:
    ident = _ident("gift_cards")
    response = _call(_app(), "gift_cards", {BAR: "subtab-gift-cards", f"{ident}-platform": "Nintendo eShop", f"{ident}-min-discount": 10}, [f"{ident}-min-discount.value"], rendered=True)
    content = response[f"{ident}-content"]["children"]

    assert _shown(content[0]) == ["2 of 8 gift cards under their face value · at 10% off or more · on Nintendo eShop · best discount first"]
    assert _rows(_of_type(content[1], "Table")[0]) == [
        ["Tarjeta Nintendo eShop 100 EUR Key SPAIN", "Eneba", "Nintendo eShop", "Spain", "€100.00", "€84.99", "15%"],
        ["Tarjeta Nintendo eShop 15 EUR Key EUROPE", "Eneba", "Nintendo eShop", "Europe", "€15.00", "€13.49", "10%"],
    ]

    ident = _ident("gift_cards")
    response = _call(_app(), "gift_cards", {BAR: "subtab-gift-cards", f"{ident}-platform": "Xbox Live"}, [f"{ident}-platform.value"], rendered=True)
    content = response[f"{ident}-content"]["children"]
    assert _shown(content[0]) == ["0 of 8 gift cards under their face value · on Xbox Live · best discount first"]
    assert _shown(content[1]) == ["No row matches these filters."]  # the alert, not a table
    assert _of_type(content[1], "Table") == []


# --- Requests a controller does not answer with a table ---
def test_back_on_a_subtab_whose_table_is_on_screen_costs_no_render(root) -> None:
    app = _app()

    assert _open(app, "gift_cards") != {}
    assert _call(app, "gift_cards", {BAR: "subtab-gift-cards"}, [f"{BAR}.active_tab"], rendered=True) == {}  # the table of the first visit is still there


def test_a_file_that_cannot_be_read_says_so(root) -> None:
    (root / "gift_card_deals.json").write_text("{not json", encoding="utf-8")
    ident = _ident("gift_cards")

    response = _open(_app(), "gift_cards")

    assert _shown(response[f"{ident}-content"]["children"]) == ["No gift card data currently available or failed to load."]
    assert response[f"{ident}-rendered"]["data"] is False  # the next visit asks again: the file may have come
    assert f"{ident}-platform" not in response


def test_an_empty_file_is_a_quiet_state_not_an_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(games_tab, "get_data_path", lambda domain, name: str(tmp_path / name))
    for key, tracker in games_tab.GAME_TRACKERS.items():
        monkeypatch.setitem(tracker, "repo", games_tab.GamesRepository(str(tmp_path / tracker["file"])))
    (tmp_path / "key_shop_deals.json").write_text("[]", encoding="utf-8")
    ident = _ident("key_shops")

    response = _open(_app(), "key_shops")

    assert _shown(response[f"{ident}-content"]["children"]) == ["No game of the daily selection is at a discount right now.", games_tab.GAME_TRACKERS["key_shops"]["note"]]
    assert response[f"{ident}-platform"]["options"] == []
    assert response[f"{ident}-rendered"]["data"] is True


# --- The app ---
def test_the_standalone_app_registers_the_controllers(root) -> None:
    app = games_tab.build_test_app()  # python -m src.web.dashboard.components.games_tab

    assert len(app._callback_list) == 3
    assert {cb["output"] for cb in app._callback_list} == {_controller(_app(), key)["output"] for key in TRACKER_TABS}


def test_the_dashboard_app_wires_the_controllers() -> None:
    """In the real app the three controllers are registered once, and nothing else writes what they write."""
    from src.web.dashboard import app as dashboard_app

    every_output = [part.rsplit(".", 1)[0] for cb in dashboard_app.app._callback_list for part in (cb["output"][2:-2].split("...") if cb["output"].startswith("..") else [cb["output"]])]
    tracker_outputs = [f"{_ident(key)}-{ending}" for key in TRACKER_TABS for ending in ("content", "platform", "rendered")]

    assert [every_output.count(ident) for ident in tracker_outputs] == [1] * 9  # one writer per Output id: no "Duplicate callback outputs" in the browser
    assert {cb["output"] for cb in dashboard_app.app._callback_list if f"{_ident('gift_cards')}-content" in cb["output"]} == {_controller(_app(), "gift_cards")["output"]}
