"""The "Trendshift" subtab of Knowledge Garden (T-134).

The subtab follows the pattern of the other twelve (lazy table, one controller,
``prevent_initial_call=True``) and its rows show what a ranked repository
carries: rank, stars, the trend figure of the period, forks, language and the
description. The callbacks are driven through Dash's real endpoint, as the
browser would. Fixture-based: the data loader and the saved-items file are
replaced, so nothing reads ``data/`` and nothing touches the network.

The records here have the shape ``src/etl/github/trendshift_etl.py`` stores. The last
section covers the rows of opensourceprojects.dev, which share the builder (T-204).
"""

from pathlib import Path

import dash
import pytest
from dash import html

from src.etl.github import trendshift_etl as etl
from src.models.github import TrendshiftRepoModel
from src.services.data_loader import KNOWLEDGE_SOURCES_CONFIG, format_article_date, get_sortable_date
from src.web.dashboard.components import knowledge_garden_tab as tab
from src.web.dashboard.components import saved_items
from src.web.dashboard.components.saved_items import SAVE_CANDIDATES
from src.web.dashboard.components.shared.table import title_cell

SEARCH = "knowledge-search-trendshift"
SUBTAB = "knowledge-tab-trendshift"
SNAPSHOT = "2026-11-28T06:00:00Z"

# What the ETL stores, per repository of the daily ranking:
# full name, rank, language, stars, forks, stars gained, description, first sighting.
REPOS = [
    ("trustno1-coder/VIctory-NVIDIA", 1, "Rust", 3466, 116, 603, "VIctory (Xbox Series compatibility layer) made to draw everything on NVIDIA cards.", "2026-11-26T06:00:00Z"),
    ("openBitFun/OpenBitFun", 5, "Rust", 4252, 346, 117, "OpenBitFun combines a high-performance agent runtime written in Rust with a polished desktop application.", "2026-11-27T06:00:00Z"),
    ("CSJianYang/Industrial-Coder", 11, "Python", 725, 28, 101, "", "2026-11-27T06:00:00Z"),
    ("google-gemini/demolab", 14, "", 1077, 25, 105, "Skills, prompts, and scripts used to build and reproduce Gemini model demos", "2026-11-20T06:00:00Z"),
    ("m-bain/whisperX", 18, "Python", 25950, 2613, 63, "WhisperX:  Automatic Speech Recognition with Word-level Timestamps (& Diarization)", SNAPSHOT),
]
META = {
    "trustno1-coder/VIctory-NVIDIA": "#1 · 3,466 stars · +603 today · 116 forks · Rust",
    "openBitFun/OpenBitFun": "#5 · 4,252 stars · +117 today · 346 forks · Rust",
    "CSJianYang/Industrial-Coder": "#11 · 725 stars · +101 today · 28 forks · Python",
    "google-gemini/demolab": "#14 · 1,077 stars · +105 today · 25 forks",
    "m-bain/whisperX": "#18 · 25,950 stars · +63 today · 2,613 forks · Python",
}
# Newest sighting first; among equals, the order of the ranking.
NEWEST_FIRST = ["m-bain/whisperX", "openBitFun/OpenBitFun", "CSJianYang/Industrial-Coder", "trustno1-coder/VIctory-NVIDIA", "google-gemini/demolab"]
NEWEST_FIRST_DATES = ["2026-11-28T06:00:00+00:00", "2026-11-27T06:00:00+00:00", "2026-11-27T06:00:00+00:00", "2026-11-26T06:00:00+00:00", "2026-11-20T06:00:00+00:00"]

# Items of sources that are not rankings: a description, and a "language" that is a human one.
ARTICLES = [
    {"title": "Post 01", "url": "http://example.com/01", "source": "LessWrong", "published": "2026-08-01T00:00:00", "description": "A post with a description", "language": "en"},
    {"title": "A newsletter", "url": "http://example.com/02", "source": "Substack", "published": "2026-08-02T00:00:00", "summary": "Summary text", "stars": "1,0k"},
]


