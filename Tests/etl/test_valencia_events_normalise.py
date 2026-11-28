"""What a Valencia event record says after normalisation (T-143), and the vocabularies behind it.

``normalise_record`` is the one place a raw record becomes what the tab and the API read. These tests
pin the two rules the user was burned by before: every date is a real datetime with its zone and a
readable local form (T-178), and a date, a time, a venue or a price the source did not give stays
empty (T-193). No network, no file outside ``tmp_path``.
"""

import json
from datetime import datetime, timedelta
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.etl.news.valencia_events import categories, dates, zones
from src.etl.news.valencia_events.categories import CATEGORIES, infer_category, normalise_category
from src.etl.news.valencia_events.normalise import event_id, event_moments, normalise_record, parse_price, plain_description
from src.etl.news.valencia_events.stamps import RETENTION_DAYS, load_stamps, save_stamps, update_stamps
from src.etl.news.valencia_events.storage import write_text_atomic

MADRID = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 11, 28, 6, 24, 10, tzinfo=MADRID)
BASE = {"title": "Taller de paella", "source": "test.example", "url": "https://example.invalid/paella", "start_date": "2026-11-28", "end_date": "", "date_text": "28/11/2026"}


def _normalise(**overrides):
    event = {**BASE, **overrides}
    return normalise_record(event, now=NOW, stamps={})


# --- when: real datetimes with a zone, and the readable local form (T-178) ------------------------


def test_an_all_day_event_is_midnight_in_madrid_and_shows_its_day():
    record = _normalise()
    assert record["all_day"] is True
    assert record["start_at"] == "2026-11-28T00:00:00+01:00"
    assert record["end_at"] == "2026-11-29T00:00:00+01:00"  # the midnight after the day
    assert record["start_local"] == "sáb 28/11/2026"
    assert record["end_local"] == ""  # one day: no end to show
    assert record["start_time"] == "" and record["end_time"] == ""


def test_a_range_shows_its_last_day_and_ends_the_morning_after():
    record = _normalise(end_date="2026-11-30")
    assert (record["start_at"], record["end_at"]) == ("2026-11-28T00:00:00+01:00", "2026-12-01T00:00:00+01:00")
    assert (record["start_local"], record["end_local"]) == ("sáb 28/11/2026", "lun 30/11/2026")


def test_a_clock_becomes_a_timed_moment():
    record = _normalise(start_time="18:00", end_time="20:30", date_text="sáb 28 nov · 18:00 h")
    assert record["all_day"] is False
    assert (record["start_at"], record["end_at"]) == ("2026-11-28T18:00:00+01:00", "2026-11-28T20:30:00+01:00")
    assert (record["start_local"], record["end_local"]) == ("sáb 28/11/2026 · 18:00", "sáb 28/11/2026 · 20:30")
    assert (record["start_time"], record["end_time"]) == ("18:00", "20:30")


def test_a_timed_event_without_an_end_never_gets_one():
    record = _normalise(start_time="18:00")
    assert record["start_at"] == "2026-11-28T18:00:00+01:00"
    assert record["end_at"] == "" and record["end_local"] == ""


def test_a_utc_timestamp_is_shown_in_valencia_time_on_the_valencia_day():
    """Meetup prints UTC: an evening there is already the next day in Spain (T-178)."""
    evening = _normalise(date_text="2026-11-27T19:30:00.000Z", start_date="2026-11-27")
    assert (evening["all_day"], evening["start_at"], evening["start_local"]) == (False, "2026-11-27T20:30:00+01:00", "vie 27/11/2026 · 20:30")
    after_midnight = _normalise(date_text="2026-11-27T23:30:00.000Z", start_date="2026-11-27")
    assert (after_midnight["start_at"], after_midnight["start_local"]) == ("2026-11-28T00:30:00+01:00", "sáb 28/11/2026 · 00:30")
    august = _normalise(date_text="2026-08-28T18:30:00.000Z", start_date="2026-08-28")
    assert (august["start_at"], august["start_local"]) == ("2026-08-28T20:30:00+02:00", "vie 28/08/2026 · 20:30")  # summer time
    # The offset in brackets wins over a zone name printed next to it
    assert _normalise(date_text="2026-11-27T20:30:00+01:00[Europe/Madrid]", start_date="2026-11-27")["start_local"] == "vie 27/11/2026 · 20:30"


