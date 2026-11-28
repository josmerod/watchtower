"""La Rambleta (València): the shows on sale on its home page.

`https://larambleta.com/` — HTML, one request. One ``.content_entradas`` card
per event: title, a one-line summary, the event page link, a date line written
in words with the year (``Del 27 al 28 de noviembre de 2026``, ``20 de febrero
de 2027``, ``Del 21 de octubre al 16 de diciembre de 2026``) and its labels as
CSS classes (``musica``, ``humor``, ``escenicas``, ``familiar``, ``teatro``,
``ram-club``, ``la-cambra``, ``factoria``, ``blog``). The label sets seen on
2026-11-28 decide the category: ``familiar`` first, then ``humor``, ``musica``
and ``escenicas``/``teatro``; a label that names a series (``ram-club``,
``la-cambra``, ``factoria``) says nothing about the kind of show, and a title
that says what the show is (``Concierto``) wins over a label. Blog cards are
not events: the ones with the placeholder date ``31 de diciembre de 9999`` are
dropped by the year bound, the ones labelled ``blog`` by their label.

Only the day is printed, so the record is all-day; the time is on the event
page. No price on the listing. A plain HTTP client gets the data (verified
2026-11-28: 200, 220 KB, 72 dated events).
"""

import logging
import re
from collections.abc import Iterable
from datetime import date
from typing import Any

from bs4 import BeautifulSoup

from src.etl.news.valencia_events.categories import fold
from src.etl.news.valencia_events.dates import parse_written_range
from src.etl.news.valencia_events.dom import text_of
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record

HOME_URL = "https://larambleta.com/"
SOURCE = "larambleta.com"
LABEL = "La Rambleta"
VENUE = "La Rambleta"
MAX_YEARS_AHEAD = 2

_STRUCTURAL_CLASSES = frozenset({"content_entradas", "last", "slider-home"})
# A blog card is a post with a date span, not a show.
BLOG_LABEL = "blog"

# In order of precedence: a show with several labels takes the first that matches.
CATEGORY_RULES = (("familiar", "infantil"), ("humor", "humor"), ("musica", "música"), ("escenicas", "teatro"), ("teatro", "teatro"), ("danza", "danza"), ("circ", "teatro"), ("infantil", "infantil"))

# A label can be filed wrong (a choral concert under ``humor``): a title that says
# what the show is in so many words wins over the label.
_TITLE_RULES = (
    ("música", re.compile(r"\b(conciert|concerts?\b|recital|orquest|sinfon|opera|jazz|flamenco|coro\b|coral\b|banda de musica)")),
    ("cine", re.compile(r"\b(cine\b|proyeccion|pelicula)")),
    ("danza", re.compile(r"\b(ballet|danza|dansa)")),
)


def labels_of(card: Any) -> list[str]:
    """The card's labels: its CSS classes without the structural ones, lower-cased."""
    return [str(name).lower() for name in card.get("class") or [] if str(name).lower() not in _STRUCTURAL_CLASSES]


def category_of(labels: Iterable[str], title: str = "") -> str:
    """Vocabulary category from a card's labels; "" when none of them says what the show is.

    A title that names the kind of show outright (``Concierto Solidario``,
    ``Proyección``) wins over the labels.
    """
    folded_title = fold(title)
    for category, pattern in _TITLE_RULES:
        if pattern.search(folded_title):
            return category
    present = set(labels)
    for label, category in CATEGORY_RULES:
        if label in present:
            return category
    return ""


def parse(html: bytes, today: date | None = None) -> list[dict[str, Any]]:
    """Read the dated event cards.

    Args:
        html: Raw body of the home page.
        today: Reference day for the year bound; the current day when None.

    Returns:
        Raw records in page order. Cards without a readable date, dated more
        than two years ahead (the placeholder of blog cards) or labelled as a
        blog post are skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    reference = today or date.today()
    records: list[dict[str, Any]] = []
    for card in soup.select(".content_entradas"):
        link = card.select_one("a.enlacelast[href]")
        title = text_of(card.select_one(".subtitulolast"))
        date_text = text_of(card.select_one(".fechalast"))
        start, end = parse_written_range(date_text)
        if link is None or not title or start is None or start.year > reference.year + MAX_YEARS_AHEAD:
            continue
        labels = labels_of(card)
        if BLOG_LABEL in labels:
            continue
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=str(link.get("href") or ""),
                start_date=start,
                end_date=end,
                date_text=date_text,
                category=category_of(labels, title),
                description=text_of(card.select_one(".resumenlast")),
                venue=VENUE,
                city=CITY_VALENCIA,
                metadata={"labels": labels, "default_category": "teatro"},
            )
        )
    return records


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the home page once and return its events."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching La Rambleta programme from {HOME_URL}")
    records = parse(fetch_page(HOME_URL))
    log.info(f"Retrieved {len(records)} events from La Rambleta")
    return records
