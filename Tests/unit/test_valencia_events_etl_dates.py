"""Unit tests for T-072: Valencia events ETL date extraction.

Covers the three merged sources with fixture HTML/JSON and monkeypatched
``requests.get`` — no network in unit tests:

- visitvalencia.com: structured ``standard-card`` listing with Spanish
  "DD/MM/YYYY - DD/MM/YYYY" date text, plus the legacy heuristic fallback.
- eventbrite.es: schema.org ItemList JSON-LD with ISO startDate/endDate.
- meetup.com: JSON-LD array of schema.org Events with full ISO timestamps,
  plus the static event-card fallback carrying ``<time datetime>`` tags.
"""

import json
from datetime import datetime

from src.etl.news.valencia_events_etl import (
    ValenciaEvent,
    ValenciaEventsETL,
    _parse_dates_from_text,
    _to_iso_date,
)


class _BytesResponse:
    """Minimal requests.Response stand-in carrying raw page bytes."""

    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self):
        return None


_YEAR = datetime.now().year  # fixtures stay valid across year rollovers


def _card(title: str, href: str, dates: str | None) -> str:
    """Build a visitvalencia listing card with the probed BEM structure."""
    dates_p = f'<p class="paragraph standard-card__dates">{dates}</p>' if dates is not None else ""
    return (
        '<div class="standard-card standard-card--horizontal standard-card--featured">'
        '<div class="standard-card__content">'
        f'<a class="link standard-card__link" href="{href}">'
        f'<h3 class="heading heading--mini standard-card__heading">{title}</h3>'
        f"{dates_p}"
        "</a>"
        "</div>"
        "</div>"
    )


VISITVALENCIA_HTML = (
    "<html><body>"
    "<h2>Main navigation</h2>"
    "<h2>EVENTOS EN VALÈNCIA</h2>"
    + _card(f"Cine de verano en València {_YEAR}: cartelera y espacios", "/agenda-valencia/cine-de-verano", f"17/08/{_YEAR} - 30/08/{_YEAR}")
    + _card("Mercado de Navidad", "/agenda-valencia/mercado-navidad", f"25/12/{_YEAR}")
    + _card("Exposición permanente sin fechas", "/agenda-valencia/sin-fechas", None)
    + "</body></html>"
).encode()

EVENTBRITE_HTML = (
    "<html><body>"
    '<script type="application/ld+json">'
    '{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Valencia"}]}'
    "</script>"
    '<script type="application/ld+json">'
    + json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {
                    "position": 1,
                    "@type": "ListItem",
                    "item": {
                        "startDate": f"{_YEAR}-11-26",
                        "endDate": f"{_YEAR}-11-27",
                        "name": "Valencia Tech Job Fair Autumn",
                        "description": "Connect, recruit and celebrate diversity.",
                        "url": "https://www.eventbrite.co.uk/e/valencia-tech-job-fair",
                        "location": {
                            "address": {
                                "streetAddress": "1 Carrer de la Vall d'Aiora",
                                "addressLocality": "València",
                                "addressCountry": "ES",
                            }
                        },
                    },
                },
                {
                    "position": 2,
                    "@type": "ListItem",
                    "item": {
                        "startDate": f"{_YEAR}-09-05",
                        "name": "Noche de comedia",
                        "url": "https://www.eventbrite.com/e/noche-de-comedia",
                    },
                },
            ],
        }
    )
    + "</script>"
    '<script type="application/ld+json">{"broken": '
    "</body></html>"
).encode()

MEETUP_HTML = (
    "<html><body>"
    '<script type="application/ld+json">'
    '{"@context":"https://schema.org","@type":"Organization","name":"Meetup","url":"https://www.meetup.com"}'
    "</script>"
    '<script type="application/ld+json">'
    + json.dumps(
        [
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "Sunset Beach Party & Dance",
                "url": "https://www.meetup.com/premiumvalencia/events/316214965/",
                "description": "Reggaeton & Latino open air session.",
                "startDate": f"{_YEAR}-08-28T18:30:00.000Z",
                "endDate": f"{_YEAR}-08-28T21:30:00.000Z",
                "location": {"name": "Playa de la Malvarrosa", "address": {"addressLocality": "València"}},
            },
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "Brunch de domingo",
                "url": "https://www.meetup.com/premiumvalencia/events/316214966/",
                "startDate": f"{_YEAR}-09-04T10:00:00+02:00[Europe/Madrid]",
                "endDate": "",
                "location": "Café de las Horas",
            },
        ]
    )
    + "</script>"
    "</body></html>"
).encode()