def test_a_timestamp_that_runs_on_later_days_keeps_the_last_day():
    record = _normalise(date_text="2026-11-27T19:30:00.000Z", start_date="2026-11-27", end_date="2026-11-29")
    assert (record["start_at"], record["end_at"], record["start_local"], record["end_local"]) == ("2026-11-27T20:30:00+01:00", "2026-11-30T00:00:00+01:00", "vie 27/11/2026 · 20:30", "dom 29/11/2026")


def test_a_timestamp_without_a_zone_is_valencia_time():
    record = _normalise(date_text="2026-11-27T23:30:00", start_date="2026-11-27")
    assert (record["start_at"], record["start_local"]) == ("2026-11-27T23:30:00+01:00", "vie 27/11/2026 · 23:30")


def test_the_zoned_datetimes_of_a_source_win_over_the_calendar_dates():
    record = _normalise(date_text="2026-12-02T17:00:00.000Z", start_time="18:00", start_datetime="2026-12-02T17:00:00+00:00", end_datetime="2026-12-02T19:00:00+00:00")
    assert (record["start_at"], record["end_at"], record["start_local"], record["end_local"]) == ("2026-12-02T18:00:00+01:00", "2026-12-02T20:00:00+01:00", "mié 02/12/2026 · 18:00", "mié 02/12/2026 · 20:00")


def test_an_undated_event_stays_undated():
    """Nothing in the record tells when it happens: no date is made up (T-193)."""
    record = _normalise(title="Sin fecha", start_date="", end_date="", date_text="Próximamente")
    assert (record["start_date"], record["end_date"], record["start_at"], record["end_at"], record["start_local"], record["end_local"]) == ("", "", "", "", "", "")
    assert record["all_day"] is True
    assert record["date_text"] == "Próximamente"


def test_a_text_without_a_year_is_not_dated():
    """The Filmoteca prints "sáb 28 nov": the day comes from the date box, never from the clock of the machine."""
    assert dates.parse_written_range("sáb 28 nov") == (None, None)
    assert dates.parse_written_range("Del 26 Dic al 4 Ene") == (None, None)
    assert dates.parse_written_range("Del 26 Dic al 4 Ene", default_year=2026) == (date(2026, 12, 26), date(2027, 1, 4))


def test_an_end_before_the_start_is_dropped():
    assert event_moments({"start_date": "2026-11-28", "end_date": "2026-11-20"}).end == datetime(2026, 11, 29, tzinfo=MADRID)


@pytest.mark.parametrize(
    ("text", "start", "end"),
    [
        ("del 28 al 29 noviembre de 2026", "2026-11-28", "2026-11-29"),
        ("Del 21 de octubre al 16 de diciembre de 2026", "2026-10-21", "2026-12-16"),  # the first day takes the year of the last
        ("Del 23 de marzo de 2026 al 1 de enero de 2027", "2026-03-23", "2027-01-01"),
        ("20 diciembre de 2026", "2026-12-20", ""),
        ("Del DO 29.11.26 al DO 14.02.27", "2026-11-29", "2027-02-14"),
        ("SA 28.11.26", "2026-11-28", ""),
        ("MI 09.12.26 | 19:29 h", "2026-12-09", ""),
        ("01 dic. 2026", "2026-12-01", ""),
        ("25 ene. 2026 – 08 dic. 2026", "2026-01-25", "2026-12-08"),
        ("Del 16/06/2025 al 31/12/2026", "2025-06-16", "2026-12-31"),
        ("5/6/7 febrero 2027", "2027-02-05", "2027-02-07"),
        ("27 i 28 novembre 2026 - Comiat de la producció", "2026-11-27", "2026-11-28"),
        ("29 noviembre 2026 - Hipersuerte en una de nuestras Ram Sessions", "2026-11-29", ""),
        ("de 10 a 12 años", None, None),  # ages, not dates
    ],
)
def test_written_dates_of_every_listing(text, start, end):
    expected_start = date.fromisoformat(start) if start else None
    expected_end = date.fromisoformat(end) if end else None
    assert dates.parse_written_range(text) == (expected_start, expected_end)


def test_a_day_that_does_not_exist_is_not_a_date():
    assert dates.parse_written_range("29 de febrero de 2026") == (None, None)
    assert dates.parse_written_range("29 de febrero de 2028") == (date(2028, 2, 29), None)


# --- how long: a permanent offering is tagged, not dated on every day --------------------------------


