"""Tests for the cinema sessions ETL: one parser per source, the shared helpers and the pipeline.

No test touches the network. The parsers read trimmed excerpts of the real listing pages from
``Tests/etl/fixtures/cinema_*.html``; the pipeline reads them through a fake page fetcher, and a real
``requests.get`` is replaced by one that fails the test.
"""

import json
import os
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import requests
from pydantic import ValidationError

from src.config.settings import get_settings
from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.cinema import babel, cinema_sessions_etl, exhicine, filmaffinity, filmoteca
from src.etl.cinema import common
from src.etl.cinema.cinema_sessions_etl import OUTPUT_FILE, SOURCES, STATUS_FILE, CinemaSessionsETL
from src.etl.cinema.common import Listing, ListingResult, PageFetcher, SourceUnavailable
from src.models.cinema import CinemaSession, session_id, session_key
from src.watchers.data_freshness_watcher import SOURCE_FILES, assess_freshness

FIXTURES = Path(__file__).parent / "fixtures"
REFERENCE_DAY = date(2026, 11, 28)  # a Saturday: the day the fixture pages were saved
TIVOLI_PAGE = "cinema_exhicine_tivoli.html"

# Two pages a source must not take for a listing: a bot check, and a cartelera with nothing on.
BLOCKED_PAGE = b"<!doctype html><html><head><title>Just a moment...</title></head><body>Checking your browser before accessing the site.</body></html>"
EMPTY_FILMAFFINITY_PAGE = b'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Cartelera Abc El Saler - Filmaffinity</title></head><body><h1 id="main-title">Abc El Saler</h1><div class="th-data"><div class="street"><div>Av. del Saler, 16</div>Valencia, <a>Valencia/Val\xc3\xa8ncia</a> (Espa\xc3\xb1a)</div></div></body></html>'


def fixture(name: str) -> bytes:
    """Read a trimmed listing page."""
    return (FIXTURES / name).read_bytes()


def stub_response(status: int = 200, content: bytes = b"<html></html>") -> object:
    """An object with what ``PageFetcher`` reads off a ``requests`` response."""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)

    return type("Response", (), {"status_code": status, "content": content, "raise_for_status": raise_for_status})()


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path, monkeypatch):
    """Keep every write of a real ``run()`` out of the project's ``data/``.

    BaseETL resolves all of its paths from the cached settings singleton: its directories, the circuit
    breaker, the run summaries and the aggregated metrics. Patching ``project_root`` on that singleton
    sends them all to tmp_path.
    """
    monkeypatch.setattr(get_settings(), "project_root", str(tmp_path))


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """A real HTTP call fails the test: the pages come from fixtures or from the fake fetcher."""

    def refuse(*args, **kwargs):
        raise AssertionError("the test tried to reach the network")

    monkeypatch.setattr(common.requests, "get", refuse)


class FakeFetcher:
    """Stands in for ``PageFetcher``: answers from a dictionary of pages and records what was asked for."""

    def __init__(self, pages: dict[str, bytes] | None = None, default: bytes | None = None, failing: Callable[[str], bool] | None = None):
        self.pages = pages if pages is not None else {}
        self.default = default
        self.failing = failing or (lambda url: False)
        self.urls_requested: list[str] = []

    def get(self, url: str) -> bytes:
        """Answer one page: the one asked for, the default, an error, or a refusal."""
        self.urls_requested.append(url)
        if self.failing(url):
            raise SourceUnavailable(f"{url}: HTTP 403, the site refuses automated reads")
        if url in self.pages:
            return self.pages[url]
        if self.default is None:
            raise SourceUnavailable(f"{url}: not a cinema cartelera page")
        return self.default


ALL_LISTINGS = {"exhicine": exhicine.LISTINGS, "babel": babel.LISTINGS, "filmoteca": filmoteca.LISTINGS, "filmaffinity": filmaffinity.LISTINGS}
EVERY_URL = [listing.url for listings in ALL_LISTINGS.values() for listing in listings]
# One page per URL of the pipeline: the four trimmed listings, and an empty cartelera for the other cinemas.
PAGES = {
    exhicine.LISTINGS[0].url: fixture("cinema_exhicine_tivoli.html"),
    babel.LISTINGS[0].url: fixture("cinema_babel_cartelera.html"),
    filmoteca.LISTINGS[0].url: fixture("cinema_filmoteca_programacion.html"),
    filmaffinity.LISTINGS[0].url: fixture("cinema_filmaffinity_kinepolis.html"),
    filmaffinity.LISTINGS[5].url: fixture("cinema_filmaffinity_yelmo.html"),
}


def stub_pages(monkeypatch, **fetcher_options) -> FakeFetcher:
    """Make the pipeline read the fixture pages through a ``FakeFetcher`` built with ``fetcher_options``."""
    fetcher = FakeFetcher(**({"pages": dict(PAGES), "default": EMPTY_FILMAFFINITY_PAGE} | fetcher_options))

    def build() -> FakeFetcher:
        return fetcher

    monkeypatch.setattr(cinema_sessions_etl, "PageFetcher", build)
    monkeypatch.setattr(cinema_sessions_etl, "today", lambda: REFERENCE_DAY)
    return fetcher


def session(title: str, time: str, **fields) -> dict:
    """A minimal session record for the pipeline, at Cine Tívoli today."""
    return {"title": title, "cinema": "Cine Tívoli", "city": "Burjassot", "date": "2026-11-28", "time": time, "source": "exhicine.es", **fields}


# --- the model -------------------------------------------------------------------------------------