def _record(full_name, rank, language, stars, forks, stars_gained, description, first_seen) -> dict:
    """One stored record, with every field the ETL writes."""
    return {
        "source": "Trendshift",
        "title": full_name,
        "full_name": full_name,
        "url": f"https://github.com/{full_name}",
        "description": description,
        "language": language,
        "stars": stars,
        "forks": forks,
        "stars_gained": stars_gained,
        "forks_gained": 0,
        "rank": rank,
        "score": None,
        "trend_period": "daily",
        "period_starts_at": "2026-11-28T00:00:00Z",
        "tags": [],
        "social_mention_platforms": [],
        "repo_created_at": None,
        "trendshift_id": None,
        "trendshift_url": "",
        "snapshot_at": SNAPSHOT,
        "first_seen": first_seen,
        "platform": "github",
        "content_type": "trending_repo",
    }


@pytest.fixture
def saved_file(tmp_path, monkeypatch):
    """A temp file as the saved-items store: the stars never touch the real one."""
    fake = tmp_path / "saved_items.json"
    monkeypatch.setattr(saved_items, "SAVED_FILE", fake)
    monkeypatch.setattr(saved_items, "_saved_stamp", None)
    SAVE_CANDIDATES.clear()
    yield fake
    SAVE_CANDIDATES.clear()


@pytest.fixture
def records() -> list[dict]:
    return [_record(*repo) for repo in REPOS]


@pytest.fixture
def app(saved_file, monkeypatch, records):
    """The Knowledge Garden app over fixture data: Trendshift and two other sources."""
    data = {"trendshift": [dict(record) for record in records], "lesswrong": [dict(ARTICLES[0])], "substack": [dict(ARTICLES[1])]}
    monkeypatch.setattr(tab, "get_all_knowledge_data", lambda force_refresh=False: data)
    application = dash.Dash("test-kg-trendshift")
    tab.register_knowledge_garden_callbacks(application)
    application.layout = tab.render_knowledge_garden_tab()
    return application


# --- Trees as Dash serializes them: dictionaries, lists and strings ---


def _json(component):
    """A component tree as dictionaries, lists and plain values (what the endpoint answers)."""
    if hasattr(component, "to_plotly_json"):
        component = component.to_plotly_json()
    if isinstance(component, dict):
        return {key: _json(value) for key, value in component.items()}
    if isinstance(component, (list, tuple)):
        return [_json(item) for item in component]
    return component


def _components(node, kind: str | None = None) -> list[dict]:
    """Every serialized component of a type, in document order."""
    return [item for item in _components_of(node) if kind is None or item.get("type") == kind]


def _components_of(node):
    if isinstance(node, dict):
        if "type" in node and "props" in node:
            yield node
        for value in node.values():
            yield from _components_of(value)
    elif isinstance(node, list):
        for child in node:
            yield from _components_of(child)


def _visible(node) -> list[str]:
    """The strings a tree shows (component children), in document order."""
    if isinstance(node, dict) and "props" in node:
        return _visible(node["props"].get("children"))
    if isinstance(node, list):
        return [text for child in node for text in _visible(child)]
    return [node] if isinstance(node, str) else []


def _text(component) -> str:
    return " ".join(_visible(_json(component)))


def _links(component) -> list[dict]:
    return _components(component, "A")


def _ids(component) -> set:
    return {item["props"]["id"] for item in _components(component) if "id" in item["props"]}


def _with(component, attribute: str) -> list[dict]:
    """Every component that carries a ``data-*`` attribute (set after construction by the tab)."""
    return [item for item in _components(component) if attribute in item["props"]]


def _rows(component) -> list[dict]:
    """Table rows that carry a NUEVO date, in order."""
    return [item for item in _components(component, "Tr") if "data-kg-date" in item["props"]]


def _cards(component) -> list[dict]:
    """Card wrappers: the ``Div`` of each card carries the NUEVO date."""
    return [item for item in _components(component, "Div") if "data-kg-date" in item["props"]]


def _callback(app, marker: str) -> dict:
    """The callback whose output spec contains ``marker``, as the app lists it for the renderer."""
    return next(entry for entry in app._callback_list if marker in entry["output"])