def test_an_event_that_last_the_whole_year_is_tagged_permanent():
    record = _normalise(start_date="2026-01-01", end_date="2026-12-31")
    assert "permanente" in record["tags"]
    assert (record["start_local"], record["end_local"]) == ("jue 01/01/2026", "jue 31/12/2026")
    assert "permanente" not in _normalise(start_date="2026-11-01", end_date="2026-11-30")["tags"]


# --- how much: the price is a number, 0 when free, None when the source says nothing (T-193) -------


@pytest.mark.parametrize(
    ("price_info", "is_free", "expected"),
    [
        ("", None, (None, None, "", None)),
        ("Gratis", None, (0.0, None, "EUR", True)),
        ("Entrada gratuita", None, (0.0, None, "EUR", True)),
        ("Desde 3 €", None, (3.0, None, "EUR", False)),
        ("12,50 - 25 €", None, (12.5, 25.0, "EUR", False)),
        ("10 USD", None, (10.0, None, "USD", False)),
        ("1.234,56 €", None, (1234.56, None, "EUR", False)),  # Spanish thousands mark
        ("1 234,56 €", None, (1234.56, None, "EUR", False)),
        ("12.50", None, (12.5, None, "EUR", False)),  # an English decimal point; a bare number is euros here
        ("$25.00", None, (25.0, None, "USD", False)),
        ("3.14159", None, (None, None, "", None)),  # not a price
        ("Consultar", None, (None, None, "", None)),  # a text that is not a price is not a price
        ("", True, (0.0, None, "EUR", True)),
        ("", False, (None, None, "", False)),  # not free, amount unknown: never 0
    ],
)
def test_the_price_text_becomes_a_number(price_info, is_free, expected):
    price = parse_price(price_info, is_free)
    assert (price.price, price.price_max, price.currency, price.is_free) == expected
    record = _normalise(price_info=price_info, is_free=is_free)
    assert (record["price"], record["price_max"], record["currency"], record["is_free"]) == expected


def test_a_title_that_says_gratuito_makes_the_event_free_and_says_so():
    record = _normalise(title="Visitas guiadas gratuitas a la torre")
    assert (record["price"], record["is_free"], record["metadata"]["price_basis"]) == (0.0, True, "title")
    assert _normalise(title="Concierto de Ara Malikian")["price"] is None
    assert "price_basis" not in _normalise(title="Concierto de Ara Malikian")["metadata"]


def test_the_price_text_of_a_listing_is_never_invented():
    """None of the listings prints a price: the record says so instead of a number."""
    record = _normalise(title="EL RETRAT DE DORIAN GRAY", price_info="")
    assert record["price"] is None and record["price_info"] == ""


# --- what: plain text, and one category ----------------------------------------------------------


def test_the_description_is_plain_text_and_never_repeats_the_title():
    assert _normalise(title="Taller", description="<p>Hola <b>mundo</b></p>")["description"] == "Hola mundo"
    assert plain_description("<p>Un <a href='https://x'>enlace</a> y **negrita**</p>", "Título") == "Un enlace y negrita"
    assert _normalise(title="Taller de paella", description="Taller de paella")["description"] == ""
    assert _normalise(description="   ")["description"] == ""
    long = "palabra " * 200
    assert len(_normalise(description=long)["description"]) <= 401


@pytest.mark.parametrize(
    ("title", "description", "expected"),
    [
        ("Concierto de Ara Malikian en València", "", "música"),
        ("Concierto Solidario: Carmina Burana de Carl Orff", "", "música"),
        ("Talleres de horchata artesanal en Alboraya con Món Orxata", "", "gastronomía"),  # "artesanal" is not "arte"
        ("Disfruta de la programación de otoño e invierno de L'ETNO Sona", "", ""),  # a programme is no kind in particular
        ("Cineforum: Blade Runner", "", "cine"),
        ("El folclore valenciano llena las calles cada domingo", "", "danza"),  # codespell:ignore -- Spanish
        ("Visitas guiadas por el Jardín Botánico de València", "", "visitas y rutas"),
        ("Taller familiar. La veueta del museu", "", "infantil"),
        ("Partidos del Valencia Basket en el Roig Arena", "", "deporte"),
        ("Nada que diga nada", "Una charla sobre cine", "cine"),  # the description is read when the title says nothing
    ],
)
def test_the_category_the_words_suggest(title, description, expected):
    assert infer_category(title, description) == expected


