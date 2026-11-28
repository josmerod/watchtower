"""The Cine tab: layout, day bar, filters and empty states (T-151).

The repositories are swapped for ones over tmp_path, so nothing under ``data/`` is read. The callback is
called the way the browser calls it: POST /_dash-update-component on a Dash app through Flask's test client.
"""

import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import dash
import dash_bootstrap_components as dbc
import pytest
from dash import dcc, html

from src.web.dashboard.components import cinema_tab

TODAY = date(2026, 11, 28)  # a Saturday
TODAY_ISO = TODAY.isoformat()
YESTERDAY, TOMORROW = "2026-11-27", "2026-11-29"
CITIES = {"Cine Tívoli": "Burjassot", "Cines Babel": "València", "Filmoteca València": "València", "Kinépolis Valencia": "Paterna"}
SESSIONS_FILE = Path("cinema") / "cinema_sessions_latest.json"
STATUS_FILE = Path("cinema") / "cinema_sources_latest.json"


def record(title: str, cinema: str, day: str, time: str, **extra: Any) -> dict[str, Any]:
    """One session as the ETL stores it."""
    return {"title": title, "cinema": cinema, "city": CITIES[cinema], "date": day, "time": time, "source": "test", "version": "", "format": "", "price": None, "original_title": "", "ticket_url": f"https://tickets.test/{cinema}/{day}/{time}", "film_url": "", **extra}


SESSIONS = [
    record("EL GATO CON SOMBRERO", "Cine Tívoli", TODAY_ISO, "17:00", room="1"),
    record("ARRIBA TUTTO", "Cine Tívoli", TODAY_ISO, "19:30"),
    record("Oro sin ley", "Cines Babel", TODAY_ISO, "16:00", version="VOSE", director="Padraic McKinley", duration_min=115, language="Inglés · subt. Castellano"),
    record("El director", "Cines Babel", TODAY_ISO, "12:00", duration_min=115),
    record("Dune: Parte Tres", "Kinépolis Valencia", TODAY_ISO, "19:20", version="VOSE", room="Sala 5", year=2026, duration_min=152, director="Denis Villeneuve", film_url="https://films.test/dune"),
    record("Dune: Parte Tres", "Kinépolis Valencia", TODAY_ISO, "15:00", format="IMAX", room="Sala 10", year=2026, duration_min=152, director="Denis Villeneuve", film_url="https://films.test/dune"),
    record("Dune: Parte Tres", "Kinépolis Valencia", TOMORROW, "19:20", version="VOSE"),
    record("Oro sin ley", "Cines Babel", TOMORROW, "16:00", version="VOSE"),
    record("GREMLINS", "Filmoteca València", "2026-12-22", "18:00", version="DOB", director="Joe Dante", ticket_url=""),
    record("Lo de ayer", "Cines Babel", YESTERDAY, "16:00"),  # the last run still lists yesterday
]
STATUS = {"generated_at": "2026-11-28T06:12:00+00:00", "reference_day": TODAY_ISO, "sessions": len(SESSIONS), "listings": [{"source": "exhicine", "host": "exhicine.es", "cinema": "Cine Tívoli", "city": "Burjassot", "url": "https://exhicine.es/cine/cine-tivoli/", "sessions": 2, "error": ""}]}
NO_MATCH = "No hay sesiones que coincidan con este día y estos filtros."


# --- reading a layout ---


def walk(component: Any):
    """Every component of a layout, depth first, the parent before its children."""
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            if child is not None:
                yield from walk(child)
    elif children is not None and not isinstance(children, str):
        yield from walk(children)


def by_id(layout: Any, ident: str) -> Any:
    """The component with ``ident`` as its id."""
    return next(component for component in walk(layout) if getattr(component, "id", None) == ident)


def texts_of(component: Any) -> list[str]:
    """Every piece of text a layout prints, in the order the page shows it."""
    if isinstance(component, str):
        return [component]
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        return [piece for child in children if child is not None for piece in texts_of(child)]
    return texts_of(children) if children is not None else []