def _post(app, entry, values: dict, changed, states: dict | None = None) -> dict:
    """POST the callback as the browser would and return what it changed.

    ``values`` and ``states`` map ``id.property`` to the value sent; a slot
    left out is sent as ``None``. ``changed`` are the ``id.prop`` keys the
    renderer reports. Outputs the callback left alone are not in the answer.
    """
    if entry["output"].startswith(".."):
        outputs = [dict(zip(("id", "property"), part.rsplit(".", 1), strict=True)) for part in entry["output"][2:-2].split("...")]
    else:
        outputs = dict(zip(("id", "property"), entry["output"].rsplit(".", 1), strict=True))
    states = states or {}
    body = {
        "output": entry["output"],
        "outputs": outputs,
        "inputs": [{**spec, "value": values.get(f"{spec['id']}.{spec['property']}")} for spec in entry["inputs"]],
        "changedPropIds": list(changed),
        "state": [{**spec, "value": states.get(f"{spec['id']}.{spec['property']}")} for spec in entry["state"]],
    }
    response = app.server.test_client().post("/_dash-update-component", json=body)
    assert response.status_code == 200, response.get_data(as_text=True)[-800:]
    return response.get_json()["response"]


def _actuate(app, *, activate=None, search=None, clicks: str | None = None, view="list", page=None, changed: str) -> dict:
    """Send one request to the subtab's controller. ``page`` is what the page store holds: empty until the table exists."""
    controller = _callback(app, f"{SEARCH}-results.children")
    values = {f"{SEARCH}.value": search, f"{SEARCH}-activate.data": activate}
    if clicks:
        values[f"{SEARCH}-{clicks}.n_clicks"] = 1
    return _post(app, controller, values, [changed], {f"{SEARCH}-page.data": page, f"{SEARCH}-view.data": view})


def _open(app, search: str | None = None) -> dict:
    """Open the Trendshift subtab as the browser does: the dispatcher marks it, its controller builds the table."""
    dispatch = _callback(app, f"{SEARCH}-activate.data")

    marked = _post(app, dispatch, {f"{tab.KG_TABS_ID}.active_tab": SUBTAB}, [f"{tab.KG_TABS_ID}.active_tab"])

    assert marked == {f"{SEARCH}-activate": {"data": 1}}
    return _actuate(app, activate=1, search=search, changed=f"{SEARCH}-activate.data")


# --- The subtab and its wiring ---


def test_the_subtab_sits_between_substack_and_rss_feeds(app):
    labels = [definition["label"] for definition in tab.KNOWLEDGE_TAB_DEFINITIONS]

    assert labels.index("Trendshift") == labels.index("Substack") + 1
    assert labels.index("Trendshift") == labels.index("RSS Feeds") - 1
    layout = _json(app.layout)
    (subtab,) = [item for item in _components(layout, "Tab") if item["props"].get("tab_id") == SUBTAB]
    assert subtab["props"]["label"] == "Trendshift"
    (box,) = [item for item in _components(layout) if item["props"].get("id") == SEARCH]
    assert box["props"]["placeholder"] == "Filter Trendshift by term..."
    assert box["props"]["debounce"] == tab.KG_SEARCH_DEBOUNCE_MS


def test_the_subtab_reads_the_file_the_etl_writes():
    source = KNOWLEDGE_SOURCES_CONFIG["trendshift"]
    path = Path(source["path"])

    assert source["name"] == "Trendshift"
    assert path.parts[-3:] == ("data", "github", "trendshift_daily_latest.json")
    assert etl.latest_path(path.parent, "daily") == path
    assert etl.FETCH_PERIODS == ("daily",)


def test_the_table_is_not_built_until_the_subtab_is_opened(app):
    (results,) = [item for item in _components(_json(app.layout)) if item["props"].get("id") == f"{SEARCH}-results"]

    assert _rows(results) == []
    assert _text(results) == "Cargando…"
    # The counter of new items reads the first sightings, not the snapshot: the snapshot changes every cycle.
    (pending,) = _with(results, "data-kg-dates")
    assert pending["props"]["data-kg-dates"].split(",") == NEWEST_FIRST_DATES


