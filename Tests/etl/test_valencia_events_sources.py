"""The new sources of Valencia events (T-143): what each listing gives, read from a trimmed copy of its page.

Every fixture under ``fixtures/valencia_events/`` is a slice of the public page as it answered on
2026-11-28: the few cards the parser needs and nothing else. No network: ``parse`` gets bytes.

What these tests pin, per source: the dates are the ones the page prints (nothing is invented, T-193),
the clock and the venue are kept when the page has them and stay empty when it does not, and the
records are in the shape the composer reads (``records.build_record``).
"""

from datetime import date
from pathlib import Path

import pytest

from src.etl.news.valencia_events.records import CITY_VALENCIA
from src.etl.news.valencia_events.sources import LEGACY_SOURCE_KEYS, SOURCE_BY_KEY, SOURCES
from src.etl.news.valencia_events.sources import ayuntamiento, escalante, feriavalencia, filmoteca, ivam, larambleta, lesarts, meetup_tech, teatre_principal, visitvalencia_monthly

FIXTURES = Path(__file__).parent / "fixtures" / "valencia_events"
FETCH_DAY = date(2026, 11, 28)  # the day the fixture pages were read


def _page(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _assert_well_formed(records, source):
    """Every record carries its source id, a title and an ISO start date; a URL, when there is one, is absolute."""
    assert records, "the fixture must yield records"
    for record in records:
        assert record["source"] == source
        assert record["title"].strip()
        assert record["start_date"] == "" or date.fromisoformat(record["start_date"])
        assert record["url"] == "" or record["url"].startswith("https://")
        assert record["end_date"] == "" or record["end_date"] >= record["start_date"]


# --- the registry ---------------------------------------------------------------------------------


def test_the_registry_lists_thirteen_sources_with_unique_keys():
    keys = [source.key for source in SOURCES]
    assert len(keys) == 13
    assert len(set(keys)) == 13
    assert SOURCE_BY_KEY.keys() == set(keys)


def test_the_three_legacy_sources_come_first_and_are_marked():
    assert [source.key for source in SOURCES[:3]] == ["visitvalencia.com", "meetup.com", "eventbrite.com"]
    assert LEGACY_SOURCE_KEYS == {"visitvalencia.com", "meetup.com", "eventbrite.com"}


@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source.key)
def test_every_source_is_keyless_and_fetchable(source):
    assert source.label
    assert source.urls, "the pages a run reads are listed, for the report"
    assert all(url.startswith("https://") for url in source.urls)
    assert callable(source.fetch)
    assert "key" not in source.key and "@" not in source.key


def test_every_parser_emits_a_registered_source():
    """A record whose source is not in the registry would lose its label in the report."""
    parsed = [
        ayuntamiento.parse(_page("ayuntamiento_agenda.html")),
        visitvalencia_monthly.collect([_page("visitvalencia_monthly.html")]),
        filmoteca.parse(_page("filmoteca.html")),
        lesarts.parse(_page("lesarts.html")),
        teatre_principal.parse(_page("teatre_principal.html")),
        escalante.parse(_page("escalante.html")),
        larambleta.parse(_page("larambleta.html")),
        feriavalencia.parse(_page("feriavalencia.html"), FETCH_DAY),
        ivam.parse_page(_page("ivam_actividades.html"), "activities"),
        ivam.parse_page(_page("ivam_exposiciones.html"), "exhibitions"),
        meetup_tech.parse(_page("meetup_tech.html")),
    ]
    for records in parsed:
        assert {record["source"] for record in records} <= SOURCE_BY_KEY.keys()


# --- Ayuntamiento de València ---------------------------------------------------------------------


def test_ayuntamiento_reads_the_embedded_array_and_maps_its_categories():
    records = ayuntamiento.parse(_page("ayuntamiento_agenda.html"))
    _assert_well_formed(records, ayuntamiento.SOURCE)
    assert len(records) == 5
    by_title = {record["title"]: record for record in records}
    pergola = by_title["Ciclo 'Els concerts de la Pèrgola'"]
    # Epoch milliseconds read as the Valencia calendar day; the page prints no clock, venue or price
    assert pergola["start_date"] == "2026-11-14" and pergola["end_date"] == "2026-12-19"
    assert pergola["category"] == "música"
    assert pergola["start_time"] == "" and pergola["venue"] == "" and pergola["price_info"] == ""
    assert pergola["is_free"] is None
    assert pergola["city"] == CITY_VALENCIA
    assert pergola["url"].startswith(ayuntamiento.DETAIL_URL)
    assert pergola["metadata"]["source_category"] == "MÚSICA"
    assert by_title["Exposición 'Jaume I, regnar el futur' - MuVIM"]["category"] == "arte"
    assert by_title["Feria de atracciones de Navidad"]["category"] == "ferias"