def _oneline(pieces: list[str]) -> str:
    """Pieces of text on one line, spaced as the page shows them (a comma hugs the word before it)."""
    printed = re.sub(r"\s+([,.;:?!])", r"\1", " ".join(pieces))
    return re.sub(r"(?<=\S) {2,}(?=\S)", " ", printed)


def texts(component: Any) -> str:
    """The text of a layout on one line."""
    return _oneline(texts_of(component))


def response_texts(payload: Any) -> list[str]:
    """``texts_of`` for a list as the renderer receives it: plain dicts with a ``props`` key."""
    if isinstance(payload, list):
        return [piece for item in payload for piece in response_texts(item)]
    if isinstance(payload, dict):
        return response_texts(payload.get("props", {}).get("children"))
    return [payload] if isinstance(payload, str) else []


def cards_of(layout: Any) -> list[dbc.Card]:
    """The film cards inside a layout or a drawn list, in order."""
    return [component for component in walk(layout) if isinstance(component, dbc.Card)]


def title_of(card: dbc.Card) -> str:
    """The first text of a card: its title, linked or not."""
    return texts_of(card)[0]


def title_link_of(card: dbc.Card) -> str | None:
    """Where the title of a card links; None when it is plain text."""
    link = next((component for component in walk(card) if isinstance(component, html.A)), None)
    return link.href if link is not None else None


def cinemas_of(card: dbc.Card) -> list[str]:
    """The cinemas a card lists, in order."""
    return [component.children for component in walk(card) if isinstance(component, html.Span) and "fw-semibold" in (component.className or "")]


def chips_of(card: dbc.Card) -> list[dbc.Button]:
    """The session chips of a card, in order."""
    return [component for component in walk(card) if isinstance(component, dbc.Button)]


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _point_at(monkeypatch, root: Path) -> None:
    """The tab's repositories over ``root``, and today fixed."""
    monkeypatch.setattr(cinema_tab, "sessions_repo", cinema_tab.CinemaSessionsRepository(root / SESSIONS_FILE))
    monkeypatch.setattr(cinema_tab, "status_repo", cinema_tab.CinemaStatusRepository(root / STATUS_FILE))
    monkeypatch.setattr(cinema_tab, "cinema_today", lambda: TODAY)


@pytest.fixture()
def data_dir(tmp_path, monkeypatch) -> Path:
    """A root holding the sample sessions and the status of a run, where the ETL leaves them."""
    _write(tmp_path / SESSIONS_FILE, SESSIONS)
    _write(tmp_path / STATUS_FILE, STATUS)
    _point_at(monkeypatch, tmp_path)
    return tmp_path


@pytest.fixture()
def bare_dir(tmp_path, monkeypatch) -> Path:
    """A root where the ETL has not written anything yet."""
    _point_at(monkeypatch, tmp_path)
    return tmp_path


