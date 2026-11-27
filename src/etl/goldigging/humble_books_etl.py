"""Humble book bundles for the Scavenging tab, one record per book.

Source: https://humble.dadand.dev, a public index of Humble's book bundles
(no key). Its front page lists the active bundles as cards that carry their
dates in ``data-start-date`` / ``data-end-date``; each bundle page lists its
books, and every book has a page of its own on the site.
"""

import json
import re
import time
from datetime import datetime
from typing import Any, cast

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.base import BaseETL
from src.utils.logging import get_logger

logger = get_logger("HumbleBooksETL")

INDEX_URL = "https://humble.dadand.dev/"
BASE_URL = "https://humble.dadand.dev"
REQUEST_DELAY_SECONDS = 1.0

# A card is clickable through an inline onclick, not through a link.
_CARD_URL = re.compile(r"href='(/bundles/\d+)'")
_HUMBLE_LINK = re.compile(r"^https?://(?:www\.)?humblebundle\.com/")
_RATING = re.compile(r"(\d+(?:\.\d+)?)\s*\((\d+)\)")


class HumbleBundle(BaseModel):
    """An active bundle as the front page lists it."""

    title: str
    url: str  # its page on the index site
    humble_url: str  # the bundle on humblebundle.com, "" until its page is read
    formats: list[str]  # the site's type badge, e.g. ["ebook"]
    starts_at: datetime | None
    ends_at: datetime | None


class HumbleBundlePage(BaseModel):
    """One fetched bundle page, kept with the bundle it belongs to."""

    bundle: HumbleBundle
    html: str


class HumbleOffer(BaseModel):
    """A book's presence in one active bundle."""

    bundle: str
    humble_url: str
    starts_at: datetime | None
    ends_at: datetime | None


class HumbleBook(BaseModel):
    title: str
    url: str  # the book's page on the index site
    authors: str
    rating: float | None
    rating_count: int
    formats: list[str]
    offers: list[HumbleOffer]