def test_one_controller_is_wired_and_idle_on_insertion(app):
    listening = [entry for entry in app._callback_list if f"{SEARCH}-results.children" in entry["output"]]

    assert len(listening) == 1
    (controller,) = listening
    assert controller["prevent_initial_call"] is True
    assert [spec["id"] for spec in controller["inputs"]] == [SEARCH, f"{SEARCH}-prev", f"{SEARCH}-next", f"{SEARCH}-refresh", f"{SEARCH}-view-toggle", f"{SEARCH}-activate"]
    assert [spec["id"] for spec in controller["state"]] == [f"{SEARCH}-page", f"{SEARCH}-view"]
    assert {spec["id"] for spec in controller["inputs"] + controller["state"]} <= _ids(_json(app.layout))
    (dispatcher,) = [entry for entry in app._callback_list if f"{SEARCH}-activate.data" in entry["output"]]
    assert [spec["id"] for spec in dispatcher["inputs"]] == [tab.KG_TABS_ID]


def test_another_subtab_does_not_reach_the_trendshift_controller(app):
    dispatch = _callback(app, f"{SEARCH}-activate.data")

    answer = _post(app, dispatch, {f"{tab.KG_TABS_ID}.active_tab": "knowledge-tab-lesswrong"}, [f"{tab.KG_TABS_ID}.active_tab"])

    assert f"{SEARCH}-activate" not in answer
    assert _actuate(app, activate=0, changed=f"{SEARCH}-activate.data") == {}


# --- Rows: what a repository carries ---


def test_opening_the_subtab_builds_rows_with_description_language_and_stars(app):
    answer = _open(app)
    results = answer[f"{SEARCH}-results"]["children"]

    assert answer[f"{SEARCH}-page"] == {"data": 1}
    assert answer[f"{SEARCH}-view"] == {"data": "list"}
    assert answer[f"{SEARCH}-page-info"]["children"] == "Showing 5 of 5 · Page 1 of 1"
    assert answer[f"{SEARCH}-prev"] == {"disabled": True}
    rows = _rows(results)
    assert [row["props"]["data-kg-date"] for row in rows] == NEWEST_FIRST_DATES
    for row, full_name in zip(rows, NEWEST_FIRST, strict=True):
        text = _text(row)
        (link,) = _links(row)
        assert link["props"]["href"] == f"https://github.com/{full_name}"
        assert _text(link) == full_name
        assert META[full_name] in text
        assert "Trendshift" in text
    assert "VIctory (Xbox Series compatibility layer) made to draw everything on NVIDIA cards." in _text(rows[3])
    assert "Automatic Speech Recognition" in _text(rows[0])
    assert "1,0k" not in _text(results)  # nothing of the other sources leaks in


def test_a_repository_without_description_or_language_shows_no_empty_line(app):
    rows = _rows(_open(app)[f"{SEARCH}-results"]["children"])

    industrial = _text(rows[2])
    assert "#11 · 725 stars · +101 today · 28 forks · Python" in industrial
    assert industrial.split("28 forks · Python", 1)[1].strip().startswith("Trendshift")
    demolab = _text(rows[4])
    assert demolab.split("25 forks", 1)[1].strip().startswith("Skills, prompts")
    assert demolab.count(" · ") == 3  # rank, stars, figure, forks: no fifth part for a language it does not have


def test_the_date_column_shows_the_first_sighting_never_the_snapshot(app, records):
    rows = _rows(_open(app)[f"{SEARCH}-results"]["children"])
    first = records[0]

    assert first["snapshot_at"] == SNAPSHOT and first["first_seen"] == "2026-11-26T06:00:00Z"
    assert get_sortable_date(first).isoformat() == "2026-11-26T06:00:00+00:00"
    assert format_article_date(first) == "2026-11-26 06:00 UTC"
    assert "2026-11-26 06:00 UTC" in _text(rows[3])
    # The snapshot moves on; the sighting stays: the row is not new again on the next visit.
    later = {**first, "snapshot_at": "2026-11-28T08:00:00Z"}

    assert get_sortable_date(later) == get_sortable_date(first)
    assert tab._kg_date_iso(later) == tab._kg_date_iso(first)


def test_the_title_stays_the_first_link_of_the_row_for_the_new_badge(app):
    for row in _rows(_open(app)[f"{SEARCH}-results"]["children"]):
        links = _links(row)

        assert len(links) == 1
        assert links[0]["props"]["href"].startswith("https://github.com/")
        assert "trendshift.io" not in _text(row)


