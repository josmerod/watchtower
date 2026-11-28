"""Cine tab: what is on at the cinemas of València and its area, by day.

The cinema ETL writes one record per screening; the tab reads them through a
repository, together with the status of the last run (which listing pages
answered and which did not). The layout is drawn from the files when the tab
is opened, and one callback redraws the list when the day or a filter changes.
"""

import logging
from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html

from src.etl.cinema.common import today as cinema_today
from src.repositories import BaseRepository, RepositoryError
from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)

SESSIONS_FILE = ("cinema", "cinema_sessions_latest.json")
STATUS_FILE = ("cinema", "cinema_sources_latest.json")

# The value of both filters that keeps every session, and how each of them reads.
ALL = "all"
ALL_CINEMAS = "Todos los cines"
ALL_VERSIONS = "Todas las versiones"
VERSION_ORDER = ("VOSE", "VOS", "VO", "DOB")
SOURCES = (("exhicine.es", "https://exhicine.es"), ("cinesbabel.com", "https://cinesbabel.com"), ("ivc.gva.es", "https://ivc.gva.es"), ("filmaffinity.com", "https://www.filmaffinity.com"))

_MADRID = ZoneInfo("Europe/Madrid")
_WEEKDAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
_WEEKDAYS_FULL = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
_MONTHS_FULL = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


# --- Data Loading ---


class CinemaSessionsRepository(BaseRepository[list[dict[str, Any]]]):
    """Repository for the cinema sessions: one record per screening."""

    def __init__(self, data_path: Path | None = None):
        """Point at the sessions file unless another path is given (the tests give one under tmp)."""
        super().__init__(data_path=data_path if data_path is not None else Path(get_data_path(*SESSIONS_FILE)), cache_ttl_seconds=3600, enable_cache=True)

    def transform_data(self, raw_data: Any) -> list[dict[str, Any]]:
        """Keep the records that say what, where and when; a file that is not a list of them gives nothing."""
        if not isinstance(raw_data, list):
            return []
        return [record for record in raw_data if isinstance(record, dict) and all(isinstance(record.get(field), str) and record[field] for field in ("title", "cinema", "date", "time"))]


class CinemaStatusRepository(BaseRepository[dict[str, Any]]):
    """Repository for what the last run read: one line per listing page, with the reason when it failed."""

    def __init__(self, data_path: Path | None = None):
        """Point at the status file unless another path is given."""
        super().__init__(data_path=data_path if data_path is not None else Path(get_data_path(*STATUS_FILE)), cache_ttl_seconds=3600, enable_cache=True)

    def transform_data(self, raw_data: Any) -> dict[str, Any]:
        """The status as the ETL wrote it; anything else gives an empty status."""
        return raw_data if isinstance(raw_data, dict) else {}


# Create singleton instances
sessions_repo = CinemaSessionsRepository()
status_repo = CinemaStatusRepository()


def load_sessions() -> list[dict[str, Any]]:
    """The sessions the last run saved, or nothing when the file is missing or unreadable."""
    try:
        return sessions_repo.get()
    except RepositoryError as exc:
        logger.warning("Cine: could not load the sessions: %s", exc)
        return []


def load_status() -> dict[str, Any]:
    """The status of the last run, or an empty status when the file is missing or unreadable."""
    try:
        return status_repo.get()
    except RepositoryError as exc:
        logger.warning("Cine: could not load the sources status: %s", exc)
        return {}


# --- The view of the sessions: pure functions, so the tab is tested without a browser ---


def _day(value: Any) -> date | None:
    """Read a day printed as YYYY-MM-DD, or None when it is not one."""
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _is_today(day: date, reference: date) -> bool:
    """True when ``day`` is the reference day."""
    return day == reference


def _is_tomorrow(day: date, reference: date) -> bool:
    """True when ``day`` is the day after the reference day."""
    return (day - reference).days == 1


def _bar_label(day: date, reference: date, with_month: bool) -> str:
    """A day as the bar prints it: "Hoy · sáb 28 nov", "Mañana · dom 29 nov", then "lun 30" or "mar 1 dic"."""
    printed = f"{_WEEKDAYS[day.weekday()]} {day.day}" + (f" {_MONTHS[day.month - 1]}" if with_month else "")
    if _is_today(day, reference):
        return f"Hoy · {printed}"
    if _is_tomorrow(day, reference):
        return f"Mañana · {printed}"
    return printed