def test_ayuntamiento_leaves_out_programmes_and_permanent_facilities():
    """A year-long museum agenda is not an event: it would sit on every day of the calendar."""
    titles = {record["title"] for record in ayuntamiento.parse(_page("ayuntamiento_agenda.html"))}
    assert "Museo de Prehistoria de València - Actividades" not in titles
    assert not any("rogramaci" in title for title in titles)
    assert all(record["metadata"]["span_days"] < 180 for record in ayuntamiento.parse(_page("ayuntamiento_agenda.html")))


def test_ayuntamiento_page_without_the_array_gives_nothing():
    assert ayuntamiento.parse(b"<html><body>Mantenimiento</body></html>") == []
    assert ayuntamiento.parse(b"<script>var eventosInicio = [{broken;\n</script>") == []


# --- Visit València, monthly agenda ----------------------------------------------------------------


def test_monthly_agenda_merges_the_cards_of_one_event_into_one_span():
    records = visitvalencia_monthly.collect([_page("visitvalencia_monthly.html")])
    _assert_well_formed(records, visitvalencia_monthly.SOURCE)
    by_title = {record["title"]: record for record in records}
    assert len(records) == 3
    ruzafa = by_title["Explora Ruzafa y su historia con esta visita cultural"]
    # Three cards of the same event: 16/06/2025–31/12/2026, 23/06/2025–07/01/2027, 30/06/2025–14/01/2027
    assert (ruzafa["start_date"], ruzafa["end_date"]) == ("2025-06-16", "2027-01-14")
    assert ruzafa["metadata"]["sessions"] == 3
    assert ruzafa["url"] == "https://www.visitvalencia.com/agenda-valencia/explora-ruzafa-y-su-historia-con-esta-visita-cultural"
    assert ruzafa["venue"] == "" and ruzafa["category"] == ""  # the listing names neither


def test_monthly_agenda_single_day_and_card_without_date():
    records = visitvalencia_monthly.collect([_page("visitvalencia_monthly.html")])
    single = next(record for record in records if record["title"] == "Ciclo de conciertos de flamenco en Les Arts")
    assert (single["start_date"], single["end_date"], single["date_text"]) == ("2026-11-27", "", "27/11/2026")
    # The fixture holds five dated cards: three of one event, and two of one day each
    assert sum(record["metadata"]["sessions"] for record in records) == 5


def _card(node_id: str, title: str, dates: str | None) -> str:
    date_div = f'<div class="card__date">{dates}</div>' if dates is not None else ""
    return f'<div class="card card--event" data-history-node-id="{node_id}" about="/agenda-valencia/x">{date_div}<h3 class="card__heading">{title}</h3></div>'


def test_monthly_agenda_skips_a_card_without_a_readable_date():
    html = "<html><body>" + _card("1", "Sin fecha", "Próximamente") + _card("2", "Con fecha", "12/12/2026") + _card("3", "Sin dia", None) + "</body></html>"
    records = visitvalencia_monthly.collect([html.encode()])
    assert [(record["title"], record["start_date"], record["end_date"]) for record in records] == [("Con fecha", "2026-12-12", "")]
    assert visitvalencia_monthly.collect([b"<html><body></body></html>"]) == []


def test_monthly_agenda_merges_touching_spans_only():
    merge = visitvalencia_monthly.merge_intervals
    a, b, c = date(2026, 11, 1), date(2026, 11, 10), date(2026, 11, 11)
    # Overlapping spans, whatever the order they come in
    assert merge([(b, c), (a, b)]) == [(a, c)]
    # Touching: the next starts the day after the previous ends
    assert merge([(a, a), (date(2026, 11, 2), date(2026, 11, 4))]) == [(a, date(2026, 11, 4))]
    # A gap of one day keeps two spans
    assert merge([(a, a), (date(2026, 11, 3), date(2026, 11, 3))]) == [(a, a), (date(2026, 11, 3), date(2026, 11, 3))]


def test_monthly_agenda_month_url():
    assert visitvalencia_monthly.month_url("2026-12") == visitvalencia_monthly.AGENDA_URL + "?date=2026-12"


# --- Filmoteca ------------------------------------------------------------------------------------


