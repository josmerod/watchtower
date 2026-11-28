"""The Tech Radar figure, and the theme every graph of the dashboard is drawn in.

The graph was an empty rectangle in production: the legacy sheet painted every Plotly layer svg, and the two
upper layers covered the plot (guard in test_visual_refresh_guards.py). Under it sat a figure nobody had seen:
all the bubbles of a quadrant-and-ring cell on one spot, their names on top of one another, dark text on the
dark paper and a hover that indexed records as if they were lists.
"""

from datetime import datetime, timedelta

import pytest

from src.web.dashboard.components import metrics_tab, spanish_public_aid_tab
from src.web.dashboard.components import tech_radar_tab as tab
from src.web.dashboard.utils import DARK_FIGURE

RECORD = {"tech": "docker", "quadrant": "Platforms", "mentions": 9, "sources": ["Hacker News"], "examples": [], "ring": "Adopt"}
ADOPT_CROWD = [{**RECORD, "tech": f"tech{index}", "mentions": 70 - index} for index in range(10)]  # Platforms x Adopt: ten technologies, as in the real data


def _spots(fig):
    return [(x, y) for trace in fig.data for x, y in zip(trace.x, trace.y, strict=True)]


def _layout(graph) -> dict:
    """The layout a builder hands to dcc.Graph, as a figure or in its dict form."""
    figure = graph.figure if hasattr(graph, "figure") else graph
    return figure["layout"] if isinstance(figure, dict) else figure.to_plotly_json()["layout"]


# --- The theme ---


def test_every_graph_is_drawn_for_the_dark_dashboard():
    """Plotly draws for a white page by default: dark text, and nothing to see once the paper is painted dark."""
    closing = (datetime.now() + timedelta(days=3)).isoformat()
    graphs = {
        "radar": tab._build_radar_figure([RECORD]),
        "radar, nothing detected": tab._build_radar_figure([]),
        "metrics, errors": metrics_tab.create_error_chart({"news_get_devto": 2}),
        "metrics, no errors": metrics_tab.create_error_chart({}),
        "metrics, time series": metrics_tab.create_time_series_chart([{"timestamp": datetime.now(), "name": "news_get_devto", "error_count": 0, "duration": 12.5}]),
        "metrics, no time series": metrics_tab.create_time_series_chart([]),
        "aids, category": spanish_public_aid_tab.create_category_chart([{"category": "innovacion"}]),
        "aids, no aids": spanish_public_aid_tab.create_category_chart([]),
        "aids, scope": spanish_public_aid_tab.create_scope_chart([{"scope": {"scope": "nacional"}}]),
        "aids, timeline": spanish_public_aid_tab.create_status_timeline([{"title": "Ayuda", "closing_date": closing, "category": "innovacion", "status": "abierta"}]),
    }

    for name, graph in graphs.items():
        layout = _layout(graph)
        assert layout["paper_bgcolor"] == DARK_FIGURE["paper_bgcolor"], name
        assert layout["plot_bgcolor"] == DARK_FIGURE["plot_bgcolor"], name
        assert "template" in layout, name


def test_the_theme_keeps_the_card_visible():
    assert DARK_FIGURE["paper_bgcolor"] == "rgba(0, 0, 0, 0)"
    assert DARK_FIGURE["plot_bgcolor"] == "rgba(0, 0, 0, 0)"


# --- One spot per bubble ---


def test_the_bubbles_of_a_cell_do_not_share_a_spot():
    fig = tab._build_radar_figure(ADOPT_CROWD)
    trace = fig.data[0]

    spots = _spots(fig)
    assert len(set(spots)) == len(ADOPT_CROWD)
    assert all(1.5 < x < 2.5 for x, _ in spots)  # inside the Platforms column whatever the figure's width
    assert list(trace.text) == [record["tech"] for record in ADOPT_CROWD]


def test_the_most_mentioned_sits_on_the_ring_line_and_the_others_where_there_is_room():
    spots = dict(zip((record["tech"] for record in ADOPT_CROWD), _spots(tab._build_radar_figure(ADOPT_CROWD)), strict=True))

    assert spots["tech0"] == pytest.approx((2.0, 2.0))  # Adopt is the second ring from the bottom
    assert spots["tech1"] == pytest.approx((1.72, 2.0)) and spots["tech2"] == pytest.approx((2.28, 2.0))
    assert all(y > 2.0 for x, y in list(spots.values())[3:])  # above the line: Adopt has no ring above it
    assert len({y for _, y in spots.values()}) == 3  # three rows, the same step between them


def test_assess_spreads_below_its_line():
    assess = [{**RECORD, "tech": f"tech{index}", "mentions": 2, "ring": "Assess"} for index in range(5)]
    ys = [y for _, y in _spots(tab._build_radar_figure(assess))]

    assert ys[:3] == [0.0, 0.0, 0.0] and all(y < 0.0 for y in ys[3:])  # a row on the line, the next one below it: the room Assess has


