"""Shortcuts tab — personal bookmark launcher with full CRUD.

Reads ``data/shortcuts/predefined_shortcuts.json`` (read-only catalog) and
``data/shortcuts/custom_shortcuts.json`` (user-created, persisted from the
UI). Adding, editing (as a custom copy for predefined items) and deleting
custom shortcuts happens without restarting the server.
"""

import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dcc, html

# Import repository pattern (NEW)
from src.repositories import BaseRepository

# Import shared utilities
from src.web.dashboard.utils import get_data_path

logger = logging.getLogger(__name__)

CUSTOM_SHORTCUTS_PATH = Path(get_data_path("shortcuts", "custom_shortcuts.json"))


def _normalize_shortcuts_dict(raw: Any) -> dict[str, Any]:
    """Normalize both storage formats (dict-of-lists / categories list)."""
    if isinstance(raw, dict) and "categories" in raw:
        return {c.get("category", "Uncategorized"): c.get("items", []) for c in raw["categories"] if isinstance(c, dict)}
    if isinstance(raw, dict):
        return raw
    return {}


# NEW: Repository-based loading (SOLID Pattern)
class ShortcutsRepository(BaseRepository[dict[str, Any]]):
    """Repository for shortcuts data."""

    def __init__(self, data_path: str):
        """Initialize shortcuts repository.

        Args:
            data_path: Path to shortcuts JSON file
        """
        super().__init__(
            data_path=Path(data_path),
            cache_ttl_seconds=3600,  # 1 hour cache
            enable_cache=True,
        )

    def transform_data(self, raw_data: Any) -> dict[str, Any]:
        """Normalize both storage formats (dict-of-lists / categories list)."""
        return _normalize_shortcuts_dict(raw_data)


# Create singleton instances for each source
predefined_shortcuts_repo = ShortcutsRepository(get_data_path("shortcuts", "predefined_shortcuts.json"))
custom_shortcuts_repo = ShortcutsRepository(str(CUSTOM_SHORTCUTS_PATH))


def _load_custom_raw() -> dict[str, list[dict[str, Any]]]:
    """Read custom_shortcuts.json directly (empty dict when missing)."""
    if not CUSTOM_SHORTCUTS_PATH.exists():
        return {}
    try:
        data = json.loads(CUSTOM_SHORTCUTS_PATH.read_text(encoding="utf-8"))
        return _normalize_shortcuts_dict(data)
    except (OSError, ValueError) as e:
        logger.warning(f"Could not read custom shortcuts: {e}")
        return {}


def _persist_custom(data: dict[str, list[dict[str, Any]]]) -> bool:
    """Write custom_shortcuts.json and drop the repository cache."""
    try:
        CUSTOM_SHORTCUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CUSTOM_SHORTCUTS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        custom_shortcuts_repo.clear_cache()
        return True
    except OSError as e:
        logger.error(f"Could not write custom shortcuts: {e}")
        return False


def _normalize_url(url: str) -> str | None:
    """Return an http(s) URL, prepending https:// when the scheme is missing."""
    url = (url or "").strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc and "." in parsed.netloc:
        return url
    return None


def _is_custom_item(item: dict[str, Any], category: str, custom_data: dict[str, list[dict[str, Any]]]) -> bool:
    """Check whether a merged-list item lives in the custom file."""
    return any(c.get("name") == item.get("name") and c.get("url") == item.get("url") for c in custom_data.get(category, []))


def create_shortcut_button(shortcut_info, category, index):
    """Creates the anchor plus the edit affordance for a shortcut."""
    icon = shortcut_info.get("icon") or ""
    name = shortcut_info.get("name", "Untitled")
    description = shortcut_info.get("description") or ""
    tooltip = f"{name}\n{description}" if description else name

    edit_button = html.Button(
        "✏️",
        id={"type": "shortcut-open", "action": "edit", "category": category, "index": index},
        title="Edit shortcut",
        n_clicks=0,
        className="btn btn-link btn-sm p-0 ms-1 text-secondary",
    )

    return dbc.Col(
        html.Span(
            [
                html.A(
                    [f"{icon} {name}" if icon else name],
                    href=shortcut_info.get("url", "#"),
                    target="_blank",
                    title=tooltip,
                    className="btn btn-outline-primary m-1",
                ),
                edit_button,
            ]
        ),
        width="auto",
    )