def _iso(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def _formats(tag: BeautifulSoup | Any) -> list[str]:
    badge = tag.find("span", class_="type") if tag is not None else None
    text = badge.get_text(strip=True) if badge else ""
    return [text] if text else []


def parse_active_bundles(html: str) -> list[HumbleBundle]:
    """The active bundles of the front page, one per card, in the site's order.

    Only the cards count: the section also holds the links of the "duplicates
    in N bundle(s)" dropdowns, and those point at bundles that already ended.
    """
    soup = BeautifulSoup(html, "html.parser")
    heading = next((h for h in soup.find_all("h2") if "Active Bundles" in h.get_text()), None)
    card_list = heading.find_next_sibling("div", class_="card-list") if heading else None
    bundles = []
    for card in card_list.find_all("div", class_="bundle-card", recursive=False) if card_list else []:
        title = card.find("h3", class_="bundle-title")
        match = _CARD_URL.search(cast("str", card.get("onclick")) or "")
        if title is None or match is None:
            logger.warning("Active bundle card without a title or a link: skipped")
            continue
        bundles.append(
            HumbleBundle(
                title=title.get_text(" ", strip=True),
                url=BASE_URL + match.group(1),
                humble_url="",
                formats=_formats(card),
                # The casts only drop bs4's AttributeValueList union: a date attribute is never a list.
                starts_at=_iso(cast("str | None", card.get("data-start-date"))),
                ends_at=_iso(cast("str | None", card.get("data-end-date"))),
            )
        )
    return bundles


def parse_bundle_page(page: HumbleBundlePage) -> tuple[HumbleBundle, list[HumbleBook]]:
    """Read one bundle page: the bundle's own dates and Humble link, and its books."""
    soup = BeautifulSoup(page.html, "html.parser")
    header = soup.find("div", id="bundle-container") or soup.find("div", class_="bundle-header")
    bundle = page.bundle
    if header is not None:
        shop = header.find("a", class_="btn", href=_HUMBLE_LINK)
        bundle = bundle.model_copy(
            update={
                "humble_url": cast("str", shop["href"]) if shop else bundle.humble_url,
                "formats": _formats(header) or bundle.formats,
                "starts_at": _iso(cast("str | None", header.get("data-start-date"))) or bundle.starts_at,
                "ends_at": _iso(cast("str | None", header.get("data-end-date"))) or bundle.ends_at,
            }
        )

    items = soup.select("div.book-list-item")
    if items:
        return bundle, [_book(item, bundle, item.select_one("h4.book-title a[href]")) for item in items]

    # Older markup: the books are bare <h4> titles.
    return bundle, [_book(h4, bundle, h4.find("a", href=True)) for h4 in soup.find_all("h4")]


def _book(item: Any, bundle: HumbleBundle, link: Any) -> HumbleBook:
    title = item.get_text(" ", strip=True) if link is None else link.get_text(" ", strip=True)
    href = cast("str", link["href"]) if link is not None and link.has_attr("href") else ""
    if href.startswith("/"):
        href = BASE_URL + href
    authors = item.find("div", class_="book-meta")
    rating = item.select_one(".book-rating .rating-count")
    match = _RATING.search(rating.get_text(" ", strip=True)) if rating else None
    return HumbleBook(
        title=title,
        url=href,
        authors=authors.get_text(" ", strip=True).removeprefix("Authors:").strip() if authors else "",
        rating=float(match.group(1)) if match else None,
        rating_count=int(match.group(2)) if match else 0,
        formats=bundle.formats,
        offers=[HumbleOffer(bundle=bundle.title, humble_url=bundle.humble_url, starts_at=bundle.starts_at, ends_at=bundle.ends_at)],
    )


def merge_books(parsed: list[tuple[HumbleBundle, list[HumbleBook]]]) -> list[HumbleBook]:
    """One record per book: one that two active bundles include keeps both offers."""
    merged: dict[str, HumbleBook] = {}
    for _bundle, books in parsed:
        for book in books:
            key = book.url or book.title.lower()
            known = merged.get(key)
            merged[key] = book if known is None else known.model_copy(update={"offers": known.offers + book.offers})
    return list(merged.values())


def _day(value: datetime | None) -> str:
    return f"{value:%b} {value.day}, {value.year}" if value else "unknown"


def _summary(book: HumbleBook) -> str:
    """What the Details cell shows, next to the title and the bundle link."""
    parts = []
    if book.authors:
        parts.append(f"Authors: {book.authors}")
    if book.rating is not None and book.rating_count:
        parts.append(f"★ {book.rating:.1f} ({book.rating_count})")
    offers = "; ".join(f"{offer.bundle} (ends {_day(offer.ends_at)})" for offer in book.offers)
    parts.append(f"Bundle: {offers}" if len(book.offers) == 1 else f"Bundles: {offers}")
    return " · ".join(parts)


def _record(book: HumbleBook) -> dict[str, Any]:
    """One book in the shape the Scavenging tab reads."""
    starts = [offer.starts_at for offer in book.offers if offer.starts_at]
    ends = [offer.ends_at for offer in book.offers if offer.ends_at]
    return {
        "title": book.title,
        "link": book.url,
        # When the bundle launched: the date the tab sorts by.
        "published": min(starts).isoformat() if starts else "",
        "ends_at": max(ends).isoformat() if ends else "",
        "summary": _summary(book),
        "category": "humble_books",
        "source": "humble.dadand.dev",
        "price": "Pay what you want",
        "deal_type": "Book bundle",
        "authors": book.authors,
        "format": "/".join(book.formats),
        "rating": book.rating,
        "rating_count": book.rating_count,
        "bundles": [offer.bundle for offer in book.offers],
        "humble_urls": [offer.humble_url for offer in book.offers if offer.humble_url],
    }


class HumbleBooksETL(BaseETL[HumbleBundlePage, HumbleBook]):
    """Reads the active Humble book bundles and their books from humble.dadand.dev."""

    def __init__(self):
        super().__init__(
            name="humble_books",
            description="Reads active Humble Book Bundles and their books",
            enable_checkpointing=False,
            max_retries=3,
        )
        self.headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}

    def _get(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.text

    def extract(self) -> list[HumbleBundlePage]:
        """Fetch the front page and then the page of every active bundle."""
        self.logger.info("Fetching the bundle index")
        bundles = parse_active_bundles(self._get(INDEX_URL))
        self.logger.info(f"Found {len(bundles)} active bundles.")

        pages = []
        for bundle in bundles:
            self.logger.info(f"Fetching bundle: {bundle.title}")
            try:
                pages.append(HumbleBundlePage(bundle=bundle, html=self._get(bundle.url)))
            except Exception as e:  # broad by design: one bundle that fails to load must not take the others down
                self.logger.error(f"Failed to fetch bundle {bundle.url}: {e}")
            time.sleep(REQUEST_DELAY_SECONDS)
        return pages

    def transform(self, data: list[HumbleBundlePage]) -> list[HumbleBook]:
        """Parse the bundle pages and keep one record per book."""
        parsed = []
        for page in data:
            try:
                parsed.append(parse_bundle_page(page))
            except Exception as e:  # broad by design: a page the parser does not recognise must not take the others down
                self.logger.error(f"Failed to read bundle {page.bundle.url}: {e}")

        books = merge_books(parsed)
        self.logger.info(f"{len(books)} books across {len(parsed)} bundles.")
        return books

    def load(self, structured_data: list[HumbleBook]) -> None:
        """Persist books to the canonical ETL output dir (data/humble_books/output/).

        The records keep the scavenging display shape (title/link/published/
        summary/category/source/price) that the dashboard Scavenging tab reads
        via its SCAVENGING_SOURCES config.
        """
        if not structured_data:
            self.logger.warning("No books found to load. Returning early.")
            return

        output_file = self.output_dir / "humble_books_latest.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([_record(book) for book in structured_data], f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved {len(structured_data)} books to {output_file}")


if __name__ == "__main__":
    import argparse
    import logging

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    etl = HumbleBooksETL()
    etl.run()
