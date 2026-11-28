"""Fetches the gaming gift cards sold under their face value: Nintendo eShop, PlayStation Store and Xbox Live.

Two shops publish their gift-card shelves to any visitor, and their robots.txt allows these pages:

- Eneba: ``https://www.eneba.com/es/store/<category>`` (20 cards a page; the region is on each card and the
  page links to the next one);
- Instant Gaming: ``https://www.instant-gaming.com/es/<platform>/tarjetas-regalo/`` (the cards of a platform),
  then the page of each card for its region and its stock.

A gift card is worth what it says on it, so the base price is the face value in the card's name and the
discount is computed from it; the regular price the shop lists is kept beside it. In-game currency shares
the same shelves and is left out. Prices stay in euros, the currency of both shops. No shop gives an end
date for a card price, so none is recorded.
"""

import html
import json
import re
import sys
from typing import Any

from src.etl.games.games_tracker_common import (
    IG_BASE,
    SourceError,
    discount_pct,
    fetch_page,
    finish,
    logger,
    parse_ig_product,
    parse_ig_tiles,
    previous_records,
    region_label,
    region_scope,
    split_ig_title,
    stamp_records,
    to_amount,
    utc_now_iso,
)

OUTPUT_NAME = "gift_card_deals"

ENEBA_BASE = "https://www.eneba.com"
# The largest of the three shelves has 43 products
ENEBA_CATEGORIES = ("nintendo-gift-cards", "psn-gift-cards", "xbox-gift-cards")
ENEBA_MAX_PAGES = 3
ENEBA_PLATFORMS = {"Nintendo": "Nintendo eShop", "PSN": "PlayStation Store", "Xbox Live": "Xbox Live"}
_ENEBA_PRICE = 'price({"currency":"EUR"})'
_ENEBA_MSRP = 'msrp({"currency":"EUR"})'

IG_CATEGORIES = (("nintendo", "Nintendo eShop"), ("playstation", "PlayStation Store"), ("xbox", "Xbox Live"))

_APOLLO_SCRIPT = re.compile(r'<script id="__APOLLO_STATE__"[^>]*>(.*?)</script>', re.S)
_ANCHOR = re.compile(r"<a\b([^>]*)>")
_NEXT_LINK = re.compile(r'<a\b[^>]*\brel="next"[^>]*>')
# "Tarjeta Nintendo eShop 50 EUR Key SPAIN", "Tarjeta regalo de PlayStation Store 20€ - España"
_FACE_VALUE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:EUR|€)", re.I)
_CARD_WORD = re.compile(r"tarjeta|card|saldo|gift|voucher", re.I)


def face_value_eur(name: str) -> float | None:
    """The euros a gift card is worth, from its name; None when the name is not a card with a value."""
    match = _FACE_VALUE.search(name)
    if match is None or not _CARD_WORD.search(name):
        return None
    return to_amount(match.group(1))


def _cents(block: Any) -> float | None:
    """A Eneba money block (cents) as euros."""
    amount = to_amount(block.get("amount")) if isinstance(block, dict) else None
    return amount / 100 if amount is not None else None


def _product_links(page: str) -> dict[str, str]:
    """Card name -> product path, from the anchors of the page (the path is not derived from the card's id)."""
    links: dict[str, str] = {}
    for attrs in _ANCHOR.findall(page):
        title = re.search(r'\btitle="([^"]*)"', attrs)
        href = re.search(r'\bhref="([^"]*)"', attrs)
        if title and href and href.group(1).startswith("/es/") and "/store/" not in href.group(1):
            links[html.unescape(title.group(1))] = html.unescape(href.group(1))
    return links


def build_eneba_card(product: dict[str, Any], auction: dict[str, Any], href: str | None) -> dict[str, Any] | None:
    """One discounted card from its product and the cheapest offer; None for anything that is not one."""
    kind = product.get("type")
    if not isinstance(kind, dict) or kind.get("value") != "GIFTCARD":
        return None  # a subscription or a game points pack
    name = str(product.get("name") or "")
    face_value = face_value_eur(name)
    price = _cents(auction.get(_ENEBA_PRICE))
    discount = discount_pct(face_value, price)
    if face_value is None or price is None or discount is None or discount < 1:
        return None  # no face value in the name, no offer, or not a whole percent under what it is worth
    regions = product.get("regions") if isinstance(product.get("regions"), list) else []
    code = regions[0].get("code") if regions and isinstance(regions[0], dict) else None
    drm = (product.get("drm") or {}).get("name") if isinstance(product.get("drm"), dict) else None
    label = auction.get("msrpDiscountPercent")
    region = region_label(code)
    return {
        "card_id": f"eneba:{product.get('shortId') or href}",
        "title": name,
        "shop": "Eneba",
        "platform": ENEBA_PLATFORMS.get(drm or "", "Unknown"),
        "region": region,
        "region_scope": region_scope(region),
        "base_price": face_value,
        "base_source": "face_value",
        "regular_price": _cents(auction.get(_ENEBA_MSRP)),
        "sale_price": price,
        "currency": (auction.get(_ENEBA_PRICE) or {}).get("currency") or "EUR",
        "discount_pct": discount,
        "source_discount_label": f"-{label}%" if label is not None else None,
        "in_stock": bool(auction.get("isInStock")),
        "url": f"{ENEBA_BASE}{href}" if href else None,
    }


