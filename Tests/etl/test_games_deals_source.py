"""The deals ETL names itself to the feeds and fails when one is refused (T-192).

IsThereAnyDeal answered 403 to the default Python client from 2026-07-22 on. The ETL swallowed it, logged
"completed successfully" and exited 0, so deals.json and bundles.json kept July data for four months while the
scheduler counted the script as a success. The giveaways feed had moved to another address meanwhile and was
written as an empty list every cycle, the same way. Fixtures only: the feeds are strings built here and every
file goes to tmp_path, never data/.
"""

import json
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.etl.games import games_get_deals as etl

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _pub(moment: datetime) -> str:
    """An RFC-2822 date in English whatever the locale of the machine running the tests."""
    return f"{_DAYS[moment.weekday()]}, {moment.day:02d} {_MONTHS[moment.month - 1]} {moment.year} {moment:%H:%M:%S} +0000"


def _rss(items: list[str]) -> bytes:
    head = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>test</title><link>https://example.invalid/</link><description>test</description>'
    return (head + "".join(items) + "</channel></rss>").encode()


def _deal(title: str, price: str, discount: int, store: str, days_ago: int = 0) -> str:
    published = _pub(datetime.now(timezone.utc) - timedelta(days=days_ago))
    return (
        "<item>"
        f"<title>{title}</title><link>https://example.invalid/d/{title}</link><pubDate>{published}</pubDate>"
        f'<description><![CDATA[ <b>{price} €</b> (<i>-{discount}%</i>) on <a href="https://itad.link/x/" target="_blank">{store}</a><br /> ]]></description>'
        "</item>"
    )


def _bundle(title: str, tiers: list[tuple[str, str]], games: list[str], days_ago: int = 0) -> str:
    published = _pub(datetime.now(timezone.utc) - timedelta(days=days_ago))
    prices = "".join(f"<b>Tier {i + 1}</b><br /><div>Price: {price} €</div>" for i, (_tier, price) in enumerate(tiers))
    links = "".join(f'<a href="https://isthereanydeal.com/game/{game}/info/">{game}</a>' for game in games)
    return f"<item><title>{title}</title><link>https://example.invalid/b/{title}</link><pubDate>{published}</pubDate><description><![CDATA[ {prices}{links} ]]></description></item>"


def _giveaway(title: str, hours_left: float) -> str:
    """Shaped like the feed: the game, when it expires, then a bar and the store link."""
    now = datetime.now(timezone.utc)
    return (
        f"<item><title>{title}</title><link>https://example.invalid/g/{title}</link><pubDate>{_pub(now - timedelta(hours=1))}</pubDate>"
        f'<description><![CDATA[ <a href="https://isthereanydeal.com/game/{title}/info/">{title}</a><br /><br /> expires on {_pub(now + timedelta(hours=hours_left))} | <a href=https://example.invalid/x>go to giveaway</a> ]]></description></item>'
    )


LIVE = {
    etl.DEALS_RSS: _rss([_deal("Cheap", "0,47", 93, "Fanatical"), _deal("Pricey", "10,80", 6, "Steam")]),
    etl.BUNDLES_RSS: _rss([_bundle("Two tiers", [("one", "4,57"), ("two", "12,30")], ["Alpha", "Beta"])]),
    etl.GIVEAWAYS_RSS: _rss([_giveaway("Live one", 48), _giveaway("Gone one", -48)]),
}


@pytest.fixture
def feeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A temp project root and a stand-in for the network: ``feeds.bodies`` is what each URL answers."""
    (tmp_path / "data" / "games").mkdir(parents=True)
    monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr(etl, "ensure_directories", lambda dirs: None)
    calls: list[tuple[str, dict[str, str] | None]] = []
    state = {"bodies": dict(LIVE), "calls": calls, "refused": set()}

    def fake_fetch(url: str, *, headers: dict[str, str] | None = None, **_kw) -> bytes:
        calls.append((url, headers))
        if url in state["refused"]:
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        return state["bodies"][url]

    monkeypatch.setattr(etl, "fetch_with_retry", fake_fetch)
    return state


def _records(tmp_path: Path, name: str) -> list[dict]:
    return json.loads((tmp_path / "data" / "games" / f"{name}.json").read_text(encoding="utf-8"))


def test_every_feed_is_asked_for_with_the_project_name(feeds, tmp_path: Path) -> None:
    etl.main()

    assert [url for url, _headers in feeds["calls"]] == [etl.DEALS_RSS, etl.BUNDLES_RSS, etl.GIVEAWAYS_RSS]
    assert all((headers or {}).get("User-Agent", "").startswith("Watchtower/") for _url, headers in feeds["calls"])


def test_a_read_feed_rewrites_the_three_files(feeds, tmp_path: Path) -> None:
    etl.main()

    deals = _records(tmp_path, "deals")
    assert [(deal["title"], deal["price"], deal["discount"], deal["store"], deal["currency"]) for deal in deals] == [
        ("Cheap", 0.47, "-93%", "Fanatical", "EUR"),
        ("Pricey", 10.8, "-6%", "Steam", "EUR"),
    ]
    assert all(deal["published"].endswith("Z") for deal in deals)  # ISO in UTC: the form the dashboard dates

    bundles = _records(tmp_path, "bundles")
    assert [(bundle["title"], bundle["price"], bundle["games"], bundle["currency"]) for bundle in bundles] == [("Two tiers", 12.3, ["Alpha", "Beta"], "EUR")]

    assert [giveaway["title"] for giveaway in _records(tmp_path, "giveaways")] == ["Live one"]  # the expired one is skipped
    assert (tmp_path / "data" / "games" / "giveaways.csv").exists()
    assert not list((tmp_path / "data" / "games").glob("*.partial"))


def test_a_refused_feed_fails_the_run_and_keeps_the_previous_files(feeds, tmp_path: Path) -> None:
    games = tmp_path / "data" / "games"
    for name in ("deals", "bundles"):
        (games / f"{name}.json").write_text('[{"title": "the previous file"}]', encoding="utf-8")
    feeds["refused"] = set(LIVE)

    with pytest.raises(SystemExit) as excinfo:
        etl.main()

    assert excinfo.value.code == 1  # the scheduler counts a dead source as failed
    assert (games / "deals.json").read_text(encoding="utf-8") == '[{"title": "the previous file"}]'
    assert (games / "bundles.json").read_text(encoding="utf-8") == '[{"title": "the previous file"}]'
    assert not list(games.glob("*.partial"))


def test_one_refused_feed_fails_the_run_but_the_others_are_saved(feeds, tmp_path: Path) -> None:
    feeds["refused"] = {etl.BUNDLES_RSS}

    with pytest.raises(SystemExit) as excinfo:
        etl.main()

    assert excinfo.value.code == 1
    assert [deal["title"] for deal in _records(tmp_path, "deals")] == ["Cheap", "Pricey"]
    assert [giveaway["title"] for giveaway in _records(tmp_path, "giveaways")] == ["Live one"]


def test_a_deals_feed_with_no_deals_is_a_failed_run(feeds) -> None:
    feeds["bodies"][etl.DEALS_RSS] = _rss([])

    with pytest.raises(SystemExit) as excinfo:
        etl.main()

    assert excinfo.value.code == 1


def test_no_live_giveaway_is_not_a_failure(feeds, tmp_path: Path) -> None:
    feeds["bodies"][etl.GIVEAWAYS_RSS] = _rss([_giveaway("Gone one", -1)])

    etl.main()  # no SystemExit

    assert (tmp_path / "data" / "games" / "giveaways.json").read_text(encoding="utf-8") == "[]"
