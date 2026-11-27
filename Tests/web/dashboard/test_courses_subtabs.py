"""Tests for the Learning tab's subtab list (T-128, T-144).

Pins which providers the tab offers, so a source that was removed on purpose
(freeCodeCamp, HF Learn, DeepLearning.AI — the user judged them low quality)
does not creep back with a copied config block, and that the Microsoft Learn
catalog is offered as two subtabs, certifications and applied skills, each with
its own search box and table callback. Fixtures only: the in-memory data is
stubbed and the loader is kept away from data/.
"""

import time

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, html

from src.web.dashboard.components import courses_tab

EXPECTED_SUBTABS = ["🔎 Todos", "Coursera", "Udemy", "MS Certificaciones", "MS Applied Skills", "AWS Skill Builder", "GCP Skills Boost"]

# Shaped like ms_applied_skills.json after load_ms_applied_skills_data():
# the ETL copies the credential type into `category`.
MS_CREDENTIALS = [
    {"title": "Microsoft Certified: Azure Administrator Associate", "category": "cert", "subject": "N/A", "level": "Intermediate", "roles": ["administrator"], "url": "https://learn.microsoft.com/a", "detected_str": "2026-07-22"},
    {"title": "GitHub Administration", "category": "cert", "subject": "N/A", "level": "Intermediate", "roles": ["devops-engineer"], "url": "https://learn.microsoft.com/b", "detected_str": "2026-07-22"},
    {"title": "Microsoft Applied Skills: Develop AI agents on Azure", "category": "applied_skill", "subject": "Artificial Intelligence", "level": "Intermediate", "roles": ["ai-engineer"], "url": "https://learn.microsoft.com/c", "detected_str": "2026-10-14"},
    {"title": "Unlabelled credential", "category": "N/A", "subject": "N/A", "level": "Beginner", "roles": "N/A", "url": "https://learn.microsoft.com/d", "detected_str": "2026-10-14"},
]


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


def _stubbed_layout(monkeypatch, frames=None):
    """Render the Learning tab on stubbed in-memory data (empty catalogs unless `frames` says otherwise)."""
    frames = frames or {key: pd.DataFrame() for key in courses_tab.ALL_COURSES_DATA}
    monkeypatch.setattr(courses_tab, "ALL_COURSES_DATA", frames)
    monkeypatch.setattr(courses_tab, "COURSES_DATA_LOADED", dict.fromkeys(frames, True))
    monkeypatch.setattr(courses_tab, "_COURSES_LOADED_AT", time.time())  # fresh enough: ensure_courses_data() must not reload
    monkeypatch.setattr(courses_tab, "load_all_courses_data", lambda: None)
    return courses_tab.render_courses_tab()


def _subtab_labels(monkeypatch):
    """Return the subtab labels of the Learning tab rendered on empty catalogs."""
    layout = _stubbed_layout(monkeypatch)
    tabs = [component for component in _walk(layout) if isinstance(component, dbc.Tabs)]
    assert len(tabs) == 1 and tabs[0].id == "courses-main-tabs"
    return [tab.label for tab in tabs[0].children]


def _ms_frames():
    return {key: pd.DataFrame() for key in courses_tab.ALL_COURSES_DATA} | {"ms_skills": pd.DataFrame(MS_CREDENTIALS)}


def _table_texts(table):
    """Return (header cell texts, row cell texts) of a simple dbc.Table."""
    head, body = table.children
    header = [cell.children for cell in head.children.children]
    rows = [[cell.children for cell in row.children] for row in body.children]
    return header, rows


def test_learning_tab_offers_only_the_kept_providers(monkeypatch):
    assert _subtab_labels(monkeypatch) == EXPECTED_SUBTABS


def test_ms_certifications_and_applied_skills_get_one_subtab_each(monkeypatch):
    layout = _stubbed_layout(monkeypatch, _ms_frames())
    tabs = [component for component in _walk(layout) if isinstance(component, dbc.Tabs)]
    tab_ids = {tab.tab_id for tab in tabs[0].children}
    ids = {component.id for component in _walk(layout) if getattr(component, "id", None)}

    assert {"tab-ms-certs", "tab-ms-applied"} <= tab_ids
    assert "tab-ms-skills" not in tab_ids  # the merged "MS Credentials" subtab is gone
    for kind in ("certs", "applied"):
        assert courses_tab.MS_CREDENTIAL_KINDS[kind]["search_id"] in ids
        assert courses_tab.MS_CREDENTIAL_KINDS[kind]["table_id"] in ids


