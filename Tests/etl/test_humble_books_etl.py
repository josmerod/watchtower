"""Unit tests for the Humble Books ETL (T-149).

HTML fixtures reproduce the structure of humble.dadand.dev: nothing here
touches the network, and the output goes to a temporary project root.
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import src.etl.base as etl_base
from src.etl.goldigging.humble_books_etl import (
    BASE_URL,
    HumbleBook,
    HumbleBooksETL,
    HumbleBundle,
    HumbleBundlePage,
    HumbleOffer,
    _record,
    merge_books,
    parse_active_bundles,
    parse_bundle_page,
)
from src.services.data_loader import deduplicate_items

INDEX_HTML = """
<h2>Active Bundles</h2>
<div class="card-list">
  <div class="card bundle-card" data-start-date="2026-11-10T21:00:28+00:00" data-end-date="2026-12-01T19:00:00+00:00"
       onclick="window.location.href='/bundles/356'" role="link" tabindex="0">
    <div class="bundle-status">
      <span class="badge bundle-status-badge">Loading...</span>
      <span class="badge type">ebook</span>
      <div class="dropdown">
        <div class="dropdown-content"><ul><li><a href="/bundles/124"><div class="bundle-item"><div class="bundle-name">Old bundle</div></div></a></li></ul></div>
      </div>
    </div>
    <h3 class="bundle-title">Tech Bundle A</h3>
    <div class="bundle-dates"><p>Loading dates...</p></div>
  </div>
  <div class="card bundle-card" data-start-date="2026-11-01T21:00:00+00:00" data-end-date="2026-11-22T19:00:00+00:00"
       onclick="window.location.href='/bundles/355'" role="link" tabindex="0">
    <span class="badge type">ebook</span>
    <h3 class="bundle-title">Book Bundle B</h3>
    <div class="bundle-dates"><p>Loading dates...</p></div>
  </div>
</div>
<h2>Past Bundles</h2>
<div class="card-list">
  <div class="card bundle-card" data-start-date="2026-04-14T21:00:00+00:00" data-end-date="2026-05-12T19:00:00+00:00"
       onclick="window.location.href='/bundles/227'">
    <h3 class="bundle-title">Ended bundle</h3>
  </div>
</div>
"""

BOOK_ITEM = """
<div class="book-list-item">
  <div class="book-info">
    <div class="book-title-container"><h4 class="book-title"><a href="/books/{book_id}">{title}</a></h4></div>
    <div class="book-meta"><span>Authors: {authors}</span></div>
    <p class="book-description">{description}</p>
  </div>
  <div class="book-rating">
    <div class="rating-stars">{stars}</div>
    <div class="rating-count">{rating}</div>
  </div>
  <div class="book-actions">{actions}</div>
</div>
"""

HUMBLE_A = "https://www.humblebundle.com/books/tech-bundle-a"
HUMBLE_B = "https://www.humblebundle.com/books/book-bundle-b"


def _bundle_page(books: list[dict] | None = None, title: str = "Tech Bundle A", humble: str = HUMBLE_A, starts: str = "2026-11-10T21:00:28+00:00", ends: str = "2026-12-01T19:00:00+00:00") -> str:
    items = "".join(
        BOOK_ITEM.format(
            book_id=book["id"],
            title=book["title"],
            authors=book["authors"],
            description="A book.",
            stars=book.get("stars", "★★★★☆"),
            rating=book.get("rating", "0.0 (0)"),
            actions='<a href="https://hardcover.app/books/x" class="rating-btn">Hardcover</a>' if book.get("hardcover") else "",
        )
        for book in (books if books is not None else [{"id": "10156", "title": "Conquer the command line", "authors": "Richard Smedley", "rating": "4.0 (1)"}])
    )
    return f"""
<main class="container">
  <div id="bundle-container" class="bundle-header" data-start-date="{starts}" data-end-date="{ends}">
    <div class="bundle-info">
      <h1>{title}</h1>
      <div class="bundle-meta">
        <div class="bundle-status"><span id="status-badge" class="badge">Loading...</span><span class="badge type">ebook</span></div>
        <div class="bundle-dates"><p id="bundle-dates">Loading dates...</p></div>
      </div>
      <a href="{humble}" target="_blank" rel="noopener noreferrer" class="btn"> View on Humble Bundle </a>
    </div>
  </div>
  <section>
    <h2>Books in this Bundle</h2>
    <div class="book-list">
      <div class="book-list-header"><div class="book-info-header">Book</div><div class="book-rating-header">Rating</div><div class="book-actions-header">Links</div></div>
      {items}
    </div>
  </section>