def test_filmoteca_keeps_the_clock_and_the_hall_and_splits_the_sessions():
    records = filmoteca.parse(_page("filmoteca.html"))
    _assert_well_formed(records, filmoteca.SOURCE)
    sherlock = [record for record in records if record["title"] == "LA VIDA PRIVADA DE SHERLOCK HOLMES"]
    assert [(record["start_date"], record["start_time"]) for record in sherlock] == [("2026-11-28", "18:00"), ("2026-11-29", "20:00")]
    first = sherlock[0]
    assert first["venue"] == "Edificio Rialto" and first["category"] == "cine"
    assert first["all_day"] is False and first["end_time"] == "" and first["price_info"] == ""
    assert first["metadata"]["cycle"] == "BILLY WILDER"
    assert first["metadata"]["ticket_url"].startswith("https://taquilla.ivc.gva.es/")
    assert "Billy Wilder" in first["description"]


# --- Palau de les Arts -----------------------------------------------------------------------------


def test_lesarts_reads_the_date_boxes_and_skips_the_ones_without_a_date():
    records = lesarts.parse(_page("lesarts.html"))
    _assert_well_formed(records, lesarts.SOURCE)
    by_title = {record["title"]: record for record in records}
    assert set(by_title) == {"FRANCO FAGIOLI", "Matins a Les Arts", "LOHENGRIN", "PLEC"}  # the first box of the page has no date box
    fagioli = by_title["FRANCO FAGIOLI"]
    assert (fagioli["start_date"], fagioli["end_date"], fagioli["start_time"]) == ("2026-11-28", "", "19:00")
    assert fagioli["venue"] == "Sala Principal" and fagioli["category"] == "música"
    assert fagioli["description"] == "FARINELLI"


def test_lesarts_resolves_a_range_that_crosses_new_year():
    matins = next(record for record in lesarts.parse(_page("lesarts.html")) if record["title"] == "Matins a Les Arts")
    # "Del DO 29.11.26 al DO 14.02.27"
    assert (matins["start_date"], matins["end_date"], matins["start_time"]) == ("2026-11-29", "2027-02-14", "12:00")


def test_lesarts_keeps_the_hour_the_page_prints_even_when_it_looks_odd():
    """The page says 19:29 h for a preview: the source's text is kept, not corrected (T-193)."""
    lohengrin = next(record for record in lesarts.parse(_page("lesarts.html")) if record["title"] == "LOHENGRIN")
    assert (lohengrin["start_date"], lohengrin["start_time"], lohengrin["venue"]) == ("2026-12-09", "19:29", "Aula Magistral")


# --- Teatre Principal ------------------------------------------------------------------------------


def test_teatre_principal_names_the_hall_the_company_plays_in():
    records = teatre_principal.parse(_page("teatre_principal.html"))
    _assert_well_formed(records, teatre_principal.SOURCE)
    assert len(records) == 4
    assert all(record["category"] == "teatro" for record in records)
    dorian = records[0]
    # "del 28 al 29 noviembre de 2026 · Teatre Principal de València al Teatre Martín i Soler"  # codespell:ignore -- venue name
    assert (dorian["start_date"], dorian["end_date"], dorian["venue"]) == ("2026-11-28", "2026-11-29", "Teatre Martín i Soler")  # codespell:ignore -- venue name
    assert dorian["metadata"]["company"] == "Teatre Principal de València"
    assert dorian["all_day"] is True and dorian["price_info"] == ""


def test_teatre_principal_venue_of():
    assert teatre_principal.venue_of("Teatre Principal de València al Teatre Martín i Soler") == ("Teatre Martín i Soler", "Teatre Principal de València")  # codespell:ignore -- venue name
    assert teatre_principal.venue_of("Teatre Principal de València") == ("Teatre Principal de València", "")
    assert teatre_principal.venue_of("") == (teatre_principal.DEFAULT_VENUE, "")


def test_teatre_principal_skips_the_season_pass_and_an_undated_production():
    html = (
        b'<div class="minificha"><p class="fecha">20 diciembre de 2026</p><h2><a href="https://ivc.gva.es/x">ABONO 2027</a></h2></div>'
        b'<div class="minificha"><p class="fecha">Proximamente</p><h2><a href="https://ivc.gva.es/y">Una obra</a></h2></div>'
        b'<div class="minificha"><p class="fecha">20 diciembre de 2026</p><h2><a href="https://ivc.gva.es/z">Otra obra</a></h2></div>'
    )
    records = teatre_principal.parse(html)
    assert [(record["title"], record["start_date"]) for record in records] == [("Otra obra", "2026-12-20")]