@pytest.mark.parametrize(
    ("said", "title", "expected"),
    [
        ("teatro", "Lo que sea", "teatro"),  # a value of the vocabulary is believed
        ("exposición", "Lo que sea", "arte"),  # a legacy hint is mapped
        ("Exposicion", "Lo que sea", "arte"),  # the hint is folded before the lookup
        ("tecnología", "Lo que sea", "tech"),
        ("meetup", "Charla sobre docker", "tech"),  # a value that says nothing: inferred
        ("eventbrite", "Partido de baloncesto", "deporte"),
        ("festival", "Festival de cine", "cine"),
        ("cultura", "Nada", "otro"),
        ("", "Nada", "otro"),
    ],
)
def test_a_category_becomes_one_of_the_vocabulary(said, title, expected):
    assert normalise_category(said, title) == expected
    assert expected in CATEGORIES


def test_the_default_of_a_source_and_a_technology_meetup():
    assert normalise_category("", "Nada", default_category="teatro") == "teatro"
    assert normalise_category("", "Quality vs. velocity: can you have both?", url="https://www.meetup.com/valencia-codes/events/317443844/") == "tech"
    assert normalise_category("", "Quality vs. velocity", url="https://www.meetup.com/valencia-senderismo/events/1/") == "otro"
    assert categories.meetup_group("https://www.meetup.com/Cloud-Native-Valencia/events/1/") == "cloud-native-valencia"
    assert _normalise(title="Nada", category="música")["category"] == "música"


def test_every_category_pattern_is_accent_free():
    """The texts are folded to plain ASCII before matching: a pattern with an accent could never match."""
    for pattern in categories._PATTERNS.values():
        assert categories.fold(pattern) == pattern


# --- where: the zone is read from tables, never guessed ---------------------------------------------


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"venue": "Sala Principal"}, "Quatre Carreres"),
        ({"venue": "Auditori"}, "Quatre Carreres"),
        ({"venue": "Teatre Martín i Soler - Palau de les Arts"}, "Quatre Carreres"),  # codespell:ignore -- venue name
        ({"venue": "Edificio Rialto"}, "Ciutat Vella"),
        ({"venue": "Teatre El Musical"}, "El Cabanyal"),
        ({"venue": "Teatre Principal de València al Teatre Martín i Soler"}, ""),  # two halls, two zones: neither  # codespell:ignore -- venue name
        ({"address": "C/ de Suīssa, 11, València"}, "Quatre Carreres"),
        ({"address": "Av. de la República de Guinea Ecuatorial, 4"}, "Poblats Marítims"),
        ({"address": "Carrer del Vall d'Aiora, 3"}, "Benicalap"),
        ({"address": "1 Plaça Manuel Sanchís Guarner, València"}, "Ruzafa"),
        ({"address": "C. de la Travesía, Poblados Marítimos, 46024 Valencia, Spain"}, "Poblats Marítims"),
        ({"address": "Carrer de la Vall d'Aiora, 3", "location": "El Carme"}, "Benicalap"),  # the street is more precise than a name
        ({"address": "Rascaña, 4"}, "Rascanya"),
        ({"address": "Carrer de Guillem de Castro, El Carme"}, "El Carme"),
        ({"venue": "Hackerspace Valencia"}, "Benimaclet"),
        ({"city": "Alcoi"}, "Alcoi"),
        ({"city": "Paterna"}, "Paterna"),
        ({"city": "València", "address": "Calle Desconocida 5"}, ""),  # Valencia itself is no zone
        ({"online": True, "venue": "Zoom"}, "Online"),
        ({"address": "Calle Desconocida 5, Valencia"}, ""),
        ({}, ""),
    ],
)
def test_the_zone_of_an_address_or_a_venue(fields, expected):
    assert zones.zone_of(**fields) == expected


def test_the_zone_values_are_consistent():
    assert zones.ONLINE_ZONE == "Online"
    assert zones.zone_label("") == "Sin zona" and zones.zone_label(None) == "Sin zona" and zones.zone_label("Ruzafa") == "Ruzafa"
    assert zones.zones_of([{"zone": "Ruzafa"}, {"zone": ""}, {"zone": "Ruzafa"}]) == ["", "Ruzafa"]
    # Every name a title can carry is a venue of the table, with one spelling of the zone
    assert all(name in zones.VENUE_ZONES for name in zones.TITLE_VENUES)
    assert "Poblats Marítimos" not in set(zones.VENUE_ZONES.values())