</main>
"""


BOOKS_A = [
    {"id": "10156", "title": "Conquer the command line", "authors": "Richard Smedley", "rating": "4.0 (1)"},
    {"id": "10157", "title": "Experiment with the Sense HAT", "authors": "Raspberry Pi Foundation Learning Team", "rating": "4.0 (364)", "stars": "★★★★½"},
    {"id": "10162", "title": "The Official Raspberry Pi Beginner's Guide 2026", "authors": "Gareth Halfacree", "rating": "0.0 (0)", "stars": "☆☆☆☆☆"},
]
BOOKS_B = [
    {"id": "90001", "title": "A book only in B", "authors": "Someone", "rating": "3.5 (12)"},
    {"id": "10157", "title": "Experiment with the Sense HAT", "authors": "Raspberry Pi Foundation Learning Team", "rating": "4.0 (364)"},
]


class _FakeSettings:
    """Minimal settings stand-in redirecting BaseETL dirs under tmp_path."""

    def __init__(self, project_root):
        self.project_root = str(project_root)
        self.etl = SimpleNamespace(batch_size=100)


@pytest.fixture
def fake_root(tmp_path, monkeypatch):
    """Point BaseETL's project root (and so the data dirs) at tmp_path."""
    monkeypatch.setattr(etl_base, "get_settings", lambda: _FakeSettings(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Front page: the active bundles are the cards, nothing else
# ---------------------------------------------------------------------------


def test_active_bundles_come_from_the_cards_only():
    bundles = parse_active_bundles(INDEX_HTML)

    assert [b.url for b in bundles] == [f"{BASE_URL}/bundles/356", f"{BASE_URL}/bundles/355"]
    assert [b.title for b in bundles] == ["Tech Bundle A", "Book Bundle B"]
    # Not the link of the "duplicates" dropdown, not a bundle that already ended.
    assert f"{BASE_URL}/bundles/124" not in [b.url for b in bundles]
    assert f"{BASE_URL}/bundles/227" not in [b.url for b in bundles]


def test_active_bundle_card_gives_dates_and_format():
    (first, _second) = parse_active_bundles(INDEX_HTML)

    assert first.starts_at == datetime(2026, 11, 10, 21, 0, 28, tzinfo=timezone.utc)
    assert first.ends_at == datetime(2026, 12, 1, 19, 0, tzinfo=timezone.utc)
    assert first.formats == ["ebook"]
    assert first.humble_url == ""  # known once the bundle page is read


@pytest.mark.parametrize("html", ["<html><body></body></html>", "<h2>Past Bundles</h2>", ""])
def test_front_page_without_active_bundles_gives_none(html):
    assert parse_active_bundles(html) == []


def test_card_without_link_is_skipped_not_guessed():
    html = '<h2>Active Bundles</h2><div class="card-list"><div class="card bundle-card"><h3 class="bundle-title">No link</h3></div></div>'

    assert parse_active_bundles(html) == []


# ---------------------------------------------------------------------------
# Bundle page: books with their own page, authors and rating
# ---------------------------------------------------------------------------


def _page(html: str, title: str = "Tech Bundle A") -> HumbleBundlePage:
    bundle = HumbleBundle(title=title, url=f"{BASE_URL}/bundles/356", humble_url="", formats=["ebook"], starts_at=None, ends_at=None)
    return HumbleBundlePage(bundle=bundle, html=html)


def test_bundle_page_gives_dates_format_and_humble_link():
    bundle, _books = parse_bundle_page(_page(_bundle_page()))

    assert bundle.humble_url == HUMBLE_A
    assert bundle.starts_at == datetime(2026, 11, 10, 21, 0, 28, tzinfo=timezone.utc)
    assert bundle.ends_at == datetime(2026, 12, 1, 19, 0, tzinfo=timezone.utc)
    assert bundle.formats == ["ebook"]


def test_every_book_of_the_bundle_is_kept_with_its_own_page():
    _bundle, books = parse_bundle_page(_page(_bundle_page(books=BOOKS_A)))

    assert [b.title for b in books] == ["Conquer the command line", "Experiment with the Sense HAT", "The Official Raspberry Pi Beginner's Guide 2026"]
    # One URL per book: the dashboard drops records that share a link, and all the books of a bundle used to share the bundle's.
    assert [b.url for b in books] == [f"{BASE_URL}/books/10156", f"{BASE_URL}/books/10157", f"{BASE_URL}/books/10162"]
    assert [b.authors for b in books] == ["Richard Smedley", "Raspberry Pi Foundation Learning Team", "Gareth Halfacree"]
    assert [(b.rating, b.rating_count) for b in books] == [(4.0, 1), (4.0, 364), (0.0, 0)]
    assert all(b.formats == ["ebook"] for b in books)
    assert all(len(b.offers) == 1 and b.offers[0].humble_url == HUMBLE_A and b.offers[0].bundle == "Tech Bundle A" for b in books)


def test_older_markup_with_bare_titles_still_reads_books():
    html = '<div class="bundle-header"><h1>Old layout</h1></div><h4><a href="/books/5">First</a></h4><h4>Second</h4>'

    _bundle, books = parse_bundle_page(_page(html))

    assert [(b.title, b.url) for b in books] == [("First", f"{BASE_URL}/books/5"), ("Second", "")]


def test_absolute_book_links_are_kept_as_they_are():
    html = '<div class="book-list-item"><h4 class="book-title"><a href="https://example.com/books/9">Away</a></h4></div>'

    _bundle, books = parse_bundle_page(_page(html))

    assert books[0].url == "https://example.com/books/9"


# ---------------------------------------------------------------------------
# One record per book
# ---------------------------------------------------------------------------


def _parsed() -> list[tuple[HumbleBundle, list[HumbleBook]]]:
    bundles = parse_active_bundles(INDEX_HTML)
    return [
        parse_bundle_page(HumbleBundlePage(bundle=bundles[0], html=_bundle_page(books=BOOKS_A))),
        parse_bundle_page(HumbleBundlePage(bundle=bundles[1], html=_bundle_page(books=BOOKS_B, title="Book Bundle B", humble=HUMBLE_B, starts="2026-11-01T21:00:00+00:00", ends="2026-11-22T19:00:00+00:00"))),
    ]


def test_a_book_in_two_bundles_is_one_record_with_both_offers():
    books = merge_books(_parsed())

    by_title = {b.title: b for b in books}
    assert len(books) == 4  # 3 + 2 books, one of them shared
    shared = by_title["Experiment with the Sense HAT"]
    assert [o.bundle for o in shared.offers] == ["Tech Bundle A", "Book Bundle B"]
    assert by_title["A book only in B"].offers[0].bundle == "Book Bundle B"


def test_record_links_to_the_book_and_dates_it_by_the_bundle():
    shared = next(b for b in merge_books(_parsed()) if b.title == "Experiment with the Sense HAT")

    record = _record(shared)

    assert record["link"] == f"{BASE_URL}/books/10157"
    assert record["published"] == "2026-11-01T21:00:00+00:00"  # when the earliest bundle launched
    assert record["ends_at"] == "2026-12-01T19:00:00+00:00"  # the last bundle to end
    assert record["authors"] == "Raspberry Pi Foundation Learning Team"
    assert record["rating"] == 4.0 and record["rating_count"] == 364
    assert record["format"] == "ebook"
    assert record["bundles"] == ["Tech Bundle A", "Book Bundle B"]
    assert record["category"] == "humble_books"
    assert record["summary"] == "Authors: Raspberry Pi Foundation Learning Team · ★ 4.0 (364) · Bundles: Tech Bundle A (ends Dec 1, 2026); Book Bundle B (ends Nov 22, 2026)"


def test_record_without_rating_or_dates_still_reads_well():
    book = HumbleBook(title="Bare", url="", authors="", rating=None, rating_count=0, formats=[], offers=[HumbleOffer(bundle="B", humble_url="", starts_at=None, ends_at=None)])

    record = _record(book)

    assert record["summary"] == "Bundle: B (ends unknown)"
    assert record["published"] == "" and record["ends_at"] == ""
    assert record["humble_urls"] == []


# ---------------------------------------------------------------------------
# Load: the canonical file, and every book survives the dashboard's dedupe
# ---------------------------------------------------------------------------


def test_humble_books_writes_canonical_only(fake_root):
    etl = HumbleBooksETL()
    books = merge_books(_parsed())

    etl.load(books)

    canonical = fake_root / "data" / "humble_books" / "output" / "humble_books_latest.json"
    assert canonical.is_file()
    assert not (fake_root / "data" / "scavenging").exists()
    records = json.loads(canonical.read_text(encoding="utf-8"))
    assert len(records) == 4
    # The tab loads through deduplicate_items(): with the bundle's URL on every book, only the first one was left.
    assert [r["title"] for r in deduplicate_items([dict(r) for r in records])] == [b.title for b in books]


def test_nothing_is_written_when_there_are_no_books(fake_root):
    HumbleBooksETL().load([])

    assert not list((fake_root / "data").rglob("humble_books_latest.json"))


def test_a_bundle_page_that_cannot_be_read_does_not_take_the_others_down(fake_root, monkeypatch):
    import src.etl.goldigging.humble_books_etl as module

    bundles = parse_active_bundles(INDEX_HTML)
    pages = [HumbleBundlePage(bundle=b, html=_bundle_page(books=books)) for b, books in zip(bundles, [BOOKS_A, BOOKS_B], strict=True)]
    real_parse = module.parse_bundle_page

    def parse_or_fail(page):
        if page.bundle.title == "Book Bundle B":
            raise ValueError("unrecognised page")
        return real_parse(page)

    monkeypatch.setattr(module, "parse_bundle_page", parse_or_fail)

    books = HumbleBooksETL().transform(pages)

    assert [b.title for b in books] == ["Conquer the command line", "Experiment with the Sense HAT", "The Official Raspberry Pi Beginner's Guide 2026"]