MEETUP_CARDS_HTML = (
    "<html><body>"
    '<div data-testid="event-card">'
    "<h3>Ruta de senderismo</h3>"
    f'<time datetime="{_YEAR}-09-10T19:00:00+02:00">{_YEAR}-09-10 19:00</time>'
    '<a href="https://www.meetup.com/premiumvalencia/events/1/">Ruta de senderismo</a>'
    "<p>Salida desde la plaza.</p>"
    "</div>"
    '<div data-testid="event-card">'
    "<h3>Quedada sin fecha</h3>"
    "</div>"
    "</body></html>"
).encode()


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def test_to_iso_date_normalizes_all_source_formats():
    assert _to_iso_date(f"17/08/{_YEAR}") == f"{_YEAR}-08-17"  # Spanish listing text
    assert _to_iso_date(f"7/8/{_YEAR}") == f"{_YEAR}-08-07"  # unpadded Spanish
    assert _to_iso_date(f"{_YEAR}-11-26") == f"{_YEAR}-11-26"  # plain ISO
    assert _to_iso_date(f"{_YEAR}-08-28T18:30:00.000Z") == f"{_YEAR}-08-28"  # meetup UTC timestamp
    assert _to_iso_date(f"{_YEAR}-09-04T10:00:00+02:00[Europe/Madrid]") == f"{_YEAR}-09-04"  # bracketed zone
    assert _to_iso_date(None) == ""
    assert _to_iso_date("") == ""


def test_to_iso_date_rejects_garbage_and_invalid_dates():
    assert _to_iso_date("Cada dos semanas") == ""
    assert _to_iso_date("2026") == ""
    assert _to_iso_date(f"31/02/{_YEAR}") == ""  # impossible calendar date
    assert _to_iso_date(None) == ""


def test_parse_dates_from_text_handles_ranges_and_single_dates():
    assert _parse_dates_from_text(f"17/08/{_YEAR} - 30/08/{_YEAR}") == (f"{_YEAR}-08-17", f"{_YEAR}-08-30")
    assert _parse_dates_from_text(f"Del 17/08/{_YEAR} al 30/08/{_YEAR}") == (f"{_YEAR}-08-17", f"{_YEAR}-08-30")
    assert _parse_dates_from_text(f"Fecha: Del 1/12/{_YEAR} al 6/1/{_YEAR + 1}") == (f"{_YEAR}-12-01", f"{_YEAR + 1}-01-06")
    assert _parse_dates_from_text(f"25/12/{_YEAR}") == (f"{_YEAR}-12-25", "")
    assert _parse_dates_from_text(f"{_YEAR}-11-26 al {_YEAR}-11-27") == (f"{_YEAR}-11-26", f"{_YEAR}-11-27")
    # A repeated identical date is a one-day event, not a range
    assert _parse_dates_from_text(f"17/08/{_YEAR} - 17/08/{_YEAR}") == (f"{_YEAR}-08-17", "")
    # Month names without digits stay unparsed (kept in date_text only)
    assert _parse_dates_from_text("Del 5 de septiembre al 9 de septiembre") == ("", "")
    assert _parse_dates_from_text("") == ("", "")


# ---------------------------------------------------------------------------
# visitvalencia.com
# ---------------------------------------------------------------------------


