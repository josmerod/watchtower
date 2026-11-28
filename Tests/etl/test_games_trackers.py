"""The game price trackers: the discount comes from two prices, and a silent source keeps the last good file.

Three ETLs share ``games_tracker_common``: the sales of the Japanese eShop (``games_get_eshop_jp``), the daily
selection of a key shop (``games_get_key_shops``) and the gift cards sold under their face value
(``games_get_gift_cards``). The fixtures under fixtures/ are the pages and the API answer the sites really
returned on 2026-11-28, trimmed to a few entries. Nothing here reaches the network: ``Site`` answers from the
fixtures, and every file goes to tmp_path, never data/.
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

from src.etl.games import games_get_eshop_jp as eshop
from src.etl.games import games_get_gift_cards as cards
from src.etl.games import games_get_key_shops as keys
from src.etl.games import games_tracker_common as common

FIXTURES = Path(__file__).parent / "fixtures"
NOW = "2026-11-28T06:00:00+00:00"
LATER = "2026-11-28T08:00:00+00:00"

# The three titles of the eShop fixtures, in the order the listing shows them
IDS = "70010000102604,70010000038868,70010000113450"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class Site:
    """Stands in for the sites: answers each address from what the test mapped, and remembers what was asked."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.pages: dict[str, str] = {}
        self.refused: str | None = None  # the address that answers 403

    def fetch(self, url: str) -> str:
        self.calls.append(url)
        if url == self.refused:
            raise common.SourceRefused(f"{url}: HTTP 403")
        assert url in self.pages, f"nothing mapped for {url}"
        return self.pages[url]


class Answer:
    """What requests.get returns, reduced to what fetch_page reads."""

    def __init__(self, status: int, body: bytes = b"") -> None:
        self.status_code = status
        self.content = body


