"""Fetches the games on sale at the Japanese Nintendo eShop with their regular price (My Nintendo Store JP).

The store publishes two things that together make a record:

- the sale listing, ``https://store-jp.nintendo.com/list/software/?isSale=true&softType=TITLE&srule=most-popular&page=N``
  (18 titles a page, the most popular first; the regular price is not in it);
- the price API, ``https://api.ec.nintendo.com/v1/price?country=JP&lang=ja&ids=<nsuid>,<nsuid>...``
  (regular price, sale price and the sale window of up to 50 titles).

Both answer an anonymous client, and the store's robots.txt allows every page to crawlers. Prices stay in
yen: nothing in this repository converts currency. The discount is computed from the two prices and the
store's own label ("25%OFF") is kept beside it for comparison.
"""

import json
import re
import sys
from typing import Any

from src.etl.games.games_tracker_common import (
    SourceError,
    discount_pct,
    fetch_page,
    finish,
    logger,
    previous_records,
    stamp_records,
    to_amount,
    utc_now_iso,
)

LISTING_URL = "https://store-jp.nintendo.com/list/software/"
LISTING_PARAMS = "isSale=true&softType=TITLE&srule=most-popular"
# The 180 most popular of about 2,260 titles on sale. The whole listing is 126 pages and 46 price calls a run.
LISTING_PAGES = 10
PRICE_URL = "https://api.ec.nintendo.com/v1/price"
PRICE_BATCH = 50  # from the 51st id on the API answers 400 "Over ids limit number"
SHOP = "My Nintendo Store JP"
CURRENCY = "JPY"
OUTPUT_NAME = "eshop_jp_deals"

_MOBIFY_SCRIPT = re.compile(r'<script id="mobify-data" type="application/json">(.*?)</script>', re.S)
_LABEL_PERCENT = re.compile(r"(\d+)\s*%")


def parse_listing_page(html: str) -> list[dict[str, Any]]:
    """The tiles of a listing page: the state the store ships inside its HTML.

    Each tile keeps the nsuid, the title, the platform, the sale price and the discount label the store shows.
    """
    match = _MOBIFY_SCRIPT.search(html)
    if match is None:
        raise SourceError("sale listing: no embedded state in the page")
    try:
        state = json.loads(match.group(1))
        queries = state["__PRELOADED_STATE__"]["__reactQuery"]["queries"]
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceError(f"sale listing: unexpected embedded state ({type(exc).__name__})") from exc
    for query in queries if isinstance(queries, list) else []:
        data = query.get("state", {}).get("data") if isinstance(query, dict) else None
        if isinstance(data, dict) and isinstance(data.get("resultProducts"), list):
            tiles = [tile for tile in data["resultProducts"] if isinstance(tile, dict) and tile.get("id")]
            logger.debug(f"sale listing: page {data.get('pagingInfo', {}).get('currentPage')}: {len(tiles)} titles")
            return tiles
    raise SourceError("sale listing: the embedded state has no product list")


def platform_of(tile: dict[str, Any]) -> str:
    """The console a title runs on, from the store's own classification.

    ``BEE`` is native Nintendo Switch 2 software. ``HAC`` is Nintendo Switch software; when the store also
    flags ``includesSuperPlatform``, the title is the "Nintendo Switch 2 Edition" of a Switch game.
    """
    code = tile.get("productClassCode")
    if code == "BEE":
        return "Nintendo Switch 2"
    if code == "HAC":
        return "Nintendo Switch 2 Edition" if tile.get("includesSuperPlatform") else "Nintendo Switch"
    return "Unknown"


def _yen(value: Any) -> int | None:
    """A price in whole yen: the currency has no minor unit and the API states whole yen."""
    amount = to_amount(value)
    return int(amount) if amount is not None and amount > 0 else None


