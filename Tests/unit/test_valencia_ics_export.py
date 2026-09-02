"""Unit tests for the Valencia Events clientside .ics export (T-068).

Covers the Python half: upcoming-from-today filtering, the compact JSON
payload consumed by assets/js/valencia_ics.js, and the rendered layout
(button with count, hidden data-events Div, hidden when nothing to export).
The JS VCALENDAR builder itself is browser-only; the payload tests assert
everything it needs (well-formed JSON with the expected fields).
"""

import json
from datetime import datetime, timedelta
from typing import Any

from dash.development.base_component import Component

from src.web.dashboard.components import valencia_events_new_tab as vet

NOW = datetime.now().replace(microsecond=0)


def _event(title: str, start_date: str, **extra: Any) -> dict[str, Any]:
    return {"title": title, "start_date": start_date, "end_date": "", "url": f"https://example.com/{title[:8]}", "category": "General", "source": "test", **extra}


def _find_by_id(component: Any, comp_id: str) -> list[Component]:
    """Recursively collect components whose id matches (Dash trees only)."""
    if component is None or isinstance(component, (str, int, float, bool)):
        return []
    if not isinstance(component, Component):
        return []
    data = component.to_plotly_json()
    props = data.get("props", data)  # Dash 4 nests props; older Dash is flat
    found = [component] if props.get("id") == comp_id else []
    for value in props.values():
        items = value if isinstance(value, list) else [value]
        for item in items:
            found.extend(_find_by_id(item, comp_id))
    return found


FIXTURE_EVENTS = [
    _event("Past Event", (NOW - timedelta(days=27)).strftime("%Y-%m-%d")),
    _event("Today Event", NOW.strftime("%Y-%m-%d")),
    _event("Future ISO Event", (NOW + timedelta(days=18)).strftime("%Y-%m-%dT19:30:00"), end_date=(NOW + timedelta(days=18)).strftime("%Y-%m-%dT21:00:00")),
    _event("Future Spanish Date", (NOW + timedelta(days=33)).strftime("%d/%m/%Y")),
    _event("No Date Event", "TBC"),
    _event("Empty Date Event", ""),
]


def test_exportable_upcoming_filters_from_today():
    """Only events with a parseable start date >= today are exportable."""
    exportable = vet._exportable_upcoming_events(FIXTURE_EVENTS, NOW)
    titles = [e["title"] for e in exportable]
    assert titles == ["Today Event", "Future ISO Event", "Future Spanish Date"]


def test_exportable_upcoming_no_upper_cutoff():
    """Far-future events are kept (no 30-day window for the export)."""
    events = [_event("Far Future", "2027-03-01"), _event("Past", "2026-01-01")]
    exportable = vet._exportable_upcoming_events(events, NOW)
    assert [e["title"] for e in exportable] == ["Far Future"]


def test_exportable_upcoming_includes_today_midnight():
    """An event earlier today still counts (cutoff is the day, not the hour)."""
    exportable = vet._exportable_upcoming_events([_event("Tonight", NOW.strftime("%Y-%m-%d"))], NOW)
    assert len(exportable) == 1


def test_build_ics_payload_fields():
    """Payload keeps exactly the fields the JS builder needs."""
    events = [
        _event("Meetup; tech, valencia", "2026-09-01", end_date="2026-09-02", location="Las Naves"),
        _event("Venue in metadata", "2026-09-03", metadata={"venue": "La Nau"}),
        _event("No location", "2026-09-04"),
        {"start_date": "2026-09-05"},  # missing title/url → safe defaults
    ]
    payload = vet._build_ics_payload(events)

    assert payload[0] == {"title": "Meetup; tech, valencia", "start_date": "2026-09-01", "end_date": "2026-09-02", "url": events[0]["url"], "location": "Las Naves"}
    assert payload[1]["location"] == "La Nau"
    assert "location" not in payload[2]
    assert payload[3]["title"] == "Untitled" and payload[3]["url"] == ""


def test_build_ics_payload_prefers_extracted_venue():
    """The extracted venue name (T-080) wins over address-style locations."""
    events = [
        _event("Named venue event", "2026-09-10", venue="Teatro El Musical", location="1 Calle Example", metadata={"location": "1 Carrer de la Vall d'Aiora, València"}),
        _event("Only address", "2026-09-11", metadata={"location": "10 Carrer de Rugat, València"}),
    ]
    payload = vet._build_ics_payload(events)
    assert payload[0]["location"] == "Teatro El Musical"
    assert payload[1]["location"] == "10 Carrer de Rugat, València"  # venue absent → address fallback


VENUE_PRICE_EVENTS = [
    _event("Free Meetup", (NOW + timedelta(days=3)).strftime("%Y-%m-%d"), venue="Book Lovers Valencia", price_info="Gratis", is_free=True),
    _event("Paid Concert", (NOW + timedelta(days=5)).strftime("%Y-%m-%d"), venue="Teatro El Musical", price_info="12,50 €", is_free=False),
    _event("Undisclosed Price", (NOW + timedelta(days=7)).strftime("%Y-%m-%d"), venue="Café de las Horas"),
    _event("No Venue Event", (NOW + timedelta(days=9)).strftime("%Y-%m-%d")),
]