def test_the_card_view_shows_the_same_figures(app):
    _open(app)
    answer = _actuate(app, clicks="view-toggle", view="list", page=1, changed=f"{SEARCH}-view-toggle.n_clicks")

    assert answer[f"{SEARCH}-view"] == {"data": "cards"}
    assert answer[f"{SEARCH}-view-toggle"]["children"] == "☰ Lista"
    cards = _cards(answer[f"{SEARCH}-results"]["children"])
    assert len(cards) == 5
    for card, full_name in zip(cards, NEWEST_FIRST, strict=True):
        text = _text(card)
        assert META[full_name] in text
        assert full_name in text
        assert "Trendshift" in text
    assert "VIctory (Xbox Series compatibility layer)" in _text(cards[3])
    assert "2026-11-26 06:00 UTC" in _text(cards[3])


def test_a_search_filters_by_description_and_highlights(app):
    answer = _open(app, search="speech")

    rows = _rows(answer[f"{SEARCH}-results"]["children"])
    assert len(rows) == 1
    assert "m-bain/whisperX" in _text(rows[0])
    assert "#18 · 25,950 stars · +63 today · 2,613 forks · Python" in _text(rows[0])
    marks = _components(rows[0], "Mark")
    assert ["".join(_visible(mark)) for mark in marks] == ["Speech"]
    assert answer[f"{SEARCH}-page-info"]["children"] == "Showing 1 of 1 · Page 1 of 1"


def test_a_long_description_is_cut_in_rows(records):
    long_description = "A description that goes on. " * 40

    lines = [child for child in tab._knowledge_title_cell({**records[0], "description": long_description}, "").children if isinstance(child, html.Div)]

    assert len(lines) == 2
    assert lines[0].children == META["trustno1-coder/VIctory-NVIDIA"]
    assert lines[1].children == long_description[:200] + "…"
    assert len(tab._knowledge_title_cell({**records[0], "description": ""}, "").children) == 2  # the link and the figures only


def test_the_garden_wide_search_shows_the_figures_too(app):
    search = _callback(app, "kg-global-results.children")

    answer = _post(app, search, {"kg-global-search-input.value": "whisperx"}, ["kg-global-search-input.value"])

    text = _text(answer["kg-global-results"]["children"])
    assert "Trendshift" in text
    assert "#18 · 25,950 stars · +63 today · 2,613 forks · Python" in text
    assert "Automatic Speech Recognition" in text


def test_starring_a_repository_saves_its_name_and_github_page(app):
    _open(app)

    assert len(SAVE_CANDIDATES) == 5
    for candidate in SAVE_CANDIDATES.values():
        assert candidate["title"] in NEWEST_FIRST
        assert candidate["url"] == f"https://github.com/{candidate['title']}"
        assert candidate["tab"] == "knowledge_garden"


# --- Other sources: rows as before ---


def test_rows_of_sources_without_star_counts_are_unchanged():
    for article in ARTICLES:
        assert tab._is_repository(article) is False
        assert tab._repo_meta(article) == ""
        assert _json(tab._knowledge_title_cell(article, "post")) == _json(title_cell(article, "post"))
        assert _json(tab._knowledge_title_cell(article, "")) == _json(title_cell(article, ""))
        assert "stars" not in _text(tab._knowledge_card(article, "post"))


def test_a_repository_without_numbers_is_not_one(records):
    cell = tab._knowledge_title_cell({**records[0], "stars": None}, "")

    assert len(cell.children) == 1 and isinstance(cell.children[0], html.A)


def test_the_period_of_the_trend_figure_is_named(records):
    weekly = {**records[0], "trend_period": "weekly", "stars_gained": 0}

    assert tab._repo_meta(weekly) == "#1 · 3,466 stars · +0 this week · 116 forks · Rust"
    assert tab._repo_meta({**records[0], "trend_period": "yearly"}) == "#1 · 3,466 stars · +603 this year · 116 forks · Rust"
    assert tab._repo_meta({**records[0], "trend_period": "monthly"}) == "#1 · 3,466 stars · +603 this month · 116 forks · Rust"
    assert tab._repo_meta({**records[0], "trend_period": None}) == "#1 · 3,466 stars · +603 in the period · 116 forks · Rust"
    assert tab._repo_meta({**records[0], "rank": None, "stars_gained": None, "forks": None, "language": ""}) == "3,466 stars"