def test_split_ms_credentials_partitions_the_catalog():
    certs, applied = courses_tab.split_ms_credentials(pd.DataFrame(MS_CREDENTIALS))

    assert certs["title"].tolist() == ["Microsoft Certified: Azure Administrator Associate", "GitHub Administration"]
    # An unlabelled credential is not dropped: it stays with the applied skills, the ETL's own fallback.
    assert applied["title"].tolist() == ["Microsoft Applied Skills: Develop AI agents on Azure", "Unlabelled credential"]
    assert len(certs) + len(applied) == len(MS_CREDENTIALS)

    empty_certs, empty_applied = courses_tab.split_ms_credentials(pd.DataFrame())
    assert empty_certs.empty and empty_applied.empty


def test_ms_table_shows_the_subject_only_where_it_exists(monkeypatch):
    certs, applied = courses_tab.split_ms_credentials(pd.DataFrame(MS_CREDENTIALS))

    cert_header, cert_rows = _table_texts(courses_tab._ms_credentials_table(certs, "certs"))
    assert cert_header == ["Title", "Level", "Roles", "First Detected"]  # certifications carry no subject: no all-"N/A" column
    assert cert_rows[0][1:3] == ["Intermediate", "Administrator"]
    assert cert_rows[0][0].children == "Azure Administrator Associate"  # the kind prefix only repeats the subtab label
    assert cert_rows[0][0].href == "https://learn.microsoft.com/a"
    assert cert_rows[1][0].children == "GitHub Administration"  # a title without the prefix is left alone

    applied_header, applied_rows = _table_texts(courses_tab._ms_credentials_table(applied, "applied"))
    assert applied_header == ["Title", "Subject", "Level", "Roles", "First Detected"]
    assert applied_rows[0][1:3] == ["Artificial Intelligence", "Intermediate"]
    assert applied_rows[0][3] == "AI Engineer"
    assert applied_rows[1][3] == "N/A"  # no roles


def test_ms_role_labels_keep_the_acronyms_of_the_catalog_vocabulary():
    # Every role id seen in the production catalog on 2026-11-26.
    vocabulary = [
        "administrator",
        "developer",
        "solution-architect",
        "ai-engineer",
        "functional-consultant",
        "business-user",
        "devops-engineer",
        "maker",
        "business-analyst",
        "data-engineer",
        "database-administrator",
        "security-engineer",
        "data-analyst",
        "security-operations-analyst",
        "student",
        "ip-admin",
        "support-engineer",
        "technology-manager",
        "business-leader",
        "ai-edge-engineer",
        "business-owner",
        "identity-access-admin",
        "platform-engineer",
        "service-adoption-specialist",
    ]

    labels = [courses_tab._ms_role_label(role) for role in vocabulary]

    assert "AI Engineer" in labels and "DevOps Engineer" in labels and "IP Admin" in labels
    assert not [label for label in labels if "-" in label or label != label.strip()]
    assert len(set(labels)) == len(vocabulary)  # no two roles collapse into the same label


def test_ms_search_matches_the_full_title_subject_and_roles(monkeypatch):
    _, applied = courses_tab.split_ms_credentials(pd.DataFrame(MS_CREDENTIALS))

    def titles(search_term):
        return courses_tab._search_ms_credentials(applied, search_term)["title"].tolist()

    assert titles("microsoft applied") == ["Microsoft Applied Skills: Develop AI agents on Azure"]  # the prefix is gone from the link text, not from the search
    assert titles("intelligence") == ["Microsoft Applied Skills: Develop AI agents on Azure"]
    assert titles("AI-ENGINEER") == ["Microsoft Applied Skills: Develop AI agents on Azure"]
    assert titles("nothing-matches") == []
    assert len(titles(None)) == 2


def test_unified_catalog_badges_each_ms_credential_by_its_kind(monkeypatch):
    layout = _stubbed_layout(monkeypatch, _ms_frames())
    badges = [component.children for component in _walk(layout) if isinstance(component, dbc.Badge)]

    assert badges.count("MS Certificación") == 2
    assert badges.count("MS Applied Skill") == 2
    assert "Microsoft" not in badges


def test_each_ms_subtab_owns_exactly_one_table_callback():
    app = Dash(__name__)
    courses_tab.register_courses_callbacks(app)
    owners = {}
    for key in app.callback_map:
        output_id = key.split(".")[0]
        owners[output_id] = owners.get(output_id, 0) + 1

    for kind in ("certs", "applied"):
        assert owners[courses_tab.MS_CREDENTIAL_KINDS[kind]["table_id"]] == 1
        assert owners.get(courses_tab.MS_CREDENTIAL_KINDS[kind]["search_id"], 0) == 0  # the search box is only ever an Input
    assert "ms-skills-table-container" not in owners


def test_ms_subtab_without_rows_says_so_instead_of_rendering_an_empty_table(monkeypatch):
    html_div = courses_tab.render_ms_credentials_sub_tab("certs", pd.DataFrame())
    alert = next(component for component in _walk(html_div) if isinstance(component, dbc.Alert))
    assert "MS Certificaciones" in alert.children


