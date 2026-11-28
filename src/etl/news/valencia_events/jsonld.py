"""schema.org helpers shared by the sources that embed JSON-LD (Meetup, Eventbrite)."""

import json
from collections.abc import Iterator
from typing import Any

from bs4 import BeautifulSoup


def iter_jsonld_items(soup: BeautifulSoup) -> Iterator[dict[str, Any]]:
    """Yield every object embedded in the page's application/ld+json blocks.

    Handles blocks holding a single object, an array of objects, or an object
    with a @graph. Malformed blocks are skipped silently.

    Args:
        soup: Parsed page.

    Yields:
        Individual schema.org node dictionaries.
    """
    for block in soup.find_all("script", type="application/ld+json"):
        raw = block.string or block.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        queue = data if isinstance(data, list) else [data]
        for node in queue:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                yield from (item for item in graph if isinstance(item, dict))
            else:
                yield node


def jsonld_location(node: dict[str, Any]) -> str:
    """Best-effort human-readable location from a schema.org event node.

    Args:
        node: schema.org Event (or ItemList item) dictionary.

    Returns:
        "street, city" (or whichever parts exist), "" when no location.
    """
    location = node.get("location")
    if isinstance(location, str):
        return location
    if not isinstance(location, dict):
        return ""
    address = location.get("address")
    if isinstance(address, str):
        return address
    if isinstance(address, dict):
        parts = [address.get("streetAddress"), address.get("addressLocality")]
        return ", ".join(str(part) for part in parts if part)
    return str(location.get("name") or "")


def jsonld_venue(node: dict[str, Any]) -> str:
    """Venue name from a schema.org event node's location.

    Args:
        node: schema.org Event (or ItemList item) dictionary.

    Returns:
        The Place's ``name`` (or the location string itself when the source
        emits a bare string), "" when the location carries no name — online
        events with a VirtualLocation intentionally yield "".
    """
    location = node.get("location")
    if isinstance(location, str):
        return location.strip()
    if not isinstance(location, dict):
        return ""
    return str(location.get("name") or "").strip()


def jsonld_is_online(node: dict[str, Any]) -> bool:
    """True when the node's location is a VirtualLocation and it names no physical place."""
    location = node.get("location")
    if isinstance(location, list):
        return bool(location) and all(isinstance(entry, dict) and entry.get("@type") == "VirtualLocation" for entry in location)
    return isinstance(location, dict) and location.get("@type") == "VirtualLocation"


def parse_amount(raw: Any) -> float | None:
    """Parse a non-negative monetary amount from a JSON-LD price field.

    Args:
        raw: Raw value; numbers and point/comma decimal strings are accepted.

    Returns:
        The amount as float, or None when missing/negative/unparsable.
    """
    text = str(raw if raw is not None else "").strip().replace(",", ".")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value >= 0 else None


def format_amount(value: float) -> str:
    """Format an amount Spanish-style without currency: "12" or "12,50"."""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".replace(".", ",")


def price_pair(amount: float, suffix: str) -> tuple[str, bool]:
    """(price_info, is_free) for one exact amount — exactly zero means free."""
    if amount == 0:
        return "Gratis", True
    return f"{format_amount(amount)} {suffix}", False


def jsonld_offers(node: dict[str, Any]) -> dict[str, Any]:
    """Extract ticket price information from a schema.org event node's offers.

    Handles the shapes seen in the wild: a single Offer (``price``), an
    AggregateOffer (``lowPrice``/``highPrice``), a nested priceSpecification
    (``minPrice``/``maxPrice``) and lists of those. ``is_free`` is True only
    when the full price is exactly zero — a range starting at 0 still has
    paid tiers and counts as paid. When several offers exist the first one
    carrying a usable price wins.

    Args:
        node: schema.org Event (or ItemList item) dictionary.

    Returns:
        Dict that may carry ``price_info`` (str), ``is_free`` (bool),
        ``offers_availability`` (str, short form) and ``offers_url`` (str);
        empty when the node exposes no usable offers.
    """
    offers = node.get("offers")
    if isinstance(offers, dict):
        offer_list: list[dict[str, Any]] = [offers]
    elif isinstance(offers, list):
        offer_list = [entry for entry in offers if isinstance(entry, dict)]
    else:
        offer_list = []

    result: dict[str, Any] = {}
    for offer in offer_list:
        spec = offer.get("priceSpecification")
        spec = spec if isinstance(spec, dict) else {}
        currency = str(offer.get("priceCurrency") or spec.get("priceCurrency") or "").strip().upper()
        suffix = "€" if currency in ("", "EUR") else currency

        single = parse_amount(offer.get("price"))
        low = parse_amount(offer.get("lowPrice"))
        high = parse_amount(offer.get("highPrice"))
        if single is None and low is None:
            low = parse_amount(spec.get("minPrice"))
        if single is None and high is None:
            high = parse_amount(spec.get("maxPrice"))

        if single is not None:
            price_info, is_free = price_pair(single, suffix)
        elif low is not None and high is not None:
            price_info, is_free = price_pair(low, suffix) if low == high else (f"{format_amount(low)} – {format_amount(high)} {suffix}", False)
        elif low is not None:
            price_info, is_free = f"Desde {format_amount(low)} {suffix}", False
        elif high is not None:
            price_info, is_free = price_pair(high, suffix)
        else:
            continue  # no usable price in this offer — try the next one

        result["price_info"] = price_info
        result["is_free"] = is_free
        availability = str(offer.get("availability") or "")
        if availability:
            result["offers_availability"] = availability.rsplit("/", 1)[-1]
        url = str(offer.get("url") or "")
        if url:
            result["offers_url"] = url
        break
    return result