def create_category_card(category_name, shortcuts_list, search_term="", custom_data=None):
    """Creates a Bootstrap Card for a category of shortcuts."""
    custom_data = custom_data or {}
    if search_term:
        term = search_term.lower()
        shortcuts_list = [s for s in shortcuts_list if term in s.get("name", "").lower() or term in s.get("url", "").lower() or term in (s.get("description") or "").lower()]

    if not shortcuts_list:
        return None

    add_button = html.Button(
        "＋ Add",
        id={"type": "shortcut-open", "action": "add", "category": category_name, "index": -1},
        n_clicks=0,
        className="btn btn-sm btn-outline-success ms-2",
        title=f"Add a shortcut to {category_name}",
    )

    buttons = []
    for index, shortcut in enumerate(shortcuts_list):
        buttons.append(create_shortcut_button(shortcut, category_name, index))

    return dbc.Card(
        [
            dbc.CardHeader(
                html.Div(
                    [html.H5(category_name, className="mb-0 d-inline"), add_button],
                    className="d-flex align-items-center justify-content-between",
                )
            ),
            dbc.CardBody(dbc.Row(buttons, className="g-2")),
        ],
        className="mb-3",
    )


def render_shortcuts_tab_layout(shortcuts_data, search_term="", custom_data=None):
    """Renders the full layout for the shortcuts tab based on data and search term."""
    if not shortcuts_data:
        return html.Div(dbc.Alert("No shortcut data loaded or available.", color="warning"))

    cards = []
    for category, shortcut_items in shortcuts_data.items():
        card = create_category_card(category, shortcut_items, search_term, custom_data)
        if card:
            cards.append(card)

    if not cards and search_term:
        return html.Div(dbc.Alert(f"No shortcuts found matching '{search_term}'.", color="info"))

    return html.Div(cards)