def test_visitvalencia_standard_cards_extract_iso_dates(monkeypatch):
    monkeypatch.setattr("src.etl.news.valencia_events_etl.requests.get", lambda url, **kw: _BytesResponse(VISITVALENCIA_HTML))
    etl = ValenciaEventsETL()
    events = etl.get_valencia_events(f"{_YEAR}-09")

    by_title = {e["title"]: e for e in events}
    assert len(events) == 3

    cine = by_title[f"Cine de verano en València {_YEAR}: cartelera y espacios"]
    assert cine["start_date"] == f"{_YEAR}-08-17"
    assert cine["end_date"] == f"{_YEAR}-08-30"
    assert cine["date_text"] == f"17/08/{_YEAR} - 30/08/{_YEAR}"
    assert cine["url"] == "https://www.visitvalencia.com/agenda-valencia/cine-de-verano"
    assert cine["source"] == "visitvalencia.com"

    # Single-day event: end stays empty
    mercado = by_title["Mercado de Navidad"]
    assert mercado["start_date"] == f"{_YEAR}-12-25"
    assert mercado["end_date"] == ""

    # Undated event stays gracefully undated
    sin_fecha = by_title["Exposición permanente sin fechas"]
    assert sin_fecha["start_date"] == ""
    assert sin_fecha["end_date"] == ""


def test_visitvalencia_falls_back_to_heuristics_without_cards(monkeypatch):
    html = (f'<html><body><div><h3>Exposición de arte moderno</h3>Del 17/08/{_YEAR} al 30/08/{_YEAR}<a href="/agenda-valencia/arte">más</a></div></body></html>').encode()
    monkeypatch.setattr("src.etl.news.valencia_events_etl.requests.get", lambda url, **kw: _BytesResponse(html))
    etl = ValenciaEventsETL()
    events = etl.get_valencia_events(f"{_YEAR}-08")
    assert len(events) >= 1
    arte = next(e for e in events if e["title"] == "Exposición de arte moderno")
    assert "17/08" in arte["date_text"]


# ---------------------------------------------------------------------------
# eventbrite.es
# ---------------------------------------------------------------------------


def test_eventbrite_jsonld_items_carry_iso_dates(monkeypatch):
    monkeypatch.setattr("src.etl.news.valencia_events_etl.requests.get", lambda url, **kw: _BytesResponse(EVENTBRITE_HTML))
    etl = ValenciaEventsETL()
    events = etl.get_eventbrite_events()

    assert len(events) == 2
    job_fair = events[0]
    assert job_fair["title"] == "Valencia Tech Job Fair Autumn"
    assert job_fair["start_date"] == f"{_YEAR}-11-26"
    assert job_fair["end_date"] == f"{_YEAR}-11-27"
    assert job_fair["url"] == "https://www.eventbrite.co.uk/e/valencia-tech-job-fair"
    assert job_fair["source"] == "eventbrite.com"
    assert job_fair["metadata"]["location"] == "1 Carrer de la Vall d'Aiora, València"

    # Missing endDate stays empty, malformed JSON-LD block is skipped
    comedia = events[1]
    assert comedia["start_date"] == f"{_YEAR}-09-05"
    assert comedia["end_date"] == ""


# ---------------------------------------------------------------------------
# meetup.com
# ---------------------------------------------------------------------------


def test_meetup_jsonld_events_normalize_timestamps_to_dates(monkeypatch):
    monkeypatch.setattr("src.etl.news.valencia_events_etl.requests.get", lambda url, **kw: _BytesResponse(MEETUP_HTML))
    etl = ValenciaEventsETL()
    events = etl.get_meetup_events()

    assert len(events) == 2
    beach = events[0]
    assert beach["title"] == "Sunset Beach Party & Dance"
    assert beach["start_date"] == f"{_YEAR}-08-28"  # 18:30Z collapses to its calendar date
    assert beach["end_date"] == f"{_YEAR}-08-28"
    assert beach["url"] == "https://www.meetup.com/premiumvalencia/events/316214965/"
    assert beach["source"] == "meetup.com"
    assert beach["metadata"]["location"] == "València"

    brunch = events[1]
    assert brunch["start_date"] == f"{_YEAR}-09-04"  # +02:00[Europe/Madrid] zone ignored
    assert brunch["end_date"] == ""  # empty endDate passes through
    assert brunch["metadata"]["location"] == "Café de las Horas"


def test_meetup_card_fallback_parses_time_datetime(monkeypatch):
    monkeypatch.setattr("src.etl.news.valencia_events_etl.requests.get", lambda url, **kw: _BytesResponse(MEETUP_CARDS_HTML))
    etl = ValenciaEventsETL()
    events = etl.get_meetup_events()

    assert len(events) == 2
    ruta = events[0]
    assert ruta["title"] == "Ruta de senderismo"
    assert ruta["date_text"] == f"{_YEAR}-09-10T19:00:00+02:00"
    quedada = events[1]
    assert quedada["date_text"] == ""