def day_heading(day: date, reference: date) -> str:
    """The selected day in full, over its list: "Hoy, sábado 28 de noviembre", "jueves 10 de diciembre"."""
    lead = "Hoy, " if _is_today(day, reference) else "Mañana, " if _is_tomorrow(day, reference) else ""
    return f"{lead}{_WEEKDAYS_FULL[day.weekday()]} {day.day} de {_MONTHS_FULL[day.month - 1]}"


def published_days(sessions: Iterable[dict[str, Any]], reference: date) -> list[dict[str, Any]]:
    """Every day with a session, from ``reference`` on, in order, each with its number of sessions.

    The bar scrolls sideways (the dashboard styles every tab list that way), so a month of days still
    takes one line. The month is printed on the first two days and whenever it changes: the rest read
    "mié 2", which fits more of them in view.

    Args:
        sessions: The session records of every day.
        reference: Today, in the calendar of the cinemas.

    Returns:
        One option per published day, the earliest first. Yesterday is left out even when the last run
        still lists it.
    """
    counts = Counter(record["date"] for record in sessions)
    days: list[dict[str, Any]] = []
    previous: date | None = None
    for value in sorted(counts):
        day = _day(value)
        if day is None or day < reference:
            continue
        with_month = previous is None or _is_tomorrow(day, reference) or day.month != previous.month
        days.append({"value": value, "label": _bar_label(day, reference, with_month), "count": counts[value]})
        previous = day
    return days


