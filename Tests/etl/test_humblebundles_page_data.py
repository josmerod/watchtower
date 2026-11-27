"""The Humble ETL reads what the listing page states instead of inventing it (T-193).

Every bundle came out with "now + 14 days" as its end date and no item: the tiles alone state neither. The page
embeds an object per bundle with the end date, the item count and the first titles. Fixtures only: the pages are
strings built here in the page's shape, and the scraper's files go to tmp_path, never data/.
"""

import asyncio
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from src.etl.games import games_get_humblebundles as etl

HUMBLE = "https://www.humblebundle.com"


def _bundle(slug: str, titles: list[str], items_count=11, end_date="2026-12-08T05:00:00.000Z", category="games", title=None) -> dict:
    """An object in the shape the page embeds, trimmed to what the ETL reads plus two keys it ignores."""
    return {
        "category": category,
        "endDate": end_date,
        "id": "e8ee7155-838e-4290-83b2-6d9acd69815e",
        "includedItemTitles": titles,
        "itemsCount": str(items_count),
        "platforms": ["windows", "mac"],
        "displayPrice": {"currentPrice": {"centAmount": "1367", "currencyCode": "EUR"}},
        "productKey": slug.replace("-", ""),
        "productType": "humble-bundle",
        "slug": slug,
        "title": slug.replace("-", " ").title() if title is None else title,
        "url": f"/{category}/{slug}",
    }


def _page(*lines: str) -> str:
    """A page in the shape Next.js ships: its data as an escaped string inside a push call, among other lines."""
    chunk = json.dumps("\n".join(lines))  # the JS string literal
    return f'<!DOCTYPE html><html><head></head><body><script>self.__next_f.push([1,{chunk}])</script><div id="__next"></div></body></html>'


def _line(*objects: dict) -> str:
    return "b:" + json.dumps(["$", "div", None, {"bundles": list(objects)}])


class _FakePage:
    """What the scraper asks of a Playwright page: it loads one content and answers one script."""

    def __init__(self, content: str, scripts: list | None = None):
        self._content = content
        self._scripts = scripts or []
        self.goto_calls = 0

    async def goto(self, url, timeout=None):
        self.goto_calls += 1

    async def wait_for_timeout(self, ms):
        pass

    async def content(self):
        return self._content

    async def screenshot(self, path=None):
        pass

    async def evaluate(self, script):
        return self._scripts.pop(0) if self._scripts else []


