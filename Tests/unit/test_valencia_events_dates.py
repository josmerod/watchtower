"""Unit tests for the dates of the Valencia Events tab (T-178).

The three sources print dates their own way — visitvalencia Spanish calendar
text, Meetup a UTC timestamp, Eventbrite a bare ISO date — and the tab used
to show each of them raw. These tests pin the one readable local date every
source gets, and the list in start order.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from dash.development.base_component import Component

from src.web.dashboard.components import valencia_events_new_tab as vet

MEETUP = {"title": "Friday Language Exchange", "source": "meetup.com", "date_text": "2026-11-27T19:30:00.000Z", "start_date": "2026-11-27", "end_date": ""}
VISITVALENCIA = {"title": "MotoGP", "source": "visitvalencia.com", "date_text": "27/11/2026 - 29/11/2026", "start_date": "2026-11-27", "end_date": "2026-11-29"}
EVENTBRITE = {"title": "SG[Spain] 2026", "source": "eventbrite.com", "date_text": "2026-11-27", "start_date": "2026-11-27", "end_date": "2026-11-28"}
UNDATED = {"title": "Sin fecha", "source": "visitvalencia.com", "date_text": "Próximamente", "start_date": "", "end_date": ""}
# The morning before the three dated events, in Valencia: they are all still to come.
NOW = datetime(2026, 11, 26, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))


def test_meetup_times_show_in_valencia_time():
    """Meetup timestamps are UTC: the tab shows the local hour, on the local day."""
    assert vet._format_event_date(MEETUP) == "vie 27/11/2026 · 20:30"  # November: UTC+1
    assert vet._format_event_date({"date_text": "2026-08-28T18:30:00.000Z", "start_date": "2026-08-28"}) == "vie 28/08/2026 · 20:30"  # August: UTC+2
    # An evening in UTC that is already the next day in Spain
    assert vet._format_event_date({"date_text": "2026-11-27T23:30:00.000Z", "start_date": "2026-11-27"}) == "sáb 28/11/2026 · 00:30"
    # The offset wins over a zone name in brackets
    assert vet._format_event_date({"date_text": "2026-11-27T20:30:00+01:00[Europe/Madrid]"}) == "vie 27/11/2026 · 20:30"


def test_calendar_dates_show_without_a_time():
    """visitvalencia and Eventbrite give calendar dates: day, plus the end when it differs."""
    assert vet._format_event_date(VISITVALENCIA) == "vie 27/11/2026 – 29/11/2026"
    assert vet._format_event_date(EVENTBRITE) == "vie 27/11/2026 – 28/11/2026"
    # A one-day event that the source prints as a range
    assert vet._format_event_date({"date_text": "28/11/2026 - 28/11/2026", "start_date": "2026-11-28", "end_date": ""}) == "sáb 28/11/2026"
    # A single day with an end equal to the start
    assert vet._format_event_date({"date_text": "2026-12-02", "start_date": "2026-12-02", "end_date": "2026-12-02"}) == "mié 02/12/2026"
    # A timed start that also runs on later days
    assert vet._format_event_date(MEETUP | {"end_date": "2026-11-29"}) == "vie 27/11/2026 · 20:30 – 29/11/2026"


def test_a_timestamp_without_a_zone_is_local_time():
    assert vet._format_event_date({"date_text": "2026-11-27T23:30:00", "start_date": "2026-11-27"}) == "vie 27/11/2026 · 23:30"
    # The ISO datetime can also arrive in start_date, as older files had it
    assert vet._format_event_date({"start_date": "2026-12-01T18:30:00"}) == "mar 01/12/2026 · 18:30"


def test_undated_events_keep_their_text():
    assert vet._format_event_date(UNDATED) == "Próximamente"
    assert vet._format_event_date({"date_text": "Del 17/08/2026 al 30/08/2026"}) == "17/08/2026 – 30/08/2026"
    assert vet._format_event_date({"start_date": "TBC"}) == "N/A"
    assert vet._format_event_date({}) == "N/A"


def test_events_sort_by_start_and_the_undated_go_last():
    after_midnight_utc = MEETUP | {"title": "Late party", "date_text": "2026-11-27T23:30:00.000Z"}
    events = [UNDATED, after_midnight_utc, {"title": "Sin fecha tampoco"}, EVENTBRITE, MEETUP, VISITVALENCIA]

    ordered = vet.sort_events_by_start(events)

    # Same day: all-day events first, in the order they came, then by hour
    assert [event["title"] for event in ordered] == ["SG[Spain] 2026", "MotoGP", "Friday Language Exchange", "Late party", "Sin fecha", "Sin fecha tampoco"]
    assert [event["title"] for event in events][:2] == ["Sin fecha", "Late party"], "the list of the repository is not reordered in place"


def _date_cells(component: Any) -> list[str]:
    """Collect the text of every "Cuándo" cell of the layout, in document order."""
    out: list[str] = []
    if component is None or isinstance(component, (str, int, float, bool)) or not isinstance(component, Component):
        return out
    data = component.to_plotly_json()
    props = data.get("props", data)  # Dash 4 nests props; older Dash is flat
    if type(component).__name__ == "Span" and props.get("className") == "text-nowrap" and isinstance(props.get("children"), str):
        out.append(props["children"])
    for value in props.values():
        for item in value if isinstance(value, list) else [value]:
            out.extend(_date_cells(item))
    return out


def test_the_tab_shows_sorted_readable_dates(monkeypatch):
    """The table of the layout carries the local dates, and the list goes by start."""
    monkeypatch.setattr(vet, "load_valencia_events", lambda: [UNDATED, MEETUP, VISITVALENCIA, EVENTBRITE])
    monkeypatch.setattr(vet, "load_sources_status", lambda: {})
    monkeypatch.setattr(vet, "_now", lambda: NOW)
    layout = vet.render_valencia_events_tab()

    # Same day: all-day events first, in the order they came, then by hour
    assert _date_cells(layout)[:3] == ["vie 27/11/2026 – 29/11/2026", "vie 27/11/2026 – 28/11/2026", "vie 27/11/2026 · 20:30"]
    assert "2026-11-27T19:30:00.000Z" not in str(layout)
    # Without a date an event fits no window: it stays out of the default view, and keeps its text
    assert "Próximamente" not in str(layout)
    assert vet._when_text(UNDATED) == "Próximamente"
    # An older file is shown with the rule the table always applied
    assert vet._when_text(MEETUP) == vet._format_event_date(MEETUP) == "vie 27/11/2026 · 20:30"
