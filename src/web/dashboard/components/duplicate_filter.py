"""Duplicate filter switch for dashboard tabs.

Trimmed 2026-09-10 to the one helper with a live consumer: the static
"mostrar duplicados" switch consumed by the News tab's single-controller
callback (spec 01 M4/M5). The self-contained store+callback API that used to
live here was never adopted by any tab.
"""

import dash_bootstrap_components as dbc


def create_duplicate_toggle(component_id: str, label: str = " mostrar duplicados", checked: bool = False) -> dbc.Checklist:
    """Build a "mostrar duplicados" switch for tabs with a single controller callback.

    Returns only the static switch: tabs that aggregate data inside one
    controller callback (e.g. News "Top Tech") feed the switch's value into
    that callback as an extra Input and render the summary line inside their
    own results container, so no second callback chain owns any output.

    Args:
        component_id: Base ID; the switch gets id ``{component_id}-show-duplicates``.
        label: Text shown next to the switch.
        checked: Initial state (default OFF = duplicates hidden).

    Returns:
        A dbc.Checklist rendered as a Bootstrap switch.
    """
    return dbc.Checklist(
        id=f"{component_id}-show-duplicates",
        options=[{"label": label, "value": 1}],
        value=[1] if checked else [],
        switch=True,
        inline=True,
        className="user-select-none",
    )
