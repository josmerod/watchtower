"""Fetches the daily selection of Instant Gaming, the key shop, with the regular price of every game.

The shop publishes the selection at ``https://www.instant-gaming.com/es/ofertas-del-dia/`` ("a new selection
every day, for 24 hours only"): product tiles with the price and the discount label. A tile has no regular
price; the page of each game states it (``window.productModel``), so every tile costs one more request and
the run stops at ``MAX_PRODUCTS``. robots.txt allows these pages; it closes the search pages, which list
every discount, and this module does not read them.

The discount is computed from the two prices and the shop's label is kept beside it. The date until which
the shop honours the price is recorded when the page states it. Prices stay in euros.
"""

import sys
from typing import Any

from src.etl.games.games_tracker_common import (
    SourceError,
    discount_pct,
    fetch_page,
    finish,
    logger,
    parse_ig_product,
    parse_ig_tiles,
    previous_records,
    region_scope,
    split_ig_title,
    stamp_records,
    utc_now_iso,
)

DAILY_DEALS_URL = "https://www.instant-gaming.com/es/ofertas-del-dia/"
MAX_PRODUCTS = 40  # the selection had 35 tiles; one request each
OUTPUT_NAME = "key_shop_deals"


def split_tile_title(title: str) -> tuple[str, str | None]:
    """A tile title as its game and its device: "Little Nightmares III - PC (Steam)" -> ("Little Nightmares III", "PC").

    The shop ends a title with " - " and the device; a PC key adds the store in parentheses.
    """
    name, separator, tail = title.rpartition(" - ")
    if not separator:
        return title.strip(), None
    device = tail.partition("(")[0].strip()
    return name.strip(), device or None


def build_record(tile: dict[str, Any], product: dict[str, Any]) -> dict[str, Any] | None:
    """One deal from its tile and its page; None when there is no real discount or nothing to buy."""
    discount = discount_pct(product["regular_price"], product["price"])
    if discount is None or discount < 1 or not product["in_stock"]:
        return None
    label = tile.get("discount_label")
    if label is not None and abs(label - discount) > 1:
        logger.warning(f"{tile['title']}: computed {discount}% off, the shop labels it {label}% off")
    title, region = split_ig_title(product.get("name") or tile.get("title"))
    device = split_tile_title(tile["title"])[1]
    return {
        "deal_id": f"instant-gaming:{product.get('id')}",
        "title": title,
        "shop": "Instant Gaming",
        "deal_type": "daily_deal",
        "platform": device or "Unknown",
        "store": product.get("store"),
        "region": region,
        "region_scope": region_scope(region),
        "base_price": product["regular_price"],
        "sale_price": product["price"],
        "currency": product.get("currency") or "EUR",
        "discount_pct": discount,
        "source_discount_label": f"-{label}%" if label is not None else None,
        "sale_end": product.get("price_valid_until"),
        "in_stock": True,
        "url": tile.get("url"),
    }


def collect(previous: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    """Read the selection, then the page of each discounted tile."""
    tiles = [tile for tile in parse_ig_tiles(fetch_page(DAILY_DEALS_URL)) if tile["discount_label"] is not None and tile["price"] is not None]
    tiles = tiles[:MAX_PRODUCTS]
    logger.info(f"daily selection: {len(tiles)} discounted tiles")

    records: list[dict[str, Any]] = []
    for tile in tiles:
        product = parse_ig_product(fetch_page(tile["url"]))
        if product is None:
            raise SourceError(f"Instant Gaming: {tile['url']} has no product model")
        record = build_record(tile, product)
        if record:
            records.append(record)
    logger.info(f"daily selection: {len(records)} deals with a regular price and a sale price")
    return stamp_records(records, "deal_id", previous, now_iso)


def main() -> None:
    """Read the selection once; the exit code tells the scheduler whether the file is fresh."""
    logger.info("Starting key shop deals ETL")
    try:
        records = collect(previous_records(OUTPUT_NAME), utc_now_iso())
    except SourceError as e:
        # A shop that refused or did not answer leaves its previous file in place: a failed run, not a quiet one
        logger.error(f"Key shop deals ETL failed: {e}")
        sys.exit(1)
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Key shop deals ETL failed: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)
    finish(records, OUTPUT_NAME, "key shop deals")
    logger.info("Key shop deals ETL completed")


if __name__ == "__main__":
    main()