class TestCinemaSession:
    def test_a_session_gets_an_id_derived_from_what_makes_it_one(self):
        first = CinemaSession(**session("EL GATO CON SOMBRERO", "17:00"))
        again = CinemaSession(**session("EL GATO CON SOMBRERO", "17:00"))
        later = CinemaSession(**session("EL GATO CON SOMBRERO", "22:30"))
        assert first.id == again.id
        assert first.id == session_id(session_key(cinema="Cine Tívoli", title="el gato con sombrero", date="2026-11-28", time="17:00"))
        assert later.id != first.id

    def test_the_key_tells_a_plain_an_imax_and_a_dubbed_screening_apart(self):
        plain = session_key(cinema="c", title="t", date="2026-11-28", time="19:00")
        imax = session_key(cinema="c", title="t", date="2026-11-28", time="19:00", format="IMAX")
        dubbed = session_key(cinema="c", title="t", date="2026-11-28", time="19:00", version="DOB")
        assert len({plain, imax, dubbed}) == 3

    def test_the_day_and_the_time_must_be_what_the_watcher_and_the_tab_read(self):
        with pytest.raises(ValidationError):
            CinemaSession(**session("X", "17:00", date="28/11/2026"))
        with pytest.raises(ValidationError):
            CinemaSession(**session("X", "17:00", date="2026-02-30"))
        with pytest.raises(ValidationError):
            CinemaSession(**session("X", "6:30"))
        with pytest.raises(ValidationError):
            CinemaSession(**session("X", "24:10"))
        with pytest.raises(ValidationError):
            CinemaSession(**session("   ", "17:00"))
        with pytest.raises(ValidationError):
            CinemaSession(**session("X", "17:00", cinema=""))

    def test_no_price_and_no_original_title_unless_a_listing_gives_one(self):
        record = CinemaSession(**session("X", "17:00"))
        assert record.price is None
        assert record.original_title == ""
        with pytest.raises(ValidationError):
            CinemaSession(**session("X", "17:00", price=-1))
        assert CinemaSession(**session("X", "17:00", price=7.5)).price == 7.5

    def test_the_stored_fields_come_back_as_json_and_validate_again(self):
        record = CinemaSession(**session("Oro sin ley", "16:00", version="VOSE", format="IMAX", first_detected_at=datetime(2026, 11, 28, 6, tzinfo=timezone.utc)))
        stored = record.model_dump(mode="json")
        assert (stored["date"], stored["time"], stored["price"], stored["original_title"]) == ("2026-11-28", "16:00", None, "")
        assert datetime.fromisoformat(stored["first_detected_at"]) == datetime(2026, 11, 28, 6, tzinfo=timezone.utc)
        assert CinemaSession(**stored) == record


# --- the shared helpers ----------------------------------------------------------------------------


class TestHelpers:
    def test_past_days_are_dropped_and_today_stays(self):
        records = [{"date": "2026-11-27"}, {"date": "2026-11-28"}, {"date": "2026-11-29"}, {"date": "2026-12-30"}, {"date": ""}]
        kept = common.drop_past_days(records, date(2026, 11, 28))
        assert [record["date"] for record in kept] == ["2026-11-28", "2026-11-29", "2026-12-30"]

    def test_a_stray_date_beyond_the_season_is_dropped(self):
        records = [{"date": "2027-03-28"}, {"date": "2027-03-29"}, {"date": "2027-08-30"}]  # the horizon is 120 days out: 2027-03-28
        assert [record["date"] for record in common.drop_past_days(records, date(2026, 11, 28))] == ["2027-03-28"]

    @pytest.mark.parametrize(
        ("label", "expected"),
        [
            ("Sáb 28 Nov", "2026-11-28"),
            ("domingo, 29 de noviembre", "2026-11-29"),
            ("Hoy, 28 de noviembre", "2026-11-28"),
            ("Mar 1 Dic", "2026-12-01"),
            ("Jue 10 Dic", "2026-12-10"),
            ("Viernes 25 Dic", "2026-12-25"),
            ("Sáb 2 Ene", "2027-01-02"),  # the weekday says it is next year's Saturday
            ("Sin sesiones", ""),
        ],
    )
    def test_a_day_printed_without_its_year_is_dated_against_the_reference_day(self, label, expected):
        assert common.day_from_label(label, date(2026, 11, 28)) == expected

    def test_a_day_that_exists_in_neither_nearby_year_is_none(self):
        assert common.resolve_day(29, 2, date(2026, 12, 30)) is None
        assert common.resolve_day(29, 2, date(2027, 12, 30)) == date(2028, 2, 29)

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("VOS español", "VOSE"),
            ("VOSE", "VOSE"),
            ("VOS CASTELLANO", "VOSE"),
            ("V.O.S.ING./CAST.*", "VOSE"),
            ("VOS VALENCIANO", "VOS"),
            ("VOS", "VOS"),
            ("VO", "VO"),
            ("V.O.", "VO"),
            ("sin subtítulos", "VO"),
            ("DOBLADA AL ESPAÑOL", "DOB"),
            ("DOBLADA CAST.", "DOB"),
            ("-", ""),
            ("Color", ""),
            ("Digital HD", ""),
            ("España", ""),
        ],
    )
    def test_every_spelling_of_a_version_folds_into_one_label(self, raw, expected):
        assert common.normalise_version(raw) == expected

    @pytest.mark.parametrize(
        ("audio", "subtitles", "expected"),
        [
            ("Castellano (doblada)", "", "DOB"),
            ("Castellano", "", ""),
            ("Inglés", "Castellano", "VOSE"),
            ("Alemán", "Castellano", "VOSE"),
            ("Japonés", "Inglés", "VOS"),
            ("Inglés", "", "VO"),
            ("Inglés, español", "Español", ""),  # both audios are on offer: the listing does not say which
        ],
    )
    def test_the_version_comes_from_the_audio_and_subtitle_lines(self, audio, subtitles, expected):
        assert common.version_from_language(audio, subtitles) == expected

    @pytest.mark.parametrize(
        ("label", "expected"),
        [
            ("Dune: Parte Tres", ("Dune: Parte Tres", "", "")),
            ("Dune: Parte Tres (VOS español) (IMAX)", ("Dune: Parte Tres", "VOSE", "IMAX")),
            ("Vengadores: Doomsday (Infinity Vision) (ScreenX)", ("Vengadores: Doomsday", "", "Infinity Vision / ScreenX")),
            ("Hechizo: Bienvenidos a Hexe (4DX 3D)", ("Hechizo: Bienvenidos a Hexe", "", "4DX 3D")),
            ("La bola negra (sin subtítulos)", ("La bola negra", "VO", "")),
            ("La Odisea (DOBLADA AL ESPAÑOL)", ("La Odisea", "DOB", "")),
            ("Dune: Parte 3 (Digital) (VOS)", ("Dune: Parte 3", "VOS", "")),
            ("PRIMAVERA (2026)", ("PRIMAVERA (2026)", "", "")),  # a year is part of the title
            ("Los juegos del hambre (iSense) (VOSE)", ("Los juegos del hambre", "VOSE", "iSense")),
            ("VOSE La Profecía (VOS español)", ("La Profecía", "VOSE", "")),
            ("Madoka Magica (Digital)", ("Madoka Magica", "", "")),
        ],
    )
    def test_version_and_format_are_split_off_the_listing_title(self, label, expected):
        assert common.split_title(label) == expected

    @pytest.mark.parametrize(("text", "expected"), [("9:30", "09:30"), (" 20:15 ", "20:15"), ("18:00 h", ""), ("25:00", ""), ("soon", ""), ("", "")])
    def test_a_start_time_is_hh_mm_on_a_24_hour_clock(self, text, expected):
        assert common.clock_time(text) == expected

    def test_every_start_time_of_a_line_is_read(self):
        assert common.clock_times("18:00 y 22:00 h") == ["18:00", "22:00"]
        assert common.clock_times("22:15") == ["22:15"]

    def test_a_record_without_a_day_time_title_cinema_or_city_is_not_a_session(self):
        base = {"title": "X", "cinema": "C", "city": "Y", "day": "2026-11-28", "time": "17:00", "source": "s"}
        assert common.make_session(**base, address="  A  ", room="", price=None) == {"title": "X", "cinema": "C", "city": "Y", "date": "2026-11-28", "time": "17:00", "source": "s", "address": "A"}
        assert common.make_session(**{**base, "day": ""}) is None
        assert common.make_session(**{**base, "time": ""}) is None
        assert common.make_session(**{**base, "title": " "}) is None
        assert common.make_session(**{**base, "city": ""}) is None
        assert common.make_session(**{**base, "city": "Valencia"})["city"] == "València"