@pytest.fixture
def scraper(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> etl.HumbleBundleScraper:
    monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(etl, "ensure_directories", lambda dirs: None)
    (tmp_path / "data" / "games" / "debug").mkdir(parents=True)  # the JS fallback writes a debug dump there
    return etl.HumbleBundleScraper()


def test_each_embedded_bundle_becomes_a_record_with_what_the_page_states() -> None:
    first = _bundle("survival-fittest", ["Palworld", "V Rising", "Subnautica: Below Zero"], items_count=12, title="Humble 15th Anniversary - Survival of the Fittest")
    second = _bundle("ai-agents-manning", ["Build a Large Language Model (From Scratch)"], items_count=35, end_date="2026-12-15T19:00:00.000Z", category="books")
    page = _page('a:["$","$L1",null,{"children":"$L2"}]', _line(first, second))

    records = etl.embedded_bundles(page)

    assert [(r["title"], r["link"], r["end_date"], r["items_count"], r["games"], r["type"], r["price"]) for r in records] == [
        (
            "Humble 15th Anniversary - Survival of the Fittest",
            f"{HUMBLE}/games/survival-fittest",
            "2026-12-08T05:00:00+00:00",
            12,
            ["Palworld", "V Rising", "Subnautica: Below Zero"],
            "games",
            "Pay what you want",
        ),
        ("Ai Agents Manning", f"{HUMBLE}/books/ai-agents-manning", "2026-12-15T19:00:00+00:00", 35, ["Build a Large Language Model (From Scratch)"], "books", "Pay what you want"),
    ]


def test_what_the_page_does_not_state_stays_empty() -> None:
    undated = _bundle("undated", ["A", "B"], items_count="lots", end_date=None)
    unreadable = _bundle("unreadable", [], end_date="soon", title="")
    page = _page(_line(undated, unreadable))

    records = etl.embedded_bundles(page)

    assert [(r["title"], r["end_date"], r["items_count"]) for r in records] == [("Undated", None, None), ("Unreadable", None, 11)]


def test_braces_and_quotes_inside_titles_lose_no_bundle() -> None:
    """A brace inside a string, before or after the key, must not read as structure."""
    odd = _bundle("odd-one", ["Close } brace", 'Open { and "quote"'], title='Odd {Bundle} "Edition"} and more')
    plain = _bundle("plain-one", ["B"])
    page = _page(_line(odd, plain))

    assert [(r["title"], r["games"]) for r in etl.embedded_bundles(page)] == [('Odd {Bundle} "Edition"} and more', ["Close } brace", 'Open { and "quote"']), ("Plain One", ["B"])]


def test_an_object_cut_short_is_dropped_not_malformed() -> None:
    whole = _bundle("whole-one", ["A"])
    page = _page('b:["$","div",null,{"bundles":[' + json.dumps(whole) + ',"productType":"humble-bundle","title":"cut here}')

    assert [r["title"] for r in etl.embedded_bundles(page)] == ["Whole One"]


def test_a_bundle_listed_twice_is_kept_once_and_other_products_are_skipped() -> None:
    bundle = _bundle("listed-twice", ["A"])
    other_product = {"productType": "humble-choice", "title": "Choice", "url": "/subscription/choice", "endDate": "2026-12-01T05:00:00.000Z"}
    page = _page(_line(bundle, other_product), _line(bundle))

    assert [r["title"] for r in etl.embedded_bundles(page)] == ["Listed Twice"]


def test_a_page_without_embedded_data_gives_no_bundle() -> None:
    assert etl.embedded_bundles("<html><body><div>the tiles alone</div></body></html>") == []


def test_a_listing_page_is_read_from_its_embedded_data(scraper) -> None:
    page = _FakePage(_page(_line(_bundle("from-data", ["A", "B"], items_count=2))))

    bundles: list[dict] = []
    asyncio.run(scraper._process_single_bundle_url(page, f"{HUMBLE}/games", "games", bundles))

    assert [(b["title"], b["end_date"], b["items_count"]) for b in bundles] == [("From Data", "2026-12-08T05:00:00+00:00", 2)]


def test_a_page_that_embeds_nothing_falls_back_to_its_markup_and_states_no_date(scraper) -> None:
    page = _FakePage('<html><body><div class="tile"><a href="/games/other-bundle">Other Bundle</a></div></body></html>')

    bundles: list[dict] = []
    asyncio.run(scraper._process_single_bundle_url(page, f"{HUMBLE}/games", "games", bundles))

    # the markup fallback titles a bundle from its URL ("Other Bundle" minus the word Bundle), as it always did
    assert [(b["title"], b["link"], b["end_date"], b["games"]) for b in bundles] == [("Other", f"{HUMBLE}/games/other-bundle", None, [])]


def test_the_markup_fallback_states_no_date_it_was_not_given(scraper) -> None:
    soup = BeautifulSoup('<div class="tile"><a href="/games/some-bundle"><span class="title">Some Bundle</span></a><span class="price">Pay What You Want</span></div>', "html.parser")

    record = scraper._extract_bundle_info(soup.select_one("a"), "games")

    assert (record["title"], record["link"], record["end_date"], record["games"]) == ("Some Bundle", f"{HUMBLE}/games/some-bundle", None, [])


def test_the_link_fallback_states_no_date_either(scraper) -> None:
    page = _FakePage("", scripts=[[{"source": "bundleUrls", "data": [{"url": f"{HUMBLE}/games/x-bundle", "title": "X Bundle"}]}]])

    bundles: list[dict] = []
    asyncio.run(scraper._extract_bundles_from_js(page, "all", bundles))

    assert [(b["title"], b["end_date"], b["type"]) for b in bundles] == [("X Bundle", None, "games")]