def _app() -> dash.Dash:
    """A Dash app holding the tab's layout and its callback."""
    app = dash.Dash("test-cinema-tab", external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = cinema_tab.render_cinema_tab()
    cinema_tab.register_cinema_callbacks(app)
    return app


def call(app: dash.Dash, day: str = TODAY_ISO, cinema: str = "all", version: str = "all", changed: str = "cinema-day.active_tab") -> str:
    """Change the day or a filter the way the browser does; the text of the list that comes back."""
    callback = next(cb for cb in app._callback_list if cb["output"] == "cinema-results.children")
    inputs = [{"id": "cinema-day", "property": "active_tab", "value": day}, {"id": "cinema-cinema-filter", "property": "value", "value": cinema}, {"id": "cinema-version-filter", "property": "value", "value": version}]
    body = {"output": callback["output"], "outputs": {"id": "cinema-results", "property": "children"}, "inputs": inputs, "changedPropIds": [changed], "state": []}
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code == 200, response.get_data(as_text=True)[-800:]
    redrawn = response.get_json()["response"]["cinema-results"]["children"]  # Dash groups the outputs by component
    return _oneline(response_texts(redrawn))


# --- the layout, as drawn when the tab is opened ---


class TestLayout:
    def test_today_comes_first_on_the_day_bar_with_the_filters_above_the_list(self, data_dir):
        layout = cinema_tab.render_cinema_tab()

        assert isinstance(layout, dbc.Container) and layout.fluid
        assert "🎬 Cine" in texts(layout)
        bar = by_id(layout, "cinema-day")
        assert isinstance(bar, dbc.Tabs) and bar.active_tab == TODAY_ISO
        assert [tab.tab_id for tab in bar.children] == [TODAY_ISO, TOMORROW, "2026-12-22"]
        assert [tab.label for tab in bar.children] == ["Hoy · sáb 28 nov", "Mañana · dom 29 nov", "mar 22 dic"]

        cinema_filter = by_id(layout, "cinema-cinema-filter")
        assert isinstance(cinema_filter, dcc.Dropdown)
        assert cinema_filter.options == [{"label": "Todos los cines", "value": "all"}, {"label": "Cine Tívoli · Burjassot", "value": "Cine Tívoli"}, {"label": "Cines Babel · València", "value": "Cines Babel"}, {"label": "Kinépolis Valencia · Paterna", "value": "Kinépolis Valencia"}, {"label": "Filmoteca València · València", "value": "Filmoteca València"}]
        assert cinema_filter.value == "all" and cinema_filter.clearable is False  # the value shown is one of the options
        version_filter = by_id(layout, "cinema-version-filter")
        assert version_filter.options == [{"label": "Todas las versiones", "value": "all"}, {"label": "VOSE · 4", "value": "VOSE"}, {"label": "DOB · 1", "value": "DOB"}]
        assert version_filter.value == "all" and version_filter.clearable is False

        shown = texts(by_id(layout, "cinema-results"))
        assert "Hoy, sábado 28 de noviembre · 5 películas · 6 sesiones · 3 cines" in shown
        assert "Lo de ayer" not in shown and "GREMLINS" not in shown

    def test_films_go_by_their_earliest_start_time_and_each_lists_its_sessions(self, data_dir):
        results = by_id(cinema_tab.render_cinema_tab(), "cinema-results")
        cards = cards_of(results)

        assert [title_of(card) for card in cards] == ["El director", "Dune: Parte Tres", "Oro sin ley", "EL GATO CON SOMBRERO", "ARRIBA TUTTO"]
        dune = cards[1]
        assert title_link_of(dune) == "https://films.test/dune"
        assert "2026 · 152 min · Denis Villeneuve" in texts(dune)
        assert cinemas_of(dune) == ["Kinépolis Valencia"]
        assert [(chip.children, chip.href, chip.disabled) for chip in chips_of(dune)] == [("15:00 · IMAX", "https://tickets.test/Kinépolis Valencia/2026-11-28/15:00", False), ("19:20 · VOSE", "https://tickets.test/Kinépolis Valencia/2026-11-28/19:20", False)]
        assert all(getattr(chip, "target", None) == "_blank" and getattr(chip, "rel", None) == "noopener noreferrer" for chip in chips_of(dune)), "the ticket page opens in a new tab: the list stays where it is"
        assert title_link_of(cards[0]) is None and texts(cards[0]) == "El director 115 min Cines Babel 12:00"

        # a session without a ticket page is still listed, as a chip that goes nowhere
        view = cinema_tab.results_view(SESSIONS, "2026-12-22", TODAY)
        (chip,) = chips_of(cards_of(view)[0])
        assert (chip.children, chip.href, chip.disabled, getattr(chip, "target", None)) == ("18:00 · DOB", None, True, None)
        assert "martes 22 de diciembre · 1 película · 1 sesión · 1 cine" in texts(view)

    def test_a_film_lists_one_line_per_cinema_its_name_in_front_of_its_times(self, data_dir):
        """Not a Bootstrap row: the legacy sheets give every .row a 24 px bottom margin, and a film on in nine cinemas took a screen and a half."""
        sessions = [record("Dune: Parte Tres", "Kinépolis Valencia", TODAY_ISO, "19:20", version="VOSE"), record("Dune: Parte Tres", "Cines Babel", TODAY_ISO, "16:00"), record("Dune: Parte Tres", "Cines Babel", TODAY_ISO, "21:00")]
        (card,) = cards_of(cinema_tab.results_view(sessions, TODAY_ISO, TODAY))

        assert "cinema-card" in card.className and not [node for node in walk(card) if isinstance(node, (dbc.Row, dbc.Col))]
        lines = [node for node in walk(card) if "cinema-sessions" in (getattr(node, "className", None) or "")]
        assert [(line.children[0].children, [chip.children for chip in line.children[1:]]) for line in lines] == [("Kinépolis Valencia", ["19:20 · VOSE"]), ("Cines Babel", ["16:00", "21:00"])]
        assert all("cinema-name" in line.children[0].className and "d-flex" in line.className for line in lines), "the sheet keeps the names in a column through these two classes"

    def test_every_published_day_is_on_the_bar_even_a_month_of_them(self, bare_dir):
        month = [record("Película", "Cine Tívoli", (TODAY + timedelta(days=offset)).isoformat(), "17:00") for offset in range(40)]
        _write(bare_dir / SESSIONS_FILE, month)
        app = _app()
        labels = [tab.label for tab in by_id(app.layout, "cinema-day").children]

        assert len(labels) == 40  # the dashboard styles every tab list as one row that scrolls sideways
        assert labels[:5] == ["Hoy · sáb 28 nov", "Mañana · dom 29 nov", "lun 30", "mar 1 dic", "mié 2"]
        assert labels[-6:] == ["vie 1 ene", "sáb 2", "dom 3", "lun 4", "mar 5", "mié 6"]
        assert "1 película · 1 sesión · 1 cine" in texts(by_id(app.layout, "cinema-results"))
        assert "El calendario" not in texts(app.layout)  # nothing is left out, so nothing has to be said about it

        assert "miércoles 6 de enero · 1 película · 1 sesión · 1 cine" in call(app, "2027-01-06")

    def test_the_footer_names_the_sites_and_when_they_were_read(self, data_dir):
        layout = cinema_tab.render_cinema_tab()

        assert "Fuentes: exhicine.es, cinesbabel.com, ivc.gva.es, filmaffinity.com · Actualizado: 28 nov 2026 · 07:12" in texts(layout)  # 06:12 UTC, seven in València in November

        links = [link for link in walk(layout) if isinstance(link, html.A)]
        assert [(link.children, link.href) for link in links[-4:]] == [("exhicine.es", "https://exhicine.es"), ("cinesbabel.com", "https://cinesbabel.com"), ("ivc.gva.es", "https://ivc.gva.es"), ("filmaffinity.com", "https://www.filmaffinity.com")]
        assert all(link.target == "_blank" and link.rel == "noopener noreferrer" for link in links)  # the dashboard's address does not travel to the sites
        assert "Sin actualizar" not in texts(layout)


# --- nothing to show ---


class TestEmptyState:
    def test_before_the_first_run_the_tab_says_so_and_offers_no_controls(self, bare_dir):
        layout = cinema_tab.render_cinema_tab()

        assert "🎬 Cine" in texts(layout)
        assert "Todavía no hay sesiones de cine" in texts(by_id(layout, "cinema-results"))
        for ident in ("cinema-day", "cinema-cinema-filter", "cinema-version-filter"):
            with pytest.raises(StopIteration):
                by_id(layout, ident)

    def test_a_file_of_past_sessions_only_reads_as_not_loaded_yet(self, data_dir):
        _write(data_dir / SESSIONS_FILE, [record("Lo de ayer", "Cines Babel", YESTERDAY, "16:00")])

        assert "Todavía no hay sesiones de cine" in texts(cinema_tab.render_cinema_tab())

    @pytest.mark.parametrize("payload", ["{not json", '{"sessions": []}', [{"title": "sin cine ni día"}], [1, "dos", None]], ids=["broken json", "not a list", "record without the essentials", "not records"])
    def test_an_unreadable_file_reads_as_not_loaded_yet(self, bare_dir, payload):
        _write(bare_dir / SESSIONS_FILE, payload)

        assert "Todavía no hay sesiones de cine" in texts(cinema_tab.render_cinema_tab())


# --- what the last run could not read ---


class TestSourceStatus:
    def test_the_cinemas_the_last_run_could_not_read_are_named_under_the_list(self, data_dir):
        _write(data_dir / STATUS_FILE, {**STATUS, "listings": [*STATUS["listings"], {"source": "filmaffinity", "cinema": "Kinépolis Valencia", "sessions": 0, "error": "HTTP 403"}, {"source": "babel", "cinema": "Cines Babel", "sessions": 0, "error": "timeout"}]})
        shown = texts(cinema_tab.render_cinema_tab())

        assert "Sin actualizar en la última lectura: Kinépolis Valencia, Cines Babel Sus sesiones pueden faltar o ser de un día anterior." in shown
        assert "Cine Tívoli" not in shown.split("Sin actualizar")[1]  # the listing that answered is not named

    def test_a_listing_without_a_name_is_named_by_its_page(self):
        note = cinema_tab.unread_note({"listings": [{"source": "exhicine", "url": "https://cinema.test/listing", "error": "HTTP 403"}, {"source": "babel", "error": "HTTP 500"}]})

        assert texts(note) == "Sin actualizar en la última lectura: https://cinema.test/listing, un cine Sus sesiones pueden faltar o ser de un día anterior."

    def test_without_a_status_file_the_list_still_comes_and_nothing_is_claimed_about_the_sources(self, bare_dir):
        _write(bare_dir / SESSIONS_FILE, SESSIONS)
        shown = texts(cinema_tab.render_cinema_tab())

        assert "5 películas · 6 sesiones · 3 cines" in shown
        assert "Sin actualizar" not in shown and "Actualizado" not in shown

    def test_a_listing_with_no_error_leaves_no_note(self, data_dir):
        assert cinema_tab.unread_note(STATUS) is None
        assert cinema_tab.unread_note({}) is None


# --- the list follows the day and the filters, through the endpoint the browser calls ---


class TestCallback:
    def test_one_callback_redraws_the_list_and_only_runs_on_a_change(self, data_dir):
        callback = next(cb for cb in _app()._callback_list if cb["output"] == "cinema-results.children")

        assert [(spec["id"], spec["property"]) for spec in callback["inputs"]] == [("cinema-day", "active_tab"), ("cinema-cinema-filter", "value"), ("cinema-version-filter", "value")]
        assert callback["state"] == [] and callback["prevent_initial_call"] is True

    def test_another_day(self, data_dir):
        shown = call(_app(), TOMORROW)

        assert "Mañana, domingo 29 de noviembre · 2 películas · 2 sesiones · 2 cines" in shown
        assert "Dune: Parte Tres" in shown and "Oro sin ley" in shown
        assert "ARRIBA TUTTO" not in shown and "GREMLINS" not in shown

    def test_one_cinema(self, data_dir):
        shown = call(_app(), cinema="Cine Tívoli", changed="cinema-cinema-filter.value")

        assert "Hoy, sábado 28 de noviembre · 2 películas · 2 sesiones · 1 cine" in shown
        assert "17:00" in shown and "19:30" in shown
        assert "Kinépolis Valencia" not in shown and "Cines Babel" not in shown

    def test_one_version(self, data_dir):
        shown = call(_app(), version="VOSE", changed="cinema-version-filter.value")

        assert "2 películas · 2 sesiones · 2 cines" in shown
        assert "19:20 · VOSE" in shown and "16:00 · VOSE" in shown
        assert "15:00" not in shown and "EL GATO" not in shown

    def test_day_and_cinema_together(self, data_dir):
        shown = call(_app(), TOMORROW, cinema="Cines Babel")

        assert "Mañana, domingo 29 de noviembre · 1 película · 1 sesión · 1 cine" in shown
        assert "Oro sin ley" in shown and "Dune" not in shown

    def test_a_day_with_nothing_for_that_cinema_and_version(self, data_dir):
        assert NO_MATCH in call(_app(), cinema="Cine Tívoli", version="VOSE")
        assert NO_MATCH in call(_app(), day="2027-01-01")

    def test_a_cinema_with_nothing_on_that_day_says_so_and_its_day_finds_it(self, data_dir):
        assert NO_MATCH in call(_app(), TOMORROW, cinema="Filmoteca València")

        shown = call(_app(), "2026-12-22", cinema="Filmoteca València")
        assert "martes 22 de diciembre · 1 película · 1 sesión · 1 cine" in shown and "GREMLINS" in shown

    def test_a_failure_while_reading_shows_in_the_list_and_in_the_log(self, data_dir, monkeypatch, caplog):
        app = _app()  # drawn while the file can still be read

        def broken():
            raise RuntimeError("file locked")

        monkeypatch.setattr(cinema_tab, "load_sessions", broken)
        with caplog.at_level(logging.ERROR, logger="src.web.dashboard.components.cinema_tab"):
            shown = call(app)

        assert "No se pudo actualizar la lista: file locked" in shown
        assert "Cine: could not update the list" in caplog.text


# --- the view of the sessions, without a browser ---


class TestSelection:
    def test_the_day_bar_starts_today_and_names_the_month_where_it_changes(self):
        spread = [record("Película", "Cine Tívoli", (TODAY + timedelta(days=offset)).isoformat(), "17:00") for offset in (-3, -1, 0, 1, 5)]
        spread.append(record("Otra", "Cines Babel", TODAY_ISO, "19:00"))
        assert cinema_tab.published_days(spread, TODAY) == [{"value": TODAY_ISO, "label": "Hoy · sáb 28 nov", "count": 2}, {"value": TOMORROW, "label": "Mañana · dom 29 nov", "count": 1}, {"value": "2026-12-03", "label": "jue 3 dic", "count": 1}]

        three_weeks = [record("Película", "Cine Tívoli", (TODAY + timedelta(days=offset)).isoformat(), "17:00") for offset in range(20)]
        assert [option["label"] for option in cinema_tab.published_days(three_weeks, TODAY)] == ["Hoy · sáb 28 nov", "Mañana · dom 29 nov", "lun 30", "mar 1 dic", "mié 2", "jue 3", "vie 4", "sáb 5", "dom 6", "lun 7", "mar 8", "mié 9", "jue 10", "vie 11", "sáb 12", "dom 13", "lun 14", "mar 15", "mié 16", "jue 17"]

        month_turn = [record("A", "Cine Tívoli", day, "17:00") for day in ("2026-11-30", "2026-12-01", "2026-12-02")]
        assert [option["label"] for option in cinema_tab.published_days(month_turn, date(2026, 11, 30))] == ["Hoy · lun 30 nov", "Mañana · mar 1 dic", "mié 2"]
        assert cinema_tab.published_days([], TODAY) == []

    def test_a_film_shown_in_two_cinemas_is_one_card_with_a_line_per_cinema(self):
        sessions = [record("Dune", "Cine Tívoli", TODAY_ISO, "18:00"), record("dune", "Cine Tívoli", TODAY_ISO, "22:00"), record("DUNE", "Kinépolis Valencia", TODAY_ISO, "19:20", version="VOSE"), record("Otra", "Cines Babel", TODAY_ISO, "10:00")]  # the ETL lists Cine Tívoli first
        cards = cards_of(cinema_tab.results_view(sessions, TODAY_ISO, TODAY))

        assert [title_of(card) for card in cards] == ["Otra", "Dune"]  # one card however the listings spell it; titled as its first session does
        assert cinemas_of(cards[1]) == ["Cine Tívoli", "Kinépolis Valencia"]
        assert [chip.children for chip in chips_of(cards[1])] == ["18:00", "22:00", "19:20 · VOSE"]

    def test_counts_use_the_right_words(self):
        one = [record("A", "Cine Tívoli", TODAY_ISO, "17:00")]
        assert cinema_tab.counts_line(one) == "1 película · 1 sesión · 1 cine"
        assert cinema_tab.counts_line(SESSIONS) == "7 películas · 10 sesiones · 4 cines"
        assert cinema_tab.counts_line([]) == "0 películas · 0 sesiones · 0 cines"

    def test_how_the_selected_day_reads_over_the_list(self):
        assert cinema_tab.day_heading(date(2026, 11, 28), TODAY) == "Hoy, sábado 28 de noviembre"
        assert cinema_tab.day_heading(date(2026, 11, 29), TODAY) == "Mañana, domingo 29 de noviembre"
        assert cinema_tab.day_heading(date(2026, 12, 1), TODAY) == "martes 1 de diciembre"
        assert cinema_tab.day_heading(date(2027, 1, 6), TODAY) == "miércoles 6 de enero"

    def test_versions_come_in_reading_order_without_the_unlabelled_one(self):
        assert cinema_tab.version_options(SESSIONS) == [{"label": "Todas las versiones", "value": "all"}, {"label": "VOSE · 4", "value": "VOSE"}, {"label": "DOB · 1", "value": "DOB"}]

        mixed = [record("A", "Cine Tívoli", TODAY_ISO, "17:00", version=version) for version in ("DOB", "VO", "VOS", "VOSE", "")]
        assert [option["value"] for option in cinema_tab.version_options(mixed)] == ["all", "VOSE", "VOS", "VO", "DOB"]

    def test_select_keeps_the_day_and_both_filters(self):
        assert [session["time"] for session in cinema_tab.select_sessions(SESSIONS, TODAY_ISO)] == ["17:00", "19:30", "16:00", "12:00", "19:20", "15:00"]
        assert [session["time"] for session in cinema_tab.select_sessions(SESSIONS, TODAY_ISO, cinema="Cines Babel", version="VOSE")] == ["16:00"]
        assert cinema_tab.select_sessions(SESSIONS, TODAY_ISO, cinema="Ninguno") == []

    def test_a_cinema_without_a_city_reads_as_its_name(self):
        sessions = [{"title": "A", "cinema": "Cine Raro", "date": TODAY_ISO, "time": "17:00", "city": ""}, {"title": "B", "cinema": "Cine Tívoli", "date": TODAY_ISO, "time": "17:00", "city": "Burjassot"}]
        assert cinema_tab.cinema_options(sessions) == [{"label": "Todos los cines", "value": "all"}, {"label": "Cine Raro", "value": "Cine Raro"}, {"label": "Cine Tívoli · Burjassot", "value": "Cine Tívoli"}]

    def test_the_repositories_keep_only_what_says_what_where_and_when(self, tmp_path):
        sessions = cinema_tab.CinemaSessionsRepository(tmp_path / SESSIONS_FILE)
        keep = {"title": "A", "cinema": "Cine Tívoli", "date": TODAY_ISO, "time": "17:00"}
        assert sessions.transform_data([keep, {**keep, "time": ""}, {**keep, "cinema": None}, "x", None]) == [keep]
        assert sessions.transform_data({"title": "A"}) == []

        status = cinema_tab.CinemaStatusRepository(tmp_path / STATUS_FILE)
        assert status.transform_data({"generated_at": "x"}) == {"generated_at": "x"}
        assert status.transform_data([1]) == {}


# --- the tab in the dashboard ---


class TestWiring:
    def test_the_tab_sits_after_valencia_events_and_is_drawn_lazily_with_its_callback(self):
        from src.web.dashboard import app as dashboard_app

        assert dashboard_app._TAB_RENDERERS["tab-cinema"] is cinema_tab.render_cinema_tab
        nav = next(component for component in walk(dashboard_app.app.layout) if isinstance(component, dbc.Tabs) and any(getattr(tab, "tab_id", None) == "tab-cinema" for tab in component.children))
        tab_ids = [tab.tab_id for tab in nav.children]
        assert tab_ids[tab_ids.index("tab-cinema") - 1] == "tab-valencia"
        assert next(tab for tab in nav.children if tab.tab_id == "tab-cinema").label == "🎬 Cine"
        callback = next(cb for cb in dashboard_app.app._callback_list if cb["output"] == "cinema-results.children")
        assert callback["prevent_initial_call"] is True