def parse_prices(payload: Any) -> dict[str, dict[str, Any]]:
    """The price API answer as ``nsuid -> prices and sale window``; a title without a sale price stays out."""
    prices: dict[str, dict[str, Any]] = {}
    entries = payload.get("prices") if isinstance(payload, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        discount = entry.get("discount_price") if isinstance(entry, dict) else None
        regular = entry.get("regular_price") if isinstance(entry, dict) else None
        if not isinstance(discount, dict) or not isinstance(regular, dict):
            continue
        prices[str(entry.get("title_id"))] = {
            "base_price": _yen(regular.get("raw_value")),
            "sale_price": _yen(discount.get("raw_value")),
            "sale_start": discount.get("start_datetime"),
            "sale_end": discount.get("end_datetime"),
            "sales_status": entry.get("sales_status"),
        }
    return prices


def build_records(tiles: list[dict[str, Any]], prices: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per title that the price API reports on sale; the discount is computed, the label kept beside it."""
    records: list[dict[str, Any]] = []
    for tile in tiles:
        price = prices.get(str(tile.get("id")))
        if price is None:
            continue
        discount = discount_pct(price["base_price"], price["sale_price"])
        if discount is None:
            continue
        label_match = _LABEL_PERCENT.search(str(tile.get("saleLabel") or ""))
        # The store truncates its label (72%OFF for 299 out of 1098 yen); one point of difference is that
        if label_match and abs(int(label_match.group(1)) - discount) > 1:
            logger.warning(f"{tile.get('name')}: computed {discount}% off, the store labels it {label_match.group(1)}% off")
        nsuid = str(tile["id"])
        records.append(
            {
                "nsuid": nsuid,
                "title": tile.get("name"),
                "shop": SHOP,
                "platform": platform_of(tile),
                "base_price": price["base_price"],
                "sale_price": price["sale_price"],
                "currency": CURRENCY,
                "discount_pct": discount,
                "source_discount_label": tile.get("saleLabel"),
                "sale_start": price["sale_start"],
                "sale_end": price["sale_end"],
                # "onsale" or "preorder": the store discounts some titles before their release
                "sales_status": price["sales_status"],
                "manufacturer": tile.get("manufacturerName"),
                "url": f"https://store-jp.nintendo.com/item/software/D{nsuid}",
            }
        )
    return records


def collect(previous: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    """Read the first ``LISTING_PAGES`` pages of the sale listing and price their titles in batches."""
    # The same nsuid can come back twice; a dict keeps the first tile of each
    tiles: dict[str, dict[str, Any]] = {}
    pages = 0
    for page in range(1, LISTING_PAGES + 1):
        page_tiles = parse_listing_page(fetch_page(f"{LISTING_URL}?{LISTING_PARAMS}&page={page}"))
        if not page_tiles:
            logger.info(f"sale listing: page {page} has no titles, stopping there")
            break
        pages = page
        for tile in page_tiles:
            tiles.setdefault(str(tile["id"]), tile)
    ids = list(tiles)
    logger.info(f"sale listing: {len(ids)} titles on sale in {pages} pages")

    prices: dict[str, dict[str, Any]] = {}
    for start in range(0, len(ids), PRICE_BATCH):
        batch = ",".join(ids[start : start + PRICE_BATCH])
        prices.update(parse_prices(json.loads(fetch_page(f"{PRICE_URL}?country=JP&lang=ja&ids={batch}"))))
    records = build_records(list(tiles.values()), prices)
    logger.info(f"price API: {len(prices)} titles with a sale price, {len(records)} with a discount")
    return stamp_records(records, "nsuid", previous, now_iso)


def main() -> None:
    """Read the store once; the exit code tells the scheduler whether the file is fresh."""
    logger.info("Starting eShop JP sales ETL")
    try:
        records = collect(previous_records(OUTPUT_NAME), utc_now_iso())
    except SourceError as e:
        # A store that refused or did not answer leaves its previous file in place: a failed run, not a quiet one
        logger.error(f"eShop JP sales ETL failed: {e}")
        sys.exit(1)
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"eShop JP sales ETL failed: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)
    finish(records, OUTPUT_NAME, "games on sale")
    logger.info("eShop JP sales ETL completed")


if __name__ == "__main__":
    main()