def cinema_options(sessions: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """Every cinema, in the order the sessions list it (the ETL lists Cine Tívoli first), after "Todos los cines"."""
    cities: dict[str, str] = {}
    for record in sessions:
        cities.setdefault(record["cinema"], str(record.get("city") or ""))
    return [{"label": ALL_CINEMAS, "value": ALL}, *({"label": f"{cinema} · {city}" if city else cinema, "value": cinema} for cinema, city in cities.items())]


def version_options(sessions: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """Each version the sessions carry, in reading order with its number of sessions, after "Todas las versiones"."""
    counts = Counter(str(record.get("version") or "") for record in sessions)
    return [{"label": ALL_VERSIONS, "value": ALL}, *({"label": f"{version} · {counts[version]}", "value": version} for version in VERSION_ORDER if counts.get(version))]


def select_sessions(sessions: Iterable[dict[str, Any]], day: str, cinema: str = ALL, version: str = ALL) -> list[dict[str, Any]]:
    """The sessions of one day that pass both filters, in the order they are listed.

    Args:
        sessions: The session records of every day.
        day: The selected day as YYYY-MM-DD.
        cinema: A cinema name, or ``ALL``.
        version: A version label, or ``ALL``.

    Returns:
        The matching records; nothing when the day is not one of the published days.
    """
    return [record for record in sessions if record["date"] == day and cinema in (ALL, record["cinema"]) and version in (ALL, record.get("version") or "")]


def group_by_film(sessions: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    """The sessions of one day by film, whatever case each listing spells the title in.

    Films go by their earliest start time, so the first film that can still be seen is first. Inside a
    film the cinemas keep the order of the list (Cine Tívoli first) and the sessions go by time; the
    title of the film is the one its first session in that order prints.

    Returns:
        (film title, its sessions in that order) for each film.
    """
    cinema_order: dict[str, int] = {}
    for record in sessions:
        cinema_order.setdefault(record["cinema"], len(cinema_order))

    films: dict[str, list[dict[str, Any]]] = {}
    for record in sessions:
        films.setdefault(record["title"].casefold(), []).append(record)

    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for records in films.values():
        records.sort(key=lambda record: (cinema_order[record["cinema"]], record["time"]))
        groups.append((records[0]["title"], records))
    groups.sort(key=lambda group: (min(record["time"] for record in group[1]), group[0].casefold()))
    return groups


def _count(number: int, singular: str, plural: str | None = None) -> str:
    """Count with the right word: "1 película", "12 películas"."""
    return f"{number} {singular if number == 1 else plural or singular + 's'}"


def counts_line(sessions: list[dict[str, Any]]) -> str:
    """How many films, sessions and cinemas the selection holds."""
    films = {record["title"].casefold() for record in sessions}
    cinemas = {record["cinema"] for record in sessions}
    return f"{_count(len(films), 'película')} · {_count(len(sessions), 'sesión', 'sesiones')} · {_count(len(cinemas), 'cine')}"


# --- Layout ---


def _heading() -> list[Any]:
    """The title of the tab, the same with and without sessions."""
    return [
        html.H3("🎬 Cine", className="mb-1"),
        html.P("Qué se proyecta en los cines de València y su área, hoy y en los próximos días.", className="text-muted mb-3", style={"fontSize": "0.9rem"}),
    ]


def _session_chip(record: dict[str, Any]) -> dbc.Button:
    """A start time that opens the ticket page: "19:20 · VOSE", "15:00 · IMAX"."""
    label = " · ".join(part for part in (record["time"], record.get("version") or "", record.get("format") or "") if part)
    ticket_url = str(record.get("ticket_url") or "")
    return dbc.Button(
        label,
        href=ticket_url or None,
        disabled=not ticket_url,
        # In a new tab, so the list stays where it is. dbc 2.0 no longer opens an external_link button in one.
        **({"target": "_blank", "rel": "noopener noreferrer"} if ticket_url else {}),
        color="outline-primary",
        size="sm",
        className="cinema-session-chip me-1 mb-1",
        title=" · ".join(part for part in (record["cinema"], record.get("room") or "", record.get("language") or "") if part),
    )


def film_card(title: str, records: list[dict[str, Any]]) -> dbc.Card:
    """One film: its title linking to the film page, what the listing says about it, and its sessions per cinema."""
    first = records[0]
    minutes = first.get("duration_min")
    facts = " · ".join(str(part) for part in (first.get("year"), f"{minutes} min" if minutes else None, first.get("director") or None) if part)
    film_url = str(first.get("film_url") or "")

    by_cinema: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_cinema.setdefault(record["cinema"], []).append(record)
    # One line per cinema, its name in front of its start times. Not a Bootstrap row: the legacy sheets give
    # every .row a 24 px bottom margin, and a film on in nine cinemas took a screen and a half. The rules that
    # keep the names in a column and the chips small are in zz_visual_refresh.css, under .cinema-card.
    rows = [
        html.Div(
            [html.Span(cinema, className="fw-semibold small text-muted cinema-name"), *[_session_chip(record) for record in cinema_records]], className="cinema-sessions d-flex flex-wrap align-items-center"
        )
        for cinema, cinema_records in by_cinema.items()
    ]

    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(html.A(title, href=film_url, target="_blank", rel="noopener noreferrer", className="text-decoration-none text-info") if film_url else title, className="fw-bold mb-1"),
                html.Div(facts, className="small text-muted mb-2") if facts else None,
                *rows,
            ],
            className="py-2",
        ),
        className="cinema-card mb-2",
    )


def results_view(sessions: list[dict[str, Any]], day: str, reference: date, cinema: str = ALL, version: str = ALL) -> html.Div:
    """The list for one day: the day in full and the counts, then one card per film with its sessions per cinema.

    Args:
        sessions: The session records of every day.
        day: The selected day as YYYY-MM-DD.
        reference: Today, in the calendar of the cinemas; it says whether the day is today or tomorrow.
        cinema: A cinema name, or ``ALL``.
        version: A version label, or ``ALL``.
    """
    selected = select_sessions(sessions, day, cinema, version)
    if not selected:
        return html.Div(
            dbc.Alert(["No hay sesiones que coincidan con este día y estos filtros.", html.Br(), html.Small('Prueba con otro día, otro cine o "Todos" en los filtros.')], color="info", className="mt-2")
        )
    chosen = _day(day)
    return html.Div(
        [html.P(f"{day_heading(chosen, reference) if chosen else day} · {counts_line(selected)}", className="text-muted small mb-3"), *[film_card(title, records) for title, records in group_by_film(selected)]]
    )