def parse_eneba_page(page: str) -> tuple[list[dict[str, Any]], str | None]:
    """The discounted cards of a shelf page and the address of the next page, if the page links to one."""
    match = _APOLLO_SCRIPT.search(page)
    if match is None:
        raise SourceError("Eneba: no embedded state in the page")
    try:
        state = json.loads(match.group(1))
    except ValueError as exc:
        raise SourceError(f"Eneba: embedded state is not JSON ({type(exc).__name__})") from exc
    root = state.get("ROOT_QUERY") if isinstance(state, dict) else None
    search = next((value for key, value in root.items() if key.startswith("search(") and isinstance(value, dict)), None) if isinstance(root, dict) else None
    edges = ((search or {}).get("results") or {}).get("edges") or []
    links = _product_links(page)
    cards = []
    for edge in edges if isinstance(edges, list) else []:
        node = edge.get("node", {}).get("__ref") if isinstance(edge, dict) else None
        product = state.get(node) if isinstance(node, str) else None
        if not isinstance(product, dict):
            continue
        auction_ref = (product.get("cheapestAuction") or {}).get("__ref")
        auction = state.get(auction_ref) if isinstance(auction_ref, str) else {}
        card = build_eneba_card(product, auction if isinstance(auction, dict) else {}, links.get(str(product.get("name"))))
        if card:
            cards.append(card)
    next_link = _NEXT_LINK.search(page)
    href = re.search(r'href="([^"]+)"', next_link.group(0)) if next_link else None
    return cards, html.unescape(href.group(1)) if href else None


def collect_eneba() -> list[dict[str, Any]]:
    """Read the first pages of each shelf until the page has no next one."""
    cards: list[dict[str, Any]] = []
    for category in ENEBA_CATEGORIES:
        next_url: str | None = f"{ENEBA_BASE}/es/store/{category}"
        category_cards = 0
        for _ in range(ENEBA_MAX_PAGES):
            if next_url is None:
                break
            page_cards, next_url = parse_eneba_page(fetch_page(next_url))
            cards.extend(page_cards)
            category_cards += len(page_cards)
        logger.info(f"Eneba {category}: {category_cards} cards under their face value")
    return cards


def build_ig_card(tile: dict[str, Any], product: dict[str, Any], face_value: float, shelf: str) -> dict[str, Any] | None:
    """One discounted card from its tile and its page; None when it cannot be bought under its face value."""
    price = product.get("price") if product.get("price") is not None else tile.get("price")
    discount = discount_pct(face_value, price)
    if discount is None or discount < 1 or not product.get("in_stock"):
        return None
    title, region = split_ig_title(product.get("name") or tile.get("title"))
    label = tile.get("discount_label")
    if label is not None and abs(label - discount) > 1:
        # The shelf is cached and its label lags: the page of the card has the price of now
        logger.info(f"{tile['title']}: computed {discount}% off, the shelf labels it {label}% off")
    return {
        "card_id": f"instant-gaming:{product.get('id')}",
        "title": title,
        "shop": "Instant Gaming",
        "platform": shelf,  # the shelf says the platform; the page names the store the key redeems on ("Microsoft Store")
        "region": region,
        "region_scope": region_scope(region),
        "base_price": face_value,
        "base_source": "face_value",
        "regular_price": product.get("regular_price"),
        "sale_price": price,
        "currency": product.get("currency") or "EUR",
        "discount_pct": discount,
        "source_discount_label": f"-{label}%" if label is not None else None,
        "in_stock": True,
        "url": tile.get("url"),
    }


def collect_instant_gaming() -> list[dict[str, Any]]:
    """Read the gift-card shelf of each platform, then the page of every card with a face value."""
    cards: list[dict[str, Any]] = []
    for slug, shelf in IG_CATEGORIES:
        shelf_cards = 0
        for tile in parse_ig_tiles(fetch_page(f"{IG_BASE}/es/{slug}/tarjetas-regalo/")):
            face_value = face_value_eur(tile["title"])
            if face_value is None or tile.get("price") is None:
                continue  # in-game currency and add-ons share the shelf; a tile without a price is out of stock
            product = parse_ig_product(fetch_page(tile["url"]))
            if product is None:
                raise SourceError(f"Instant Gaming: {tile['url']} has no product model")
            card = build_ig_card(tile, product, face_value, shelf)
            if card:
                cards.append(card)
                shelf_cards += 1
        logger.info(f"Instant Gaming {slug}: {shelf_cards} cards under their face value")
    return cards


def collect(previous: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    """Read both shops once."""
    # A card that moves from one page to the next between two requests comes back twice; the first one stays
    unique: dict[str, dict[str, Any]] = {}
    for card in collect_eneba() + collect_instant_gaming():
        unique.setdefault(str(card["card_id"]), card)
    return stamp_records(list(unique.values()), "card_id", previous, now_iso)


def main() -> None:
    """Read both shops once; the exit code tells the scheduler whether the file is fresh."""
    logger.info("Starting gift card deals ETL")
    try:
        records = collect(previous_records(OUTPUT_NAME), utc_now_iso())
    except SourceError as e:
        # A shop that refused or did not answer leaves the previous file in place: a failed run, not a quiet one
        logger.error(f"Gift card deals ETL failed: {e}")
        sys.exit(1)
    except Exception as e:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Gift card deals ETL failed: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)
    finish(records, OUTPUT_NAME, "gift cards under their face value")
    logger.info("Gift card deals ETL completed")


if __name__ == "__main__":
    main()
