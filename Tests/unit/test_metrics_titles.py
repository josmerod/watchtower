"""The two Metrics charts are named by their cards, not by the figures (T-203).

Each figure carried a title of its own, which Plotly draws above the plot in its own font and colour, under the Bootstrap
header of its card: the trends chart was named twice with the same words, and the error chart carried two names. The
names live in the card headers now, as everywhere else in the dashboard, and the figures say nothing.

Fixtures only. The charts are built from hand-made data, and the tab is rendered over an empty temporary data root:
nothing under ``data/`` is read or written.
"""

import pandas as pd
import pytest
from dash import dcc, html

from src.web.dashboard.components import metrics_tab as tab

TRENDS, ERRORS = "metrics-time-series-chart", "metrics-error-chart"


def _walk(node, ancestors=()):
    """Yield ``(node, ancestors)`` for every node of a Dash component tree, nearest ancestor last."""
    yield node, ancestors
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child, (*ancestors, node))


def _texts(node) -> str:
    """Every text a tree shows, in order."""
    if isinstance(node, str):
        return node
    if isinstance(node, (list, tuple)):
        return " ".join(_texts(item) for item in node)
    if hasattr(node, "children"):
        return _texts(node.children)
    return ""


def _card_of(layout, component) -> object:
    """The card that holds ``component`` in the rendered tab."""
    ancestors = next(ancestors for node, ancestors in _walk(layout) if node is component)
    return next(node for node in reversed(ancestors) if type(node).__name__ == "Card")


def _card_header_of(layout, graph_id: str) -> str:
    """What the header of the card that holds the graph says."""
    (graph,) = [node for node, _ in _walk(layout) if getattr(node, "id", None) == graph_id]
    (header,) = [child for child in _card_of(layout, graph).children if type(child).__name__ == "CardHeader"]
    return _texts(header)


def _header_of(layout, graph_id: str):
    """The header component of the card that holds the graph."""
    (graph,) = [node for node, _ in _walk(layout) if getattr(node, "id", None) == graph_id]
    return next(child for child in _card_of(layout, graph).children if type(child).__name__ == "CardHeader")


def _runs() -> list[dict]:
    stamps = pd.date_range("2026-11-20", periods=3, freq="D", tz="UTC")
    return [{"timestamp": stamp, "name": "news", "error_count": index, "duration": 1.5 + index} for index, stamp in enumerate(stamps)]


@pytest.fixture
def no_data_root(tmp_path, monkeypatch):
    """The tab reads an empty directory: no run summary, no freshness file."""
    monkeypatch.setattr(tab, "DATA_DIR", str(tmp_path / "data"))


# --- The figures say nothing ---


@pytest.mark.parametrize(
    ("figure", "data"),
    [
        pytest.param(tab.create_time_series_chart, _runs(), id="trends-with-data"),
        pytest.param(tab.create_time_series_chart, [], id="trends-empty"),
        pytest.param(tab.create_error_chart, {"news": 3, "etl": 1}, id="errors-with-data"),
        pytest.param(tab.create_error_chart, {}, id="errors-empty"),
    ],
)
def test_no_figure_carries_a_title(figure, data):
    assert figure(data).layout.title.text is None


def test_the_charts_still_draw_their_data():
    """Taking the title out took nothing else: axes are named and the traces are there."""
    trends, errors = tab.create_time_series_chart(_runs()), tab.create_error_chart({"news": 3, "etl": 1})

    assert [trace.name for trace in trends.data] == ["Runs", "Errors", "Avg duration (s)"]
    assert trends.layout.yaxis.title.text == "Runs / Errors" and trends.layout.yaxis2.title.text == "Avg duration (s)"
    assert list(errors.data[0].x) == ["news", "etl"] and list(errors.data[0].y) == [3, 1]
    assert errors.layout.yaxis.title.text == "Error Count"


# --- The cards name them ---


@pytest.mark.usefixtures("no_data_root")
def test_each_chart_is_named_by_the_header_of_its_card():
    """The header of each chart's card holds a title, and comes before the graph."""
    layout = tab.render_metrics_tab()

    assert "ETL Performance Trends" in _card_header_of(layout, TRENDS)
    assert "Error Distribution" in _card_header_of(layout, ERRORS)


@pytest.mark.usefixtures("no_data_root")
def test_the_headers_keep_what_the_figure_titles_said():
    """The period each chart covers was in the figure titles: it moved to the headers, word for word."""
    layout = tab.render_metrics_tab()

    assert "Last 7 Days" in _card_header_of(layout, TRENDS)
    error_header = _card_header_of(layout, ERRORS)
    assert "Error count by source, last 24 hours" in error_header  # was "Error Count by Source (Last 24 Hours)" inside the figure


@pytest.mark.usefixtures("no_data_root")
def test_the_error_chart_header_has_a_title_and_a_line_under_it():
    """The error chart had two names, a heading and a period: the header keeps both, one under the other."""
    header = _header_of(tab.render_metrics_tab(), ERRORS)
    title, line = header.children

    assert isinstance(title, html.H5) and isinstance(line, html.Small)
    assert "Error count by source, last 24 hours" in _texts(line)


@pytest.mark.usefixtures("no_data_root")
def test_every_chart_card_puts_its_header_before_its_body():
    layout = tab.render_metrics_tab()

    for graph_id in (TRENDS, ERRORS):
        (graph,) = [node for node, _ in _walk(layout) if getattr(node, "id", None) == graph_id]
        assert [type(child).__name__ for child in _card_of(layout, graph).children] == ["CardHeader", "CardBody"], graph_id


@pytest.mark.usefixtures("no_data_root")
def test_both_graphs_are_in_the_layout():
    graphs = {node.id for node, _ in _walk(tab.render_metrics_tab()) if isinstance(node, dcc.Graph)}

    assert {TRENDS, ERRORS} <= graphs