def _shortcut_modal():
    """The add/edit modal (single instance, driven by pattern-matching buttons)."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Shortcut", id="shortcut-modal-title")),
            dbc.ModalBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(dbc.Label("Name"), width=3, className="text-end pt-1"),
                            dbc.Col(dcc.Input(id="shortcut-field-name", type="text", placeholder="Name", className="form-control"), width=9),
                        ],
                        className="mb-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Label("URL"), width=3, className="text-end pt-1"),
                            dbc.Col(dcc.Input(id="shortcut-field-url", type="text", placeholder="example.com/tool", className="form-control"), width=9),
                        ],
                        className="mb-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Label("Icon"), width=3, className="text-end pt-1"),
                            dbc.Col(dcc.Input(id="shortcut-field-icon", type="text", placeholder="🎧 (emoji or short text)", className="form-control"), width=9),
                        ],
                        className="mb-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Label("Description"), width=3, className="text-end pt-1"),
                            dbc.Col(dcc.Input(id="shortcut-field-description", type="text", placeholder="Optional note (shown as tooltip)", className="form-control"), width=9),
                        ],
                        className="mb-2",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(dbc.Label("Category"), width=3, className="text-end pt-1"),
                            dbc.Col(
                                dcc.Input(
                                    id="shortcut-field-category",
                                    type="text",
                                    list="shortcut-category-options",
                                    placeholder="Category (existing or new)",
                                    className="form-control",
                                ),
                                width=9,
                            ),
                        ],
                        className="mb-2",
                    ),
                    html.Div(id="shortcut-modal-feedback"),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("🗑 Delete", id="shortcut-delete-btn", color="danger", outline=True, className="me-auto", disabled=True),
                    dbc.Button("Cancel", id="shortcut-modal-close", color="secondary", outline=True),
                    dbc.Button("Save", id="shortcut-save-btn", color="success"),
                ]
            ),
        ],
        id="shortcut-modal",
        is_open=False,
    )


def render_shortcuts_tab():
    """Main function to create the shortcuts tab layout."""
    custom_data = _load_custom_raw()
    shortcuts_data = get_shortcuts_data()
    return html.Div(
        [
            dbc.Input(
                id="search-shortcuts-input",
                placeholder="Search shortcuts by name, URL, or description...",
                type="text",
                className="mb-3",
                value="",
                debounce=True,
            ),
            # Category suggestions for the modal's category field
            html.Datalist(
                id="shortcut-category-options",
                children=[html.Option(value=category) for category in shortcuts_data],
            ),
            # Editing context for the add/delete modal (action, category, item identity)
            dcc.Store(id="shortcut-edit-context", data={}),
            html.Div(
                id="shortcuts-cards-container",
                children=render_shortcuts_tab_layout(shortcuts_data, custom_data=custom_data),
            ),
            _shortcut_modal(),
        ]
    )


def register_shortcuts_callbacks(app):
    """Single controller callback for search, modal toggling and CRUD actions."""

    @app.callback(
        Output("shortcuts-cards-container", "children"),
        Output("shortcut-modal", "is_open"),
        Output("shortcut-field-name", "value"),
        Output("shortcut-field-url", "value"),
        Output("shortcut-field-icon", "value"),
        Output("shortcut-field-description", "value"),
        Output("shortcut-field-category", "value"),
        Output("shortcut-delete-btn", "disabled"),
        Output("shortcut-edit-context", "data"),
        Output("shortcut-modal-feedback", "children"),
        Input("search-shortcuts-input", "value"),
        Input({"type": "shortcut-open", "action": ALL, "category": ALL, "index": ALL}, "n_clicks"),
        Input("shortcut-modal-close", "n_clicks"),
        Input("shortcut-save-btn", "n_clicks"),
        Input("shortcut-delete-btn", "n_clicks"),
        State("shortcut-field-name", "value"),
        State("shortcut-field-url", "value"),
        State("shortcut-field-icon", "value"),
        State("shortcut-field-description", "value"),
        State("shortcut-field-category", "value"),
        State("shortcut-edit-context", "data"),
        prevent_initial_call=True,
    )
    def shortcuts_controller(
        search_value,
        open_clicks,
        close_clicks,
        save_clicks,
        delete_clicks,
        name_value,
        url_value,
        icon_value,
        description_value,
        category_value,
        context,
    ):
        no_change = dash.no_update

        def re_render(term=None):
            return render_shortcuts_tab_layout(get_shortcuts_data(), term or search_value or "", custom_data=_load_custom_raw())

        try:
            ctx = dash.callback_context
            if not ctx.triggered:
                return re_render(), *[no_change] * 9

            trigger = ctx.triggered[0]
            trigger_prop = trigger["prop_id"]
            trigger_id = trigger_prop.split(".")[0]

            # --- Open modal (add or edit) ---
            if trigger_id.startswith("{"):
                payload = json.loads(trigger_id)
                if payload.get("type") != "shortcut-open":
                    return re_render(), *[no_change] * 9

                all_data = get_shortcuts_data()
                if payload["action"] == "add":
                    return (
                        no_change,  # container
                        True,  # open
                        "",
                        "",
                        "",
                        "",
                        payload.get("category", ""),
                        True,  # delete disabled
                        {"action": "add", "category": payload.get("category", "")},
                        None,
                    )

                # Edit: prefill from the merged list
                category = payload.get("category", "")
                index = int(payload.get("index", -1))
                items = all_data.get(category, [])
                if 0 <= index < len(items):
                    item = items[index]
                    is_custom = _is_custom_item(item, category, _load_custom_raw())
                    feedback = None if is_custom else dbc.Alert("This is a predefined shortcut: saving creates your own copy.", color="info", className="small py-1 px-2")
                    return (
                        no_change,
                        True,
                        item.get("name", ""),
                        item.get("url", ""),
                        item.get("icon", ""),
                        item.get("description", ""),
                        category,
                        not is_custom,
                        {"action": "edit", "category": category, "index": index, "name": item.get("name"), "url": item.get("url"), "custom": is_custom},
                        feedback,
                    )
                return re_render(), *[no_change] * 9

            # --- Close modal ---
            if trigger_id == "shortcut-modal-close":
                return no_change, False, *[no_change] * 8

            # --- Save (add new or save custom copy / edited custom) ---
            if trigger_id == "shortcut-save-btn":
                url = _normalize_url(url_value)
                name = (name_value or "").strip()
                category = (category_value or "").strip() or "Misc"
                if not name or not url:
                    return (
                        no_change,
                        no_change,
                        *[no_change] * 5,
                        no_change,
                        no_change,
                        dbc.Alert("Name and a valid URL are required.", color="warning", className="small py-1 px-2"),
                    )

                custom_data = _load_custom_raw()
                custom_items = custom_data.setdefault(category, [])

                context = context or {"action": "add", "category": category}
                editing_custom = context.get("action") == "edit" and context.get("custom")

                if editing_custom:
                    # Replace the matching custom entry
                    replaced = False
                    for i, item in enumerate(custom_items):
                        if item.get("name") == context.get("name") and item.get("url") == context.get("url"):
                            custom_items[i] = {"name": name, "url": url, "icon": icon_value or "", "description": description_value or ""}
                            replaced = True
                            break
                    if not replaced:
                        custom_items.append({"name": name, "url": url, "icon": icon_value or "", "description": description_value or ""})
                else:
                    if any(item.get("url") == url for item in custom_items):
                        return (
                            no_change,
                            no_change,
                            *[no_change] * 5,
                            no_change,
                            no_change,
                            dbc.Alert(f"'{url}' already exists in {category}.", color="warning", className="small py-1 px-2"),
                        )
                    custom_items.append({"name": name, "url": url, "icon": icon_value or "", "description": description_value or ""})

                if not _persist_custom(custom_data):
                    return re_render(), *[no_change] * 9

                logger.info(f"Saved shortcut '{name}' to category '{category}'")
                return re_render(), False, *[no_change] * 8

            # --- Delete (custom items only) ---
            if trigger_id == "shortcut-delete-btn" and context and context.get("custom"):
                custom_data = _load_custom_raw()
                category = context.get("category", "")
                custom_data[category] = [item for item in custom_data.get(category, []) if not (item.get("name") == context.get("name") and item.get("url") == context.get("url"))]
                if not custom_data[category]:
                    del custom_data[category]
                if _persist_custom(custom_data):
                    logger.info(f"Deleted custom shortcut '{context.get('name')}' from '{category}'")
                return re_render(), False, *[no_change] * 8

            return re_render(), *[no_change] * 9

        except Exception as e:
            logger.error(f"Error in shortcuts controller: {e}", exc_info=True)
            return html.Div(dbc.Alert(f"Error: {e}", color="danger")), *[no_change] * 9


def get_all_shortcuts():
    """Loads shortcuts from predefined and custom files using repository pattern (NEW)."""
    shortcuts_by_category: dict[str, list[dict[str, Any]]] = {}

    for repo in (predefined_shortcuts_repo, custom_shortcuts_repo):
        try:
            data = repo.get()
            for category_name, items in (data or {}).items():
                shortcuts_by_category.setdefault(category_name, []).extend(items or [])
        except Exception as e:
            logger.warning(f"Failed to load shortcuts from {repo.data_path}: {e}")

    return shortcuts_by_category


# Load data dynamically instead of at import time
def get_shortcuts_data():
    """Get fresh shortcuts data."""
    return get_all_shortcuts()


if __name__ == "__main__":
    # This part is for testing the component independently
    app_test = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app_test.layout = dbc.Container(
        [
            html.H1("Shortcuts Tab Test (Standalone)"),
            render_shortcuts_tab(),
        ]
    )
    register_shortcuts_callbacks(app_test)
    print("Running standalone test for shortcuts_tab.py on port 8051...")
    app_test.run_server(debug=True, port=8051)
