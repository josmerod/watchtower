"""Escalante, Centre de Teatre Infantil i Juvenil (Diputació de València): the current season.

`https://escalantecentreteatral.dival.es/programacion/temporada-actual` —
HTML, one request. One ``div.item_espec_grid`` per show: title, company, date
range (``25/11/2026  - 30/11/2026``), recommended age, the hall and a ticket
link. The page lists the next twelve shows and nothing else.

The status marks ("esgotades", "cancelado", "aplazado") are in the markup of
every show and shown by the page script, so they cannot be read from the HTML
and are not reported. No price on the listing. A plain HTTP client gets the
data (verified 2026-11-28: 200, 104 KB, 12 shows).
"""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from src.etl.news.valencia_events.dates import parse_written_range
from src.etl.news.valencia_events.dom import text_of
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record

LISTING_URL = "https://escalantecentreteatral.dival.es/programacion/temporada-actual"
SOURCE = "escalantecentreteatral.dival.es"
LABEL = "Escalante (teatre infantil)"


def parse(html: bytes) -> list[dict[str, Any]]:
    """Read the shows of the current season.

    Args:
        html: Raw body of the season page.

    Returns:
        Raw records in page order; a show without a readable start date is skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for item in soup.select("div.item_espec_grid"):
        link = item.select_one("a.bot_grid_espec[href]")
        title = text_of(item.select_one(".grid_espec_tit"))
        date_text = text_of(item.select_one(".grid_espec_inicio_fin"))
        start, end = parse_written_range(date_text)
        if link is None or not title or start is None:
            continue
        tickets = item.select_one("a.bot_entradas[href]")
        audience = text_of(item.select_one(".grid_espec_publico"))
        records.append(
            build_record(
                source=SOURCE,
                title=title,
                url=str(link.get("href") or "").split("?")[0],
                start_date=start,
                end_date=end,
                date_text=date_text,
                category="infantil",
                description=text_of(item.select_one(".grid_espec_cia")),
                venue=text_of(item.select_one(".grid_espec_espacio")),
                city=CITY_VALENCIA,
                tags=["teatro"],
                metadata={"audience": audience, "ticket_url": str(tickets.get("href") or "") if tickets else ""},
            )
        )
    return records


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the season page once and return its shows."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching Escalante season from {LISTING_URL}")
    records = parse(fetch_page(LISTING_URL))
    log.info(f"Retrieved {len(records)} shows from Escalante")
    return records
