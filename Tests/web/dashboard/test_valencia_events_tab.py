"""The Valencia Events tab: a table one can filter, order and page (T-143).

The layout is rendered through Dash (a real app serves it the way the renderer receives it, /_dash-layout), and the
callbacks are called the way the browser calls them, POST /_dash-update-component on that app through Flask's test
client (see Tests/web/dashboard/test_inserted_buttons.py), so ``dash.ctx`` is Dash's own and not a mock.

Fixtures only: ``load_valencia_events`` and ``load_sources_status`` are replaced, so nothing under data/ is read.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import dash
import dash_bootstrap_components as dbc
import pytest
from dash import html

from src.web.dashboard.components import valencia_events_new_tab as vet

MADRID = ZoneInfo("Europe/Madrid")
# A Saturday morning: the weekend is today and tomorrow, the week ends tomorrow, the month in two days.
NOW = datetime(2026, 11, 28, 9, 0, tzinfo=MADRID)
TODAY = NOW.date()
CET = "+01:00"
WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
JS_PATH = Path(__file__).resolve().parents[3] / "src" / "web" / "dashboard" / "assets" / "js" / "valencia_state.js"


def _iso(day: int) -> str:
    return (TODAY + timedelta(days=day)).isoformat()


def _event(title: str, day: int | None, *, hour: str = "", last_day: int | None = None, category: str = "otro", price: float | None = None, detected: float | None = None, **extra) -> dict:
    """An event as the ETL of T-143 stores it: aware ISO moments, and the readable local form next to them.

    ``day`` and ``last_day`` are offsets from today; ``day=None`` is an event without a date. ``detected`` is the
    moment of the first detection, in hours before ``NOW``; ``None`` leaves the record without a stamp, as in the
    files written before T-143.
    """
    if day is None:
        start_date, start_at, end_at = "", "", ""
    elif hour:
        start_date = _iso(day)
        start_at = f"{start_date}T{hour}:00{CET}"
        end_at = f"{_iso(last_day)}T04:00:00{CET}" if last_day is not None else ""  # a night ends at 04:00
    else:
        start_date = _iso(day)
        start_at = f"{start_date}T00:00:00{CET}"
        end_at = f"{_iso(day + 1 if last_day is None else last_day + 1)}T00:00:00{CET}"  # all-day: the midnight after the last day
    moment = datetime.fromisoformat(start_at) if start_at else None
    event = {
        "title": title,
        "url": f"https://example.invalid/{title.lower().replace(' ', '-')}",
        "source": "fixture",
        "category": category,
        "description": "",
        "start_date": start_date,
        "end_date": _iso(last_day) if last_day is not None else "",
        "venue": "",
        "address": "",
        "price": price,
        "price_info": "",
        "is_free": price == 0,
        "tags": [],
        "start_at": start_at,
        "end_at": end_at,
        "all_day": not hour,
    }
    if moment is not None:
        event["start_local"] = f"{WEEKDAYS[moment.weekday()]} {moment:%d/%m/%Y}" + (f" · {moment:%H:%M}" if hour else "")
    if detected is not None:
        event["first_detected_at"] = (NOW - timedelta(hours=detected)).isoformat()
    event.update(extra)
    return event


T = {
    "A": "Concierto en Ruzafa",
    "B": "Taller de cerámica",
    "C": "Feria Horeq",
    "D": "IVAM permanente",
    "E": "Visita al Mercado Central",
    "F": "Partido de baloncesto",
    "G": "Meetup de Python",
    "H": "Ciclo de cine",
    "I": "Próximamente, sin fecha",
    "J": "El dragón",
    "K": "Sesión de ayer",
    "L": "Noche larga",
    "M": "Festival de luz",
}

EVENTS = [
    _event(T["A"], 0, hour="20:00", category="música", price=12.5, detected=72, venue="Sala Russafa", zone="Ruzafa"),
    _event(T["B"], 0, hour="12:00", category="infantil", price=0, detected=48, venue="Centre del Carme", zone="Ciutat Vella", description="Taller gratis de cerámica, con inscripción"),
    _event(T["C"], 3, last_day=4, category="ferias", detected=1, venue="Feria Valencia", address="Av. de les Fires, 4", zone="Paterna"),
    _event(T["D"], -30, last_day=60, category="arte", detected=240, venue="IVAM", zone="Ciutat Vella", tags=["permanente"]),
    _event(T["E"], 1, hour="10:00", category="visitas y rutas", price=0, detected=0.5, venue="Mercado Central", zone="Ciutat Vella", metadata={"source_label": "Ajuntament"}),
    _event(T["F"], 20, hour="18:30", category="deporte", price=15, detected=24, venue="Roig Arena", zone="Quatre Carreres", price_max=60),
    _event(T["G"], 2, hour="19:00", category="tech", price=0, detected=0, venue="Cowork Ruzafa", zone="Ruzafa"),
    _event(T["H"], 40, hour="17:00", category="cine", detected=100, venue="Filmoteca"),
    _event(T["I"], None, detected=50),
    _event(T["J"], 1, hour="17:00", category="infantil", price=6, detected=200, venue="Escalante", zone="Extramurs", description="Teatro para niños de 4 a 9 años"),
    _event(T["K"], -1, hour="20:00", detected=300, venue="Sala Velvet"),  # over yesterday: never listed
    _event(T["L"], 0, hour="23:00", last_day=1, category="música", venue="Sala Midnight"),  # no stamp: an older file
    _event(T["M"], -2, last_day=2, category="fiestas", price=0, detected=300, venue="Jardín del Turia", zone="Pla del Real"),  # began on Thursday, still on
]


def _names(keys: str) -> list[str]:
    """The titles of the events ``keys`` names, in that order."""
    return [T[key] for key in keys]


def _titles(events: list[dict]) -> list[str]:
    return [event["title"] for event in events]


def _under(period: str = "all", **filters) -> list[str]:
    """What the filters let through among EVENTS, as a set of titles."""
    return set(_titles(vet.apply_filters(EVENTS, now=NOW, period=period, **filters)))


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vet, "load_valencia_events", lambda: [dict(event) for event in EVENTS])
    monkeypatch.setattr(vet, "load_sources_status", lambda: {})
    monkeypatch.setattr(vet, "_now", lambda: NOW)


# --- reading a rendered tree -------------------------------------------------------------------------


def _props(node) -> dict:
    """The props of a Dash component, as Dash serializes them."""
    return node.to_plotly_json()["props"]


def _walk(node):
    """Every props dict of a component tree, in document order; a tree as Dash serialized it in an answer goes the same way."""
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk(item)
    elif hasattr(node, "to_plotly_json"):
        yield from _walk(_props(node))
    elif isinstance(node, dict) and "props" in node:  # a serialized component: {"type": ..., "props": {...}}
        yield from _walk(node["props"])
    elif isinstance(node, dict):
        yield node
        yield from _walk(node.get("children"))


def _flat(node) -> list[str]:
    """Every text a component tree shows, the labels of its options included, in document order."""
    if hasattr(node, "to_plotly_json"):
        return _flat(_props(node))
    if isinstance(node, dict):
        return [text for key in ("props", "children", "options", "label") for text in _flat(node.get(key))]
    if isinstance(node, (list, tuple)):
        return [text for item in node for text in _flat(item)]
    if isinstance(node, bool) or node is None:
        return []
    return [str(node)]


def _texts(node) -> str:
    return " | ".join(_flat(node))


def _plain(node) -> str:
    """The text of a title, mark-up apart."""
    return "".join(_flat(node))


def _ids(node) -> list[str]:
    return [props["id"] for props in _walk(node) if isinstance(props.get("id"), str)]


def _find(node, comp_id: str) -> dict | None:
    """The props of the component ``comp_id``."""
    return next((props for props in _walk(node) if props.get("id") == comp_id), None)


def _rows(results) -> list[dict]:
    return [props for props in _walk(results) if props.get("className") == "wt-valencia-event"]


def _listed(results) -> list[str]:
    """The titles of the rows in the table, in order."""
    return [_plain(row["children"][0]) for row in _rows(results)]


def _buttons(pager) -> dict[str, dict]:
    return {props["id"]: props for props in _walk(pager) if props.get("id") in (vet.PREV_ID, vet.NEXT_ID)}


def _cards(row) -> list[tuple[str, str]]:
    """``(value, label)`` of every stat card."""
    texts = [_flat(props["children"])[0] for props in _walk(row) if props.get("className") in ("card-title mb-0", "card-text text-muted small mb-0")]
    return list(zip(texts[0::2], texts[1::2], strict=True))


def _options(layout, comp_id: str) -> list[tuple[str, object]]:
    return [(option["label"], option["value"]) for option in _find(layout, comp_id)["options"]]


# --- the layout --------------------------------------------------------------------------------------


def test_the_layout_has_every_control_and_its_labels_are_spanish() -> None:
    layout = vet.render_valencia_events_tab()

    ids = _ids(layout)
    for comp_id in (
        vet.SEARCH_ID,
        vet.SEARCH_CLEAR_ID,
        vet.PERIOD_ID,
        vet.FROM_ID,
        vet.TO_ID,
        vet.RANGE_ROW_ID,
        vet.CATEGORY_ID,
        vet.ZONE_ID,
        vet.FREE_ID,
        vet.ONLY_NEW_ID,
        vet.ONGOING_ID,
        vet.SORT_ID,
        vet.PER_PAGE_ID,
        vet.CLEAR_ID,
        vet.RESULTS_ID,
        vet.PAGER_ID,
        vet.PREV_ID,
        vet.NEXT_ID,
        vet.PAGE_STORE_ID,
        vet.LAST_VISIT_ID,
        vet.NEW_BOX_ID,
        vet.NOTICE_ID,
        vet.SHOW_ALL_ID,
        vet.MARK_SEEN_ID,
    ):
        assert comp_id in ids, comp_id
    texts = _texts(layout)
    for label in ("Eventos en València", "Buscar", "Cuándo", "Orden", "Por página", "Desde", "Hasta", "Categoría", "Zona", "Limpiar filtros", "Solo gratis", "Solo los nuevos desde mi última visita", "Incluir lo que ya ha empezado", "Marcar como vistos"):
        assert label in texts, label
    assert _find(layout, vet.SEARCH_ID)["placeholder"] == "Nombre, lugar, categoría… (vale sin tildes)"
    for option in ("Próximos 7 días", "Hoy", "Este fin de semana", "Esta semana", "Este mes", "Rango personalizado", "Todas las fechas"):
        assert option in texts, option
    for option in ("Fecha: más cercano primero", "Fecha: más lejano primero", "Precio: más barato primero", "Precio: más caro primero", "Detectados hace menos tiempo"):
        assert option in texts, option
    for header in ("Evento", "Cuándo", "Dónde", "Precio", "Categoría"):
        assert header in texts, header
    for leftover in ("Showing", "Free Events", "Upcoming Events", "Total Events", "All Events", "Search", "N/D", "Venue", "Price"):
        assert leftover not in texts, leftover


def test_the_default_view_lists_what_starts_in_the_next_seven_days() -> None:
    layout = vet.render_valencia_events_tab()

    results = _find(layout, vet.RESULTS_ID)["children"]
    assert _listed(results) == _names("BALEJGC")  # by start: the hour today, then tomorrow...
    assert _flat(results[0]) == ["7 eventos", " · 3 gratis"]
    assert _flat(_find(layout, vet.PAGER_ID)) == ["← Prev", "Mostrando 1–7 de 7 · Página 1 de 1", "Next →"]
    # The exhibition that began a month ago, the festival that began on Thursday, the undated one and what is over are not in it.
    assert not _under("week7") & set(_names("DIMK"))
    assert _find(layout, vet.RANGE_ROW_ID)["hidden"] is True
    assert _find(layout, vet.NEW_BOX_ID)["hidden"] is True


def test_the_options_carry_the_count_of_the_events_still_on() -> None:
    layout = vet.render_valencia_events_tab()

    categories = _options(layout, vet.CATEGORY_ID)
    assert categories[:4] == [("Todas las categorías", "all"), ("infantil (2)", "infantil"), ("música (2)", "música"), ("arte (1)", "arte")]
    assert categories[-1] == ("visitas y rutas (1)", "visitas y rutas")
    assert "Sesión de ayer" not in _flat(layout)  # what is over counts nowhere
    zones = _options(layout, vet.ZONE_ID)
    assert zones[:3] == [("Todas las zonas", "all"), ("Ciutat Vella (3)", "Ciutat Vella"), ("Ruzafa (2)", "Ruzafa")]
    assert zones[-1] == ("(sin zona) (3)", vet.NO_ZONE)  # the events that name no zone, last
    assert [label for label, _ in zones[3:-1]] == ["Extramurs (1)", "Paterna (1)", "Pla del Real (1)", "Quatre Carreres (1)"]


def test_the_stat_cards_count_over_every_event_still_on() -> None:
    assert _cards(vet._stat_cards(EVENTS, NOW)) == [("12", "Eventos próximos"), ("4", "Gratis"), ("3", "Empiezan hoy"), ("5", "Este fin de semana")]
    # Without one price, a 0 would read as "nothing is free": the card says there is no data.
    assert _cards(vet._stat_cards([_event("Sin precio", 1), _event("Otro", 2)], NOW))[1] == ("—", "Gratis (sin datos de precio)")


def test_dates_are_the_readable_local_form() -> None:
    assert vet._when_text(EVENTS[0]) == "sáb 28/11/2026 · 20:00"
    assert vet._when_text(EVENTS[2]) == "mar 01/12/2026 – 02/12/2026"  # an all-day span: the last day
    assert vet._when_text(EVENTS[11]) == "sáb 28/11/2026 · 23:00 – 04:00"  # a night that ends after midnight
    assert vet._when_text(EVENTS[3]) == "jue 29/10/2026 – 27/01/2027"
    assert vet._when_text(EVENTS[8]) == "N/A"  # without a date, the rule that always applied
    # What began before today says so when it is listed, with its last day when the source gives one.
    assert _flat(vet._when_cell(EVENTS[3], NOW)) == ["jue 29/10/2026 – 27/01/2027", " · en curso hasta 27/01/2027"]
    assert _flat(vet._when_cell(EVENTS[12], NOW)) == ["jue 26/11/2026 – 30/11/2026", " · en curso hasta 30/11/2026"]
    assert _flat(vet._when_cell(EVENTS[0], NOW)) == ["sáb 28/11/2026 · 20:00"]


def test_rows_carry_the_first_detection_for_the_script() -> None:
    layout = vet.render_valencia_events_tab()

    stamps = {event["title"]: event.get("first_detected_at") for event in EVENTS}
    rows = _rows(_find(layout, vet.RESULTS_ID)["children"])
    assert {_plain(row["children"][0]): row.get("data-valencia-detected") for row in rows} == {title: stamps[title] for title in _names("BALEJGC")}
    # An event of an older file has no stamp: no attribute, so the script leaves it alone.
    assert "data-valencia-detected" not in _props(vet._event_cell({"title": "Viejo", "start_date": "28/11/2026"}))


def test_what_the_cells_say() -> None:
    assert _texts(vet._price_cell({"price": 0})) == "Gratis"
    assert _texts(vet._price_cell({"price": 12.5})) == "12,5 €"
    assert _texts(vet._price_cell({"price": 15, "price_max": 60})) == "15 € – 60 €"
    assert _texts(vet._price_cell({"price": 1234})) == "1.234 €"
    assert _texts(vet._price_cell({"price": None})) == "—"  # never a guess
    assert _props(vet._price_cell({"price": None}))["title"] == "La fuente no indica el precio"
    assert _texts(vet._price_cell({"price": None, "price_info": "Consultar"})) == "Consultar"  # what the source prints
    assert _texts(vet._price_cell({"is_free": True})) == "Gratis"  # an older file: the source said it is free

    assert _texts(vet._where_cell({"venue": "Feria Valencia", "address": "Av. de les Fires, 4", "zone": "Paterna"})) == "Feria Valencia | Av. de les Fires, 4 | Paterna"
    assert _texts(vet._where_cell({"venue": "Roig Arena", "address": "Roig Arena"})) == "Roig Arena"  # the address repeats the venue
    assert _texts(vet._where_cell({})) == "—"
    assert _texts(vet._event_cell({"title": "Ciclo", "metadata": {"carried_over": True, "source_label": "Filmoteca"}})) == "Ciclo | sin confirmar | Fuente: Filmoteca"
    assert _texts(vet._event_cell({"title": "Sin enlace"})) == "Sin enlace"
    assert _texts(vet._category_cell({"category": "música"})) == "música"
    assert _texts(vet._category_cell({})) == "otro"


def test_a_description_is_plain_text_and_cut_short() -> None:
    cell = vet._event_cell({"title": "Largo", "description": "<p>" + "x" * 400})

    shown = _flat(_props(cell)["children"][1])[0]
    assert shown.startswith("x") and len(shown) == 180 and shown.endswith("…")


def test_the_search_term_is_marked_in_the_title_and_the_place() -> None:
    title = _props(vet._event_cell(EVENTS[0], "concierto"))["children"][0]
    marked = [child for props in _walk(title) for child in props.get("children", []) if hasattr(child, "to_plotly_json") and child.to_plotly_json()["type"] == "Mark"]
    assert [_texts(mark) for mark in marked] == ["Concierto"]
    assert _plain(title) == T["A"]
    assert _plain(_props(vet._where_cell(EVENTS[0], "rusafa"))["children"][0]) == "Sala Russafa"


def test_an_older_file_still_renders() -> None:
    older = [
        {"title": "Legacy tarde", "url": "https://example.invalid/legacy", "start_date": "2026-11-28T19:30:00", "date_text": "2026-11-28T19:30:00", "end_date": "", "is_free": True},
        {"title": "Legacy mañana", "start_date": "29/11/2026", "end_date": "30/11/2026", "is_free": False, "venue": "MUVa"},
    ]

    assert vet._when_text(older[0]) == "sáb 28/11/2026 · 19:30"
    assert vet._when_text(older[1]) == "dom 29/11/2026 – 30/11/2026"
    assert _titles(vet.apply_filters(older, now=NOW)) == ["Legacy tarde", "Legacy mañana"]
    assert _texts(vet._price_cell(older[0])) == "Gratis"
    assert "data-valencia-detected" not in _props(vet._event_cell(older[0]))
    assert _texts(vet._category_cell(older[0])) == "otro"
    assert vet.new_since(older, NOW - timedelta(days=10), NOW) == []  # no stamp: never "new"


def test_without_events_the_tab_says_so_and_shows_no_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vet, "load_valencia_events", lambda: [])
    layout = vet.render_valencia_events_tab()

    assert "Todavía no hay eventos de València" in _texts(layout)
    ids = _ids(layout)
    for comp_id in (vet.SEARCH_ID, vet.RESULTS_ID, vet.PAGER_ID, vet.NEW_BOX_ID, "valencia-ics-export-btn", "valencia-ics-events"):
        assert comp_id not in ids, comp_id  # no filters to use and nothing to export


def test_the_status_line_names_the_agendas_that_did_not_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    def _status(*sources: dict) -> None:
        monkeypatch.setattr(vet, "load_sources_status", lambda: {"updated_at": "2026-11-28T06:24:10+01:00", "events": 522, "sources": list(sources)})

    _status({"label": "Ajuntament", "status": "ok"}, {"label": "Filmoteca", "status": "failed"})
    assert _flat(vet._source_status_note()) == ["1 de 2 agendas respondieron · datos del sáb 28/11/2026 · 06:24", " · ", "sin datos de: Filmoteca"]
    _status({"label": "Ajuntament", "status": "ok"})
    assert _flat(vet._source_status_note()) == ["1 de 1 agendas respondieron · datos del sáb 28/11/2026 · 06:24"]
    monkeypatch.setattr(vet, "load_sources_status", lambda: {})
    assert vet._source_status_note() == ""


def test_the_ics_export_button_counts_what_starts_today_or_later() -> None:
    layout = vet.render_valencia_events_tab()

    assert "⬇ .ics (9)" in _texts(layout)
    assert "valencia-ics-export-btn" in _ids(layout)


def test_the_layout_has_no_duplicate_ids() -> None:
    ids = _ids(vet.render_valencia_events_tab())

    assert len(ids) == len(set(ids))


def test_the_search_box_and_the_two_dates_send_their_value_after_a_pause() -> None:
    """Every field one types in sends its value after a pause, a day picked in the calendar included.

    A debounce of True sends a date only when the field loses focus or gets Enter, and the native calendar
    leaves the focus in the field: the table kept the old list until the user clicked somewhere else, while
    every select next to it had answered at once.
    """
    layout = vet.render_valencia_events_tab()

    typed = {props["id"]: props["debounce"] for props in _walk(layout) if props.get("id") in (vet.SEARCH_ID, vet.FROM_ID, vet.TO_ID) and "debounce" in props}
    assert typed == {vet.SEARCH_ID: vet.DEBOUNCE_MS, vet.FROM_ID: vet.DEBOUNCE_MS, vet.TO_ID: vet.DEBOUNCE_MS}
    assert isinstance(vet.DEBOUNCE_MS, int) and vet.DEBOUNCE_MS > 0


# --- the filters -------------------------------------------------------------------------------------


@pytest.mark.parametrize(("period", "expected"), [("today", "ABL"), ("weekend", "ABLEJ"), ("this_week", "ABLEJ"), ("this_month", "ABEGJL"), ("week7", "ABLEJGC"), ("all", "ABCEFGHIJL")])
def test_each_period_lets_through_the_events_that_start_in_it(period: str, expected: str) -> None:
    assert _under(period) == set(_names(expected))


@pytest.mark.parametrize(("period", "expected"), [("today", (TODAY, TODAY)), ("this_week", (TODAY, date(2026, 11, 29))), ("this_month", (TODAY, date(2026, 11, 30))), ("all", (TODAY, None)), ("week7", (TODAY, date(2026, 12, 4)))])
def test_each_period_covers_the_days_it_names(period: str, expected: tuple) -> None:
    assert vet._window(period, TODAY, None, None) == expected


@pytest.mark.parametrize(("today", "saturday"), [(date(2026, 11, 23), date(2026, 11, 28)), (date(2026, 11, 27), date(2026, 11, 28)), (date(2026, 11, 28), date(2026, 11, 28)), (date(2026, 11, 29), date(2026, 11, 28)), (date(2026, 12, 1), date(2026, 12, 5))])
def test_the_weekend_is_always_saturday_and_sunday_of_the_current_week(today: date, saturday: date) -> None:
    assert vet._window("weekend", today, None, None) == (saturday, saturday + timedelta(days=1))


def test_on_sunday_the_weekend_is_yesterday_and_today_minus_what_is_over() -> None:
    sunday = datetime(2026, 11, 29, 10, 0, tzinfo=MADRID)
    kept = vet.apply_filters(EVENTS, now=sunday, period="weekend")

    assert _titles(kept) == _names("EJ")  # Saturday's concert and the night that ended at 04:00 are over


def test_a_custom_range_uses_the_two_dates_and_can_be_open_at_one_end() -> None:
    everything = lambda **filters: _under("custom", **filters)  # noqa: E731

    assert everything(date_from="2026-12-01", date_to="2026-12-20") == set(_names("CF"))
    assert everything(date_from="2026-12-20", date_to="2026-12-01") == set(_names("CF"))  # reversed: the same days
    assert everything(date_from="2026-12-15") == set(_names("FHI"))  # no last day: the undated one fits too
    assert everything(date_to="2026-11-29") == set(_names("ABLEJ"))  # no first day: from today
    assert everything() == set(_names("ABLEJGC"))  # nothing chosen yet: the default week
    assert everything(date_from="garbage", date_to="también") == set(_names("ABLEJGC"))
    # A range in the past keeps what began in it and is still on; what ended is gone.
    assert everything(date_from="2026-11-20", date_to="2026-11-27") == {T["M"]}
    assert everything(date_from="2026-11-20", date_to="2026-11-25") == set()


def test_what_began_earlier_is_listed_only_on_request() -> None:
    assert _under("week7", include_ongoing=True) == set(_names("ABLEJGCDM"))
    assert _under("today", include_ongoing=True) == set(_names("ABLDM"))
    assert _under("week7", include_ongoing=True, term="ivam") == {T["D"]}


def test_what_is_over_is_never_listed_whatever_the_filters() -> None:
    assert T["K"] not in _under("all", include_ongoing=True)
    assert T["K"] not in _under("custom", date_from="2026-11-01", date_to="2026-11-30", include_ongoing=True)


def test_an_event_without_a_date_is_listed_only_when_the_window_has_no_last_day() -> None:
    assert T["I"] not in _under("week7") | _under("today") | _under("this_month") | _under("weekend")
    assert T["I"] in _under("all") and T["I"] in _under("custom", date_from="2026-12-15")
    assert T["I"] not in _under("custom", date_to="2027-01-01")


def test_category_zone_and_solo_gratis_narrow_the_list() -> None:
    assert _under(category="infantil") == set(_names("BJ"))
    assert _under(zone="Ruzafa") == set(_names("AG"))
    assert _under(zone=vet.NO_ZONE) == set(_names("HIL"))
    assert _under(free_only=True) == set(_names("BEG"))  # what states no price is not free
    assert _under(category="infantil", zone="Extramurs") == {T["J"]}  # both at once
    assert _under(category="tech", free_only=True) == {T["G"]}
    assert _under(category="música", free_only=True, zone="Ciutat Vella") == set()


def test_a_term_matches_without_accents_and_every_word_must_appear() -> None:
    found = lambda term: _titles(vet.apply_filters(EVENTS, now=NOW, period="all", term=term))  # noqa: E731

    assert found("musica") == _names("AL")  # the category
    assert found("MÚSICA ruzafa") == [T["A"]]  # every word, accents and case apart
    assert found("ruzafa") == _names("AG")  # the zone: the venue spells it "Russafa"
    assert found("russafa") == [T["A"]]
    assert found("ninos") == [T["J"]]  # the description
    assert found("taller gratis") == [T["B"]]
    assert found("fires") == [T["C"]]  # the address
    assert found("ajuntament") == [T["E"]]  # the label of the source
    assert found("zzz") == [] and found("taller zz") == []
    assert found("  ") == _titles(vet.apply_filters(EVENTS, now=NOW, period="all"))  # blanks are no term


def test_the_search_covers_the_tags_and_the_source() -> None:
    events = [_event("Charla", 1, category="tech", tags=["python", "meetup"], source="meetup_tech"), _event("Otro", 1, tags=["cine"], address="C/ Mayor, 1")]

    assert _titles(vet.apply_filters(events, now=NOW, period="all", term="meetup")) == ["Charla"]
    assert _titles(vet.apply_filters(events, now=NOW, period="all", term="mayor")) == ["Otro"]
    assert _titles(vet.apply_filters(events, now=NOW, period="all", term="python")) == ["Charla"]


# --- "new since your last visit" ----------------------------------------------------------------------


def test_new_since_keeps_what_was_detected_after_the_previous_visit_and_is_still_on() -> None:
    previous = NOW - timedelta(hours=3)
    events = EVENTS + [_event("Lo de ayer, visto hoy", -1, hour="20:00", detected=1)]

    assert _titles(vet.new_since(events, previous, NOW)) == _names("CEG")
    assert vet.new_since(events, None, NOW) == []  # a first visit: nothing to compare with
    assert vet.new_since(events, NOW, NOW) == []  # everything was seen
    assert _under(new_only=True, last_visit=previous) == set(_names("CEG"))
    # The dates still apply on top of it.
    assert set(_titles(vet.apply_filters(EVENTS, now=NOW, period="weekend", new_only=True, last_visit=previous))) == {T["E"]}
    assert vet.apply_filters(EVENTS, now=NOW, new_only=True, last_visit=None) == []  # nothing "new" on a first visit


def test_the_notice_lists_the_new_events_and_its_button_names_the_rest() -> None:
    notice, label = vet.build_new_notice(EVENTS, NOW - timedelta(hours=3), NOW)

    assert label == "Ver los 3 nuevos en la tabla"
    assert _flat(notice[0]) == ["🆕 ", "Nuevos desde tu última visita: 3 eventos"]
    assert [_plain(item) for item in _props(notice[1])["children"]] == [
        "Feria Horeq · mar 01/12/2026 – 02/12/2026 · Feria Valencia",
        "Visita al Mercado Central · dom 29/11/2026 · 10:00 · Mercado Central · Gratis",
        "Meetup de Python · lun 30/11/2026 · 19:00 · Cowork Ruzafa · Gratis",
    ]
    second = _props(_props(notice[1])["children"][1])["children"][0]  # the title is a link to the event
    assert second.to_plotly_json()["type"] == "A" and _props(second)["href"] == f"https://example.invalid/{T['E'].lower().replace(' ', '-')}"
    # One event reads in the singular.
    notice, label = vet.build_new_notice(EVENTS, NOW - timedelta(minutes=15), NOW)  # only G (detected at NOW)
    assert label == "Ver el nuevo en la tabla" and _flat(notice[0])[-1] == "Nuevos desde tu última visita: 1 evento"


def test_the_notice_is_capped_and_says_how_many_more() -> None:
    dozen = [_event(f"Nuevo {index}", 3, detected=1) for index in range(12)]
    notice, label = vet.build_new_notice(dozen, NOW - timedelta(hours=2), NOW)

    assert label == "Ver los 12 nuevos en la tabla"
    assert [_plain(item) for item in _props(notice[1])["children"]] == [f"Nuevo {index} · mar 01/12/2026" for index in range(8)]
    assert _flat(notice[2]) == ["… y 4 más"]


def test_no_notice_without_a_previous_visit_or_without_something_new() -> None:
    assert vet.build_new_notice(EVENTS, None, NOW) == ("", "")
    assert vet.build_new_notice(EVENTS, NOW, NOW) == ("", "")
    assert vet.build_new_notice([], NOW - timedelta(hours=1), NOW) == ("", "")


# --- the orders --------------------------------------------------------------------------------------


def _ordered(sort_by: str, events: list[dict] | None = None) -> list[str]:
    return _titles(vet.sort_events(events if events is not None else vet.apply_filters(EVENTS, now=NOW, period="all"), sort_by, first_day=TODAY, now=NOW))


def test_the_orders() -> None:
    assert _ordered("start") == _names("BALEJGCFHI")
    assert _ordered("start_desc") == _names("HFCGJELABI")
    assert _ordered("price") == _names("BEGJAFLCHI")  # the free ones first, what states no price last
    assert _ordered("price_desc") == _names("FAJBEGLCHI")
    assert _ordered("newest") == _names("GECFBIAHJL")  # L has no stamp: an older file goes last
    assert _ordered("something else") == _names("BALEJGCFHI")  # an unknown order is the default one


def test_what_began_earlier_comes_after_what_starts_in_the_window() -> None:
    with_ongoing = vet.apply_filters(EVENTS, now=NOW, period="all", include_ongoing=True)

    assert _ordered("start", with_ongoing) == _names("BALEJGCFH" + "MD" + "I")  # the festival closes before the exhibition
    assert _ordered("start_desc", with_ongoing)[:-3] == _names("HFCGJELAB") and _ordered("start_desc", with_ongoing)[-3:] == _names("MDI")
    assert _ordered("newest", with_ongoing)[:3] == _names("GEC")


def test_the_events_of_one_run_keep_the_order_by_date_under_newest() -> None:
    same_run = [_event("Lejos", 5, detected=2), _event("Cerca", 1, detected=2), _event("Medio", 3, detected=2)]

    assert _ordered("newest", same_run) == ["Cerca", "Medio", "Lejos"]


def test_sorting_leaves_the_input_alone() -> None:
    events = [_event("B", 2), _event("A", 1)]

    assert _ordered("start", events) == ["A", "B"] and _titles(events) == ["B", "A"]


# --- the callbacks, as the browser calls them ---------------------------------------------------------

SEARCH_CLEAR, PREV, NEXT, CLEAR, SHOW_ALL = vet.SEARCH_CLEAR_ID, vet.PREV_ID, vet.NEXT_ID, vet.CLEAR_ID, vet.SHOW_ALL_ID
FILTERS = (vet.PERIOD_ID, vet.FROM_ID, vet.TO_ID, vet.CATEGORY_ID, vet.ZONE_ID, vet.FREE_ID, vet.ONLY_NEW_ID, vet.ONGOING_ID, vet.SORT_ID)
PREVIOUS = {"stamp": (NOW - timedelta(hours=3)).isoformat(), "n": 1}  # what valencia_state.js hands over
EXTRAS = [_event(f"Extra {index}", 5) for index in range(30)]


def sid(ident) -> str:
    """A component id as the renderer stringifies it: JSON for a pattern id, the text otherwise."""
    return ident if isinstance(ident, str) else json.dumps(ident, sort_keys=True, separators=(",", ":"))


def entry(ident, prop, value) -> dict:
    return {"id": sid(ident), "property": prop, "value": value}


def find(app, marker) -> dict:
    """The callback whose output spec contains ``marker``, as the app lists it for the renderer."""
    return next(cb for cb in app._callback_list if marker in cb["output"])


def call(app, cb, inputs, changed, states=None) -> dict:
    """POST the callback as the browser would and return the outputs it changed, by component id."""
    if cb["output"].startswith(".."):
        outputs = [dict(zip(("id", "property"), part.rsplit(".", 1), strict=True)) for part in cb["output"][2:-2].split("...")]
    else:
        outputs = dict(zip(("id", "property"), cb["output"].rsplit(".", 1), strict=True))  # one output goes as one dict
    body = {"output": cb["output"], "outputs": outputs, "inputs": inputs, "changedPropIds": list(changed), "state": states if states is not None else [{**spec, "value": None} for spec in cb["state"]]}
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code in (200, 204), response.get_data(as_text=True)[-800:]
    if response.status_code == 204:
        return {}  # every output was prevented: a call that is not a user action
    return response.get_json()["response"]


def _prop(answer: dict, comp_id: str, prop: str):
    """One output of an answer; ``None`` when the callback left it alone (an output it did not change is not in the answer)."""
    value = answer.get(comp_id)
    return value.get(prop) if isinstance(value, dict) else None


def _app() -> dash.Dash:
    """A Dash app with the tab's layout and its callbacks, as app.py wires it."""
    app = dash.Dash("test-valencia-events", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = vet.render_valencia_events_tab()
    vet.register_valencia_events_callbacks(app)
    return app


def _drive(app, *, controls: dict | None = None, per_page: int = 25, clicks: dict | None = None, page: int = 1, visit: dict | None = None, changed: str | None = None) -> dict:
    """Call the controller with the controls as they stand, woken by ``changed`` (an ``id.prop`` key).

    Without ``changed``, the browser reports the first control that differs from the opening state.
    """
    controls = {**vet.DEFAULT_CONTROLS, **(controls or {})}
    clicks = {button: None for button in (SEARCH_CLEAR, PREV, NEXT, CLEAR, SHOW_ALL)} | (clicks or {})
    if changed is None:
        key = next((key for key, value in controls.items() if value != vet.DEFAULT_CONTROLS[key]), vet.PERIOD_ID)
        changed = f"{key}.value"
    inputs = [entry(vet.SEARCH_ID, "value", controls[vet.SEARCH_ID]), entry(SEARCH_CLEAR, "n_clicks", clicks[SEARCH_CLEAR])]
    inputs += [entry(key, "value", controls[key]) for key in FILTERS]
    inputs += [entry(vet.PER_PAGE_ID, "value", per_page)] + [entry(button, "n_clicks", clicks[button]) for button in (PREV, NEXT, CLEAR, SHOW_ALL)]
    states = [entry(vet.PAGE_STORE_ID, "data", page), entry(vet.LAST_VISIT_ID, "data", visit)]
    return call(app, find(app, f"{vet.RESULTS_ID}.children"), inputs, [changed], states)


def _table(answer: dict):
    """What the controller put in the results area: the count and the table, or the message."""
    return _prop(answer, vet.RESULTS_ID, "children")


def _count(answer: dict) -> str:
    """The line over the table: ``7 eventos · 3 gratis``."""
    return "".join(_flat(_table(answer)[0]))


def _pager(answer: dict) -> str:
    """The line between the two buttons of the pager."""
    return _flat(_prop(answer, vet.PAGER_ID, "children"))[1]


@pytest.mark.parametrize(
    ("controls", "expected"),
    [
        ({}, "BALEJGC"),
        ({vet.PERIOD_ID: "today"}, "BAL"),
        ({vet.PERIOD_ID: "weekend"}, "BALEJ"),
        ({vet.PERIOD_ID: "this_month"}, "BALEJG"),
        ({vet.PERIOD_ID: "all"}, "BALEJGCFHI"),
        ({vet.PERIOD_ID: "custom", vet.FROM_ID: "2026-12-01", vet.TO_ID: "2026-12-20"}, "CF"),
        ({vet.CATEGORY_ID: "infantil"}, "BJ"),
        ({vet.ZONE_ID: "Ruzafa"}, "AG"),
        ({vet.FREE_ID: ["free"]}, "BEG"),
        ({vet.ONGOING_ID: ["ongoing"]}, "BALEJGCMD"),
        ({vet.SEARCH_ID: "ninos"}, "J"),
        ({vet.SORT_ID: "start_desc"}, "CGJELAB"),
        ({vet.SORT_ID: "price"}, "BEGJALC"),
        ({vet.SORT_ID: "newest"}, "GECBAJL"),
        ({vet.CATEGORY_ID: "fiestas", vet.FREE_ID: ["free"], vet.ONGOING_ID: ["ongoing"]}, "M"),
    ],
)
def test_the_controller_rebuilds_the_table_for_each_filter(controls: dict, expected: str) -> None:
    answer = _drive(_app(), controls=controls)

    assert _listed(_table(answer)) == _names(expected), (controls, _texts(_table(answer))[:400])


def test_the_counts_follow_the_filters() -> None:
    app = _app()

    assert _count(_drive(app)) == "7 eventos · 3 gratis"
    assert _count(_drive(app, controls={vet.PERIOD_ID: "weekend"})) == "5 eventos · 2 gratis"
    assert _count(_drive(app, controls={vet.CATEGORY_ID: "infantil"})) == "2 eventos · 1 gratis"
    assert _count(_drive(app, controls={vet.SEARCH_ID: "dragón"})) == "1 evento · 0 gratis"
    assert _pager(_drive(app)) == "Mostrando 1–7 de 7 · Página 1 de 1"


def test_a_filter_change_goes_back_to_the_first_page_and_leaves_the_controls_alone() -> None:
    answer = _drive(_app(), controls={vet.PERIOD_ID: "today", vet.CATEGORY_ID: "infantil"}, page=4)

    assert _listed(_table(answer)) == [T["B"]]
    assert answer[vet.PAGE_STORE_ID] == {"data": 1}
    for comp_id in FILTERS:
        assert comp_id not in answer, comp_id  # the browser already holds what the user chose


def test_the_two_dates_show_only_for_a_custom_range() -> None:
    app = _app()

    chosen = _drive(app, controls={vet.PERIOD_ID: "custom", vet.FROM_ID: "2026-12-01", vet.TO_ID: "2026-12-20"})
    assert _prop(chosen, vet.RANGE_ROW_ID, "hidden") is False
    assert _prop(_drive(app, controls={vet.PERIOD_ID: "today"}), vet.RANGE_ROW_ID, "hidden") is True


@pytest.fixture
def paged(monkeypatch: pytest.MonkeyPatch) -> dash.Dash:
    """The tab with 37 events in the next seven days: two pages of 25."""
    monkeypatch.setattr(vet, "load_valencia_events", lambda: [dict(event) for event in EVENTS + EXTRAS])
    return _app()


def _disabled(answer: dict) -> dict[str, bool]:
    return {name: button["disabled"] for name, button in _buttons(_prop(answer, vet.PAGER_ID, "children")).items()}


def test_the_pager_walks_the_pages(paged: dash.Dash) -> None:
    first = _drive(paged)
    assert _listed(_table(first)) == _names("BALEJGC") + [f"Extra {index}" for index in range(18)]
    assert _count(first) == "37 eventos · 3 gratis" and _pager(first) == "Mostrando 1–25 de 37 · Página 1 de 2"
    assert _disabled(first) == {PREV: True, NEXT: False}

    second = _drive(paged, page=1, clicks={NEXT: 1}, changed=f"{NEXT}.n_clicks")
    assert _listed(_table(second)) == [f"Extra {index}" for index in range(18, 30)]
    assert _pager(second) == "Mostrando 26–37 de 37 · Página 2 de 2" and second[vet.PAGE_STORE_ID] == {"data": 2}
    assert _disabled(second) == {PREV: False, NEXT: True}

    back = _drive(paged, page=2, clicks={PREV: 1}, changed=f"{PREV}.n_clicks")
    assert back[vet.PAGE_STORE_ID] == {"data": 1} and _pager(back) == "Mostrando 1–25 de 37 · Página 1 de 2"


def test_the_pager_stays_on_the_last_and_the_first_page(paged: dash.Dash) -> None:
    beyond = _drive(paged, page=2, clicks={NEXT: 1}, changed=f"{NEXT}.n_clicks")
    before = _drive(paged, clicks={PREV: 1}, changed=f"{PREV}.n_clicks")

    assert beyond[vet.PAGE_STORE_ID] == {"data": 2} and _pager(beyond) == "Mostrando 26–37 de 37 · Página 2 de 2"
    assert before[vet.PAGE_STORE_ID] == {"data": 1} and _pager(before) == "Mostrando 1–25 de 37 · Página 1 de 2"


def test_the_page_size_and_an_unknown_one(paged: dash.Dash) -> None:
    assert _pager(_drive(paged, per_page=50)) == "Mostrando 1–37 de 37 · Página 1 de 1"
    assert len(_rows(_table(_drive(paged, per_page=50)))) == 37
    assert _pager(_drive(paged, per_page="de ninguna manera")) == "Mostrando 1–25 de 37 · Página 1 de 2"


def test_limpiar_filtros_sets_every_control_back(paged: dash.Dash) -> None:
    answer = _drive(
        paged,
        controls={vet.SEARCH_ID: "zzz", vet.PERIOD_ID: "custom", vet.FROM_ID: "2026-12-10", vet.TO_ID: "2026-12-20", vet.CATEGORY_ID: "cine", vet.ZONE_ID: "Ruzafa", vet.FREE_ID: ["free"], vet.ONLY_NEW_ID: ["new"], vet.ONGOING_ID: ["ongoing"], vet.SORT_ID: "price_desc"},
        page=3,
        clicks={CLEAR: 1},
        changed=f"{CLEAR}.n_clicks",
    )

    assert _listed(_table(answer)) == _names("BALEJGC") + [f"Extra {index}" for index in range(18)]
    assert answer[vet.SEARCH_ID] == {"value": ""}
    assert {key: _prop(answer, key, "value") for key in FILTERS} == {key: vet.DEFAULT_CONTROLS[key] for key in FILTERS}
    assert vet.FROM_ID in answer and vet.TO_ID in answer
    assert answer[vet.PAGE_STORE_ID] == {"data": 1}
    assert _prop(answer, vet.RANGE_ROW_ID, "hidden") is True


def test_the_x_of_the_search_box_empties_it() -> None:
    answer = _drive(_app(), controls={vet.SEARCH_ID: "zzz"}, clicks={SEARCH_CLEAR: 1}, changed=f"{SEARCH_CLEAR}.n_clicks")

    assert answer[vet.SEARCH_ID] == {"value": ""}
    assert _listed(_table(answer)) == _names("BALEJGC")
    assert vet.SORT_ID not in answer  # the other controls stay as they are


def test_the_button_of_the_notice_lists_the_new_ones_in_the_table() -> None:
    answer = _drive(_app(), visit=PREVIOUS, clicks={SHOW_ALL: 1}, changed=f"{SHOW_ALL}.n_clicks")

    assert _listed(_table(answer)) == _names("GEC")  # every date, the latest detection first
    assert _count(answer) == "3 eventos · 2 gratis"
    assert {key: _prop(answer, key, "value") for key in FILTERS} == {key: vet.NEW_VIEW_CONTROLS[key] for key in FILTERS}
    assert answer[vet.SEARCH_ID] == {"value": ""} and answer[vet.PAGE_STORE_ID] == {"data": 1}


def test_only_the_new_ones_needs_a_previous_visit() -> None:
    app = _app()

    first = _drive(app, controls={vet.ONLY_NEW_ID: ["new"]})
    assert "Todavía no hay una visita anterior" in _texts(_table(first)) and _pager(first) == "0 eventos"
    with_visit = _drive(app, controls={vet.ONLY_NEW_ID: ["new"]}, visit=PREVIOUS)
    assert _listed(_table(with_visit)) == _names("EGC")  # within the next seven days, by date
    assert _count(with_visit) == "3 eventos · 2 gratis"


def test_nothing_matching_explains_how_to_widen() -> None:
    answer = _drive(_app(), controls={vet.SEARCH_ID: "zzz"})

    texts = _texts(_table(answer))
    assert "Ningún evento con estos filtros" in texts and "Limpiar filtros" in texts
    assert _pager(answer) == "0 eventos"
    assert all(_disabled(answer).values())


def test_buttons_just_inserted_change_nothing() -> None:
    app = _app()
    cb = find(app, f"{vet.RESULTS_ID}.children")
    controls = {**vet.DEFAULT_CONTROLS, vet.FREE_ID: ["free"]}
    inputs = [entry(vet.SEARCH_ID, "value", ""), entry(SEARCH_CLEAR, "n_clicks", None)]
    inputs += [entry(key, "value", controls[key]) for key in FILTERS] + [entry(vet.PER_PAGE_ID, "value", 25)]
    inputs += [entry(button, "n_clicks", None) for button in (PREV, NEXT, CLEAR, SHOW_ALL)]
    states = [entry(vet.PAGE_STORE_ID, "data", 1), entry(vet.LAST_VISIT_ID, "data", None)]
    buttons = [SEARCH_CLEAR, PREV, NEXT, CLEAR, SHOW_ALL]

    # The renderer lists every inserted button in changedPropIds, each with n_clicks=None; any of them can come first.
    for first in buttons:
        others = [f"{button}.n_clicks" for button in buttons if button != first]
        assert call(app, cb, inputs, [f"{first}.n_clicks", *others], states) == {}, first


def test_a_failure_is_shown_in_the_tab_and_leaves_the_controls_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    def _broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(vet, "_view", _broken)
    answer = _drive(_app(), controls={vet.PERIOD_ID: "today"})

    assert "No se pudo actualizar la lista de eventos" in _texts(_table(answer)) and "boom" in _texts(_table(answer))
    assert list(answer) == [vet.RESULTS_ID]


def _notice(app: dash.Dash, data) -> dict:
    return call(app, find(app, f"{vet.NOTICE_ID}.children"), [entry(vet.LAST_VISIT_ID, "data", data)], [f"{vet.LAST_VISIT_ID}.data"])


def test_the_notice_answers_what_the_browser_hands_over() -> None:
    answer = _notice(_app(), PREVIOUS)
    notice = _prop(answer, vet.NOTICE_ID, "children")

    assert _flat(notice[0]) == ["🆕 ", "Nuevos desde tu última visita: 3 eventos"]
    assert ["".join(_flat(item)) for item in notice[1]["props"]["children"]] == [
        "Feria Horeq · mar 01/12/2026 – 02/12/2026 · Feria Valencia",
        "Visita al Mercado Central · dom 29/11/2026 · 10:00 · Mercado Central · Gratis",
        "Meetup de Python · lun 30/11/2026 · 19:00 · Cowork Ruzafa · Gratis",
    ]
    assert answer[vet.NEW_BOX_ID] == {"hidden": False}
    assert answer[vet.SHOW_ALL_ID] == {"children": "Ver los 3 nuevos en la tabla"}
    # The stamp on its own, as an older version of the script sent it.
    assert _notice(_app(), PREVIOUS["stamp"])[vet.NEW_BOX_ID] == {"hidden": False}


def test_the_notice_hides_itself_when_there_is_nothing_new() -> None:
    app = _app()

    # A first visit, a stamp that cannot be read, and what "Marcar como vistos" sends: now.
    for data in (None, {"stamp": None, "n": 1}, "basura", {"stamp": NOW.isoformat(), "n": 2}):
        assert _notice(app, data) == {vet.NOTICE_ID: {"children": ""}, vet.NEW_BOX_ID: {"hidden": True}}, data


# --- what the browser would refuse --------------------------------------------------------------------


def _callback_ids(cb: dict) -> set[str]:
    outputs = cb["output"][2:-2].split("...") if cb["output"].startswith("..") else [cb["output"]]
    return {spec["id"] for spec in [*cb["inputs"], *cb["state"]]} | {part.rsplit(".", 1)[0] for part in outputs}


def _served_ids(app: dash.Dash) -> list[str]:
    """Every component id of the layout as Dash serves it to the renderer."""
    ids: list[str] = []

    def _collect(node) -> None:
        if isinstance(node, dict):
            props = node.get("props")
            if isinstance(props, dict) and isinstance(props.get("id"), str):
                ids.append(props["id"])
            for value in node.values():
                _collect(value)
        elif isinstance(node, list):
            for item in node:
                _collect(item)

    response = app.server.test_client().get("/_dash-layout")
    assert response.status_code == 200, response.get_data(as_text=True)[-400:]
    _collect(response.get_json())
    return ids


def test_every_id_the_callbacks_touch_is_in_the_layout_dash_serves() -> None:
    """The renderer skips a callback while one of its Inputs or Outputs is missing from the page, and nothing says so."""
    served = _served_ids(_app())

    assert len(served) == len(set(served))
    for cb in _app()._callback_list:
        assert _callback_ids(cb) <= set(served), _callback_ids(cb) - set(served)


def test_one_callback_per_output_and_none_at_loading() -> None:
    app = _app()
    outputs = [output for cb in app._callback_list for output in (cb["output"][2:-2].split("...") if cb["output"].startswith("..") else [cb["output"]])]

    assert len(app._callback_list) == 2
    assert len(outputs) == len(set(outputs)) == 17
    assert all(cb["prevent_initial_call"] for cb in app._callback_list)


def test_the_script_and_the_tab_share_the_same_names() -> None:
    script = JS_PATH.read_text(encoding="utf-8")

    for name in (vet.NEW_BOX_ID, vet.LAST_VISIT_ID, vet.MARK_SEEN_ID):
        assert f'"{name}"' in script, name
    assert '"wt_valencia_last_visit"' in script  # where the browser keeps the previous visit
    assert "data-valencia-detected" in script  # the attribute the rows carry
    assert "set_props" in script and "stamp" in script  # how the stamp reaches the server
    assert "NUEVO" in script
    # The tab reads what the script writes.
    assert vet._visit_stamp({"stamp": (NOW - timedelta(hours=2)).isoformat(), "n": 3}) == NOW - timedelta(hours=2)
    assert vet._visit_stamp((NOW - timedelta(hours=2)).isoformat()) == NOW - timedelta(hours=2)
    assert vet._visit_stamp("2026-11-28T06:00:00") == NOW - timedelta(hours=3)  # without a zone: Valencia time
    for data in (None, "", "basura", {"stamp": "basura", "n": 1}, {"n": 1}, []):
        assert vet._visit_stamp(data) is None, data