# --- Escalante ------------------------------------------------------------------------------------


def test_escalante_keeps_the_hall_the_audience_and_the_company():
    records = escalante.parse(_page("escalante.html"))
    _assert_well_formed(records, escalante.SOURCE)
    assert len(records) == 4
    eruga = records[0]
    assert eruga["title"] == "Rrrrrr. Història d\u2019una eruga"
    assert (eruga["start_date"], eruga["end_date"], eruga["date_text"]) == ("2026-11-25", "2026-11-30", "25/11/2026 - 30/11/2026")
    assert eruga["category"] == "infantil" and eruga["tags"] == ["teatro"]
    assert eruga["venue"] == "Centro Cultural Nau 3 Ribes" and eruga["description"] == "Príncep Totilau"
    assert eruga["metadata"]["audience"] == "De 2 a 6 años"
    selva = records[1]
    assert (selva["start_date"], selva["end_date"]) == ("2026-12-18", "")  # "18/12/2026 - 18/12/2026" is one day
    assert selva["venue"] == "Teatre Martín i Soler - Palau de les Arts"  # codespell:ignore -- venue name


# --- La Rambleta ----------------------------------------------------------------------------------


def test_larambleta_reads_the_labels_and_the_written_dates():
    records = larambleta.parse(_page("larambleta.html"))
    _assert_well_formed(records, larambleta.SOURCE)
    by_title = {record["title"]: record for record in records}
    assert set(by_title) == {"ECLIPSI TOTAL", "Veladas – Ghibli Tributo", "Muestra de Teatro Emergente – \u2018El gran sarau\u2019", "Concierto Solidario: Carmina Burana de Carl Orff"}
    assert (by_title["ECLIPSI TOTAL"]["start_date"], by_title["ECLIPSI TOTAL"]["end_date"]) == ("2026-11-27", "2026-11-28")
    assert by_title["Veladas – Ghibli Tributo"]["category"] == "música"  # labels: musica, teatro
    assert by_title["Muestra de Teatro Emergente – \u2018El gran sarau\u2019"]["category"] == "teatro"  # labels: escenicas, la-cambra
    assert all(record["venue"] == larambleta.VENUE and record["start_time"] == "" for record in records)


def test_larambleta_drops_blog_cards_and_the_placeholder_date():
    titles = {record["title"] for record in larambleta.parse(_page("larambleta.html"))}
    assert "Ram Sessions 2026" not in titles  # labelled blog
    assert not any("9999" in record["date_text"] for record in larambleta.parse(_page("larambleta.html")))


def test_larambleta_a_title_that_says_what_the_show_is_wins_over_a_wrong_label():
    """The page files a choral concert under ``humor``; "Concierto" in the title is the better evidence."""
    carmina = next(record for record in larambleta.parse(_page("larambleta.html")) if "Carmina" in record["title"])
    assert carmina["category"] == "música"
    assert "humor" in carmina["metadata"]["labels"]
    assert larambleta.category_of(["humor"], "Concierto Solidario") == "música"
    assert larambleta.category_of(["humor"], "Un monologo") == "humor"
    assert larambleta.category_of(["ram-club"], "Ram Session") == ""


# --- Feria Valencia -------------------------------------------------------------------------------


def test_feriavalencia_dates_the_list_from_the_day_of_the_fetch():
    records = feriavalencia.parse(_page("feriavalencia.html"), FETCH_DAY)
    _assert_well_formed(records, feriavalencia.SOURCE)
    assert [(record["start_date"], record["end_date"]) for record in records] == [
        ("2026-11-27", "2026-11-29"),
        ("2026-11-29", ""),
        ("2026-12-03", "2026-12-05"),
        ("2026-12-04", "2026-12-06"),
        ("2026-12-16", "2026-12-17"),
    ]
    assert all(record["venue"] == feriavalencia.VENUE for record in records)
    assert records[0]["date_text"] == "27 Nov / 29 Nov"


def test_feriavalencia_category_comes_from_the_sectors():
    records = feriavalencia.parse(_page("feriavalencia.html"), FETCH_DAY)
    by_title = {record["title"]: record for record in records}
    assert by_title["2 RUEDAS"]["category"] == "ferias"
    assert by_title["EXPO 42K FERIA VALENCIA"]["category"] == "deporte"
    assert by_title["EDOS – Cumbre Europea de Operadores de Drones"]["category"] == "tech"
    assert by_title["EDOS – Cumbre Europea de Operadores de Drones"]["tags"] == ["profesional"]  # codespell:ignore -- Spanish
    assert by_title["Elecciones Seccionales y CPCCS Ecuador 2027"]["category"] == "otro"