def test_a_venue_the_title_names_places_the_event_and_says_so():
    record = _normalise(title="Concierto de Miss Caffeina en la Sala Moon", url="")
    assert (record["zone"], record["venue"]) == ("Jesús", "Sala Moon")
    assert (record["metadata"]["zone_basis"], record["metadata"]["venue_basis"]) == ("title", "title")
    # The venue the source prints wins over one the title names
    explicit = _normalise(title="Charla en CaixaForum València", venue="La Rambleta", url="")
    assert (explicit["zone"], explicit["venue"], explicit["metadata"].get("zone_basis")) == ("Jesús", "La Rambleta", None)
    # Two venues of two zones in one title place nothing
    both = _normalise(title="Flamenco en el Teatro Ateneo Mercantil y en La Rambleta", url="")
    assert (both["zone"], both["venue"]) == ("", "")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Los grabados de Rembrandt, en CaixaForum València", ("CaixaForum València", "Quatre Carreres")),
        ("Museo & Tour del Valencia Basket en el ROIG ARENA", ("Roig Arena", "Quatre Carreres")),
        ("Ciclo de espectáculos de danza en Les Arts", ("Palau de les Arts", "Quatre Carreres")),
        ("Exposición «MEMPHIS Milano» en el MuVIM", ("MuVIM", "Ciutat Vella")),
        ("Desfile de perros en Bioparc València", ("Bioparc València", "Campanar")),
        ("Partidos de Beachbol en la playa de la Malva-rosa", ("La Malva-rosa", "La Malva-rosa")),
        ("La historia del Santo Cáliz", ("", "")),
        ("Concierto en Roig Arena y en La Rambleta", ("", "")),
    ],
)
def test_venues_named_in_a_title(title, expected):
    assert zones.venue_in_title(title) == expected


# --- identity and first detection ------------------------------------------------------------------


def test_the_event_id_is_stable_and_tells_events_apart():
    first = _normalise(title="Título", url="https://example.invalid/1/")
    assert first["event_id"] == _normalise(title="TÍTULO", url="https://example.invalid/1")["event_id"]  # case, accents and a trailing slash change nothing
    assert first["event_id"] == event_id("test.example", first["url"], first["title"], first["start_date"], "")
    assert event_id("s", "https://example.invalid/1", "A", "2026-11-28") != event_id("s", "https://example.invalid/1", "B", "2026-11-28")  # two events on one page
    assert event_id("s", "https://example.invalid/1", "A", "2026-11-28") != event_id("s", "https://example.invalid/1", "A", "2026-11-29")  # another day
    assert event_id("s", "https://example.invalid/1", "A", "2026-11-28", "18:00") != event_id("s", "https://example.invalid/1", "A", "2026-11-28", "20:00")  # another session
    assert event_id("s", "", "A", "2026-11-28") != event_id("other", "", "A", "2026-11-28")  # no page: the source tells them apart


def test_two_fairs_that_share_a_web_site_get_two_ids():
    """Feria Valencia lists FOOTOLOGY and FIMI on the same days with the same link."""
    footology = _normalise(title="FOOTOLOGY", start_date="2027-01-20", end_date="2027-01-22", url="https://fimi.es/")
    fimi = _normalise(title="FIMI-OTOÑO/INVIERNO", start_date="2027-01-20", end_date="2027-01-22", url="https://fimi.es/")
    assert footology["event_id"] != fimi["event_id"]


def test_a_new_event_is_first_detected_now_and_seen_now():
    record = _normalise()
    assert record["first_detected_at"] == "2026-11-28T06:24:10+01:00"
    assert record["first_detected_local"] == "sáb 28/11/2026 · 06:24"
    assert record["last_seen_at"] == "2026-11-28T06:24:10+01:00"


def test_the_first_detection_of_a_stored_event_is_kept():
    identifier = event_id("test.example", BASE["url"], BASE["title"], BASE["start_date"], "")
    first = "2026-11-20T04:00:00+01:00"
    record = normalise_record(BASE, now=NOW, stamps={identifier: {"first_detected_at": first, "last_seen_at": first}})
    assert record["first_detected_at"] == first
    assert record["last_seen_at"] == "2026-11-28T06:24:10+01:00"  # this run saw it again
    assert normalise_record(BASE, now=NOW, stamps={identifier: {"first_detected_at": "garbage", "last_seen_at": ""}})["first_detected_at"] == "2026-11-28T06:24:10+01:00"