# --- the HTTP call ----------------------------------------------------------------------------------


class TestPageFetcher:
    def test_one_request_per_page_a_pause_apart_with_a_real_user_agent(self, monkeypatch):
        calls, pauses = [], []
        response = stub_response()
        monkeypatch.setattr(common.requests, "get", lambda url, **kwargs: calls.append((url, kwargs)) or response)
        monkeypatch.setattr(common.time, "sleep", pauses.append)
        fetcher = PageFetcher(delay_seconds=1.5, timeout_seconds=7)

        assert fetcher.get("https://example.test/a") == b"<html></html>"
        assert fetcher.get("https://example.test/b") == b"<html></html>"

        assert [url for url, _ in calls] == ["https://example.test/a", "https://example.test/b"]
        assert calls[0][1]["headers"]["User-Agent"] == SCRAPER_DEFAULT_USER_AGENT
        assert calls[0][1]["timeout"] == 7
        assert pauses == [1.5]  # no pause before the first request, one before every next
        assert fetcher.urls_requested == ["https://example.test/a", "https://example.test/b"]

    @pytest.mark.parametrize("status", [403, 429])
    def test_a_refusal_is_reported_once_and_never_retried(self, monkeypatch, status):
        calls = []
        monkeypatch.setattr(common.requests, "get", lambda url, **kwargs: calls.append(url) or stub_response(status, b"blocked"))
        with pytest.raises(SourceUnavailable, match=f"HTTP {status}, the site refuses automated reads"):
            PageFetcher().get("https://example.test/closed")
        assert len(calls) == 1

    def test_any_other_error_status_and_a_transport_error_are_reported(self, monkeypatch):
        monkeypatch.setattr(common.requests, "get", lambda url, **kwargs: stub_response(404, b"gone"))
        with pytest.raises(SourceUnavailable, match=r"https://example\.test/gone: HTTP 404$"):
            PageFetcher().get("https://example.test/gone")

        def timeout(url, **kwargs):
            raise requests.Timeout("timed out")

        monkeypatch.setattr(common.requests, "get", timeout)
        with pytest.raises(SourceUnavailable, match="Timeout: timed out"):
            PageFetcher().get("https://example.test/slow")


def test_a_listing_that_cannot_be_read_is_reported_and_the_others_are_read():
    pages = {url: b"<html></html>" for url in ("https://example.test/one", "https://example.test/two")}

    def parse(body, listing, reference):
        return [{"title": "T", "cinema": listing.name, "city": "X", "date": "2026-11-28", "time": "17:00"}]

    listings = [Listing(url="https://example.test/one", name="One"), Listing(url="https://example.test/two", name="Two"), Listing(url="https://example.test/three", name="Three")]
    results = common.read_listings(FakeFetcher(pages), listings, parse, date(2026, 11, 28))

    assert [result.ok for result in results] == [True, True, False]
    assert results[0].sessions[0]["cinema"] == "One" and results[1].sessions[0]["cinema"] == "Two"
    assert isinstance(results[2], ListingResult) and results[2].sessions == []
    assert results[2].error == "not a cinema cartelera page"


def test_a_parser_that_blows_up_on_one_page_does_not_stop_the_next():
    def parse(body, listing, reference):
        if listing.key == "bad":
            raise AttributeError("markup changed")
        return []

    listings = [Listing(url="https://example.test/bad", key="bad"), Listing(url="https://example.test/good", key="good")]
    results = common.read_listings(FakeFetcher({listing.url: b"" for listing in listings}), listings, parse, date(2026, 11, 28))
    assert results[0].error == "parse error (AttributeError)"
    assert results[1].ok


# --- EXHICINE: Cine Tívoli ---------------------------------------------------------------------------


