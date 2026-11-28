"""Shared helpers of the game price trackers: eShop JP sales, key-shop deals and gift cards.

The trackers read pages that their sites serve to any anonymous visitor, one request per address and run.
``fetch_page`` does not retry: when a site refuses (403, 429, any other error status) the run stops and
reports it, and the file of the previous run stays where the dashboard reads it.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

logger = get_logger("Games_Trackers_ETL")

# The sites answer 403 to the default client of the library; this one names the app, as games_get_deals.py does
HEADERS = {
    "User-Agent": "Watchtower/1.0 (https://github.com/josmerod/watchtower)",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,ja;q=0.8,en;q=0.7",
}
REQUEST_TIMEOUT = 30
PAUSE_SECONDS = 1.0  # between two requests


class SourceError(Exception):
    """A source could not be read: the run gives up and the previous file stays."""


class SourceRefused(SourceError):
    """The site answered with an error status. Asking again is not an option: the run reports it."""


def fetch_page(url: str, pause: float = PAUSE_SECONDS) -> str:
    """GET *url* once and return the body as UTF-8 text. Nothing here retries.

    Raises:
        SourceRefused: the status is an error (403 and 429 included).
        SourceError: there was no answer (connection error, timeout).
    """
    time.sleep(pause)
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise SourceError(f"{url}: no answer ({type(exc).__name__})") from exc
    if response.status_code >= 400:
        raise SourceRefused(f"{url}: HTTP {response.status_code}")
    return response.content.decode("utf-8", errors="replace")


def to_amount(value: Any) -> float | None:
    """A price as a number: 4931, "4100", "45.39", "45,39 €", "1.234,56"; None when it is none of these.

    A lone comma followed by two digits at most is a decimal separator; otherwise it groups thousands.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    text = re.sub(r"[^\d.,]", "", str(value).replace("\xa0", ""))
    if not re.fullmatch(r"\d+(?:[.,]\d+)*", text):
        return None
    if "," in text and "." in text:
        decimal_mark = "," if text.rfind(",") > text.rfind(".") else "."
        text = text.replace("." if decimal_mark == "," else ",", "").replace(decimal_mark, ".")
    elif "," in text:
        head, _, tail = text.partition(",")
        text = f"{head}.{tail}" if len(tail) <= 2 else text.replace(",", "")
    return float(text)


def discount_pct(base: float | None, sale: float | None) -> int | None:
    """Percent off *base* at *sale*, rounded half up; None without two positive prices or without a discount."""
    if base is None or sale is None or base <= 0 or sale <= 0 or sale >= base:
        return None
    return math.floor((1 - sale / base) * 100 + 0.5)


# --- Regions ---
# The region a key or a gift card is sold for, as the trackers record it: one English label whatever the source
# called it (Eneba says "España", Instant Gaming "Europe" or "ES"). What matters is whether a Spanish account
# can redeem it.
_REGION_LABELS = {
    "spain": "Spain",
    "españa": "Spain",
    "espana": "Spain",
    "es": "Spain",
    "europe": "Europe",
    "europa": "Europe",
    "emea": "Europe",  # the codes Eneba uses are spain, europe, emea, global and row
    "global": "Global",
    "worldwide": "Global",
    "row": "Rest of world",
    "rest of world": "Rest of world",
    "united states": "United States",
    "estados unidos": "United States",
    "usa": "United States",
    "us": "United States",
    "united kingdom": "United Kingdom",
    "reino unido": "United Kingdom",
    "uk": "United Kingdom",
    "japan": "Japan",
    "japón": "Japan",
    "jp": "Japan",
    "germany": "Germany",
    "alemania": "Germany",
    "france": "France",
    "italy": "Italy",
    "canada": "Canada",
    "australia": "Australia",
}
_REGION_SCOPES = {"spain": "spain", "europe": "europe", "global": "global", "rest of world": "global"}


def region_label(raw: Any) -> str | None:
    """The region in English ("Spain", "Europe", "Global"), the source's own words when unknown, None when absent."""
    if not raw or not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    return _REGION_LABELS.get(text.lower(), text)


def region_scope(label: str | None) -> str:
    """ "spain", "europe", "global", "other" or "unknown": a Spanish account redeems the first three."""
    if not label:
        return "unknown"
    return _REGION_SCOPES.get(label.lower(), "other")