def test_the_record_keeps_the_fields_of_the_original_shape_and_adds_the_new_ones():
    record = _normalise()
    for field in ("title", "url", "source", "category", "description", "start_date", "end_date", "date_text", "venue", "price_info", "is_free", "metadata"):
        assert field in record
    for field in ("event_id", "start_time", "end_time", "all_day", "start_at", "end_at", "start_local", "end_local", "address", "city", "zone", "price", "price_max", "currency", "tags", "first_detected_at", "first_detected_local", "last_seen_at"):
        assert field in record
    assert normalise_record(BASE, now=NOW, stamps={}, source_label="Feria Valencia")["metadata"]["source_label"] == "Feria Valencia"
    assert normalise_record(BASE, now=NOW, stamps={})["metadata"].get("source_label") is None


def test_a_url_is_written_one_way():
    assert _normalise(url="HTTPS://WWW.Example.invalid/paella/")["url"] == "https://example.invalid/paella"
    assert _normalise(url="")["url"] == ""
    assert _normalise(url=None)["url"] == ""


def test_online_events_are_tagged_and_zoned():
    record = _normalise(tags=["online"], venue="Zoom")
    assert (record["zone"], record["tags"]) == ("Online", ["online"])
    assert _normalise(metadata={"online": True})["tags"] == ["online"]


# --- the state file of first detections ------------------------------------------------------------


def test_stamps_keep_the_first_detection_and_move_the_last_sighting():
    first_run = update_stamps({}, ["a", "b"], datetime(2026, 11, 20, tzinfo=MADRID))
    assert first_run == {"a": {"first_detected_at": "2026-11-20T00:00:00+01:00", "last_seen_at": "2026-11-20T00:00:00+01:00"}, "b": {"first_detected_at": "2026-11-20T00:00:00+01:00", "last_seen_at": "2026-11-20T00:00:00+01:00"}}
    later = datetime(2026, 11, 28, tzinfo=MADRID)
    second_run = update_stamps(first_run, ["a", "c"], later)
    assert second_run["a"] == {"first_detected_at": "2026-11-20T00:00:00+01:00", "last_seen_at": "2026-11-28T00:00:00+01:00"}  # never moved
    assert second_run["b"]["last_seen_at"] == "2026-11-20T00:00:00+01:00"  # not seen, kept as it was
    assert second_run["c"]["first_detected_at"] == "2026-11-28T00:00:00+01:00"


def test_stamps_forget_an_event_nobody_has_seen_for_a_long_time():
    old = datetime(2026, 1, 1, tzinfo=MADRID)
    stamps = update_stamps({}, ["gone", "back"], old)
    much_later = old + timedelta(days=RETENTION_DAYS + 1)
    result = update_stamps(stamps, ["back"], much_later)
    assert "gone" not in result
    assert result["back"]["first_detected_at"] == "2026-01-01T00:00:00+01:00"


def test_the_state_file_round_trips_and_survives_garbage(tmp_path: Path):
    path = tmp_path / "sub" / "detected_at.json"
    assert load_stamps(path) == {}  # absent
    save_stamps(path, {"x": {"first_detected_at": "2026-11-20T00:00:00+01:00", "last_seen_at": "2026-11-21T00:00:00+01:00"}}, NOW)
    assert load_stamps(path) == {"x": {"first_detected_at": "2026-11-20T00:00:00+01:00", "last_seen_at": "2026-11-21T00:00:00+01:00"}}
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1
    path.write_text("not json", encoding="utf-8")
    assert load_stamps(path) == {}
    path.write_text(json.dumps({"events": {"a": "nope", "b": {}, "c": {"first_detected_at": "2026-11-20T00:00:00+01:00"}}}), encoding="utf-8")
    assert load_stamps(path) == {"c": {"first_detected_at": "2026-11-20T00:00:00+01:00", "last_seen_at": "2026-11-20T00:00:00+01:00"}}


# --- writing ---------------------------------------------------------------------------------------


def test_a_file_is_replaced_whole(tmp_path: Path):
    path = tmp_path / "out" / "events.json"
    path.parent.mkdir()
    path.write_text("old", encoding="utf-8")
    write_text_atomic(path, "nuevo café")
    assert path.read_text(encoding="utf-8") == "nuevo café"
    assert [item.name for item in path.parent.iterdir()] == ["events.json"]  # no temporary file left behind
    write_text_atomic(tmp_path / "deeper" / "a" / "b.json", "x")
    assert (tmp_path / "deeper" / "a" / "b.json").read_text(encoding="utf-8") == "x"