class TestExhicine:
    def test_every_session_of_the_page_is_read_with_its_room_and_links(self):
        sessions = exhicine.parse(fixture(TIVOLI_PAGE), exhicine.LISTINGS[0], REFERENCE_DAY)

        assert [(s["date"], s["time"], s["title"]) for s in sessions] == [
            ("2026-11-28", "17:00", "EL GATO CON SOMBRERO"),
            ("2026-11-29", "16:30", "EL GATO CON SOMBRERO"),
            ("2026-11-28", "19:30", "ARRIBA TUTTO"),
            ("2026-11-29", "19:30", "ARRIBA TUTTO"),
            ("2026-11-28", "22:30", "LOS JUEGOS DEL HAMBRE: AMANECER EN LA COSECHA"),
        ]
        first = sessions[0]
        assert (first["cinema"], first["city"], first["address"], first["room"], first["source"]) == ("Cine Tívoli", "Burjassot", "Carrer de José Carsí, 50", "1", "exhicine.es")
        # The ticket form only takes a POST: the session links to the cinema page, and the film to its own page.
        assert first["ticket_url"] == "https://exhicine.es/cine/cine-tivoli/"
        assert first["film_url"] == "https://exhicine.es/movie/cine-tivoli-el-gato-con-sombrero/"
        assert not {"version", "format", "price", "director", "duration_min"} & set(first)

    def test_the_cinema_and_its_city_come_from_the_page_not_from_the_listing(self):
        listing = Listing(url="https://exhicine.es/cine/cine-tivoli/", key="cine-tivoli", name="A name that stalled", city="Somewhere else")
        sessions = exhicine.parse(fixture(TIVOLI_PAGE), listing, REFERENCE_DAY)
        assert {(s["cinema"], s["city"], s["address"]) for s in sessions} == {("Cine Tívoli", "Burjassot", "Carrer de José Carsí, 50")}

    def test_a_cinema_with_nothing_on_gives_no_sessions(self):
        listing = Listing(url="https://exhicine.es/cine/cine-museros/", key="cine-museros", name="Cine Museros", city="Museros")
        assert exhicine.parse(fixture("cinema_exhicine_nothing_on.html"), listing, REFERENCE_DAY) == []

    def test_a_page_that_is_not_a_cartelera_is_refused(self):
        with pytest.raises(SourceUnavailable, match="not a cartelera page"):
            exhicine.parse(BLOCKED_PAGE, exhicine.LISTINGS[0], REFERENCE_DAY)

    def test_a_form_without_a_date_is_dated_from_its_day_label(self):
        # No "m_date" in the form, no cinema in the heading, no address block: the label and the listing stand in.
        page = b"""<html><body><h1>Cartelera</h1><div class="movie" id="movie-1"><div class="image"><a href="https://exhicine.es/movie/x/"></a></div>
        <div class="content"><h2 class="title">UNA PELI</h2><div class="sesiones-pelicula"><div class="content-date"><div class="date">domingo, 29 de noviembre</div>
        <div class="content-hours"><div class="hour"><form method="post"><input class="link" type="submit" value="21:15"><input type="hidden" name="m_date_alt" value="x"><input type="hidden" name="m_room" value="2"></form></div></div></div></div></div></div></body></html>"""
        sessions = exhicine.parse(page, exhicine.LISTINGS[0], REFERENCE_DAY)
        assert [(s["date"], s["time"], s["room"], s["cinema"], s["city"], s["film_url"]) for s in sessions] == [("2026-11-29", "21:15", "2", "Cine Tívoli", "Burjassot", "https://exhicine.es/movie/x/")]

    def test_cine_tivoli_is_the_first_listing_and_the_only_one_read(self):
        assert [listing.name for listing in exhicine.LISTINGS] == ["Cine Tívoli"]
        assert exhicine.LISTINGS[0].url == "https://exhicine.es/cine/cine-tivoli/"


# --- Cines Babel -------------------------------------------------------------------------------------


class TestBabel:
    def test_versions_come_from_the_language_lines(self):
        sessions = babel.parse(fixture("cinema_babel_cartelera.html"), babel.LISTINGS[0], REFERENCE_DAY)
        by_title: dict[str, list[dict]] = {}
        for record in sessions:
            by_title.setdefault(record["title"], []).append(record)

        dubbed = by_title["Babelitos – El secreto del herrerillo"]
        assert (dubbed[0]["version"], dubbed[0]["language"], dubbed[0]["director"], dubbed[0]["duration_min"]) == ("DOB", "Castellano (doblada)", "Antoine Lanciaux", 78)
        assert dubbed[0]["ticket_url"] == "https://www.reservaentradas.com/sesiones/valencia/cinesbabel/babelitos---el-secreto-del-herrerillo/2651/"
        assert dubbed[0]["film_url"] == "https://cinesbabel.com/babelitos-el-secreto-del-herrerillo/"

        subtitled = by_title["Oro sin ley"]
        assert len(subtitled) == 19 and {record["version"] for record in subtitled} == {"VOSE"}
        assert subtitled[0]["language"] == "Inglés · subt. Castellano"

        spanish = by_title["El director"]
        assert len(spanish) == 20 and "version" not in spanish[0] and spanish[0]["language"] == "Castellano"

        assert len(sessions) == 50
        assert {record["cinema"] for record in sessions} == {"Cines Babel"} and {record["city"] for record in sessions} == {"València"}

    def test_day_rows_without_a_year_are_dated_against_the_reference_day(self):
        sessions = babel.parse(fixture("cinema_babel_cartelera.html"), babel.LISTINGS[0], REFERENCE_DAY)
        per_day = Counter(record["date"] for record in sessions)
        assert (per_day["2026-11-28"], per_day["2026-11-29"], per_day["2026-11-30"]) == (9, 9, 6)
        assert sorted(per_day) == ["2026-11-28", "2026-11-29", "2026-11-30", "2026-12-01", "2026-12-02", "2026-12-03", "2026-12-25", "2026-12-26", "2026-12-27", "2026-12-28", "2026-12-29", "2026-12-30"]  # six days ahead, then a cycle sold weeks ahead

    def test_the_times_of_one_day_row_link_to_their_own_ticket_page(self):
        sessions = babel.parse(fixture("cinema_babel_cartelera.html"), babel.LISTINGS[0], REFERENCE_DAY)
        monday = sorted((record["time"], record["title"]) for record in sessions if record["date"] == "2026-11-30")
        assert monday == [("16:00", "El director"), ("16:00", "Oro sin ley"), ("18:10", "El director"), ("18:15", "Rose"), ("22:30", "Oro sin ley"), ("22:40", "El director")]

    def test_a_page_that_is_not_the_cartelera_is_refused(self):
        with pytest.raises(SourceUnavailable, match="not the Babel cartelera"):
            babel.parse(BLOCKED_PAGE, babel.LISTINGS[0], REFERENCE_DAY)


