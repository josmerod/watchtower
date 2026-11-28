"""The composer of the Valencia events (T-143): one run, end to end, with stub sources.

``src/etl/news/valencia_events_etl.py`` asks every source once, merges what they give into one record per
event and per session, completes each record and writes the file the tab and the API read. These tests
pin what a user can be burned by: a source that fails or is refused does not take the others down nor
erase what it gave before; a run where nobody answers is a failure and not a "success" over stale data
(T-192); two sessions of one show stay two events; and the moment an event was first detected survives
every later run. No network (``requests.get`` is replaced) and no file outside ``tmp_path``.
"""

import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import requests

from src.config.settings import get_settings
from src.constants.etl import SCRAPER_BRANDED_USER_AGENT
from src.etl.base import ETLError
from src.etl.news.valencia_events import http
from src.etl.news.valencia_events.categories import CATEGORIES
from src.etl.news.valencia_events.records import build_record
from src.etl.news.valencia_events.sources import Source
from src.etl.news.valencia_events.stamps import STAMPS_FILE
from src.etl.news.valencia_events.storage import write_text_atomic
import src.etl.news.valencia_events_etl as composer
from src.etl.news.valencia_events_etl import CARRY_OVER_DAYS, EVENTS_FILE, SOURCE_STATUS_FILE, ValenciaEventsETL

MADRID = ZoneInfo("Europe/Madrid")
T1 = datetime(2026, 11, 28, 6, 0, tzinfo=MADRID)  # a Saturday
T2 = T1 + timedelta(days=1)
T1_ISO = "2026-11-28T06:00:00+01:00"
T2_ISO = "2026-11-29T06:00:00+01:00"


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path, monkeypatch):
    """Every file the ETL writes goes to tmp_path, never to the data/ of the checkout."""
    monkeypatch.setattr(get_settings(), "project_root", str(tmp_path))
    monkeypatch.setattr(composer, "pause", lambda: None)  # no real waiting between two stubbed sources
    monkeypatch.setattr(composer, "madrid_now", lambda: T1)
    http.reset_blocked_hosts()
    yield
    http.reset_blocked_hosts()


def _source(key: str, records: list[dict] | None = None, error: Exception | None = None) -> Source:
    """A stub source that returns ``records`` or raises ``error``, counting its calls in ``fetch.calls``."""

    def fetch(logger=None):
        fetch.calls += 1  # type: ignore[attr-defined]
        if error is not None:
            raise error
        return [dict(record) for record in records or []]

    fetch.calls = 0  # type: ignore[attr-defined]
    return Source(key, f"Agenda {key}", (f"https://{key}.example.invalid/agenda",), fetch)


def _use(monkeypatch, *sources: Source) -> None:
    """Replace the registry by ``sources``, as the orchestrator would know them."""
    monkeypatch.setattr(composer, "SOURCES", tuple(sources))
    monkeypatch.setattr(composer, "SOURCE_BY_KEY", {source.key: source for source in sources})