def test_meetup_returns_empty_on_total_failure(monkeypatch):
    def _boom(url, **kw):
        raise ConnectionError("network down")

    monkeypatch.setattr("src.etl.news.valencia_events_etl.requests.get", _boom)
    etl = ValenciaEventsETL()
    assert etl.get_meetup_events() == []


# ---------------------------------------------------------------------------
# transform pipeline + model round-trip
# ---------------------------------------------------------------------------


def test_process_prefers_preset_iso_dates_over_date_text():
    etl = ValenciaEventsETL()
    processed = etl.process_valencia_events(
        [
            {
                "title": "Preset ISO wins",
                "url": "https://example.com/1",
                "source": "eventbrite.com",
                "date_text": "junk without dates",
                "start_date": f"{_YEAR}-11-26",
                "end_date": f"{_YEAR}-11-27",
            }
        ]
    )
    assert processed[0]["start_date"] == f"{_YEAR}-11-26"
    assert processed[0]["end_date"] == f"{_YEAR}-11-27"


def test_process_parses_spanish_text_dates_when_not_preset():
    etl = ValenciaEventsETL()
    processed = etl.process_valencia_events(
        [
            {
                "title": "Fiesta grande",
                "url": "https://example.com/2",
                "source": "visitvalencia.com",
                "date_text": f"Del 17/08/{_YEAR} al 30/08/{_YEAR}",
            },
            {
                "title": "Sin fecha",
                "url": "https://example.com/3",
                "source": "visitvalencia.com",
                "date_text": "Próximamente",
            },
        ]
    )
    fiesta = processed[0]
    assert fiesta["start_date"] == f"{_YEAR}-08-17"  # normalized to ISO, not DD/MM/YYYY
    assert fiesta["end_date"] == f"{_YEAR}-08-30"
    assert processed[1]["start_date"] == ""  # undated stays empty
    assert processed[1]["end_date"] == ""


def test_transform_yields_models_with_round_tripped_dates():
    etl = ValenciaEventsETL()
    models = etl.transform(
        [
            {
                "title": "Evento con fecha",
                "url": "https://example.com/1",
                "source": "visitvalencia.com",
                "date_text": f"17/08/{_YEAR} - 30/08/{_YEAR}",
                "start_date": "",
                "end_date": "",
            },
            {
                "title": "Evento sin fecha",
                "url": "https://example.com/2",
                "source": "meetup.com",
                "date_text": "",
                "start_date": "",
                "end_date": "",
                "metadata": {"location": "Café de las Horas"},
            },
        ]
    )
    assert all(isinstance(m, ValenciaEvent) for m in models)
    dated = next(m for m in models if m.title == "Evento con fecha")
    assert dated.start_date == f"{_YEAR}-08-17"
    assert dated.end_date == f"{_YEAR}-08-30"
    undated = next(m for m in models if m.title == "Evento sin fecha")
    assert undated.start_date == ""

    # Pydantic round-trip keeps the ISO strings the tab expects
    dumped = dated.model_dump()
    assert dumped["start_date"] == f"{_YEAR}-08-17"
    restored = ValenciaEvent.model_validate(dumped)
    assert restored.start_date == dated.start_date
    assert restored.end_date == dated.end_date

    # Extractor metadata survives processing (ics exporter reads it)
    assert undated.metadata.get("location") == "Café de las Horas"
    assert undated.metadata.get("api_source") == "valencia_scraper"


def test_remove_duplicates_prefers_dated_record():
    etl = ValenciaEventsETL()
    merged = etl.remove_duplicates(
        [
            {"title": "Duplicado", "url": "", "source": "visitvalencia.com", "date_text": "", "start_date": "", "end_date": ""},
            {"title": "Duplicado", "url": "https://example.com/1", "source": "visitvalencia.com", "date_text": f"25/12/{_YEAR}", "start_date": f"{_YEAR}-12-25", "end_date": ""},
        ]
    )
    assert len(merged) == 1
    assert merged[0]["start_date"] == f"{_YEAR}-12-25"
    assert merged[0]["url"] == "https://example.com/1"