# --- Filmoteca ---------------------------------------------------------------------------------------


class TestFilmoteca:
    def test_only_the_valencia_venue_is_kept(self):
        sessions = filmoteca.parse(fixture("cinema_filmoteca_programacion.html"), filmoteca.LISTINGS[0], REFERENCE_DAY)
        assert len(sessions) == 10
        assert {record["cinema"] for record in sessions} == {"Filmoteca València"}
        assert {record["city"] for record in sessions} == {"València"}
        assert {record["address"] for record in sessions} == {"Edificio Rialto"}
        assert not any(record["title"] == "EL HOMBRE DE LONDRES" for record in sessions)  # Castelló
        assert not any(record["title"] == "ESPEJOS Nº 3" for record in sessions)  # Alicante

    def test_version_year_running_time_and_medium_come_from_the_credit_line(self):
        sessions = filmoteca.parse(fixture("cinema_filmoteca_programacion.html"), filmoteca.LISTINGS[0], REFERENCE_DAY)
        first = sessions[0]
        assert first["title"] == "LA VIDA PRIVADA DE SHERLOCK HOLMES"
        assert (first["version"], first["format"], first["year"], first["duration_min"], first["director"], first["language"]) == ("VOSE", "35 mm", 1970, 125, "Billy Wilder", "VOS CASTELLANO")
        assert (first["date"], first["time"]) == ("2026-11-28", "18:00")
        assert first["ticket_url"] == "https://taquilla.ivc.gva.es/va/entradas/la-vida-privada-de-sherlock-holmes/2026-11-28"
        assert first["film_url"] == "https://ivc.gva.es/es/audiovisuales/pelicula-2278/la-vida-privada-de-sherlock-holmes"

        by_title = {record["title"]: record for record in sessions}
        assert by_title["PRIMERA PLANA"]["version"] == "VOS"  # "VOS VALENCIANO": subtitled, but not in Spanish
        assert by_title["LA BALADA DE NARAYAMA"]["version"] == "VOSE"  # "V.O.S.ING./CAST.*"
        assert by_title["GREMLINS"]["version"] == "DOB"  # "DOBLADA CAST."
        programme = by_title["PROGRAMA PORTABELLA EN EL MUSEO"]  # "España · 1969-2008 · 55'": no director, version or medium
        assert (programme["year"], programme["duration_min"]) == (1969, 55)
        assert not {"director", "version", "format"} & set(programme)

    def test_a_screening_whose_ticket_link_carries_no_date_is_dated_from_its_date_block(self):
        page = b"""<html><body><h1>Programaci\xc3\xb3n por d\xc3\xadas</h1><div class="actividad fondo-gris"><div class="fecha fondo-audiovisuales">
        <span class="dia">09</span><span class="mes">dic</span><span class="nombre-dia">mi\xc3\xa9</span><span class="hora">20:00 h</span></div>
        <div class="cont-actividad"><div class="ficha-peli"><div class="foto-peli"></div><div class="textos-peli"><span class="lugar">Val\xc3\xa8ncia - Edificio Rialto</span>
        <h2><a href="https://ivc.gva.es/es/audiovisuales/pelicula-1/una-peli" title="UNA PELI">UNA PELI</a></h2>
        <p><strong>Alguien</strong> \xc2\xb7 Espa\xc3\xb1a \xc2\xb7 1999 \xc2\xb7 VOS CASTELLANO \xc2\xb7 110' \xc2\xb7 35 mm</p></div></div></div>
        <a class="btn-venta-entradas" href="https://taquilla.ivc.gva.es/va/entradas/una-peli/">COMPRAR</a></div></body></html>"""
        sessions = filmoteca.parse(page, filmoteca.LISTINGS[0], REFERENCE_DAY)
        assert [(s["date"], s["time"], s["version"], s["format"], s["director"], s["ticket_url"]) for s in sessions] == [("2026-12-09", "20:00", "VOSE", "35 mm", "Alguien", "https://taquilla.ivc.gva.es/va/entradas/una-peli/")]

    def test_a_page_that_is_not_the_programme_is_refused(self):
        with pytest.raises(SourceUnavailable, match="not the programme page"):
            filmoteca.parse(BLOCKED_PAGE, filmoteca.LISTINGS[0], REFERENCE_DAY)


# --- FilmAffinity ------------------------------------------------------------------------------------