def test_a_column_holds_one_cell_per_ring():
    """The slots are counted per ring: Platforms has ten in Adopt and two in Trial, and the first version sent Trial's two into Adopt's rows."""
    trial = [{**RECORD, "tech": "raspberry pi", "mentions": 5, "ring": "Trial"}, {**RECORD, "tech": "azure", "mentions": 4, "ring": "Trial"}]
    fig = tab._build_radar_figure([*ADOPT_CROWD, *trial])
    spots = dict(zip(fig.data[0].text, _spots(fig), strict=True))  # one column, so one trace

    assert spots["raspberry pi"] == pytest.approx((2.0, 1.0)) and spots["azure"] == pytest.approx((1.72, 1.0))  # the first slots of their own cell
    assert spots["tech0"] == pytest.approx((2.0, 2.0))  # and the cell above keeps its first slot


def test_two_rows_leave_room_for_the_name_under_the_upper_bubble():
    """Rows are 0.6 of a ring apart: no bubble is wider than 48 px, so the name under an upper bubble clears the lower one when a ring is 100 px."""
    fig = tab._build_radar_figure(ADOPT_CROWD)
    rows = sorted({y for _, y in _spots(fig)})

    assert rows == pytest.approx([2.0, 2.6, 3.2])
    assert max(fig.data[0].marker.size) <= 48


@pytest.mark.parametrize(
    "index, expected",
    [
        (0, (0.0, 0)),
        (1, (-0.28, 0)),
        (2, (0.28, 0)),
        (3, (-0.14, 1)),
        (4, (0.14, 1)),
        (5, (-0.38, 1)),
        (6, (0.38, 1)),
        (7, (0.0, 2)),
        (8, (-0.28, 2)),
        (9, (0.28, 2)),
        (10, (-0.14, 3)),
        (13, (0.38, 3)),
        (14, (0.0, 4)),
        (16, (0.28, 4)),
        (17, (-0.14, 5)),
    ],
)
def test_a_cell_has_a_slot_for_every_bubble(index, expected):
    assert tab._cell_slot(index) == expected


def test_no_seat_shares_its_offset_with_the_row_under_it():
    """A name lands between two names of the row below: every row is offset from the previous one."""
    rows: dict[int, set[float]] = {}
    for index in range(30):
        offset, row = tab._cell_slot(index)
        rows.setdefault(row, set()).add(offset)

    for row in range(1, max(rows)):
        assert not rows[row] & rows[row - 1], row


def test_a_cell_of_fifteen_keeps_fifteen_spots():
    crowd = [{**RECORD, "tech": f"tech{index}", "mentions": 70 - index} for index in range(15)]  # the figure shows 40 records at most

    spots = _spots(tab._build_radar_figure(crowd))
    assert len(set(spots)) == 15
    assert max(y for _, y in spots) == pytest.approx(2.0 + 4 * tab._ROW_STEP)  # rows 0 to 4: three, four, three, four, one


def test_the_axes_name_the_columns_and_the_rings_and_leave_room_for_every_bubble():
    fig = tab._build_radar_figure([*ADOPT_CROWD, {**RECORD, "tech": "old", "mentions": 2, "ring": "Assess"}])
    highest, lowest = max(y for _, y in _spots(fig)), min(y for _, y in _spots(fig))

    assert list(fig.layout.xaxis.ticktext) == tab._QUADRANT_ORDER
    assert list(fig.layout.yaxis.ticktext) == ["Assess", "Trial", "Adopt"]  # Hold is in the vocabulary, no count maps to it
    assert fig.layout.yaxis.range[1] >= highest + 0.25 and fig.layout.yaxis.range[0] <= lowest - 0.25
    assert list(fig.layout.xaxis.range) == [-0.5, 3.5]


@pytest.mark.parametrize("mentions, expected", [(2, 10 + 9 * 2**0.5), (9, 10 + 27), (70, 48)])
def test_a_bubble_grows_with_the_mentions_up_to_a_cap(mentions, expected):
    trace = tab._build_radar_figure([{**RECORD, "mentions": mentions}]).data[0]

    assert trace.marker.size == pytest.approx([expected])


# --- The hover ---


def test_the_hover_reads_the_record():
    record = {**RECORD, "sources": ["Hacker News", "InfoQ"]}
    trace = tab._build_radar_figure([record]).data[0]

    assert [list(row) for row in trace.customdata] == [[9, 2, "Hacker News, InfoQ", "Adopt", "Platforms"]]
    assert all(f"%{{customdata[{index}]}}" in trace.hovertemplate for index in range(5))
    assert "%{x}" not in trace.hovertemplate and "%{y}" not in trace.hovertemplate  # both are numbers now
