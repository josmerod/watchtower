"""Tests for the Learning tab's subtab list (T-128).

Pins which providers the tab offers, so a source that was removed on purpose
(freeCodeCamp, HF Learn, DeepLearning.AI — the user judged them low quality)
does not creep back with a copied config block. Fixtures only: the in-memory
data is stubbed and the loader is kept away from data/.
"""

import time

import dash_bootstrap_components as dbc
import pandas as pd

from src.web.dashboard.components import courses_tab


def _walk(component):
    """Yield every Dash component in a layout tree (children may be str/None/component/list)."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if hasattr(child, "children") or hasattr(child, "id"):
            yield from _walk(child)


def _subtab_labels(monkeypatch):
    """Render the Learning tab on stubbed in-memory data and return its subtab labels."""
    keys = list(courses_tab.ALL_COURSES_DATA)
    monkeypatch.setattr(courses_tab, "ALL_COURSES_DATA", {key: pd.DataFrame() for key in keys})
    monkeypatch.setattr(courses_tab, "COURSES_DATA_LOADED", {key: True for key in keys})
    monkeypatch.setattr(courses_tab, "_COURSES_LOADED_AT", time.time())  # fresh enough: ensure_courses_data() must not reload
    monkeypatch.setattr(courses_tab, "load_all_courses_data", lambda: None)

    layout = courses_tab.render_courses_tab()
    tabs = [component for component in _walk(layout) if isinstance(component, dbc.Tabs)]
    assert len(tabs) == 1 and tabs[0].id == "courses-main-tabs"
    return [tab.label for tab in tabs[0].children]


def test_learning_tab_offers_only_the_kept_providers(monkeypatch):
    assert _subtab_labels(monkeypatch) == ["🔎 Todos", "Coursera", "Udemy", "MS Credentials", "AWS Skill Builder", "GCP Skills Boost"]