# --- Records ---
def utc_now_iso(now: datetime | None = None) -> str:
    """The moment of the run in ISO 8601, UTC."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


def tracker_paths(name: str) -> tuple[str, str]:
    """The JSON and the CSV a tracker writes under data/games/."""
    folder = os.path.join(get_project_root(), "data/games")
    return os.path.join(folder, f"{name}.json"), os.path.join(folder, f"{name}.csv")


def previous_records(name: str) -> list[dict[str, Any]]:
    """The records of the previous run, [] when the file does not exist or cannot be read."""
    json_path, _ = tracker_paths(name)
    try:
        with open(json_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def stamp_records(records: list[dict[str, Any]], key_field: str, previous: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    """Add ``first_detected_at`` (kept from *previous* for a record already seen) and ``last_seen_at``."""
    first_seen = {str(row[key_field]): row["first_detected_at"] for row in previous if row.get(key_field) is not None and row.get("first_detected_at")}
    for row in records:
        row["first_detected_at"] = first_seen.get(str(row.get(key_field)), now_iso)
        row["last_seen_at"] = now_iso
    return records


def save_frame(frame: pd.DataFrame, name: str) -> bool:
    """Write *frame* to data/games/<name>.json and .csv; False when a write failed.

    The JSON is replaced in one step, so a failed write leaves the previous file whole for the dashboard.
    """
    json_path, csv_path = tracker_paths(name)
    partial_path = f"{json_path}.partial"
    try:
        ensure_directories(["data/games"])
        frame.to_json(partial_path, orient="records", date_format="iso")
        os.replace(partial_path, json_path)
        frame.to_csv(csv_path, index=False, sep="|", date_format="%Y-%m-%dT%H:%M:%SZ")
    except OSError as e:
        logger.error(f"Error saving {name} data: {e}", exc_info=True)
        return False
    except Exception as e:  # broad by design: pandas DataFrame/CSV serialization of scraped data
        logger.error(f"An unexpected error occurred while saving {name}: {e}", exc_info=True)
        return False
    logger.info(f"{name} saved to {json_path} and {csv_path}")
    return True


def finish(records: list[dict[str, Any]], name: str, what: str) -> None:
    """Save the records of a run, the best discount first, or keep the last good file when there are none.

    Exits with 1 when the write fails: the exit code tells the scheduler whether the run produced a file.
    """
    if not records:
        logger.warning(f"No {what} to record: the previous {name}.json stays as it was")
        return
    frame = pd.DataFrame(records)
    if not save_frame(frame.sort_values("discount_pct", ascending=False, kind="stable"), name):
        sys.exit(1)
    logger.info(f"{name}: {len(frame)} records")


# --- Instant Gaming ---
# The shop renders its shelves as product tiles and states the facts of a product in its page: schema.org
# microdata and ``window.productModel``. A tile has the price and the discount label but not the regular price.
IG_BASE = "https://www.instant-gaming.com"
_IG_ARTICLE = re.compile(r'<article\s+class="\s*item\s*"\s*>(.*?)</article>', re.S)
_IG_PRODUCT_MODEL = re.compile(r"window\.productModel\s*=\s*(\{[^\n]*?\})\s*;")


def parse_ig_tiles(page: str) -> list[dict[str, Any]]:
    """The product tiles of a listing page: url and title always; discount label and price when there is a sale.

    A tile without a price is out of stock.
    """
    tiles: list[dict[str, Any]] = []
    for block in _IG_ARTICLE.findall(page):
        link = re.search(r'<a\s+class="cover\s*"\s+href="([^"]+)"', block)
        title = re.search(r'class="title"[^>]*\btitle="([^"]*)"', block)
        if not link or not title:
            continue
        discount = re.search(r'class="discount">\s*-(\d+)%', block)
        price = re.search(r'class="\s*price\s*">\s*([\d.,]+)&nbsp;', block)
        tiles.append(
            {
                "url": html.unescape(link.group(1)).split("?")[0],
                "title": html.unescape(title.group(1)),
                "discount_label": int(discount.group(1)) if discount else None,
                "price": to_amount(price.group(1)) if price else None,
            }
        )
    return tiles


def parse_ig_product(page: str) -> dict[str, Any] | None:
    """What a product page states, or None when the page is not a product.

    ``name``, ``store`` (where the key redeems: Steam, Nintendo eShop...), ``price``, ``regular_price``,
    ``currency``, ``in_stock`` and ``price_valid_until``, the date the shop stops honouring the price.
    """
    model_match = _IG_PRODUCT_MODEL.search(page)
    if model_match is None:
        return None
    try:
        model = json.loads(model_match.group(1))
    except ValueError as exc:
        raise SourceError(f"Instant Gaming: product model is not JSON ({type(exc).__name__})") from exc

    def meta(prop: str) -> list[str]:
        return [html.unescape(value) for value in re.findall(r'<meta\s+itemprop="%s"\s+content="([^"]*)"' % re.escape(prop), page)]

    def first(prop: str) -> str | None:
        values = meta(prop)
        return values[0] if values else None

    availability = meta("availability")
    currency = first("priceCurrency")
    return {
        "id": model.get("prod_id"),
        "name": first("name"),
        "store": first("gamePlatform"),
        "price": to_amount(model.get("price")) if model.get("price") is not None else to_amount(first("price")),
        "regular_price": to_amount(model.get("retail")),
        "currency": currency or "EUR",
        "in_stock": bool(model.get("has_stock")) and any("InStock" in value for value in availability),
        "price_valid_until": first("priceValidUntil"),
    }


def split_ig_title(title: str | None) -> tuple[str, str | None]:
    """A product title without its region suffix, and that suffix ("Syberia 2 - Europe" -> "Syberia 2", "Europe").

    Only a known region word after the last " - " is a suffix: a title keeps every other ending.
    """
    if not title:
        return "", None
    name, separator, suffix = title.rpartition(" - ")
    if not separator or suffix.strip().lower() not in _REGION_LABELS:
        return title.strip(), None
    return name.strip(), _REGION_LABELS[suffix.strip().lower()]