def test_feriavalencia_invents_no_year_when_the_list_is_not_the_calendar_it_expects():
    """The page prints "27 Nov" without a year: the year comes from the day of the fetch, or not at all."""
    assert feriavalencia.parse(_page("feriavalencia.html"), date(2027, 6, 1)) == []
    assert feriavalencia.parse(b"<html><body>Sin eventos</body></html>", FETCH_DAY) == []


def test_feriavalencia_crosses_new_year_inside_the_list():
    html = (
        b'<div class="evento sector-feria"><h3 class="elementor-heading-title"><a href="https://feriavalencia.com/a">Feria A</a></h3><ul class="elementor-post-info"><li>28 Dic</li><li>/ 30 Dic</li></ul></div>'
        b'<div class="evento sector-feria"><h3 class="elementor-heading-title"><a href="https://feriavalencia.com/b">Feria B</a></h3><ul class="elementor-post-info"><li>8 Ene</li><li>/ 10 Ene</li></ul></div>'
    )
    records = feriavalencia.parse(html, date(2026, 12, 20))
    assert [(record["title"], record["start_date"], record["end_date"]) for record in records] == [("Feria A", "2026-12-28", "2026-12-30"), ("Feria B", "2027-01-08", "2027-01-10")]


# --- IVAM -----------------------------------------------------------------------------------------


def test_ivam_reads_the_cards_and_categories_from_the_typology():
    activities = ivam.parse_page(_page("ivam_actividades.html"), "activities")
    exhibitions = ivam.parse_page(_page("ivam_exposiciones.html"), "exhibitions")
    for records in (activities, exhibitions):
        _assert_well_formed(records, ivam.SOURCE)
        assert all(record["venue"] == "IVAM" and record["city"] == CITY_VALENCIA for record in records)
    by_title = {record["title"]: record for record in activities}
    assert (by_title["Encuentro con T. J. Demos en 'Pensamiento Anfibio'"]["start_date"], by_title["Encuentro con T. J. Demos en 'Pensamiento Anfibio'"]["category"]) == ("2026-12-01", "charlas y talleres")
    assert by_title["Taller familiar. La veueta del museu"]["category"] == "infantil"
    # "25 ene. 2026 – 08 dic. 2026"
    assert (by_title["Taller familiar. La veueta del museu"]["start_date"], by_title["Taller familiar. La veueta del museu"]["end_date"]) == ("2026-01-25", "2026-12-08")
    shows = {record["title"]: record for record in exhibitions}
    assert shows["Regina de Miguel. Un mundo turbiamente vivo"]["category"] == "arte"
    assert (shows["Regina de Miguel. Un mundo turbiamente vivo"]["start_date"], shows["Regina de Miguel. Un mundo turbiamente vivo"]["end_date"]) == ("2026-10-28", "2027-04-11")


# --- Meetup, technology ---------------------------------------------------------------------------


def test_meetup_tech_keeps_valencia_and_shows_the_local_hour():
    records = meetup_tech.parse(_page("meetup_tech.html"))
    _assert_well_formed(records, meetup_tech.SOURCE)
    assert len(records) == 4  # the fifth event of the fixture is held by another city's group
    assert all(record["category"] == "tech" for record in records)
    codes = records[0]
    assert codes["title"] == "Quality vs. velocity: can you have both?"
    # 17:00Z on 2 December is 18:00 in València
    assert (codes["start_date"], codes["start_time"], codes["date_text"]) == ("2026-12-02", "18:00", "2026-12-02T17:00:00.000Z")
    assert codes["venue"] == "Deutsche Telekom Office" and codes["address"].startswith("Av. del Marqués de Sotelo")
    assert codes["metadata"]["group"] == "valencia-codes"


def test_meetup_tech_is_in_valencia():
    assert meetup_tech.is_in_valencia("Valencia, Valencia", "https://www.meetup.com/some-group/events/1/")
    assert meetup_tech.is_in_valencia("Madrid", "https://www.meetup.com/python-valencia/events/1/")
    assert not meetup_tech.is_in_valencia("Alicante", "https://www.meetup.com/alicante-devs/events/1/")
    assert not meetup_tech.is_in_valencia("", "")