def _raw(title: str, start: str, source: str = "a", url: str = "", **fields) -> dict:
    """A raw record as a source hands it over; ``start`` is an ISO day, or "" when the source prints none."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return build_record(source=source, title=title, url=url or f"https://{source}.example.invalid/{slug}", start_date=date.fromisoformat(start) if start else None, **fields)


def _etl() -> ValenciaEventsETL:
    etl = ValenciaEventsETL()
    etl.max_retries = 0  # the stubs fail on purpose: no retries, no sleeping
    return etl


def _stored(etl: ValenciaEventsETL) -> list[dict]:
    return json.loads((etl.output_dir / EVENTS_FILE).read_text(encoding="utf-8"))


def _titles(etl: ValenciaEventsETL) -> list[str]:
    return [event["title"] for event in _stored(etl)]


def _silent_a(monkeypatch, *b_records: dict) -> None:
    """Source ``a`` stops answering while ``b`` goes on listing ``b_records``."""
    _use(monkeypatch, _source("a", error=TimeoutError("no answer")), _source("b", list(b_records)))


# --- asking the sources ----------------------------------------------------------------------------


def test_extract_asks_every_source_once_and_reports_each_status(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    ok = _source("ok", [_raw("Concierto", "2026-12-10", "ok")])
    failed = _source("failed", error=TimeoutError("no answer"))
    empty = _source("empty", [])
    refused = _source("refused", error=http.SourceBlockedError("https://refused.example.invalid/agenda", 429, "3600"))
    _use(monkeypatch, ok, failed, empty, refused)
    etl = _etl()

    records = etl.extract()

    assert [record["title"] for record in records] == ["Concierto"]  # only what the source that answered gave
    assert etl.source_status == {"ok": "ok", "failed": "failed", "empty": "empty", "refused": "blocked"}
    assert [source.fetch.calls for source in (ok, failed, empty, refused)] == [1, 1, 1, 1]  # one request per source per run
    assert "Failed to fetch Agenda failed: no answer" in caplog.text
    assert "Agenda failed: failed, 0 events" in caplog.text
    assert "Agenda empty: empty, 0 events" in caplog.text
    assert "Agenda refused: HTTP 429 from refused.example.invalid (Retry-After: 3600)" in caplog.text
    assert "Agenda refused: blocked, 0 events" in caplog.text


def test_extract_goes_on_when_one_source_answers(monkeypatch):
    _use(monkeypatch, _source("ok", [_raw("Concierto", "2026-12-10", "ok")]), _source("failed", error=TimeoutError("no answer")), _source("empty", []))
    etl = _etl()
    assert [record["title"] for record in etl.extract()] == ["Concierto"]
    assert etl.source_status == {"ok": "ok", "failed": "failed", "empty": "empty"}


def test_an_empty_answer_is_a_warning_not_a_success(monkeypatch, caplog):
    _use(monkeypatch, _source("ok", [_raw("Concierto", "2026-12-10", "ok")]), _source("empty", []))
    _etl().extract()
    assert "Agenda empty answered but gave no event (the page changed?)" in caplog.text


def test_a_run_where_nobody_answers_is_a_failure_and_asks_nobody_twice(monkeypatch, caplog):
    """Every source failed, was refused or gave nothing: the run must not count as a success (T-192)."""
    caplog.set_level(logging.INFO)
    first = _source("first", error=TimeoutError("no answer"))
    second = _source("second", [])
    _use(monkeypatch, first, second)
    etl = _etl()

    with pytest.raises(ETLError, match="No Valencia events source gave an event"):
        etl.extract()
    assert "No Valencia events source gave an event (Agenda first: failed, Agenda second: empty). The stored events are kept." in caplog.text

    with pytest.raises(ETLError, match="in this run"):
        etl.extract()  # BaseETL would retry: the second attempt asks nobody again
    assert (first.fetch.calls, second.fetch.calls) == (1, 1)


def test_a_run_where_nobody_answers_leaves_the_stored_events_as_they_are(monkeypatch):
    etl = _etl()
    _use(monkeypatch, _source("a", [_raw("Concierto", "2026-12-10", "a")]))
    etl.load(etl.transform(etl.extract()))
    before = (etl.output_dir / EVENTS_FILE).read_bytes()

    _use(monkeypatch, _source("a", error=TimeoutError("no answer")))
    with pytest.raises(ETLError, match="No Valencia events source gave an event"):
        _etl().run()  # the failure travels through BaseETL.run(): the orchestrator counts it as one
    assert (etl.output_dir / EVENTS_FILE).read_bytes() == before


def test_a_legacy_source_that_swallows_a_refusal_is_still_reported_blocked(monkeypatch):
    """Meetup and Eventbrite catch every error and return nothing: the block list still knows the host."""
    monkeypatch.setattr(http.requests, "get", lambda url, headers=None, timeout=None: _Response(429))
    with pytest.raises(http.SourceBlockedError):
        http.fetch_page("https://www.meetup.com/find/events/")  # another source of the same host, earlier in the run
    swallows = Source("meetup.com", "Meetup", ("https://www.meetup.com/find/events/",), lambda logger=None: [])

    assert _etl()._fetch_source(swallows) == ([], "blocked")
    assert _etl()._fetch_source(Source("other", "Other", ("https://www.example.invalid/",), lambda logger=None: [])) == ([], "empty")


# --- the HTTP helper ---------------------------------------------------------------------------------


class _Response:
    def __init__(self, status: int, content: bytes = b"", headers: dict | None = None):
        self.status_code, self.content, self.headers = status, content, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")


def _patch_get(monkeypatch, answers: dict[str, int]) -> list[tuple]:
    calls: list[tuple] = []

    def fake_get(url, headers=None, timeout=None):
        calls.append((url, headers, timeout))
        return _Response(answers[url])

    monkeypatch.setattr(http.requests, "get", fake_get)
    return calls


def test_fetch_page_sends_a_branded_user_agent_and_returns_the_body(monkeypatch):
    calls = _patch_get(monkeypatch, {"https://www.example.invalid/a": 200})

    assert http.fetch_page("https://www.example.invalid/a") == b""
    assert calls == [("https://www.example.invalid/a", {"User-Agent": SCRAPER_BRANDED_USER_AGENT}, http.REQUEST_TIMEOUT_SECONDS)]


def test_a_refused_host_is_not_asked_again_in_the_run(monkeypatch):
    calls = _patch_get(monkeypatch, {"https://www.example.invalid/find": 429, "https://www.example.invalid/other": 200, "https://other.example.invalid/x": 200})

    with pytest.raises(http.SourceBlockedError) as refused:
        http.fetch_page("https://www.example.invalid/find")
    assert (refused.value.status_code, refused.value.host) == (429, "www.example.invalid")
    assert http.blocked_hosts() == {"www.example.invalid"}

    with pytest.raises(http.SourceBlockedError) as again:
        http.fetch_page("https://www.example.invalid/other")  # no request: the host said no
    assert again.value.status_code == 0
    assert http.fetch_page("https://other.example.invalid/x") == b""  # another host is still asked

    assert [url for url, _headers, _timeout in calls] == ["https://www.example.invalid/find", "https://other.example.invalid/x"]
    assert len(calls) == 2

    http.reset_blocked_hosts()
    assert http.blocked_hosts() == set()


def test_the_retry_after_of_a_refusal_is_kept_in_the_error(monkeypatch):
    monkeypatch.setattr(http.requests, "get", lambda url, headers=None, timeout=None: _Response(403, headers={"Retry-After": "86400"}))
    with pytest.raises(http.SourceBlockedError, match=r"HTTP 403 from www.example.invalid \(Retry-After: 86400\)"):
        http.fetch_page("https://www.example.invalid/find")


def test_any_other_error_is_raised_and_does_not_block_the_host(monkeypatch):
    _patch_get(monkeypatch, {"https://www.example.invalid/a": 500, "https://www.example.invalid/b": 404})
    with pytest.raises(requests.HTTPError):
        http.fetch_page("https://www.example.invalid/a")
    with pytest.raises(requests.HTTPError):
        http.fetch_page("https://www.example.invalid/b")
    assert http.blocked_hosts() == set()


# --- one record per event and per session -----------------------------------------------------------


def test_two_sources_of_one_event_are_merged_into_its_most_complete_record(monkeypatch):
    monthly = _source("monthly", [_raw("EL RETRAT DE DORIAN GRAY", "2026-11-28", "monthly")])
    principal = _source("principal", [_raw("El retrat de Dorian Gray", "2026-11-28", "principal", venue="Teatre Martín i Soler", description="Una obra", category="teatro", start_time="19:30")])  # codespell:ignore -- venue name
    _use(monkeypatch, monthly, principal)
    etl = _etl()

    models = etl.transform(etl.extract())

    assert len(models) == 1
    merged = models[0]
    assert (merged.venue, merged.description, merged.category, merged.start_time) == ("Teatre Martín i Soler", "Una obra", "teatro", "19:30")  # codespell:ignore -- venue name
    assert (merged.start_at, merged.start_local, merged.all_day) == ("2026-11-28T19:30:00+01:00", "sáb 28/11/2026 · 19:30", False)
    assert (merged.source, merged.metadata["source_label"]) == ("principal", "Agenda principal")  # the record that carries the clock leads
    assert (monthly.fetch.calls, principal.fetch.calls) == (1, 1)


def test_two_sessions_of_one_show_stay_two_events(monkeypatch):
    evening = _raw("La vida privada de Sherlock Holmes", "2026-11-28", "filmoteca", start_time="18:00")
    night = _raw("La vida privada de Sherlock Holmes", "2026-11-28", "filmoteca", start_time="20:30")
    next_day = _raw("La vida privada de Sherlock Holmes", "2026-11-29", "filmoteca", start_time="20:00")
    _use(monkeypatch, _source("filmoteca", [evening, night, next_day]))
    etl = _etl()

    models = etl.transform(etl.extract())

    assert sorted((model.start_date, model.start_time) for model in models) == [("2026-11-28", "18:00"), ("2026-11-28", "20:30"), ("2026-11-29", "20:00")]
    assert len({model.event_id for model in models}) == 3
    assert [model.price for model in models] == [None, None, None]  # the listing prints no price: none is made up


def test_the_same_meetup_from_both_meetup_sources_is_one_event(monkeypatch):
    """The legacy record carries the clock in its timestamp, the technology one in ``start_time``."""
    page = "https://www.meetup.com/cloud-native-valencia/events/1/"
    legacy = build_record(source="meetup.com", title="Cloud Native Valencia #6", url=page, date_text="2026-12-10T17:00:00.000Z", venue="The Terminal Hub", category="meetup")
    legacy["start_date"] = "2026-12-10"  # as the legacy extractor fills it
    tech = _raw("Cloud Native Valencia #6", "2026-12-10", "meetup.com/tech", url=page, start_time="18:00", category="tech")
    _use(monkeypatch, _source("meetup.com", [legacy]), _source("meetup.com/tech", [tech]))
    etl = _etl()

    models = etl.transform(etl.extract())

    assert len(models) == 1
    assert (models[0].start_local, models[0].category, models[0].venue) == ("jue 10/12/2026 · 18:00", "tech", "The Terminal Hub")


def test_an_undated_record_joins_the_first_dated_one_of_its_title(monkeypatch):
    undated = _raw("Feria de Atracciones", "", "featured")
    dated = _raw("Feria de atracciones", "2026-11-27", "monthly", end_date=date(2027, 1, 24))
    later = _raw("Feria de atracciones", "2027-03-01", "monthly")
    alone = _raw("Sin fecha", "", "featured")
    _use(monkeypatch, _source("featured", [undated, alone]), _source("monthly", [dated, later]))
    etl = _etl()

    models = etl.transform(etl.extract())

    assert sorted((model.title, model.start_date, model.end_date, model.source) for model in models) == [
        ("Feria de atracciones", "2026-11-27", "2027-01-24", "monthly"),  # the dated record leads: its dates are kept
        ("Feria de atracciones", "2027-03-01", "", "monthly"),
        ("Sin fecha", "", "", "featured"),  # nothing to join: kept, undated
    ]


def test_a_category_that_says_nothing_gives_way_to_one_that_says_something(monkeypatch):
    page = "https://www.meetup.com/python-valencia/events/1/"
    weak = _raw("Charla sobre Python", "2026-12-02", "meetup.com", url=page, start_time="19:00", category="meetup")
    specific = _raw("Charla sobre Python", "2026-12-02", "tech", url=page, start_time="19:00", category="tech")
    _use(monkeypatch, _source("meetup.com", [weak]), _source("tech", [specific]))
    etl = _etl()
    models = etl.transform(etl.extract())
    assert len(models) == 1
    assert models[0].category == "tech"


def test_a_record_without_a_date_stays_without_one(monkeypatch):
    """Nothing tells when "Próximamente" happens: it is kept, undated, and sorted after the dated ones (T-193)."""
    soon = build_record(source="featured", title="Próximamente", url="https://www.example.invalid/soon", date_text="Próximamente")
    etl = _etl()
    _use(monkeypatch, _source("featured", [soon, _raw("Concierto", "2026-12-10", "featured")]))
    etl.load(etl.transform(etl.extract()))
    stored = _stored(etl)
    assert [event["title"] for event in stored] == ["Concierto", "Próximamente"]
    undated = stored[1]
    assert (undated["start_date"], undated["start_at"], undated["end_at"], undated["start_local"], undated["date_text"]) == ("", "", "", "", "Próximamente")


# --- what a run writes --------------------------------------------------------------------------------


def test_transform_yields_models_with_real_dates_categories_and_ids(monkeypatch):
    opera = _raw("FRANCO FAGIOLI", "2026-11-28", "lesarts", start_time="19:00", venue="Palau de les Arts", category="música")
    tour = _raw("Museo & Tour del Valencia Basket en el Roig Arena", "2026-12-05", "monthly")
    visit = _raw("Visitas guiadas gratuitas a la torre", "2026-11-28", "monthly", start_time="11:00")
    _use(monkeypatch, _source("lesarts", [opera]), _source("monthly", [tour, visit]))
    etl = _etl()

    models = etl.transform(etl.extract())

    assert sorted(model.title for model in models) == sorted([opera["title"], tour["title"], visit["title"]])
    by_title = {model.title: model for model in models}
    assert by_title[opera["title"]].start_at == "2026-11-28T19:00:00+01:00"
    assert by_title[opera["title"]].zone == "Quatre Carreres"
    assert by_title[tour["title"]].zone == "Quatre Carreres"  # the title names the hall
    free = by_title[visit["title"]]
    assert (free.price, free.is_free, free.start_local) == (0.0, True, "sáb 28/11/2026 · 11:00")
    assert (by_title[opera["title"]].price, by_title[tour["title"]].price) == (None, None)  # no price printed: unknown
    assert len({model.event_id for model in models}) == 3
    assert all(model.category in CATEGORIES for model in models)
    assert all(model.first_detected_at == T1_ISO for model in models)


def test_the_legacy_keyword_pass_feeds_the_vocabulary(monkeypatch):
    """The legacy sources carry a keyword as category: it becomes a value of the vocabulary."""
    titles = ["II ciclo 'Música als Museus'", "Valencia Tech Job Fair Spring 2027", "Talleres de horchata artesanal en Alboraya", "Disfruta de la programación de otoño de L'ETNO"]
    _use(monkeypatch, _source("featured", [_raw(title, "2026-12-10", "featured") for title in titles]))
    etl = _etl()

    by_title = {model.title: model.category for model in etl.transform(etl.extract())}

    assert by_title == {titles[0]: "música", titles[1]: "tech", titles[2]: "gastronomía", titles[3]: "otro"}


def test_a_description_is_kept_only_when_the_source_wrote_one(monkeypatch):
    processed = _etl().process_valencia_events([_raw("Concierto de Navidad", "2026-12-20", "featured"), _raw("Taller", "2026-12-01", "featured", description="Un taller")])
    assert [event["description"] for event in processed] == ["", "Un taller"]


def test_the_optional_fields_of_the_new_sources_pass_through(monkeypatch):
    """Meetup's technology groups add a zoned timestamp next to the clock, as the legacy record of the same event carries it."""
    record = _raw("Noche", "2026-12-01", "feria", start_time="21:00", end_time="23:00", address="Av. de les Fires, 4", tags=["profesional"])  # codespell:ignore -- Spanish
    record["start_datetime"], record["end_datetime"] = "2026-12-01T21:00:00+01:00", "2026-12-01T23:00:00+01:00"
    [processed] = _etl().process_valencia_events([record])
    assert (processed["start_time"], processed["end_time"], processed["address"], processed["tags"], processed["start_datetime"], processed["end_datetime"]) == ("21:00", "23:00", "Av. de les Fires, 4", ["profesional"], "2026-12-01T21:00:00+01:00", "2026-12-01T23:00:00+01:00")  # codespell:ignore -- Spanish