class TestFilmAffinity:
    def test_the_day_of_a_session_is_the_date_of_its_row_not_the_label_next_to_it(self):
        page = b"""<html><head><title>Cartelera X - Filmaffinity</title></head><body><h1 id="main-title">Cine X</h1>
        <div class="movie-showtimes-n" data-m-id="7" data-t-id="1"><div class="mv-title"><span class="fs-5">Una peli</span></div><div class="sessions-container">
        <div class="row g-0 mb-2" data-sess-date="2026-11-27"><div class="col-3"><span class="wday">Hoy</span><span class="mday">s\xc3\xa1bado 28 de noviembre</span></div>
        <div class="col-9"><div class="sess-times"><a class="btn btn-sm" title="Sala 3" href="https://cine.example/s/1">17:30</a></div></div></div>
        <div class="row g-0 mb-2"><div class="col-3"><span class="wday">Ma\xc3\xb1ana</span></div><div class="col-9 sess-times"></div></div>
        </div></div></body></html>"""
        sessions = filmaffinity.parse(page, filmaffinity.LISTINGS[0], REFERENCE_DAY)
        # The feed still starts on yesterday's row and labels it "Hoy": only data-sess-date is believed.
        assert [(s["date"], s["time"], s["room"], s["cinema"], s["city"]) for s in sessions] == [("2026-11-27", "17:30", "Sala 3", "Cine X", "Paterna")]

    def test_version_and_format_come_from_the_block_title(self):
        sessions = filmaffinity.parse(fixture("cinema_filmaffinity_kinepolis.html"), filmaffinity.LISTINGS[0], REFERENCE_DAY)
        kinds = Counter((record["title"], record.get("version", ""), record.get("format", "")) for record in sessions)
        assert dict(kinds) == {("Dune: Parte Tres", "", ""): 1, ("Dune: Parte Tres", "", "IMAX"): 10, ("Dune: Parte Tres", "VOSE", ""): 1, ("La bola negra", "VO", ""): 12}

    def test_cinema_address_room_film_page_year_and_running_time_are_read(self):
        sessions = filmaffinity.parse(fixture("cinema_filmaffinity_kinepolis.html"), filmaffinity.LISTINGS[0], REFERENCE_DAY)
        first = sessions[0]
        assert (first["cinema"], first["city"], first["address"], first["source"]) == ("Kinépolis Valencia", "Paterna", "C/ Francisco Tomás y Valiente, s/n", "filmaffinity.com")
        assert (first["date"], first["time"], first["room"]) == ("2026-12-15", "19:40", "Sala 9")
        assert first["ticket_url"] == "https://kinepolis.es/program/buy/1/1002183992/files/0/0"
        assert (first["film_url"], first["year"], first["duration_min"], first["director"]) == ("https://www.filmaffinity.com/es/film766877.html", 2026, 152, "Denis Villeneuve")
        assert "price" not in first
        black_ball = next(record for record in sessions if record["title"] == "La bola negra")
        assert black_ball["director"] == "Los Javis"  # the feed prints "Los Javis ...": the dots are not a name

    def test_an_affiliate_redirect_is_unwrapped_to_the_ticketing_address(self):
        sessions = filmaffinity.parse(fixture("cinema_filmaffinity_yelmo.html"), filmaffinity.LISTINGS[5], REFERENCE_DAY)
        assert len(sessions) == 7
        assert sessions[0]["ticket_url"] == "https://cine.entradas.com/cine/valencia/yelmo-cines-valencia/evento/50236/dune-parte-tres?mode=widget&change=0&language=VOSE"
        assert not any("awin1.com" in record["ticket_url"] for record in sessions)
        assert (sessions[0]["cinema"], sessions[0]["city"], sessions[0]["address"]) == ("Yelmo Cines Mercado de Campanar", "València", "C.c. Mercado Del Campanar Avda. Tirso Molina,16")
        assert (sessions[0]["title"], sessions[0]["version"], sessions[0]["duration_min"]) == ("Dune: Parte 3", "VOS", 140)  # "(Digital) (VOS)": the plain "Digital" is dropped
        plain = [record for record in sessions if record["title"] == "Madoka Magica" and "version" not in record]
        assert [(record["date"], record["time"]) for record in plain] == [("2026-11-30", "18:00")] and "format" not in plain[0] and "room" not in plain[0]
        madoka = [record for record in sessions if record["title"] == "Madoka Magica"]
        assert {record["film_url"] for record in madoka} == {"https://www.filmaffinity.com/es/film316736.html"} and {record["director"] for record in madoka} == {"Akiyuki Shinbo"}

    def test_a_cinema_with_nothing_on_gives_no_sessions(self):
        assert filmaffinity.parse(EMPTY_FILMAFFINITY_PAGE, filmaffinity.LISTINGS[3], REFERENCE_DAY) == []

    def test_a_page_without_the_cinema_heading_is_refused(self):
        with pytest.raises(SourceUnavailable, match="not a cinema cartelera page"):
            filmaffinity.parse(BLOCKED_PAGE, filmaffinity.LISTINGS[0], REFERENCE_DAY)

    def test_the_cinemas_without_a_readable_site_are_the_ones_read(self):
        assert [listing.key for listing in filmaffinity.LISTINGS] == ["295", "291", "543", "516", "507", "503", "450", "536", "519"]
        assert all(listing.url == f"https://www.filmaffinity.com/es/theater-showtimes.php?id={listing.key}" for listing in filmaffinity.LISTINGS)


def test_each_source_reads_its_pages_once_and_reports_the_one_that_failed(monkeypatch):
    monkeypatch.setattr(filmaffinity, "LISTINGS", (filmaffinity.LISTINGS[0], filmaffinity.LISTINGS[1], filmaffinity.LISTINGS[5]))
    pages = {
        exhicine.LISTINGS[0].url: fixture(TIVOLI_PAGE),
        babel.LISTINGS[0].url: fixture("cinema_babel_cartelera.html"),
        filmoteca.LISTINGS[0].url: BLOCKED_PAGE,
        filmaffinity.LISTINGS[0].url: fixture("cinema_filmaffinity_kinepolis.html"),
        filmaffinity.LISTINGS[2].url: fixture("cinema_filmaffinity_yelmo.html"),
    }
    fetcher = FakeFetcher(pages, default=b"<html></html>")

    results = exhicine.fetch(fetcher, REFERENCE_DAY) + babel.fetch(fetcher, REFERENCE_DAY) + filmoteca.fetch(fetcher, REFERENCE_DAY) + filmaffinity.fetch(fetcher, REFERENCE_DAY)

    assert [len(result.sessions) for result in results] == [5, 50, 0, 24, 0, 7]
    assert [result.ok for result in results] == [True, True, False, True, False, True]
    assert (results[2].error, results[4].error) == ("not the programme page", "not a cinema cartelera page")
    assert [result.cinema for result in results] == ["Cine Tívoli", "Cines Babel", "Filmoteca València", "Kinépolis Valencia", "Cinesa Bonaire", "Yelmo Cines Mercado de Campanar"]  # a page that failed keeps its listing's name
    # One request per listing page, each page asked for exactly once.
    assert fetcher.urls_requested == [exhicine.LISTINGS[0].url, babel.LISTINGS[0].url, filmoteca.LISTINGS[0].url, filmaffinity.LISTINGS[0].url, filmaffinity.LISTINGS[1].url, filmaffinity.LISTINGS[2].url]


