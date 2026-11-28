"""IVAM, Institut Valencià d'Art Modern: its activities and its exhibitions.

Two pages, one request each:

- `https://ivam.es/es/actividades/` — 28 ``.ivam-post-card`` cards.
- `https://ivam.es/es/exposiciones/` — 15 cards.

A card carries the title, its link, a date line (``01 dic. 2026`` or
``25 ene. 2026 - 08 dic. 2026``) and two labels: the typology (``Conversaciones``,
``Familiar``, ``Exposición``... or ``Colección`` for a display of the permanent
collection) and the centre. An activity takes its category from its typology;
an exhibition is ``arte`` unless its typology names a performance (``Cine``,
``Escénicas``, ``Danza``, ``Música``). The venue is the centre: ``IVAM Centre
Julio González`` in València, or ``IVAM Alcoi`` (the city is then Alcoi). Cards
of the ``Territorio`` programme name no municipality and are skipped. No time or
price on the listing. A plain HTTP client gets the data (verified 2026-11-28:
200, 157 KB and 130 KB).
"""

import logging
from typing import Any

from bs4 import BeautifulSoup

from src.etl.news.valencia_events.dates import parse_written_range
from src.etl.news.valencia_events.dom import text_of
from src.etl.news.valencia_events.http import fetch_page, pause
from src.etl.news.valencia_events.records import build_record

ACTIVITIES_URL = "https://ivam.es/es/actividades/"
EXHIBITIONS_URL = "https://ivam.es/es/exposiciones/"
SOURCE = "ivam.es"
LABEL = "IVAM"

TYPOLOGY_MAP = {
    "Escénicas": "teatro",
    "Cine": "cine",
    "Talleres": "charlas y talleres",
    "Visitas": "visitas y rutas",
    "Conversaciones": "charlas y talleres",
    "Seminarios": "charlas y talleres",
    "Música": "música",
    "Familiar": "infantil",
    "Educación": "charlas y talleres",
    "Colección": "visitas y rutas",
    "Danza": "danza",
    "Exposición": "arte",
}
# What an unknown typology means on each listing.
DEFAULT_TYPOLOGY = {"activities": "charlas y talleres", "exhibitions": "arte"}
# A typology that makes an exhibition something else than an art show.
_PERFORMANCE_TYPES = frozenset({"Cine", "Escénicas", "Danza", "Música"})

# centre label → (venue, city). A centre missing here names no municipality.
CENTRES = {
    "IVAM Centre Julio González": ("IVAM", "València"),
    "IVAM Alcoi": ("IVAM Alcoi", "Alcoi"),
}


def category_of(typology: str, kind: str) -> str:
    """Vocabulary category for a card's typology on the ``kind`` listing."""
    category = TYPOLOGY_MAP.get(typology, "")
    if kind == "exhibitions" and category not in _PERFORMANCE_TYPES:
        return DEFAULT_TYPOLOGY[kind]
    return category or DEFAULT_TYPOLOGY[kind]


def parse_page(html: bytes, kind: str) -> list[dict[str, Any]]:
    """Read one IVAM listing.

    Args:
        html: Raw body of the listing.
        kind: ``activities`` or ``exhibitions``.

    Returns:
        Raw records in page order. Cards without a readable date, or whose
        centre is not a known IVAM venue, are skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for card in soup.select(".ivam-post-card"):
        link = card.select_one(".ivam-post-card__header a[href]")
        title = text_of(card.select_one(".ivam-post-card__title"))
        date_text = text_of(card.select_one("p.date"))
        start, end = parse_written_range(date_text)
        labels = [text_of(span) for span in card.select(".categories span")]
        if link is None or not title or start is None or not labels:
            continue
        venue_city = CENTRES.get(labels[-1])
        if venue_city is None:
            continue
        venue, city = venue_city
        typology = labels[0]
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=str(link.get("href") or ""),
                start_date=start,
                end_date=end,
                date_text=date_text,
                category=category_of(typology, kind),
                venue=venue,
                city=city,
                metadata={"typology": typology, "centre": labels[-1], "kind": kind},
            )
        )
    return records


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch both listings (pausing between requests) and return their cards."""
    log = logger or logging.getLogger(__name__)
    pages: list[tuple[bytes, str]] = []
    for index, (url, kind) in enumerate(((ACTIVITIES_URL, "activities"), (EXHIBITIONS_URL, "exhibitions"))):
        if index:
            pause()
        log.info(f"Fetching IVAM {kind} from {url}")
        pages.append((fetch_page(url), kind))
    records = [record for html, kind in pages for record in parse_page(html, kind)]
    log.info(f"Retrieved {len(records)} cards from the IVAM")
    return records
