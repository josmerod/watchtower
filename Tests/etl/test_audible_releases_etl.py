"""Unit tests for the Audible releases ETL (T-150).

HTML fixtures reproduce the structure of an audible.es results page (the hover card with bare rows, then the labelled list), and the pages ``extract()`` reads are served from a dict: nothing touches the network.
"""

import re
from datetime import date, datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

import src.etl.base as etl_base
import src.etl.goldigging.audible_releases_etl as audible
from src.etl.goldigging.audible_releases_etl import (
    AUDIBLE_BASE,
    BROWSE_FILTERS,
    MAX_PAGES,
    NEW_RELEASES_PATH,
    PAGE_SIZE,
    AudibleReleasesETL,
    build_url,
    parse_rating,
    parse_release_date,
    parse_releases_page,
    parse_runtime_minutes,
    publication_window,
    to_record,
)

TODAY = date(2026, 11, 27)
UTC = timezone.utc

NO_RATINGS = '<li class="bc-list-item ratingsLabel"> <span class="bc-text bc-size-callout bc-color-secondary"> sin valoraciones </span> </li>'
RATED = """<li class="bc-list-item ratingsLabel" tabindex="-1"> <span class="bc-text bc-size-callout">4,5</span>
  <div class="bc-review-stars" role="img"><span class="full-review-star"><i class="bc-icon bc-icon-star-fill-s2"></i></span></div>
  <span>1.234 valoraciones</span> </li>"""


def _item(title, asin, author="An Author", narrator="A Voice", language="Inglés", runtime="8 horas y 24 mins", released="26-11-26", version='<li class="bc-list-item"> Versión íntegra </li>', subtitle="", series=None, rating=NO_RATINGS, href=None) -> str:
    """One result in the shape of the real page: a hover card of bare rows, then the labelled list."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")
    series_row = ""
    if series is not None:
        name, number = series if isinstance(series, tuple) else (series, None)
        series_row = f'<li class="bc-list-item seriesLabel"> <span class="bc-text bc-size-small bc-color-secondary"> Serie: <!-- Reset bookNum --> <a class="bc-link bc-color-link" href="/series/{slug}-Audiolibro/{asin}?pf_rd_p=abc">{name}</a> , libro {number} </span> </li>' if number else f'<li class="bc-list-item seriesLabel"> <span class="bc-text bc-size-small bc-color-secondary"> Serie: <a class="bc-link bc-color-link" href="/series/{slug}-Audiolibro/{asin}">{name}</a> </span> </li>'
    subtitle_row = f'<li class="bc-list-item subtitle"> <span class="bc-text bc-size-base bc-color-secondary">{subtitle}</span> </li>' if subtitle else ""
    link = href or f"/pd/{slug}-Audiolibro/{asin}"
    return f"""
<li class="bc-list-item productListItem" id="product-list-item-{asin}" aria-label='{title}'>
  <div class="bc-row-responsive">
    <div class="bc-trigger bc-pub-block">
      <a class="bc-link bc-color-link" href="{link}?ref_pageloadid=not_applicable&amp;pf_rd_p=abc"><img src="cover.jpg" alt="portada" /></a>
      <div class="bc-popover bc-hidden" role="tooltip">
        <ul class="bc-list">
          <li class="bc-list-item bc-spacing-micro">{title}</li>
          <li class="bc-list-item"> De: {author} </li>
          <li class="bc-list-item"> Narrado por: {narrator} </li>
          <li class="bc-list-item"> {language} </li>
          <li class="bc-list-item"> Duración: {runtime} </li>
          {version}
          <li class="bc-list-item bc-spacing-micro">General: 0</li>
          <li class="bc-list-item bc-spacing-micro">Historia: 0</li>
        </ul>
      </div>
    </div>
  </div>
  <ul>
    <li class="bc-list-item">{title}</li>
    {subtitle_row}
    <h3 class="bc-heading bc-color-link bc-pub-break-wo" id="title-{asin}"><a class="bc-link bc-color-link" href="{link}?ref_pageloadid=not_applicable&amp;pf_rd_p=abc">{title}</a></h3>
    {series_row}
    <li class="bc-list-item authorLabel"><span> De: {author} </span></li>
    <li class="bc-list-item narratorLabel"><span> Narrado por: {narrator} </span></li>
    <li class="bc-list-item languageLabel"><span> {language} </span></li>
    <li class="bc-list-item runtimeLabel"><span> Duración: {runtime} </span></li>
    <li class="bc-list-item releaseDateLabel"><span> Fecha de lanzamiento:
                                    {released} </span></li>
    {rating}
    <li class="bc-list-item mostPopularLabel"> </li>
    <li class="bc-list-item trendingLabel"> </li>
  </ul>