def _empty_state() -> dbc.Alert:
    """What the tab says before the first run has written any session."""
    return dbc.Alert(
        [
            html.H4("Todavía no hay sesiones de cine", className="h5 alert-heading"),
            html.P(
                "El ETL de cine recoge en cada ciclo las carteleras de Cine Tívoli, Cines Babel, la Filmoteca y el resto de cines del área. La primera lista tarda unos minutos en llegar tras una instalación o un despliegue."
            ),
        ],
        color="info",
        className="mt-2",
    )


def unread_note(status: dict[str, Any]) -> dbc.Alert | None:
    """The warning for the listings the last run could not read; nothing when every one answered."""
    failed = [entry for entry in status.get("listings", []) if isinstance(entry, dict) and entry.get("error")]
    if not failed:
        return None
    names = ", ".join(str(entry.get("cinema") or entry.get("url") or "un cine") for entry in failed)
    return dbc.Alert([html.Strong("Sin actualizar en la última lectura: "), names, html.Br(), html.Small("Sus sesiones pueden faltar o ser de un día anterior.")], color="warning", className="py-2 small mt-3")


def _updated_line(status: dict[str, Any]) -> str:
    """When the last run wrote the sessions, in the hour of the cinemas; "" when the status does not say."""
    try:
        moment = datetime.fromisoformat(str(status.get("generated_at") or ""))
    except ValueError:
        return ""
    moment = moment.astimezone(_MADRID) if moment.tzinfo else moment
    return f"Actualizado: {moment.day} {_MONTHS[moment.month - 1]} {moment.year} · {moment.strftime('%H:%M')}"


def footer(status: dict[str, Any]) -> html.P:
    """Where the sessions come from, and when they were read."""
    parts: list[Any] = ["Fuentes: "]
    for index, (name, url) in enumerate(SOURCES):
        parts.append(html.A(name, href=url, target="_blank", rel="noopener noreferrer", className="text-decoration-none"))
        if index < len(SOURCES) - 1:
            parts.append(", ")
    updated = _updated_line(status)
    if updated:
        parts.append(f" · {updated}")
    return html.P(parts, className="text-muted small mt-3 mb-0")


def render_cinema_tab() -> dbc.Container:
    """Return the full default view (today); called every time the tab is selected."""
    sessions = load_sessions()
    status = load_status()
    reference = cinema_today()
    days = published_days(sessions, reference)
    if not days:
        return dbc.Container([*_heading(), html.Div(_empty_state(), id="cinema-results")], fluid=True)

    return dbc.Container(
        [
            *_heading(),
            dbc.Tabs([dbc.Tab(label=option["label"], tab_id=option["value"]) for option in days], id="cinema-day", active_tab=days[0]["value"], className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(dcc.Dropdown(id="cinema-cinema-filter", options=cinema_options(sessions), value=ALL, clearable=False), xs=12, md=7),
                    dbc.Col(dcc.Dropdown(id="cinema-version-filter", options=version_options(sessions), value=ALL, clearable=False), xs=12, md=5, className="mt-2 mt-md-0"),
                ],
                className="g-2 mb-3",
            ),
            html.Div(results_view(sessions, days[0]["value"], reference), id="cinema-results"),
            unread_note(status),
            footer(status),
        ],
        fluid=True,
    )


# --- Callbacks for Interactivity ---


def register_cinema_callbacks(app: Dash) -> None:
    """Register the Cine tab's callbacks: one callback per output component."""

    @app.callback(
        Output("cinema-results", "children"),
        Input("cinema-day", "active_tab"),
        Input("cinema-cinema-filter", "value"),
        Input("cinema-version-filter", "value"),
        prevent_initial_call=True,
    )
    def update_results(day: str | None, cinema: str | None, version: str | None) -> Any:
        """Redraw the list for the selected day and filters."""
        try:
            return results_view(load_sessions(), day or "", cinema_today(), cinema or ALL, version or ALL)
        except Exception as exc:  # show the failure in the tab instead of breaking the app
            logger.exception("Cine: could not update the list")
            return dbc.Alert(f"No se pudo actualizar la lista: {exc}", color="danger")