def test_the_record_fixture_is_what_the_model_stores(records):
    assert [TrendshiftRepoModel.model_validate(record).model_dump(mode="json") for record in records] == records


# --- Open Source rows (T-204): the figures once GitHub answered, the opening from then on ---


def _project(**extra) -> dict:
    """A record as ``opensource_projects_etl`` stores it: GitHub not asked yet unless said otherwise."""
    return {
        "id": "id-triliumnext-trilium",
        "created_at": "2026-11-28 04:42:56",
        "updated_at": "2026-11-28 04:42:56",
        "title": "Trilium Notes",
        "description": "Build your personal knowledge base.",
        "url": "https://github.com/triliumnext/trilium",
        "source": "opensourceprojects.dev",
        "tags": ["CLI"],
        "published_at": "2026-11-28 01:50:02+00:00",
        "post_url": "https://www.opensourceprojects.dev/post/triliumnext-trilium",
        "topics": [],
        "detail_fetched": True,
        **extra,
    }


def _lines(cell) -> list:
    return [child for child in cell.children if isinstance(child, html.Div)]


def test_an_opensource_record_shows_its_figures_once_github_answered():
    asked = _project(stars_count=3466, forks_count=116, language="JavaScript", topics=["knowledge-base", "note-taking", "self-hosted", "markdown", "notes", "electron"], github_checked_at="2026-11-28 05:47:00")
    meta = "3,466 stars · 116 forks · JavaScript · knowledge-base, note-taking, self-hosted, markdown, notes…"

    assert tab._is_repository(asked) is True and tab._repo_meta(asked) == meta
    assert [line.children for line in _lines(tab._knowledge_title_cell(asked, ""))] == [meta, "Build your personal knowledge base."]
    assert tab._repo_meta({**asked, "topics": []}) == "3,466 stars · 116 forks · JavaScript"
    assert tab._repo_meta({**asked, "language": None, "forks_count": None}) == "3,466 stars · knowledge-base, note-taking, self-hosted, markdown, notes…"
    card = _text(tab._knowledge_card(asked, ""))
    assert meta in card and "Build your personal knowledge base." in card


def test_an_opensource_record_shows_its_opening_before_github_answered():
    fresh = _project()

    assert tab._is_repository(fresh) is False and tab._repo_meta(fresh) == ""
    cell = tab._knowledge_title_cell(fresh, "knowledge")
    (line,) = _lines(cell)
    assert "".join(_visible(_json(line))) == "Build your personal knowledge base."
    assert ["".join(_visible(mark)) for mark in _components(_json(line), "Mark")] == ["knowledge"]
    assert len(_links(_json(cell))) == 1  # the lines carry no link: the title stays the first one, for the NUEVO badge


def test_an_opensource_record_whose_description_repeats_its_title_gets_no_line():
    """The records before T-204 keep the headline as their description."""
    legacy = _project(title="Lib & tool", description="Lib & tool", published_at="2026-04-01 07:26:03.537000")

    assert _lines(tab._knowledge_title_cell(legacy, "")) == []
    assert len(tab._knowledge_title_cell(legacy, "").children) == 1


def test_the_sites_tags_are_not_shown_as_topics():
    # ``tags`` is what the site's listing says of a post; ``topics`` is what GitHub says of the repository.
    assert tab._repo_meta(_project(stars_count=10, tags=["CLI", "AI"])) == "10 stars"
    assert tab._repo_meta(_project(stars_count=10, topics=[7, " ", "cli"])) == "10 stars · cli"


def test_a_post_of_the_same_subtab_that_is_not_a_repository_is_unchanged():
    post = {"title": "A post", "url": "https://www.reddit.com/r/opensource/x", "source": "reddit_opensource", "description": "The body of the post", "language": "Python", "stars_count": None}

    assert _json(tab._knowledge_title_cell(post, "")) == _json(title_cell(post, ""))
    assert tab._is_repository(post) is False