</li>
"""


SPANISH = _item("La escuela que quiero", "B0HSH8P8MS", author="Mar Romera", narrator="Ainhoa Miguel", language="Español", runtime="6 horas y 5 mins", released="26-11-26", subtitle="En busca del sentido común: pedagogía de altura", series="El mundo dormido")
ENGLISH = _item("Creature Files", "B0RATED0001", author="Someone , Someone Else", narrator="A voice , Another voice", runtime="10 hrs and 5 mins", released="25-11-26", version="<li class=\"bc-list-item\"> Unabridged </li>", series=("Creature Files", 3), rating=RATED)
ABRIDGED = _item("Short History", "B000ABRIDG", runtime="45 mins", released="25-11-26", version="<li class=\"bc-list-item\"> Versión acortada </li>")
ORIGINAL = _item("An original", "B0ORIGINAL1", version="<li class=\"bc-list-item\"> Grabación original </li>")
THIRD = _item("Third book", "B0THIRD0001", runtime="3 horas", released="24-11-26")


def _page(*items: str) -> str:
    return "<html><body><ul>" + "".join(items) + "</ul></body></html>"


class _FakeSettings:
    """Minimal settings stand-in redirecting BaseETL dirs under tmp_path."""

    def __init__(self, project_root):
        self.project_root = str(project_root)
        self.etl = SimpleNamespace(batch_size=100)


@pytest.fixture
def etl(tmp_path, monkeypatch):
    """An ETL whose pages come from ``served`` (page number → HTML) instead of the network; ``asked`` records the pages requested."""
    monkeypatch.setattr(etl_base, "get_settings", lambda: _FakeSettings(tmp_path))
    monkeypatch.setattr(audible.time, "sleep", lambda _seconds: None)
    instance = AudibleReleasesETL()
    served: dict[int, str] = {}
    asked: list[int] = []

    def get(url: str) -> str:
        page = int(parse_qs(urlparse(url).query)["page"][0])
        asked.append(page)
        if page not in served:
            raise RuntimeError(f"no page {page} to serve")
        return served[page]

    monkeypatch.setattr(instance, "_get", get)
    instance.served = served  # type: ignore[attr-defined]
    instance.asked = asked  # type: ignore[attr-defined]
    return instance


# ---------------------------------------------------------------------------
# Window and URL
# ---------------------------------------------------------------------------


def test_window_moves_with_the_calendar():
    assert publication_window(today=TODAY) == (date(2026, 10, 29), TODAY)  # 30 days, today included
    assert publication_window(today=TODAY, days=7) == (date(2026, 11, 21), TODAY)
    assert publication_window(today=TODAY, days=1) == (TODAY, TODAY)
    assert publication_window(today=TODAY, days=0) == (TODAY, TODAY)  # never an empty or inverted window


def test_url_carries_the_window_the_page_and_its_size():
    url = build_url((date(2026, 10, 29), TODAY), 3)

    assert url.startswith(f"{AUDIBLE_BASE}{NEW_RELEASES_PATH}?{BROWSE_FILTERS}&")
    query = parse_qs(urlparse(url).query)
    assert query["publication_date"] == ["20261029-20261127"]
    assert query["page"] == ["3"] and query["pageSize"] == [str(PAGE_SIZE)] and query["sort"] == ["pubdate-desc-rank"]


def test_url_has_no_fixed_dates_left():
    # The window used to be written in the code, and it expired.
    assert not re.search(r"20260[1-9]\d{2}|20261[0-2]\d{2}", BROWSE_FILTERS)


# ---------------------------------------------------------------------------
# Reading the labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("26-11-26", datetime(2026, 11, 26, tzinfo=UTC)),
        (" 5-01-26 ", datetime(2026, 1, 5, tzinfo=UTC)),
        ("31-02-26", None),  # not a day
        ("", None),
        ("sin fecha", None),
    ],
)
def test_release_date(text, expected):
    assert parse_release_date(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("8 horas y 24 mins", 504),
        ("45 mins", 45),
        ("10 hrs and 5 mins", 605),  # the English site words it the same way
        ("2 horas", 120),
        ("Duración: 8 horas y 24 mins", 504),  # the label does not get in the way
        ("", None),
        ("no consta", None),
    ],
)
def test_runtime_in_minutes(text, expected):
    assert parse_runtime_minutes(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5,0 1 valoración", (5.0, 1)),
        ("4,5\n1.234 valoraciones", (4.5, 1234)),
        ("4.5 1,234 ratings", (4.5, 1234)),
        ("sin valoraciones", (None, 0)),
        ("", (None, 0)),
    ],
)
def test_rating(text, expected):
    assert parse_rating(text) == expected


# ---------------------------------------------------------------------------
# One results page
# ---------------------------------------------------------------------------


def test_page_gives_each_release_its_fields():
    releases = parse_releases_page(_page(SPANISH, ENGLISH, ABRIDGED, ORIGINAL))

    assert [r["title"] for r in releases] == ["La escuela que quiero", "Creature Files", "Short History", "An original"]
    # Absolute, and without the tracking parameters the site adds.
    assert [r["link"] for r in releases] == [f"{AUDIBLE_BASE}/pd/La-escuela-que-quiero-Audiolibro/B0HSH8P8MS", f"{AUDIBLE_BASE}/pd/Creature-Files-Audiolibro/B0RATED0001", f"{AUDIBLE_BASE}/pd/Short-History-Audiolibro/B000ABRIDG", f"{AUDIBLE_BASE}/pd/An-original-Audiolibro/B0ORIGINAL1"]
    assert [r["subtitle"] for r in releases] == ["En busca del sentido común: pedagogía de altura", "", "", ""]
    assert [r["author"] for r in releases] == ["Mar Romera", "Someone, Someone Else", "An Author", "An Author"]  # the markup leaves a space before the comma
    assert [r["narrator"] for r in releases] == ["Ainhoa Miguel", "A voice, Another voice", "A Voice", "A Voice"]
    assert [r["series"] for r in releases] == ["El mundo dormido", "Creature Files, libro 3", "", ""]
    assert [r["runtime"] for r in releases] == ["6 horas y 5 mins", "10 hrs and 5 mins", "45 mins", "8 horas y 24 mins"]
    assert [r["language"] for r in releases] == ["Español", "Inglés", "Inglés", "Inglés"]
    # The site says "Fecha de lanzamiento:", not "Fecha de publicación:", and puts the date on its own line.
    assert [r["release_date"] for r in releases] == ["26-11-26", "25-11-26", "25-11-26", "26-11-26"]
    assert [(r["rating"], r["rating_count"]) for r in releases] == [(None, 0), (4.5, 1234), (None, 0), (None, 0)]


def test_the_version_row_tells_whether_the_book_is_complete():
    releases = parse_releases_page(_page(SPANISH, ENGLISH, ABRIDGED, ORIGINAL))

    assert [r["version"] for r in releases] == ["Versión íntegra", "Unabridged", "Versión acortada", "Grabación original"]
    assert [r["unabridged"] for r in releases] == [True, True, False, None]


def test_a_title_or_subtitle_with_version_in_it_is_not_the_version_row():
    titled = _item("Santa Biblia: versión Reina Valera", "B0BIBLIA01", subtitle="Versión acortada para niños")
    bare = _item("No version row", "B0NOVERSION", version="")

    first, second = parse_releases_page(_page(titled, bare))

    assert (first["version"], first["unabridged"]) == ("Versión íntegra", True)
    assert (second["version"], second["unabridged"]) == ("", None)


def test_a_series_name_with_a_colon_keeps_it_whole():
    release = parse_releases_page(_page(_item("Wrong with the Chief", "B0COLON0001", series=("There's Something Wrong with the Chief: Du Zhu You Bing", 1))))[0]

    assert release["series"] == "There's Something Wrong with the Chief: Du Zhu You Bing, libro 1"


def test_a_release_without_its_link_is_skipped():
    assert parse_releases_page(_page('<li class="bc-list-item productListItem"><h3 class="bc-heading">No link</h3></li>', SPANISH)) == [parse_releases_page(_page(SPANISH))[0]]


def test_a_page_without_results_gives_nothing():
    assert parse_releases_page(_page()) == []
    assert parse_releases_page("<html><body>Maintenance</body></html>") == []


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


def test_record_carries_its_own_columns_and_the_release_date():
    record = to_record(parse_releases_page(_page(ENGLISH))[0])

    assert record["published"] == "2026-11-25T00:00:00+00:00"
    assert (record["author"], record["narrator"], record["series"]) == ("Someone, Someone Else", "A voice, Another voice", "Creature Files, libro 3")
    assert (record["runtime"], record["runtime_minutes"]) == ("10 hrs and 5 mins", 605)
    assert (record["language"], record["rating"], record["rating_count"], record["unabridged"]) == ("Inglés", 4.5, 1234, True)
    assert record["summary"] == "👨‍💻\u00a0Autor: Someone, Someone Else | 🎙️\u00a0Narrador: A voice, Another voice | 📚\u00a0Serie: Creature Files, libro 3 | ⏱️\u00a010 hrs and 5 mins | 🌐\u00a0Inglés | ★ 4.5 (1234)"
    assert (record["category"], record["source"], record["deal_type"]) == ("audible", "audible_releases_etl", "Audiobook")


def test_an_abridged_release_says_so():
    record = to_record(parse_releases_page(_page(ABRIDGED))[0])

    assert record["unabridged"] is False
    assert record["summary"].endswith("| Versión acortada")


def test_a_release_without_a_date_is_not_dated_today():
    # Every book used to get the time of the run, which also made the tab's date column meaningless.
    record = to_record({**parse_releases_page(_page(SPANISH))[0], "release_date": ""})

    assert record["published"] == ""
    assert record["summary"] == "👨‍💻\u00a0Autor: Mar Romera | 🎙️\u00a0Narrador: Ainhoa Miguel | 📚\u00a0Serie: El mundo dormido | ⏱️\u00a06 horas y 5 mins | 🌐\u00a0Español"


# ---------------------------------------------------------------------------
# Paging
# ---------------------------------------------------------------------------


def test_extract_reads_every_page_and_stops_where_the_site_repeats_itself(etl):
    # Audible answers a page past the last one with the last page again.
    etl.served.update({1: _page(SPANISH, ABRIDGED), 2: _page(ABRIDGED, THIRD), 3: _page(ABRIDGED, THIRD)})

    raw = etl.extract()

    assert etl.asked == [1, 2, 3]  # never page 4
    assert [r["title"] for r in raw] == ["La escuela que quiero", "Short History", "Short History", "Third book"]
    assert [r["title"] for r in etl.transform(raw)] == ["La escuela que quiero", "Short History", "Third book"]  # a book that spans two pages is one record


def test_extract_stops_at_an_empty_page(etl):
    etl.served.update({1: _page(SPANISH), 2: _page()})

    assert len(etl.extract()) == 1
    assert etl.asked == [1, 2]


def test_extract_asks_for_no_more_pages_than_the_site_has(etl):
    for page in range(1, 30):
        etl.served[page] = _page(_item(f"Book {page}", f"B{page:09d}"))

    assert len(etl.extract()) == MAX_PAGES
    assert etl.asked == list(range(1, MAX_PAGES + 1))


def test_max_pages_can_be_lowered(etl):
    etl.max_pages = 2
    for page in (1, 2, 3):
        etl.served[page] = _page(_item(f"Book {page}", f"B{page:09d}"))

    assert len(etl.extract()) == 2


def test_a_page_that_fails_to_load_keeps_the_earlier_ones(etl):
    etl.served[1] = _page(SPANISH)

    assert [r["title"] for r in etl.extract()] == ["La escuela que quiero"]  # page 2 raises inside _get
    assert etl.asked == [1, 2]


def test_transform_keeps_one_record_per_link_and_drops_the_linkless(etl):
    raw = parse_releases_page(_page(SPANISH, SPANISH)) + [{"title": "No link", "link": ""}]

    assert [r["title"] for r in etl.transform(raw)] == ["La escuela que quiero"]