# --- the pipeline ------------------------------------------------------------------------------------


class TestCinemaSessionsETL:
    @pytest.fixture()
    def etl(self) -> CinemaSessionsETL:
        return CinemaSessionsETL()

    def test_extract_reads_each_listing_once_and_keeps_today_onward(self, etl, monkeypatch):
        fetcher = stub_pages(monkeypatch)

        records = etl.extract()

        assert fetcher.urls_requested == EVERY_URL and len(EVERY_URL) == 12
        assert min(record["date"] for record in records) >= "2026-11-28"
        assert len(records) == 5 + 50 + 10 + (24 - 4) + (7 - 1)  # the yesterday rows of the feeds are gone
        assert [result.cinema for _, _, result in etl.listing_results][:5] == ["Cine Tívoli", "Cines Babel", "Filmoteca València", "Kinépolis Valencia", "Cinesa Bonaire"]
        assert all(result.ok for _, _, result in etl.listing_results)
        assert [source for source, _, _ in etl.listing_results] == ["exhicine", "babel", "filmoteca"] + ["filmaffinity"] * 9

    def test_a_source_that_refuses_every_page_does_not_sink_the_others(self, etl, monkeypatch):
        fetcher = stub_pages(monkeypatch, failing=lambda url: "filmaffinity" in url)

        records = etl.extract()

        assert {record["source"] for record in records} == {"exhicine.es", "cinesbabel.com", "ivc.gva.es"}
        failed = [result for _, _, result in etl.listing_results if not result.ok]
        assert len(failed) == 9 and all(result.error == "HTTP 403, the site refuses automated reads" for result in failed)
        assert len(fetcher.urls_requested) == 12  # a refused page is not asked for twice

    def test_the_run_fails_when_not_one_listing_could_be_read(self, etl, monkeypatch):
        stub_pages(monkeypatch, failing=lambda url: True)
        with pytest.raises(RuntimeError, match="none of the 12 cinema listing pages could be read"):
            etl.extract()

    def test_the_run_fails_when_pages_are_read_but_nothing_is_parsed(self, etl, monkeypatch):
        stub_pages(monkeypatch, pages={})  # the aggregator answers an empty cartelera nine times; the first-party pages are not found
        with pytest.raises(RuntimeError, match="9 cinema listing pages read and not one session parsed"):
            etl.extract()

    def test_sessions_are_deduplicated_on_cinema_film_day_time_version_and_format(self, etl):
        records = [
            session("A", "17:00"),
            session("A", "17:00", room="1"),  # the same screening, printed with its room: the room is not part of the key
            session("A", "17:00", format="IMAX"),  # another screening at the same minute
            session("A", "17:00", version="DOB"),  # and another
            session("A", "17:00", version="VOSE"),
            session("A", "19:00"),
        ]

        sessions = etl.transform(records)

        assert sorted((s.time, s.version, s.format) for s in sessions) == [("17:00", "", ""), ("17:00", "", "IMAX"), ("17:00", "DOB", ""), ("17:00", "VOSE", ""), ("19:00", "", "")]
        assert etl.metrics.duplicates_removed == 1
        assert len({s.id for s in sessions}) == 5

    def test_sessions_are_listed_in_the_order_the_cinemas_were_read_then_by_day(self, etl):
        etl.listing_results = [("exhicine", "exhicine.es", ListingResult(Listing(url="u"), cinema=name)) for name in ("Cine Tívoli", "Kinépolis Valencia", "Cines Babel")]
        # Cine Tívoli has nothing on the first published day: it still comes first
        records = [session("B", "19:00", cinema="Cines Babel"), session("A", "17:00", cinema="Kinépolis Valencia"), session("Z", "16:00", date="2026-11-29"), session("A", "20:00", date="2026-11-29")]

        sessions = etl.transform(records)

        assert [(s.date, s.cinema, s.time) for s in sessions] == [("2026-11-29", "Cine Tívoli", "16:00"), ("2026-11-29", "Cine Tívoli", "20:00"), ("2026-11-28", "Kinépolis Valencia", "17:00"), ("2026-11-28", "Cines Babel", "19:00")]

    def test_a_record_that_does_not_validate_is_dropped_and_counted(self, etl):
        sessions = etl.transform([session("A", "17:00"), session("B", "17:00", date="mañana"), session("C", "25:00")])
        assert [s.title for s in sessions] == ["A"]
        assert etl.metrics.records_failed == 2

    def test_first_detected_at_is_kept_for_a_known_session_and_set_for_a_new_one(self, etl, monkeypatch):
        clock = {"now": datetime(2026, 11, 28, 6, 0, tzinfo=timezone.utc)}

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock["now"]

        monkeypatch.setattr(cinema_sessions_etl, "datetime", FrozenDatetime)
        monkeypatch.setattr(cinema_sessions_etl, "today", lambda: date(2026, 11, 28))
        page = fixture(TIVOLI_PAGE)
        fetcher = FakeFetcher({exhicine.LISTINGS[0].url: page})  # only Cine Tívoli answers; the other pages fail
        monkeypatch.setattr(cinema_sessions_etl, "PageFetcher", lambda: fetcher)
        first_seen = datetime(2026, 11, 28, 6, tzinfo=timezone.utc)
        second_seen = datetime(2026, 11, 29, 6, tzinfo=timezone.utc)

        etl.run()
        stored = json.loads(etl.output_file.read_text(encoding="utf-8"))
        assert len(stored) == 5
        assert {datetime.fromisoformat(record["first_detected_at"]) for record in stored} == {first_seen}
        created_first_run = {(record["title"], record["date"], record["time"]): record["created_at"] for record in stored}

        # Next day: the same page, with the sessions of the 28th moved to the 30th.
        clock["now"] = second_seen
        monkeypatch.setattr(cinema_sessions_etl, "today", lambda: date(2026, 11, 29))
        fetcher.pages[exhicine.LISTINGS[0].url] = page.replace(b'name="m_date" type="hidden" value="2026-11-28"', b'name="m_date" type="hidden" value="2026-11-30"')

        etl.run()
        stored = json.loads(etl.output_file.read_text(encoding="utf-8"))
        by_key = {(record["title"], record["date"], record["time"]): record for record in stored}
        assert sorted(by_key) == [
            ("ARRIBA TUTTO", "2026-11-29", "19:30"),
            ("ARRIBA TUTTO", "2026-11-30", "19:30"),
            ("EL GATO CON SOMBRERO", "2026-11-29", "16:30"),
            ("EL GATO CON SOMBRERO", "2026-11-30", "17:00"),
            ("LOS JUEGOS DEL HAMBRE: AMANECER EN LA COSECHA", "2026-11-30", "22:30"),
        ]
        kept = by_key[("EL GATO CON SOMBRERO", "2026-11-29", "16:30")]
        assert datetime.fromisoformat(kept["first_detected_at"]) == first_seen
        assert kept["created_at"] == created_first_run[("EL GATO CON SOMBRERO", "2026-11-29", "16:30")]
        moved = by_key[("ARRIBA TUTTO", "2026-11-30", "19:30")]
        assert datetime.fromisoformat(moved["first_detected_at"]) == second_seen
        assert not any(record["date"] == "2026-11-28" for record in stored)

    def test_load_writes_a_list_of_sessions_and_the_status_of_every_listing(self, etl, monkeypatch):
        stub_pages(monkeypatch)

        metrics = etl.run()

        stored = json.loads(etl.output_file.read_text(encoding="utf-8"))
        assert isinstance(stored, list) and len(stored) == metrics.records_loaded == 91
        required = {"id", "title", "cinema", "city", "date", "time", "version", "format", "price", "ticket_url", "film_url", "source", "first_detected_at", "created_at", "updated_at", "original_title", "address", "room", "duration_min", "year", "director", "language"}
        assert required <= set(stored[0])
        assert all(record["price"] is None and record["original_title"] == "" for record in stored)
        assert all(datetime.fromisoformat(record["first_detected_at"]).tzinfo is not None for record in stored)
        assert all(record["created_at"] and record["updated_at"] for record in stored)
        assert CinemaSession(**stored[0]).date == "2026-11-28"

        status = json.loads(etl.status_file.read_text(encoding="utf-8"))
        assert (status["sessions"], status["reference_day"]) == (91, "2026-11-28")
        assert [entry["cinema"] for entry in status["listings"]] == ["Cine Tívoli", "Cines Babel", "Filmoteca València", "Kinépolis Valencia", "Cinesa Bonaire", "Abc Park", "Abc El Saler", "Cines Lys", "Yelmo Cines Mercado de Campanar", "Ocine Aqua", "Cines Mn4", "ABC Gran Turia"]
        assert [(entry["source"], entry["sessions"], entry["error"]) for entry in status["listings"]] == [("exhicine", 5, ""), ("babel", 50, ""), ("filmoteca", 10, ""), ("filmaffinity", 24, "")] + [("filmaffinity", 0, "")] * 4 + [("filmaffinity", 7, "")] + [("filmaffinity", 0, "")] * 3
        assert all(entry["url"].startswith("https://") for entry in status["listings"])
        assert status["listings"][0]["url"] == exhicine.LISTINGS[0].url and status["listings"][0]["host"] == "exhicine.es"

        assert (etl.output_file.name, etl.status_file.name, etl.data_dir.name) == (OUTPUT_FILE, STATUS_FILE, "cinema")
        assert not etl.output_file.with_name(OUTPUT_FILE + ".tmp").exists() and not etl.status_file.with_name(STATUS_FILE + ".tmp").exists()
        assert (metrics.records_extracted, metrics.records_transformed, metrics.records_loaded, metrics.error_count) == (91, 91, 91, 0)
        assert not (etl.data_dir / "checkpoints" / "latest.json").exists()

    def test_the_freshness_watcher_dates_what_the_run_wrote(self, etl, monkeypatch):
        written = datetime(2026, 11, 28, 6, 0, tzinfo=timezone.utc)

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return written

        monkeypatch.setattr(cinema_sessions_etl, "datetime", FrozenDatetime)
        stub_pages(monkeypatch)
        etl.run()
        (entry,) = [source for source in SOURCE_FILES if source["key"] == "cinema"]
        data_root = etl.data_dir.parent  # the watcher resolves its paths under the data root

        def verdict_at(now: float) -> dict:
            """What the watcher says when the file was last written at ``now``."""
            os.utime(etl.output_file, (now, now))
            return assess_freshness([entry], data_dir=data_root, now=now)["sources"][0]

        fresh = verdict_at(written.timestamp() + 2 * 3600)
        assert (fresh["status"], fresh["age_hours"], fresh["content_age_hours"]) == ("fresh", 0.0, 2.0)

        # The ETL keeps rewriting its file, but no session nobody had seen came for a week: the content is stale.
        frozen = verdict_at(written.timestamp() + 7 * 86400)
        assert (frozen["status"], frozen["content_age_hours"]) == ("stale", 168.0)

        # The ETL stopped writing a day and a quarter ago: the file's own age says so.
        os.utime(etl.output_file, (written.timestamp(), written.timestamp()))
        stalled = assess_freshness([entry], data_dir=data_root, now=written.timestamp() + 30 * 3600)["sources"][0]
        assert (stalled["status"], stalled["age_hours"]) == ("stale", 30.0)

    def test_the_sources_are_the_four_modules_and_nothing_is_retried(self, etl):
        assert [source for source, _, _ in SOURCES] == ["exhicine", "babel", "filmoteca", "filmaffinity"]
        assert [host for _, host, _ in SOURCES] == ["exhicine.es", "cinesbabel.com", "ivc.gva.es", "filmaffinity.com"]
        assert (etl.name, etl.max_retries, etl.enable_checkpointing, etl.enable_deduplication) == ("cinema", 0, False, False)
