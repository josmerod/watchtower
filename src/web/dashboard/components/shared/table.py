"""Shared table-building helpers for dashboard tabs (spec 15 M1).

One canonical items-table builder so tabs stop duplicating header/body/
badge/highlight logic. Columns are declared as small descriptors and cells
fall back to plain text when no renderer is given.
"""

from collections.abc import Callable
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from src.web.dashboard.search_utils import highlight_segments

# Standard scroll container so every tab's table scrolls the same way
TABLE_SCROLL_STYLE = {"maxHeight": "800px", "overflowY": "auto", "paddingRight": "15px"}

# Column descriptor keys:
#   header  — required, column header text
#   cell    — required, callable(item) -> Any returning a component or plain value
#   td_kwargs — optional dict of extra html.Td props (e.g. className)
Column = dict[str, Any]


def render_items_table(
    items: list[dict[str, Any]],
    columns: list[Column],
    empty_message: str = "No entries found matching your criteria.",
    wrap_scroll: bool = True,
    **table_kwargs: Any,
) -> Any:
    """Render ``items`` as a dark themed dbc.Table from column descriptors.

    Args:
        items: Rows to render; each is passed to every column's ``cell``.
        columns: List of ``{"header": str, "cell": Callable, "td_kwargs": dict}``.
        empty_message: Alert text when ``items`` is empty.
        wrap_scroll: Wrap the table in the standard scroll container.
        **table_kwargs: Overrides for the underlying ``dbc.Table`` props.

    Returns:
        dbc.Alert when empty, otherwise the (optionally wrapped) table.
    """
    if not items:
        return dbc.Alert(empty_message, color="info", className="mt-3")

    table_header = [html.Thead(html.Tr([html.Th(col["header"]) for col in columns]))]

    table_body_rows = []
    for item in items:
        cells = []
        for col in columns:
            cell_content = col["cell"](item)
            cells.append(html.Td(cell_content, **(col.get("td_kwargs") or {})))
        table_body_rows.append(html.Tr(cells))

    default_kwargs: dict[str, Any] = {
        "bordered": True,
        "hover": True,
        "responsive": True,
        "striped": True,
        "size": "sm",
        "color": "dark",
        "className": "mb-0",
    }
    default_kwargs.update(table_kwargs)
    table = dbc.Table(table_header + [html.Tbody(table_body_rows)], **default_kwargs)

    if wrap_scroll:
        return html.Div(table, style=TABLE_SCROLL_STYLE)
    return table


def title_cell(
    item: dict[str, Any],
    search_term: str = "",
    title_fields: tuple[str, ...] = ("title", "name", "full_name"),
    url_fields: tuple[str, ...] = ("url", "link", "html_url", "website"),
    subtitle: str | None = None,
    subtitle_class: str = "small text-muted",
    subtitle_max_chars: int = 200,
) -> html.Div:
    """Canonical title cell: bold link (or plain), optional muted subtitle.

    Both the title and the subtitle get real highlight marks when a search
    term is provided (see ``search_utils.highlight_segments``).
    """
    title = next((str(item[f]) for f in title_fields if item.get(f)), "No Title")
    url = next((item.get(f) for f in url_fields if item.get(f)), None)

    title_children = highlight_segments(title, search_term) if search_term else title
    title_component = html.A(title_children, href=url, target="_blank", className="fw-bold text-decoration-none text-info") if url else html.Span(title_children, className="fw-bold")

    children = [title_component]
    if subtitle:
        if search_term:
            subtitle_children: Any = highlight_segments(subtitle, search_term)[:subtitle_max_chars]
        else:
            text = str(subtitle)
            subtitle_children = text[:subtitle_max_chars] + ("…" if len(text) > subtitle_max_chars else "")
        children.append(html.Div(subtitle_children, className=subtitle_class))

    return html.Div(children)


def text_cell(value: Any, search_term: str = "", **div_kwargs: Any) -> Any:
    """Plain text cell with optional highlight marks."""
    if not value:
        return "N/A"
    text = str(value)
    return html.Div(highlight_segments(text, search_term) if search_term else text, **div_kwargs)


def badges_cell(badges: list[Any], fallback: str = "General", color: str = "info") -> html.Div:
    """Badge list cell with a fallback badge when the list is empty."""
    if not badges:
        badges = [fallback]
    return html.Div([dbc.Badge(str(b), color=color, className="me-1") for b in badges])


def create_refresh_button(tab_slug: str, label: str = "🔄 Refresh", extra: dict[str, Any] | None = None) -> dbc.Button:
    """Standard per-tab refresh button using the shared id convention.

    The id is a pattern-matching dict so a single callback can serve every
    subtab instance without dead literal-Input references.
    """
    button_id: dict[str, Any] = {"type": f"{tab_slug}-refresh", "tab": "main"}
    if extra:
        button_id.update(extra)
    return dbc.Button(label, id=button_id, color="secondary", size="sm", className="mb-2 float-end")


def paginate(items: list[Any], page: int, per_page: int) -> tuple[list[Any], int, int]:
    """Slice ``items`` for the requested 1-based page.

    Returns:
        Tuple of (page_items, total_pages, clamped_page).
    """
    per_page = max(1, per_page)
    total_pages = max(1, -(-len(items) // per_page))
    page = min(max(1, page), total_pages)
    start = (page - 1) * per_page
    return items[start : start + per_page], total_pages, page


def pagination_controls(
    tab_slug: str,
    page: int,
    total_pages: int,
    showing: int,
    total: int,
    id_prefix: str | None = None,
) -> html.Div:
    """Prev/next controls, renderer-safe by construction.

    Args:
        id_prefix: When given, emit literal ids ``{id_prefix}-prev`` /
            ``{id_prefix}-next`` — only valid if the controls are part of an
            eagerly-rendered layout (KG-style tabs). Otherwise pattern-matching
            ``{"type": "{tab_slug}-page-btn", "dir": ...}`` ids are emitted,
            which a single callback can serve regardless of when the content
            mounts (videos-tab pattern).
    """
    if id_prefix:
        prev_id: dict[str, Any] | str = f"{id_prefix}-prev"
        next_id: dict[str, Any] | str = f"{id_prefix}-next"
    else:
        prev_id = {"type": f"{tab_slug}-page-btn", "dir": "prev"}
        next_id = {"type": f"{tab_slug}-page-btn", "dir": "next"}
    return html.Div(
        [
            dbc.Button(
                "← Prev",
                id=prev_id,
                color="secondary",
                size="sm",
                disabled=page <= 1,
                className="me-2",
            ),
            html.Span(f"Showing {showing} of {total} · Page {page} of {total_pages}", className="align-middle me-2 small text-muted"),
            dbc.Button(
                "Next →",
                id=next_id,
                color="secondary",
                size="sm",
                disabled=page >= total_pages,
            ),
        ],
        className="d-flex align-items-center mb-2",
    )