def _records(root: Path, name: str) -> list[dict]:
    return json.loads((root / "data" / "games" / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A temp project root: every file the trackers read or write goes under it."""
    monkeypatch.setattr(common, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(common, "ensure_directories", lambda dirs: None)
    (tmp_path / "data" / "games").mkdir(parents=True)
    return tmp_path


def wire(monkeypatch: pytest.MonkeyPatch, site: Site, now: str) -> None:
    """Point the three ETLs at *site* and at a fixed clock."""
    for etl in (eshop, cards, keys):
        monkeypatch.setattr(etl, "fetch_page", site.fetch)
        monkeypatch.setattr(etl, "utc_now_iso", lambda: now)


# --- Shared helpers ---
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (4931, 4931.0),
        ("4100", 4100.0),
        ("45.39", 45.39),
        ("45,39 €", 45.39),
        ("1.234,56", 1234.56),
        ("1,234.56", 1234.56),
        ("1.234", 1.234),  # a lone dot is a decimal mark: the shops write 45.39
        ("12,345", 12345.0),
        (None, None),
        (True, None),
        ("", None),
        ("free", None),
    ],
)
def test_to_amount_reads_the_ways_a_price_is_written(value, expected) -> None:
    assert common.to_amount(value) == expected


@pytest.mark.parametrize(
    ("base", "sale", "expected"),
    [
        (13, 0.99, 92),  # Syberia 2 on the day of the fixture
        (1098, 299, 73),  # 72.77 rounds up; Python's round() would say 72
        (200, 199, 1),  # half a point rounds up too
        (50, 25, 50),
        (None, 1, None),
        (10, None, None),
        (0, 1, None),
        (10, 0, None),
        (10, 10, None),  # no discount
        (10, 12, None),  # sold over its base price
    ],
)
def test_discount_is_computed_from_the_two_prices(base, sale, expected) -> None:
    assert common.discount_pct(base, sale) == expected


def test_regions_get_one_english_label_and_a_scope() -> None:
    assert common.region_label("ES") == "Spain"
    assert common.region_label("España") == "Spain"
    assert common.region_label("europe") == "Europe"
    assert common.region_label("global") == "Global"
    assert common.region_label("latin america") == "latin america"  # unknown: the source's own words
    assert common.region_label(None) is None
    assert [common.region_scope(label) for label in ("Spain", "Europe", "Global", "latin america", None)] == ["spain", "europe", "global", "other", "unknown"]


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Syberia 2 - Europe", ("Syberia 2", "Europe")),
        ("Tarjeta Nintendo eShop 50€ - Europe", ("Tarjeta Nintendo eShop 50€", "Europe")),
        ("Little Nightmares III Deluxe Edition", ("Little Nightmares III Deluxe Edition", None)),
        ("The Legend of Zelda - Link's Awakening", ("The Legend of Zelda - Link's Awakening", None)),  # "Link" is not a region
        (None, ("", None)),
    ],
)
def test_a_region_suffix_is_only_a_known_region(title, expected) -> None:
    assert common.split_ig_title(title) == expected


def test_fetch_page_names_the_app_and_waits_before_asking(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple] = []
    sleeps: list[float] = []
    monkeypatch.setattr(common.requests, "get", lambda url, headers, timeout: calls.append((url, headers, timeout)) or Answer(200, "1,50 €".encode()))
    monkeypatch.setattr(common.time, "sleep", sleeps.append)

    assert common.fetch_page("https://example.invalid/a", pause=2) == "1,50 €"

    assert calls == [("https://example.invalid/a", common.HEADERS, common.REQUEST_TIMEOUT)]
    assert common.HEADERS["User-Agent"].startswith("Watchtower/")  # the site can tell who is reading
    assert sleeps == [2]


@pytest.mark.parametrize("status", [403, 429, 500])
def test_a_refusal_is_raised_at_once_and_never_retried(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    calls: list[str] = []
    monkeypatch.setattr(common.requests, "get", lambda url, **_kw: calls.append(url) or Answer(status))
    monkeypatch.setattr(common.time, "sleep", lambda seconds: None)

    with pytest.raises(common.SourceRefused, match=f"HTTP {status}"):
        common.fetch_page("https://example.invalid/a")

    assert calls == ["https://example.invalid/a"]


def test_no_answer_is_a_source_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(*_args, **_kw) -> None:
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(common.requests, "get", down)
    monkeypatch.setattr(common.time, "sleep", lambda seconds: None)

    with pytest.raises(common.SourceError, match="no answer"):
        common.fetch_page("https://example.invalid/a")


# --- My Nintendo Store JP ---
def listing(page: int) -> str:
    return f"{eshop.LISTING_URL}?{eshop.LISTING_PARAMS}&page={page}"


def price_call(ids: str) -> str:
    return f"{eshop.PRICE_URL}?country=JP&lang=ja&ids={ids}"


def embedded_state(data: dict) -> str:
    """A listing page reduced to the state the store ships inside its HTML."""
    state = {"__PRELOADED_STATE__": {"__reactQuery": {"queries": [{"state": {"data": data}}]}}}
    return f'<!DOCTYPE html><html><head><script id="mobify-data" type="application/json">{json.dumps(state)}</script></head></html>'


def eshop_site() -> Site:
    site = Site()
    site.pages[listing(1)] = fixture("eshop_jp_sale_listing.html")
    site.pages[price_call(IDS)] = fixture("eshop_jp_price_api.json")
    return site


def test_the_sale_listing_gives_the_tiles_and_their_platform() -> None:
    tiles = eshop.parse_listing_page(fixture("eshop_jp_sale_listing.html"))

    assert [(tile["id"], tile["saleLabel"], eshop.platform_of(tile)) for tile in tiles] == [
        ("70010000102604", "25%OFF", "Nintendo Switch 2"),
        ("70010000038868", "70%OFF", "Nintendo Switch"),
        ("70010000113450", "20%OFF", "Nintendo Switch 2 Edition"),
    ]
    assert eshop.platform_of({"productClassCode": "OTHER"}) == "Unknown"


def test_a_listing_page_without_the_embedded_state_is_an_error() -> None:
    with pytest.raises(common.SourceError, match="no embedded state"):
        eshop.parse_listing_page("<html><body>a captcha page</body></html>")
    with pytest.raises(common.SourceError, match="no product list"):
        eshop.parse_listing_page(embedded_state({"somethingElse": []}))


def test_prices_come_from_the_api_and_the_discount_is_computed(caplog: pytest.LogCaptureFixture) -> None:
    prices = eshop.parse_prices(json.loads(fixture("eshop_jp_price_api.json")))
    tiles = eshop.parse_listing_page(fixture("eshop_jp_sale_listing.html"))

    with caplog.at_level(logging.WARNING):
        records = eshop.build_records(tiles, prices)

    assert [(r["title"], r["platform"], r["base_price"], r["sale_price"], r["discount_pct"]) for r in records] == [
        ("モンスターハンターワイルズ", "Nintendo Switch 2", 4990, 3742, 25),  # 4990 -> 3742 is 24.97%
        ("Overcooked!® - オーバークック 王国のフルコース", "Nintendo Switch", 4100, 1230, 70),
        ("スーパーボンバーマン コレクション Nintendo Switch 2 Edition", "Nintendo Switch 2 Edition", 3300, 2640, 20),
    ]
    first = records[0]
    assert (first["shop"], first["currency"], first["source_discount_label"], first["sales_status"]) == ("My Nintendo Store JP", "JPY", "25%OFF", "preorder")
    assert first["sale_end"] == "2027-01-07T14:59:59Z"  # midnight in Japan, as the store states it
    assert first["url"] == "https://store-jp.nintendo.com/item/software/D70010000102604"
    assert caplog.text == ""  # every label of the page agrees with the computed discount


def test_a_title_the_price_api_does_not_put_on_sale_stays_out() -> None:
    payload = {
        "prices": [
            {"title_id": 70010000038868, "regular_price": {"raw_value": 4100}, "discount_price": {"raw_value": 1230}, "sales_status": "onsale"},
            {"title_id": 70010000000001, "regular_price": {"raw_value": 5000}, "sales_status": "not_found"},  # no discount_price
            {"title_id": 70010000000002, "discount_price": {"raw_value": 5000}, "sales_status": "onsale"},  # no regular_price
            {"title_id": 70010000000003, "regular_price": {"raw_value": 5000}, "discount_price": {"raw_value": 5000}, "sales_status": "onsale"},  # 0%
        ]
    }
    prices = eshop.parse_prices(payload)

    assert list(prices) == ["70010000038868", "70010000000003"]
    assert eshop.build_records([{"id": 70010000000003, "name": "Full price"}], prices) == []


def test_a_label_that_disagrees_by_more_than_a_point_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    prices = eshop.parse_prices(json.loads(fixture("eshop_jp_price_api.json")))
    tiles = eshop.parse_listing_page(fixture("eshop_jp_sale_listing.html"))
    tiles[0]["saleLabel"] = "30%OFF"  # the page really says 25%OFF

    with caplog.at_level(logging.WARNING):
        records = eshop.build_records(tiles, prices)

    assert records[0]["discount_pct"] == 25  # the two prices win
    assert "computed 25% off, the store labels it 30% off" in caplog.text


def test_the_run_reads_every_page_once_and_prices_in_batches(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    site = eshop_site()
    site.pages[listing(2)] = fixture("eshop_jp_sale_listing.html")  # the same titles again: a nsuid counts once
    first_half, second_half = IDS.rsplit(",", 1)
    site.pages[price_call(first_half)] = fixture("eshop_jp_price_api.json")
    site.pages[price_call(second_half)] = fixture("eshop_jp_price_api.json")
    monkeypatch.setattr(eshop, "PRICE_BATCH", 2)
    monkeypatch.setattr(eshop, "LISTING_PAGES", 2)
    wire(monkeypatch, site, NOW)

    eshop.main()

    assert site.calls == [listing(1), listing(2), price_call(first_half), price_call(second_half)]
    records = _records(root, eshop.OUTPUT_NAME)
    assert [(r["title"], r["discount_pct"]) for r in records] == [("Overcooked!® - オーバークック 王国のフルコース", 70), ("モンスターハンターワイルズ", 25), ("スーパーボンバーマン コレクション Nintendo Switch 2 Edition", 20)]
    assert all(r["first_detected_at"] == NOW == r["last_seen_at"] for r in records)
    assert all(isinstance(r["base_price"], int) and isinstance(r["sale_price"], int) for r in records)  # whole yen
    assert (root / "data" / "games" / f"{eshop.OUTPUT_NAME}.csv").exists()
    assert not list((root / "data" / "games").glob("*.partial"))


def test_the_run_stops_at_the_first_empty_page(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    site = eshop_site()
    site.pages[listing(2)] = embedded_state({"resultProducts": []})
    monkeypatch.setattr(eshop, "LISTING_PAGES", 4)
    wire(monkeypatch, site, NOW)

    eshop.main()

    assert site.calls == [listing(1), listing(2), price_call(IDS)]


def test_first_detected_at_survives_the_next_run(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(eshop, "LISTING_PAGES", 1)
    site = eshop_site()
    wire(monkeypatch, site, NOW)
    eshop.main()
    wire(monkeypatch, site, LATER)

    eshop.main()

    records = _records(root, eshop.OUTPUT_NAME)
    assert len(records) == 3
    assert all(r["first_detected_at"] == NOW and r["last_seen_at"] == LATER for r in records)


def test_a_sale_listing_without_titles_keeps_the_last_file(monkeypatch: pytest.MonkeyPatch, root: Path, caplog: pytest.LogCaptureFixture) -> None:
    site = Site()
    site.pages[listing(1)] = embedded_state({"resultProducts": []})
    previous = root / "data" / "games" / f"{eshop.OUTPUT_NAME}.json"
    previous.write_text('[{"nsuid": "70010000038868", "title": "the previous file"}]', encoding="utf-8")
    wire(monkeypatch, site, NOW)

    with caplog.at_level(logging.WARNING):
        eshop.main()  # not a failed run: the exit code is 0

    assert "No games on sale to record" in caplog.text
    assert json.loads(previous.read_text(encoding="utf-8")) == [{"nsuid": "70010000038868", "title": "the previous file"}]
    assert not list(previous.parent.glob("*.partial"))


def test_a_refused_store_fails_the_run_and_keeps_the_last_file(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    site = eshop_site()
    site.refused = listing(1)
    previous = root / "data" / "games" / f"{eshop.OUTPUT_NAME}.json"
    previous.write_text('[{"nsuid": "70010000038868", "title": "the previous file"}]', encoding="utf-8")
    wire(monkeypatch, site, NOW)

    with pytest.raises(SystemExit) as excinfo:
        eshop.main()

    assert excinfo.value.code == 1  # the scheduler counts a refused store as failed
    assert site.calls == [listing(1)]  # it stops there: no second page, no retry
    assert json.loads(previous.read_text(encoding="utf-8")) == [{"nsuid": "70010000038868", "title": "the previous file"}]


# --- Gift cards ---
def eneba(category: str, page: int | None = None) -> str:
    return f"{cards.ENEBA_BASE}/es/store/{category}" + (f"?page={page}" if page else "")


IG_NINTENDO_SHELF = f"{common.IG_BASE}/es/nintendo/tarjetas-regalo/"
CARD_15 = f"{common.IG_BASE}/es/2356-comprar-tarjeta-nintendo-eshop-15eur-switch-switch-2-nintendo-eshop/"
CARD_50 = f"{common.IG_BASE}/es/4931-comprar-tarjeta-nintendo-eshop-50eur-switch-switch-2-nintendo-eshop/"


def apollo_state(search: dict) -> str:
    """A Eneba page reduced to the state it ships inside its HTML."""
    return f'<!DOCTYPE html><html><head><script id="__APOLLO_STATE__" type="application/json">{json.dumps({"ROOT_QUERY": {"search(x)": search}})}</script></head></html>'


def cards_site() -> Site:
    site = Site()
    site.pages[eneba("psn-gift-cards")] = fixture("eneba_gift_cards_page.html")
    site.pages[eneba("psn-gift-cards", 2)] = fixture("eneba_gift_cards_last_page.html")  # the next page: no link to a third
    site.pages[eneba("nintendo-gift-cards")] = fixture("eneba_gift_cards_last_page.html")
    site.pages[IG_NINTENDO_SHELF] = fixture("instant_gaming_gift_cards_shelf.html")
    site.pages[CARD_15] = fixture("instant_gaming_card_product_15.html")
    site.pages[CARD_50] = fixture("instant_gaming_card_product.html")
    return site


def small_shelves(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cards, "ENEBA_CATEGORIES", ("psn-gift-cards", "nintendo-gift-cards"))
    monkeypatch.setattr(cards, "IG_CATEGORIES", (("nintendo", "Nintendo eShop"),))


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Tarjeta Nintendo eShop 50 EUR Key SPAIN", 50.0),
        ("Tarjeta Nintendo eShop 15€ - Europe", 15.0),
        ("Tarjeta Playstation Network 10 EUR (ES) PSN Key SPAIN", 10.0),
        ("Valorant 25 EUR - 2565 Riot Points", None),  # in-game currency is not a card
        ("PlayStation Plus 12 months", None),
        ("", None),
    ],
)
def test_the_face_value_needs_a_card_and_a_value(name: str, expected) -> None:
    assert cards.face_value_eur(name) == expected


def test_eneba_gives_the_cards_under_their_face_value_and_the_next_page() -> None:
    page_cards, next_url = cards.parse_eneba_page(fixture("eneba_gift_cards_page.html"))

    assert next_url == eneba("psn-gift-cards", 2)
    assert [(c["title"], c["base_price"], c["sale_price"], c["discount_pct"], c["region"]) for c in page_cards] == [
        ("Tarjeta Playstation Network 60 EUR (ES) PSN Key SPAIN", 60.0, 51.91, 13, "Spain"),
        ("Tarjeta Playstation Network 80 EUR (ES) PSN Key SPAIN", 80.0, 67.97, 15, "Spain"),
        ("Tarjeta Playstation Network 10 EUR (ES) PSN Key SPAIN", 10.0, 8.49, 15, "Spain"),
    ]
    # The page also lists a 55 EUR card sold over its value and a 150 EUR card at 149.97: neither is a deal
    assert [c["source_discount_label"] for c in page_cards] == ["-13%", None, "-15%"]
    assert page_cards[0]["regular_price"] == 60.0 and page_cards[1]["regular_price"] is None  # the shop states no regular price
    assert all(c["base_source"] == "face_value" and c["shop"] == "Eneba" and c["platform"] == "PlayStation Store" for c in page_cards)
    assert page_cards[0]["url"] == "https://www.eneba.com/es/psn-playstation-network-card-60-eur-es-psn-key-spain"


def test_the_last_page_of_a_shelf_has_no_next_page_and_skips_a_card_without_an_offer() -> None:
    page_cards, next_url = cards.parse_eneba_page(fixture("eneba_gift_cards_last_page.html"))

    assert next_url is None
    assert [(c["title"], c["sale_price"], c["discount_pct"], c["region_scope"]) for c in page_cards] == [
        ("Tarjeta Nintendo eShop 15 EUR Key EUROPE", 13.49, 10, "europe"),
        ("Tarjeta Nintendo eShop 100 EUR Key SPAIN", 84.99, 15, "spain"),
        ("Tarjeta Nintendo eShop 75 EUR Key SPAIN", 70.96, 5, "spain"),
    ]  # the 35 EUR card has no offer on the page


def test_an_eneba_page_without_the_embedded_state_is_an_error() -> None:
    with pytest.raises(common.SourceError, match="no embedded state"):
        cards.parse_eneba_page("<html><body></body></html>")


def test_instant_gaming_tiles_tell_the_price_and_what_is_out_of_stock() -> None:
    tiles = common.parse_ig_tiles(fixture("instant_gaming_gift_cards_shelf.html"))

    assert [(t["title"], t["discount_label"], t["price"]) for t in tiles] == [
        ("Tarjeta Nintendo eShop 15€", 7, 13.89),
        ("Tarjeta Nintendo eShop 50€", 9, 45.39),
        ("Super Kirby Clash 1000 Gem Apples", None, None),  # no price: out of stock
        ("Super Kirby Clash 2000 Gem Apples", 25, 14.99),
    ]
    assert tiles[1]["url"] == CARD_50
    assert common.parse_ig_product(fixture("instant_gaming_card_product.html")) == {
        "id": 4931,
        "name": "Tarjeta Nintendo eShop 50€ - Europe",
        "store": "Nintendo eShop",
        "price": 45.39,
        "regular_price": 50.0,
        "currency": "EUR",
        "in_stock": True,
        "price_valid_until": None,
    }
    assert common.parse_ig_product("<html><body>not a product</body></html>") is None


def test_an_instant_gaming_card_takes_its_face_value_as_the_base_price() -> None:
    tile = common.parse_ig_tiles(fixture("instant_gaming_gift_cards_shelf.html"))[1]
    product = common.parse_ig_product(fixture("instant_gaming_card_product.html"))

    card = cards.build_ig_card(tile, product, 50.0, "Nintendo eShop")

    assert (card["card_id"], card["title"], card["shop"], card["platform"]) == ("instant-gaming:4931", "Tarjeta Nintendo eShop 50€", "Instant Gaming", "Nintendo eShop")
    assert (card["base_price"], card["base_source"], card["regular_price"], card["sale_price"], card["discount_pct"]) == (50.0, "face_value", 50.0, 45.39, 9)
    assert (card["region"], card["region_scope"], card["currency"], card["in_stock"], card["url"]) == ("Europe", "europe", "EUR", True, CARD_50)
    assert cards.build_ig_card(tile, {**product, "in_stock": False}, 50.0, "Nintendo eShop") is None
    assert cards.build_ig_card(tile, {**product, "price": 50.0}, 50.0, "Nintendo eShop") is None  # face value is no deal


def test_the_run_follows_the_next_page_and_reads_a_page_per_card(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    small_shelves(monkeypatch)
    site = cards_site()
    wire(monkeypatch, site, NOW)

    cards.main()

    assert site.calls == [eneba("psn-gift-cards"), eneba("psn-gift-cards", 2), eneba("nintendo-gift-cards"), IG_NINTENDO_SHELF, CARD_15, CARD_50]
    # The in-game currency is never asked for; no page after the one without a next link
    records = _records(root, cards.OUTPUT_NAME)
    ids = [r["card_id"] for r in records]
    assert len(ids) == len(set(ids)) == 8  # the Nintendo page comes back on two addresses here: a card counts once
    assert [(r["title"], r["shop"], r["discount_pct"]) for r in records[:3]] == [
        ("Tarjeta Playstation Network 80 EUR (ES) PSN Key SPAIN", "Eneba", 15),
        ("Tarjeta Playstation Network 10 EUR (ES) PSN Key SPAIN", "Eneba", 15),
        ("Tarjeta Nintendo eShop 100 EUR Key SPAIN", "Eneba", 15),
    ]
    assert {r["platform"] for r in records} == {"Nintendo eShop", "PlayStation Store"}
    assert all(r["first_detected_at"] == NOW == r["last_seen_at"] and r["currency"] == "EUR" for r in records)
    assert not list((root / "data" / "games").glob("*.partial"))


def test_the_page_budget_of_a_shelf_is_a_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    site = Site()
    site.pages[eneba("psn-gift-cards")] = fixture("eneba_gift_cards_page.html")
    site.pages[eneba("psn-gift-cards", 2)] = fixture("eneba_gift_cards_page.html")  # this one also links to a next page
    site.pages[eneba("psn-gift-cards", 3)] = fixture("eneba_gift_cards_page.html")
    monkeypatch.setattr(cards, "fetch_page", site.fetch)
    monkeypatch.setattr(cards, "ENEBA_CATEGORIES", ("psn-gift-cards",))
    monkeypatch.setattr(cards, "ENEBA_MAX_PAGES", 2)

    collected = cards.collect_eneba()

    assert site.calls == [eneba("psn-gift-cards"), eneba("psn-gift-cards", 2)]
    assert len(collected) == 6


def test_first_detected_at_of_a_card_survives_the_next_run(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    small_shelves(monkeypatch)
    site = cards_site()
    wire(monkeypatch, site, NOW)
    cards.main()
    wire(monkeypatch, site, LATER)

    cards.main()

    records = _records(root, cards.OUTPUT_NAME)
    assert len(records) == 8
    assert all(r["first_detected_at"] == NOW and r["last_seen_at"] == LATER for r in records)


def test_shelves_without_a_deal_keep_the_last_file(monkeypatch: pytest.MonkeyPatch, root: Path, caplog: pytest.LogCaptureFixture) -> None:
    site = Site()
    site.pages[eneba("psn-gift-cards")] = apollo_state({"results": {"edges": []}})
    site.pages[IG_NINTENDO_SHELF] = "<html><body></body></html>"
    monkeypatch.setattr(cards, "ENEBA_CATEGORIES", ("psn-gift-cards",))
    monkeypatch.setattr(cards, "IG_CATEGORIES", (("nintendo", "Nintendo eShop"),))
    previous = root / "data" / "games" / f"{cards.OUTPUT_NAME}.json"
    previous.write_text('[{"card_id": "eneba:p3ws7fshzoe63qckwmscah15hy", "title": "the previous file"}]', encoding="utf-8")
    wire(monkeypatch, site, NOW)

    with caplog.at_level(logging.WARNING):
        cards.main()  # not a failed run: the exit code is 0

    assert "No gift cards under their face value to record" in caplog.text
    assert json.loads(previous.read_text(encoding="utf-8")) == [{"card_id": "eneba:p3ws7fshzoe63qckwmscah15hy", "title": "the previous file"}]
    assert not list(previous.parent.glob("*.partial"))


def test_a_refused_shop_fails_the_run_and_keeps_the_last_file(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    small_shelves(monkeypatch)
    site = cards_site()
    site.refused = eneba("psn-gift-cards")
    previous = root / "data" / "games" / f"{cards.OUTPUT_NAME}.json"
    previous.write_text('[{"card_id": "eneba:p3ws7fshzoe63qckwmscah15hy", "title": "the previous file"}]', encoding="utf-8")
    wire(monkeypatch, site, NOW)

    with pytest.raises(SystemExit) as excinfo:
        cards.main()

    assert excinfo.value.code == 1
    assert site.calls == [eneba("psn-gift-cards")]  # the first refusal ends the run
    assert json.loads(previous.read_text(encoding="utf-8")) == [{"card_id": "eneba:p3ws7fshzoe63qckwmscah15hy", "title": "the previous file"}]


# --- Key shops ---
SYBERIA = f"{common.IG_BASE}/es/1245-comprar-syberia-2-pc-mac-juego-steam/"
LITTLE_NIGHTMARES = f"{common.IG_BASE}/es/19670-comprar-little-nightmares-iii-deluxe-edition-pc-steam/"
FC_POINTS = f"{common.IG_BASE}/es/15005-comprar-ea-sports-fc-24-12000-fc-points-12000-fc-pc-juego-ea-app/"


def keys_site() -> Site:
    site = Site()
    site.pages[keys.DAILY_DEALS_URL] = fixture("instant_gaming_daily_deals.html")
    site.pages[SYBERIA] = fixture("instant_gaming_daily_deal_product.html")
    site.pages[LITTLE_NIGHTMARES] = fixture("instant_gaming_daily_deal_product_little_nightmares.html")
    site.pages[FC_POINTS] = fixture("instant_gaming_daily_deal_product_fc_points.html")
    return site


def selection() -> list[dict]:
    return common.parse_ig_tiles(fixture("instant_gaming_daily_deals.html"))


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Syberia 2 - PC & Mac (Steam)", ("Syberia 2", "PC & Mac")),
        ("Little Nightmares III Deluxe Edition - PC (Steam)", ("Little Nightmares III Deluxe Edition", "PC")),
        ("EA Sports FC 24 - 12000 FC Points - PC (EA App)", ("EA Sports FC 24 - 12000 FC Points", "PC")),
        ("NBA 2K26", ("NBA 2K26", None)),
    ],
)
def test_a_tile_title_splits_into_game_and_device(title: str, expected) -> None:
    assert keys.split_tile_title(title) == expected


def test_a_daily_deal_has_the_regular_price_beside_the_sale_price() -> None:
    syberia, little_nightmares, _fc_points = selection()
    product = common.parse_ig_product(fixture("instant_gaming_daily_deal_product.html"))

    record = keys.build_record(syberia, product)

    assert (record["deal_id"], record["title"], record["shop"], record["deal_type"]) == ("instant-gaming:1245", "Syberia 2", "Instant Gaming", "daily_deal")
    assert (record["base_price"], record["sale_price"], record["discount_pct"], record["source_discount_label"]) == (13, 0.99, 92, "-92%")
    assert (record["platform"], record["store"], record["region"], record["sale_end"], record["currency"]) == ("PC & Mac", "Steam", None, "2026-11-28", "EUR")
    assert record["url"] == SYBERIA and record["in_stock"] is True


def test_the_region_of_a_key_is_read_from_its_page() -> None:
    _syberia, little_nightmares, fc_points = selection()
    product = common.parse_ig_product(fixture("instant_gaming_daily_deal_product_little_nightmares.html"))

    record = keys.build_record(little_nightmares, product)

    assert (record["title"], record["region"], record["region_scope"], record["base_price"], record["sale_price"], record["discount_pct"]) == (
        "Little Nightmares III Deluxe Edition",
        "Europe",
        "europe",
        60.0,
        24.99,
        58,
    )
    record = keys.build_record(fc_points, common.parse_ig_product(fixture("instant_gaming_daily_deal_product_fc_points.html")))
    assert (record["title"], record["store"], record["base_price"], record["sale_price"], record["discount_pct"]) == ("EA Sports FC 24 - 12000 FC Points", "EA App", 100.0, 15.99, 84)


def test_a_deal_needs_two_prices_a_real_discount_and_stock() -> None:
    syberia, *_others = selection()
    product = common.parse_ig_product(fixture("instant_gaming_daily_deal_product.html"))

    assert keys.build_record(syberia, {**product, "regular_price": None}) is None  # no regular price stated
    assert keys.build_record(syberia, {**product, "price": 13.0}) is None  # no discount
    assert keys.build_record(syberia, {**product, "in_stock": False}) is None


def test_the_run_reads_the_selection_then_the_page_of_each_game(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    site = keys_site()
    wire(monkeypatch, site, NOW)

    keys.main()

    assert site.calls == [keys.DAILY_DEALS_URL, SYBERIA, LITTLE_NIGHTMARES, FC_POINTS]
    records = _records(root, keys.OUTPUT_NAME)
    assert [(r["title"], r["base_price"], r["sale_price"], r["discount_pct"]) for r in records] == [
        ("Syberia 2", 13, 0.99, 92),
        ("EA Sports FC 24 - 12000 FC Points", 100.0, 15.99, 84),
        ("Little Nightmares III Deluxe Edition", 60.0, 24.99, 58),
    ]
    assert all(r["first_detected_at"] == NOW == r["last_seen_at"] and r["sale_end"] == "2026-11-28" for r in records)
    assert (root / "data" / "games" / f"{keys.OUTPUT_NAME}.csv").exists()
    assert not list((root / "data" / "games").glob("*.partial"))


def test_the_product_budget_of_a_run_is_a_ceiling(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    site = keys_site()
    monkeypatch.setattr(keys, "MAX_PRODUCTS", 2)
    wire(monkeypatch, site, NOW)

    keys.main()

    assert site.calls == [keys.DAILY_DEALS_URL, SYBERIA, LITTLE_NIGHTMARES]
    assert len(_records(root, keys.OUTPUT_NAME)) == 2


def test_first_detected_at_of_a_deal_survives_the_next_run(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    site = keys_site()
    wire(monkeypatch, site, NOW)
    keys.main()
    # Next day: only Syberia 2 is still on sale
    for url in (LITTLE_NIGHTMARES, FC_POINTS):
        del site.pages[url]
    site.pages[keys.DAILY_DEALS_URL] = '<div class="listing-items search"><article class="item">' + '<a class="cover " href="' + SYBERIA + '" title="Syberia 2 - PC & Mac (Steam)"></a><div class="title" title="Syberia 2 - PC & Mac (Steam)"></div><div class="discount"> -92% </div><div class=" price "> 0.99&nbsp;€ </div></article></div>'
    wire(monkeypatch, site, LATER)

    keys.main()

    records = _records(root, keys.OUTPUT_NAME)
    assert [(r["title"], r["first_detected_at"], r["last_seen_at"]) for r in records] == [("Syberia 2", NOW, LATER)]


def test_a_selection_without_a_discounted_tile_keeps_the_last_file(monkeypatch: pytest.MonkeyPatch, root: Path, caplog: pytest.LogCaptureFixture) -> None:
    site = Site()
    site.pages[keys.DAILY_DEALS_URL] = "<html><body></body></html>"
    previous = root / "data" / "games" / f"{keys.OUTPUT_NAME}.json"
    previous.write_text('[{"deal_id": "instant-gaming:1245", "title": "the previous file"}]', encoding="utf-8")
    wire(monkeypatch, site, NOW)

    with caplog.at_level(logging.WARNING):
        keys.main()  # not a failed run: the exit code is 0

    assert "No key shop deals to record" in caplog.text
    assert site.calls == [keys.DAILY_DEALS_URL]
    assert json.loads(previous.read_text(encoding="utf-8")) == [{"deal_id": "instant-gaming:1245", "title": "the previous file"}]
    assert not list(previous.parent.glob("*.partial"))


def test_a_refused_shop_fails_the_run_and_keeps_the_last_file(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    site = keys_site()
    site.refused = LITTLE_NIGHTMARES
    previous = root / "data" / "games" / f"{keys.OUTPUT_NAME}.json"
    previous.write_text('[{"deal_id": "instant-gaming:1245", "title": "the previous file"}]', encoding="utf-8")
    wire(monkeypatch, site, NOW)

    with pytest.raises(SystemExit) as excinfo:
        keys.main()

    assert excinfo.value.code == 1
    assert site.calls == [keys.DAILY_DEALS_URL, SYBERIA, LITTLE_NIGHTMARES]  # the refusal ends the run at once
    assert json.loads(previous.read_text(encoding="utf-8")) == [{"deal_id": "instant-gaming:1245", "title": "the previous file"}]


# --- The wiring: the cycle runs each script, the API lists each file, the freshness watcher dates its items ---
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TRACKER_FILES = {
    "eshop_jp": ("games_get_eshop_jp.py", "eshop_jp_deals.json"),
    "key_shops": ("games_get_key_shops.py", "key_shop_deals.json"),
    "gift_cards": ("games_get_gift_cards.py", "gift_card_deals.json"),
}


def test_each_tracker_is_in_the_cycle_the_api_and_the_freshness_watcher() -> None:
    import run_all_etl_orchestrator as orch
    from src.services.data_loader import GAMES_SOURCES_CONFIG
    from src.watchers.data_freshness_watcher import SOURCE_FILES

    for key, (script, file_name) in TRACKER_FILES.items():
        assert f"src/etl/games/{script}" in orch.ETL_SCRIPTS  # an unlisted script never runs in production
        assert Path(GAMES_SOURCES_CONFIG[key]["path"]).name == file_name
        entry = next(source for source in SOURCE_FILES if source["path"] == f"games/{file_name}")
        assert entry["content_date"] == "last_seen_at"  # the field every tracker record carries


def test_the_freshness_watcher_judges_a_tracker_by_when_its_items_were_seen(tmp_path: Path) -> None:
    """A file restored from a backup is new on disk; the age of its items is what the watcher reports."""
    from src.watchers import data_freshness_watcher as watcher

    entry = next(source for source in watcher.SOURCE_FILES if source["path"] == "games/eshop_jp_deals.json")
    seen = datetime(2026, 11, 28, 6, 0, tzinfo=timezone.utc)
    prices = eshop.parse_prices(json.loads(fixture("eshop_jp_price_api.json")))
    records = common.stamp_records(eshop.build_records(eshop.parse_listing_page(fixture("eshop_jp_sale_listing.html")), prices), "nsuid", [], seen.isoformat())
    path = tmp_path / "games" / "eshop_jp_deals.json"
    path.parent.mkdir()
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    now = seen + timedelta(hours=30)
    restored = (seen + timedelta(hours=29)).timestamp()  # on disk for an hour: fresh by the age of the file alone
    os.utime(path, (restored, restored))

    record = watcher.assess_freshness([entry], data_dir=tmp_path, now=now.timestamp())["sources"][0]

    assert (record["status"], record["age_hours"], record["content_age_hours"]) == ("stale", 30.0, 30.0)