def test_load_writes_the_events_the_state_and_the_status_of_the_sources(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    etl = _etl()
    concert = _raw("Concierto", "2026-12-10", "ok", start_time="19:30")
    _use(monkeypatch, _source("ok", [concert, _raw("Hoy", "2026-11-28", "ok"), _raw("Taller gratuito de cerámica", "2026-11-28", "ok", start_time="12:00"), _raw("Mañana", "2026-11-29", "ok")]), _source("empty", []), _source("failed", error=TimeoutError("no answer")))
    etl.load(etl.transform(etl.extract()))

    stored = _stored(etl)
    assert [event["title"] for event in stored] == ["Hoy", "Taller gratuito de cerámica", "Mañana", "Concierto"]
    assert stored[3]["start_local"] == "jue 10/12/2026 · 19:30"
    assert isinstance(json.loads((etl.output_dir / EVENTS_FILE).read_text(encoding="utf-8")), list)  # the API and the tab read a list
    stamps = json.loads((etl.output_dir / STAMPS_FILE).read_text(encoding="utf-8"))["events"]
    assert sorted(stamps) == sorted(event["event_id"] for event in stored)
    assert stamps[stored[3]["event_id"]] == {"first_detected_at": T1_ISO, "last_seen_at": T1_ISO}
    status = json.loads((etl.output_dir / SOURCE_STATUS_FILE).read_text(encoding="utf-8"))
    assert status["updated_at"] == T1_ISO
    assert status["events"] == 4
    assert [(entry["key"], entry["label"], entry["status"], entry["read"], entry["events"]) for entry in status["sources"]] == [("ok", "Agenda ok", "ok", 4, 4), ("empty", "Agenda empty", "empty", 0, 0), ("failed", "Agenda failed", "failed", 0, 0)]
    assert "Saved 4 events: 1 with a price (1 free); starting today 28/11/2026: 2, tomorrow: 1" in caplog.text
    assert "Agenda ok: ok - 4 read, 4 in the file" in caplog.text
    assert "Agenda failed: failed - 0 read, 0 in the file" in caplog.text
    assert not [path for path in etl.output_dir.iterdir() if path.name.endswith(".tmp")]  # written atomically, nothing left over


def test_load_sorts_by_start_date_and_the_undated_go_last(monkeypatch):
    etl = _etl()
    undated = build_record(source="ok", title="Próximamente", url="https://www.example.invalid/soon")
    _use(monkeypatch, _source("ok", [undated, _raw("Enero", "2027-01-10", "ok"), _raw("Diciembre", "2026-12-10", "ok")]))
    etl.load(etl.transform(etl.extract()))
    assert _titles(etl) == ["Diciembre", "Enero", "Próximamente"]


def test_the_registered_script_writes_the_file_the_tab_and_the_api_read(monkeypatch, tmp_path: Path):
    _use(monkeypatch, _source("ok", [_raw("Concierto", "2026-12-10", "ok")]))
    _etl().run()
    stored = json.loads((tmp_path / "data" / "valencia_events" / "valencia_events.json").read_text(encoding="utf-8"))
    assert [event["title"] for event in stored] == ["Concierto"]


def test_the_first_detection_survives_the_next_run(monkeypatch):
    kept, gone, later = _raw("Se queda", "2026-12-10", "ok"), _raw("Desaparece", "2026-12-11", "ok"), _raw("Nuevo", "2026-12-12", "ok")
    first_run = _etl()
    _use(monkeypatch, _source("ok", [kept, gone]))
    first_run.load(first_run.transform(first_run.extract()))
    ids = {event["title"]: event["event_id"] for event in _stored(first_run)}
    assert {event["title"]: event["first_detected_at"] for event in _stored(first_run)} == {"Se queda": T1_ISO, "Desaparece": T1_ISO}

    monkeypatch.setattr(composer, "madrid_now", lambda: T2)
    second_run = _etl()
    _use(monkeypatch, _source("ok", [kept, later]))
    second_run.load(second_run.transform(second_run.extract()))
    stored = {event["title"]: event for event in _stored(second_run)}

    assert list(stored) == ["Se queda", "Nuevo"]  # an event the source no longer lists is gone
    assert (stored["Se queda"]["first_detected_at"], stored["Se queda"]["first_detected_local"], stored["Se queda"]["last_seen_at"]) == (T1_ISO, "sáb 28/11/2026 · 06:00", T2_ISO)
    assert (stored["Nuevo"]["first_detected_at"], stored["Nuevo"]["last_seen_at"]) == (T2_ISO, T2_ISO)
    assert stored["Se queda"]["event_id"] == ids["Se queda"]
    stamps = json.loads((second_run.output_dir / STAMPS_FILE).read_text(encoding="utf-8"))["events"]
    assert stamps[ids["Desaparece"]]["first_detected_at"] == T1_ISO  # remembered for a while: it may come back
    assert stamps[ids["Se queda"]] == {"first_detected_at": T1_ISO, "last_seen_at": T2_ISO}


def test_an_event_that_comes_back_keeps_its_first_detection(monkeypatch):
    """It left the listing and returned: it is the same event, so its first detection does not move."""
    back = _raw("Vuelve", "2026-12-10", "ok")
    for listed, now in (([back], T1), ([_raw("Otra", "2026-12-11", "ok")], T1), ([back], T2)):
        monkeypatch.setattr(composer, "madrid_now", lambda now=now: now)
        _use(monkeypatch, _source("ok", listed))
        run = _etl()
        run.load(run.transform(run.extract()))
    stored = {event["title"]: event for event in _stored(run)}
    assert list(stored) == ["Vuelve"]
    assert (stored["Vuelve"]["first_detected_at"], stored["Vuelve"]["last_seen_at"]) == (T1_ISO, T2_ISO)


def test_nothing_to_load_keeps_the_last_good_file(monkeypatch):
    etl = _etl()
    _use(monkeypatch, _source("ok", [_raw("Concierto", "2026-12-10", "ok")]))
    etl.load(etl.transform(etl.extract()))
    before = (etl.output_dir / EVENTS_FILE).read_bytes()

    etl.load([])
    assert (etl.output_dir / EVENTS_FILE).read_bytes() == before


# --- a source that goes silent -----------------------------------------------------------------------


def test_a_silent_source_keeps_its_events_that_have_not_ended(monkeypatch, caplog):
    future = _raw("Futura", "2026-12-20", "a", venue="La Rambleta")
    ongoing = _raw("En curso", "2026-11-20", "a", end_date=date(2026, 12, 5))
    over = _raw("Ya terminó", "2026-11-10", "a", end_date=date(2026, 11, 25))
    elsewhere = _raw("Otra fuente", "2026-12-01", "b")
    _use(monkeypatch, _source("a", [future, ongoing, over]), _source("b", [elsewhere]))
    first_run = _etl()
    first_run.load(first_run.transform(first_run.extract()))
    assert len(_stored(first_run)) == 4

    monkeypatch.setattr(composer, "madrid_now", lambda: T2)
    _silent_a(monkeypatch, elsewhere)
    second_run = _etl()
    second_run.load(second_run.transform(second_run.extract()))
    stored = {event["title"]: event for event in _stored(second_run)}

    assert sorted(stored) == ["En curso", "Futura", "Otra fuente"]  # "Ya terminó" is over: nothing to keep
    for title in ("Futura", "En curso"):
        assert stored[title]["metadata"]["carried_over"] is True
        assert (stored[title]["last_seen_at"], stored[title]["first_detected_at"]) == (T1_ISO, T1_ISO)  # the last run that really saw it
    assert stored["Futura"]["venue"] == "La Rambleta"
    assert "Carried over 2 stored events of the sources that gave nothing: a" in caplog.text
    assert (stored["Otra fuente"]["last_seen_at"], "carried_over" in stored["Otra fuente"]["metadata"]) == (T2_ISO, False)
    status = json.loads((second_run.output_dir / SOURCE_STATUS_FILE).read_text(encoding="utf-8"))
    assert [(entry["status"], entry["read"], entry["events"]) for entry in status["sources"]] == [("failed", 0, 2), ("ok", 1, 1)]


def test_a_source_that_answers_drops_what_it_no_longer_lists(monkeypatch):
    """Only a silent source keeps its old events: a source that answers and drops an event means it."""
    _use(monkeypatch, _source("a", [_raw("Queda", "2026-12-20", "a"), _raw("Sale", "2026-12-21", "a")]), _source("b", [_raw("Otra", "2026-12-01", "b")]))
    _etl().load(_etl().transform(_etl().extract()))

    monkeypatch.setattr(composer, "madrid_now", lambda: T2)
    _use(monkeypatch, _source("a", [_raw("Queda", "2026-12-20", "a")]), _source("b", [_raw("Otra", "2026-12-01", "b")]))
    second = _etl()
    second.load(second.transform(second.extract()))
    assert sorted(_titles(second)) == ["Otra", "Queda"]  # what it no longer lists is gone
    assert not any(event["metadata"].get("carried_over") for event in _stored(second))


def test_carried_events_go_a_week_after_the_last_run_that_saw_them(monkeypatch):
    future = _raw("Futura", "2027-01-20", "a")
    other = _raw("Otra", "2026-12-01", "b")
    _use(monkeypatch, _source("a", [future]), _source("b", [other]))
    first = _etl()
    first.load(first.transform(first.extract()))

    for days in (CARRY_OVER_DAYS - 1, CARRY_OVER_DAYS, CARRY_OVER_DAYS + 1):
        monkeypatch.setattr(composer, "madrid_now", lambda days=days: T1 + timedelta(days=days))
        _silent_a(monkeypatch, other)
        run = _etl()
        run.load(run.transform(run.extract()))
        titles = _titles(run)
        assert ("Futura" in titles) is (days <= CARRY_OVER_DAYS), f"on day {days}: {titles}"


def test_the_days_are_counted_from_the_last_run_that_really_saw_the_event(monkeypatch):
    """A carried event is not "seen" by the runs that repeat it: it is dropped a week after the source went silent."""
    _use(monkeypatch, _source("a", [_raw("Futura", "2027-01-20", "a")]))
    first = _etl()
    first.load(first.transform(first.extract()))
    for days in (2, 4, 6):
        monkeypatch.setattr(composer, "madrid_now", lambda days=days: T1 + timedelta(days=days))
        _silent_a(monkeypatch, _raw("Otra", f"2026-12-{days:02d}", "b"))
        run = _etl()
        run.load(run.transform(run.extract()))
        stored = {event["title"]: event for event in _stored(run)}
        assert stored["Futura"]["metadata"]["carried_over"] is True
        assert stored["Futura"]["last_seen_at"] == T1_ISO  # never moved by the runs that repeat it

    monkeypatch.setattr(composer, "madrid_now", lambda: T1 + timedelta(days=8))
    _silent_a(monkeypatch, _raw("Otra", "2026-12-10", "b"))
    run = _etl()
    run.load(run.transform(run.extract()))
    assert _titles(run) == ["Otra"]


def test_a_carried_event_is_not_kept_twice_when_two_silent_sources_listed_it(monkeypatch):
    page = "https://www.example.invalid/mismo"
    _use(monkeypatch, _source("a", [_raw("Mismo", "2026-12-20", "a", url=page)]), _source("b", [_raw("Mismo", "2026-12-20", "b", url=page)]))
    first = _etl()
    first.load(first.transform(first.extract()))
    assert _titles(first) == ["Mismo"]  # both sources described one event: one record

    monkeypatch.setattr(composer, "madrid_now", lambda: T2)
    _use(monkeypatch, _source("a", error=TimeoutError("no answer")), _source("b", error=TimeoutError("no answer")), _source("c", [_raw("Otra", "2026-12-01", "c")]))
    second = _etl()
    second.load(second.transform(second.extract()))
    assert sorted(_titles(second)) == ["Mismo", "Otra"]  # still one record, not one per silent source


def test_an_undated_event_of_a_silent_source_is_not_carried(monkeypatch):
    """Without a date nothing tells whether it is still on: it goes with the listing that printed it."""
    _use(monkeypatch, _source("a", [_raw("Sin fecha", "", "a"), _raw("Con fecha", "2027-01-20", "a")]), _source("b", [_raw("Otra", "2026-12-01", "b")]))
    _etl().load(_etl().transform(_etl().extract()))
    _silent_a(monkeypatch, _raw("Otra", "2026-12-01", "b"))
    run = _etl()
    run.load(run.transform(run.extract()))
    assert sorted(_titles(run)) == ["Con fecha", "Otra"]


def test_a_stored_event_that_this_run_lists_again_is_not_repeated(monkeypatch):
    """Another source lists the event the silent source used to list: one record, and it is not flagged."""
    _use(monkeypatch, _source("a", [_raw("Futura", "2026-12-20", "a")]), _source("b", [_raw("Otra", "2026-12-01", "b")]))
    _etl().load(_etl().transform(_etl().extract()))
    _silent_a(monkeypatch, _raw("Otra", "2026-12-01", "b"), _raw("Futura", "2026-12-20", "b"))
    run = _etl()
    run.load(run.transform(run.extract()))
    stored = {event["title"]: event for event in _stored(run)}
    assert sorted(stored) == ["Futura", "Otra"]
    assert not stored["Futura"]["metadata"].get("carried_over")
    assert stored["Futura"]["last_seen_at"] == T1_ISO


def test_the_stored_events_of_a_file_that_cannot_be_read_are_simply_none(monkeypatch, tmp_path: Path):
    etl = _etl()
    assert etl._previous_events() == []  # no file yet
    write_text_atomic(etl.output_dir / EVENTS_FILE, "{not json")
    assert etl._previous_events() == []
    write_text_atomic(etl.output_dir / EVENTS_FILE, json.dumps({"not": "a list"}))
    assert etl._previous_events() == []
    write_text_atomic(etl.output_dir / EVENTS_FILE, json.dumps([{"title": "una"}, "basura", 3]))
    assert etl._previous_events() == [{"title": "una"}]