def _collect_components(component: Any) -> list[tuple[str, dict[str, Any]]]:
    """Recursively collect (type name, props) of every Dash component in a tree."""
    out: list[tuple[str, dict[str, Any]]] = []
    if component is None or isinstance(component, (str, int, float, bool)) or not isinstance(component, Component):
        return out
    data = component.to_plotly_json()
    props = data.get("props", data)  # Dash 4 nests props; older Dash is flat
    out.append((type(component).__name__, props))
    for value in props.values():
        for item in value if isinstance(value, list) else [value]:
            out.extend(_collect_components(item))
    return out


def test_events_table_renders_venue_and_price_cells():
    """Venue column plus honest price cells: green Gratis badge / muted price / dash."""
    table = vet.create_events_table(VENUE_PRICE_EVENTS)
    rendered = str(table)

    assert "Venue" in rendered and "Price" in rendered  # new table headers
    assert "Book Lovers Valencia" in rendered
    assert "Teatro El Musical" in rendered
    assert "12,50 €" in rendered
    assert rendered.count("Gratis") == 1  # badge only — not duplicated as plain text

    badges = [props for name, props in _collect_components(table) if name == "Badge"]
    gratis = [b for b in badges if b.get("children") == "Gratis"]
    assert len(gratis) == 1
    assert gratis[0].get("color") == "success"  # the Gratis badge is green

    spans = [props for name, props in _collect_components(table) if name == "Span"]
    paid = [s for s in spans if s.get("children") == "12,50 €"]
    assert len(paid) == 1 and "text-muted" in str(paid[0].get("className"))
    # Honest dashes: undisclosed price (2 events) + missing venue (1 event)
    assert len([s for s in spans if s.get("children") == "—"]) == 3


def test_render_tab_shows_venue_and_price(monkeypatch):
    """The full tab layout carries venue names and prices into both tables."""
    rendered = str(_render_with(monkeypatch, VENUE_PRICE_EVENTS))

    assert "Book Lovers Valencia" in rendered
    assert "12,50 €" in rendered
    assert "Free Events" in rendered


def test_render_stats_count_real_free_events(monkeypatch):
    """The free-events stat counts real is_free values, stays N/D without data."""
    rendered = str(_render_with(monkeypatch, VENUE_PRICE_EVENTS))
    assert "Free Events" in rendered  # 1 of 4 events is really free

    # No is_free anywhere (older data / sources without offers) → honest N/D
    no_price = str(_render_with(monkeypatch, FIXTURE_EVENTS))
    assert "N/D" in no_price


def _render_with(monkeypatch, events):
    monkeypatch.setattr(vet, "load_valencia_events", lambda: events)
    return vet.render_valencia_events_tab()


def test_render_contains_button_and_payload(monkeypatch):
    """Button shows the upcoming count and the hidden Div carries valid JSON."""
    layout = _render_with(monkeypatch, FIXTURE_EVENTS)
    rendered = str(layout)

    assert "valencia-ics-export-btn" in rendered
    assert "⬇ .ics (3)" in rendered  # today + 2 future, past/unparsable excluded

    holders = _find_by_id(layout, "valencia-ics-events")
    assert len(holders) == 1
    payload = json.loads(holders[0].to_plotly_json()["props"]["data-events"])
    assert [item["title"] for item in payload] == ["Today Event", "Future ISO Event", "Future Spanish Date"]
    for item in payload:
        assert set(item) <= {"title", "start_date", "end_date", "url", "location"}
        assert item["title"] and item["start_date"]
        assert item["url"].startswith("https://")


def test_render_hides_button_without_upcoming(monkeypatch):
    """No upcoming events → no button; payload Div still present with []."""
    past_only = [_event("Long Gone", "2026-01-01"), _event("Undated", "soon")]
    layout = _render_with(monkeypatch, past_only)
    rendered = str(layout)

    assert "valencia-ics-export-btn" not in rendered
    holders = _find_by_id(layout, "valencia-ics-events")
    assert len(holders) == 1
    assert json.loads(holders[0].to_plotly_json()["props"]["data-events"]) == []


def test_render_empty_data_has_no_export(monkeypatch):
    """The no-data alert state must not render the export machinery."""
    layout = _render_with(monkeypatch, [])
    rendered = str(layout)

    assert "valencia-ics-export-btn" not in rendered
    assert _find_by_id(layout, "valencia-ics-events") == []


def test_existing_ids_stay_stable(monkeypatch):
    """Tab element ids that other tests/components rely on are untouched."""
    layout = _render_with(monkeypatch, FIXTURE_EVENTS)
    for comp_id in ("valencia-events-subtabs", "all-table-container", "upcoming-table-container"):
        assert _find_by_id(layout, comp_id), f"missing stable id '{comp_id}'"