# --- Language filter of the AWS Skill Builder and GCP Skills Boost subtabs (T-146, T-147) ---------

# Shaped like aws_skill_builder.json / gcp_skills_boost.json after their loaders: `language` as the ETLs write it.
AWS_COURSES = pd.DataFrame(
    [
        {"title": "Introducción a AWS", "url": "https://www.classcentral.com/course/1", "language": "es", "description": "Beginner · 1 hour · Free", "detected_str": "2026-11-27"},
        {"title": "Introduction to Blockchain", "url": "https://www.classcentral.com/course/2", "language": "en", "description": "Beginner · 1 hour · 4.8/5 (8 ratings) · Free", "detected_str": "2026-11-27"},
    ]
)
GCP_COURSES = pd.DataFrame(
    [
        {"title": "Create a VPC using Cloud Shell", "url": "https://partner.skills.google/focuses/134707", "language": "en", "course_type": "lab", "description": "Create a VPC", "duration": "1 hour", "level": "introductory", "detected_str": "2026-11-27"},
        {"title": "Explora y crea informes con Data Studio", "url": "https://partner.skills.google/focuses/99", "language": "en+es", "course_type": "course", "description": "Reports", "duration": "1 hour", "level": "introductory", "detected_str": "2026-11-27"},
    ]
)


def _cloud_frames():
    return {key: pd.DataFrame() for key in courses_tab.ALL_COURSES_DATA} | {"aws_skills": AWS_COURSES, "gcp_skills": GCP_COURSES}


def _dropdown(layout, dropdown_id):
    (dropdown,) = [component for component in _walk(layout) if getattr(component, "id", None) == dropdown_id]
    return dropdown


def test_aws_and_gcp_subtabs_offer_a_language_filter(monkeypatch):
    layout = _stubbed_layout(monkeypatch, _cloud_frames())

    aws = _dropdown(layout, "aws-skills-language-dropdown")
    gcp = _dropdown(layout, "gcp-skills-language-dropdown")

    assert [(option["label"], option["value"]) for option in aws.options] == [("Español", "es"), ("English", "en")]
    assert [(option["label"], option["value"]) for option in gcp.options] == [("English", "en"), ("English + Spanish", "en+es")]
    assert aws.placeholder == gcp.placeholder == "Filter by language"


def test_a_catalog_written_before_the_language_existed_offers_no_filter():
    legacy = pd.DataFrame([{"title": "AWS SimuLearn: 엣지에서의 ETL", "url": "https://www.classcentral.com/course/0", "language": "N/A"}])

    assert courses_tab.language_options(legacy) == []
    assert courses_tab.language_options(pd.DataFrame([{"title": "No language column"}])) == []
    assert len(courses_tab.filter_by_language(legacy, "es")) == 0
    assert len(courses_tab.filter_by_language(legacy, None)) == 1  # no language chosen: nothing is filtered


def test_language_filter_keeps_only_the_courses_in_that_language():
    spanish = courses_tab.filter_by_language(AWS_COURSES, "es")

    assert spanish["title"].tolist() == ["Introducción a AWS"]
    assert len(courses_tab.filter_by_language(AWS_COURSES, None)) == 2
    assert courses_tab.filter_by_language(GCP_COURSES, "en+es")["title"].tolist() == ["Explora y crea informes con Data Studio"]


def test_cloud_tables_render_the_rows_they_are_given():
    header, rows = _table_texts(courses_tab._aws_skills_table(courses_tab.filter_by_language(AWS_COURSES, "en")))

    assert header == ["Title", "Info", "First Detected"]
    assert rows[0][0].children == "Introduction to Blockchain" and rows[0][0].href == "https://www.classcentral.com/course/2"
    assert rows[0][1] == "Beginner · 1 hour · 4.8/5 (8 ratings) · Free"
    header, rows = _table_texts(courses_tab._gcp_skills_table(courses_tab.filter_by_language(GCP_COURSES, "en")))
    assert header == ["Title", "Type", "Description", "Duration", "Level", "First Detected"]
    assert [row[1] for row in rows] == ["lab"]


def test_cloud_table_callbacks_read_the_search_box_and_the_language_filter():
    app = Dash(__name__)
    courses_tab.register_courses_callbacks(app)

    for table_id, dropdown_id in (("aws-skills-table-container", "aws-skills-language-dropdown"), ("gcp-skills-table-container", "gcp-skills-language-dropdown")):
        owners = [key for key in app.callback_map if key.split(".")[0] == table_id]
        assert len(owners) == 1, table_id
        inputs = {spec["id"] for spec in app.callback_map[owners[0]]["inputs"]}
        assert dropdown_id in inputs, table_id
    assert not [key for key in app.callback_map if key.split(".")[0] in ("aws-skills-language-dropdown", "gcp-skills-language-dropdown")]  # the dropdown is only ever an Input
