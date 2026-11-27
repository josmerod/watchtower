"""Unit tests for the two cloud-course ETLs (T-146 AWS Skill Builder, T-147 GCP Skills Boost).

Nothing here touches the network: the page fetchers are stubbed and every
BaseETL write goes to a temporary project root. The shapes of the fixtures
reproduce what the two sites answered on 2026-11-27.
"""

import html
import json
from pathlib import Path

import pytest

from src.config.settings import get_settings
from src.etl.courses import aws_skill_builder_etl as aws
from src.etl.courses import gcp_skills_boost_etl as gcp

OLD_DETECTED = "2026-11-20T10:00:00+00:00"


@pytest.fixture(autouse=True)
def _isolated_data_root(tmp_path, monkeypatch):
    """Send every BaseETL write (data, checkpoints, circuit breaker, run summaries) to tmp_path instead of the real data/."""
    monkeypatch.setattr(get_settings(), "project_root", str(tmp_path))
    yield


# --- GCP Skills Boost ---------------------------------------------------------------------------


def _gcp_item(item_id, title, item_type="lab"):
    return {"type": item_type, "title": title, "description": f"About {title}", "path": f"/focuses/{item_id}?catalog_rank=%7B%22rank%22%3A{item_id}%7D&parent=catalog", "duration": "1 hour", "level": "introductory"}


def _gcp_pages(default_pages, spanish_pages):
    """A page fetcher keyed by (page, locale) that records the calls it gets."""
    calls = []

    def fetch(page, locale=None):
        calls.append((page, locale))
        pages = spanish_pages if locale == "es" else default_pages
        return pages[page - 1] if page <= len(pages) else None

    return fetch, calls


def test_catalog_path_drops_the_ranking_query():
    path = gcp.catalog_path("/focuses/134707?catalog_rank=%7B%22rank%22%3A1%7D&parent=catalog")

    assert path == "/focuses/134707"
    assert gcp.catalog_path(None) == ""


def test_extract_walks_every_page_in_english_and_again_in_spanish(monkeypatch):
    default = [[_gcp_item(i, f"Lab {i}") for i in range(200)], [_gcp_item(i, f"Course {i}", "course") for i in range(200, 250)]]
    spanish = [[_gcp_item(i, "Laboratorio 1" if i == 1 else f"Lab {i}") for i in range(200)], [_gcp_item(i, f"Course {i}", "course") for i in range(200, 250)]]
    fetch, calls = _gcp_pages(default, spanish)
    monkeypatch.setattr(gcp.time, "sleep", lambda seconds: None)
    etl = gcp.GcpSkillsBoostETL(name="gcp_test")
    monkeypatch.setattr(etl, "_fetch_page", fetch)

    items = etl.extract()

    assert len(items) == 250
    assert calls == [(1, None), (2, None), (1, "es"), (2, "es")]  # a short page is the last one: no request past it
    assert items[1]["title_es"] == "Laboratorio 1" and items[2]["title_es"] == "Lab 2"


def test_extract_stops_when_the_site_answers_something_that_is_not_a_list(monkeypatch):
    fetch, calls = _gcp_pages([[_gcp_item(i, f"Lab {i}") for i in range(gcp.PER_PAGE)]], [[_gcp_item(i, f"Lab {i}") for i in range(gcp.PER_PAGE)]])
    monkeypatch.setattr(gcp.time, "sleep", lambda seconds: None)
    etl = gcp.GcpSkillsBoostETL(name="gcp_test")
    monkeypatch.setattr(etl, "_fetch_page", fetch)

    assert len(etl.extract()) == gcp.PER_PAGE
    assert calls == [(1, None), (2, None), (1, "es"), (2, "es")]  # page 2 is `{"data": []}` for both locales


def test_extract_fails_loudly_when_the_first_page_is_not_a_list(monkeypatch):
    etl = gcp.GcpSkillsBoostETL(name="gcp_test")
    monkeypatch.setattr(etl, "_fetch_page", lambda page, locale=None: None)

    with pytest.raises(ValueError, match="did not answer a catalog list"):
        etl.extract()


def test_transform_builds_one_record_per_path_and_keeps_the_old_detection_dates(tmp_path):
    previous = [{"url": "https://partner.skills.google/focuses/1?catalog_rank=%7B%22rank%22%3A1%7D&parent=catalog", "first_detected_at": OLD_DETECTED}, {"url": "https://partner.skills.google/focuses/9?catalog_rank=%7B%22rank%22%3A9%7D&parent=catalog", "first_detected_at": OLD_DETECTED}]
    courses_file = tmp_path / "data" / "courses" / "gcp_skills_boost.json"
    courses_file.parent.mkdir(parents=True)
    courses_file.write_text(json.dumps(previous), encoding="utf-8")
    etl = gcp.GcpSkillsBoostETL(name="gcp_test")
    assert etl.courses_file == courses_file  # the project root of the settings, not the working directory
    items = [_gcp_item(1, "Create a VPC using Cloud Shell"), dict(_gcp_item(1, "Create a VPC using Cloud Shell")), _gcp_item(2, "Translated lab"), {"type": "lab", "title": "No path"}]
    items[2]["title_es"] = "Laboratorio traducido"

    records = {record["url"]: record for record in etl.transform(items)}

    assert list(records) == ["https://partner.skills.google/focuses/1", "https://partner.skills.google/focuses/2"]  # no query string, no duplicate, nothing without a path
    assert records["https://partner.skills.google/focuses/1"]["first_detected_at"].startswith("2026-11-20T10:00:00")  # kept although the old URL carried the query
    assert records["https://partner.skills.google/focuses/2"]["first_detected_at"][:4] >= "2026"
    assert records["https://partner.skills.google/focuses/1"]["language"] == "en"
    assert records["https://partner.skills.google/focuses/2"]["language"] == "en+es"
    assert records["https://partner.skills.google/focuses/2"]["course_type"] == "lab"


def test_transform_fails_when_no_item_has_a_title_and_a_path():
    etl = gcp.GcpSkillsBoostETL(name="gcp_test")

    with pytest.raises(ValueError, match="catalog format changed"):
        etl.transform([{"type": "lab"}])


def test_run_leaves_the_previous_file_alone_when_nothing_comes_back(monkeypatch, tmp_path):
    courses_file = tmp_path / "data" / "courses" / "gcp_skills_boost.json"
    courses_file.parent.mkdir(parents=True)
    courses_file.write_text('[{"title": "Kept"}]', encoding="utf-8")
    monkeypatch.setattr(gcp.time, "sleep", lambda seconds: None)
    etl = gcp.GcpSkillsBoostETL(name="gcp_test")
    monkeypatch.setattr(etl, "_fetch_page", lambda page, locale=None: [])

    etl.run()

    assert courses_file.read_text(encoding="utf-8") == '[{"title": "Kept"}]'


# --- AWS Skill Builder on Class Central -----------------------------------------------------------


def _course(course_id, name, slug=None, level="beginner", free=True, ratings=0, average=None, subject="AI", spans=("1 hour", "Self-Paced")):
    return {"id": course_id, "name": name, "slug": slug or f"course-{course_id}", "level": level, "free": free, "ratings": ratings, "average": average, "subject": subject, "spans": spans}


def _listing(*courses):
    """A Class Central page: every course sits in one <li> and is linked three times with the same facts."""
    items = []
    for course in courses:
        props = html.escape(json.dumps({"course_name": course["name"], "course_id": course["id"], "course_level": course["level"], "course_language": "English", "course_provider": "AWS Skill Builder", "course_subject": course["subject"], "course_num_rating": course["ratings"], "course_avg_rating": course["average"], "course_is_free": course["free"]}), quote=True)
        links = "".join(f'<a class="link{i}" data-track-click="course_click" data-track-props="{props}" href="/course/{course["slug"]}">text</a>' for i in range(3))
        provider_link = '<a data-track-props=\'{"catalog_type":"institution","catalog_title":"Amazon Web Services"}\' href="/institution/aws">Amazon Web Services</a>'
        spans = "".join(f"<span>{text}</span>" for text in ("Add to list", *course["spans"]))
        items.append(f'<li class="course-list-course"><div>{provider_link}{links}<div>{spans}</div></div></li>')
    return f"<html><body><ul>{''.join(items)}</ul></body></html>"


def _aws_etl(monkeypatch, pages, sleep_log=None):
    """An AWS ETL whose page fetcher answers from `pages` (keyed by (lang, sort, page)) and records every call."""
    calls = []

    def fetch(lang, sort, page):
        calls.append((lang, sort, page))
        answer = pages[(lang, sort, page)]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(aws.time, "sleep", lambda seconds: sleep_log.append(seconds) if sleep_log is not None else None)
    etl = aws.AwsSkillBuilderETL(name="aws_test")
    monkeypatch.setattr(etl, "_fetch_page", fetch)
    return etl, calls


SPANISH_PAGE = _listing(_course(1, "Introducción a AWS"), _course(2, "Cómo usar Amazon Bedrock (Español LATAM)", spans=("2 hours", "No Longer Offered")))
ENGLISH_PAGE = _listing(_course(3, "Introduction to Blockchain", ratings=8, average=4.75, subject="R&D"), _course(4, "Amazon Bedrock Getting Started (Español LATAM)"), _course(5, "AWS SimuLearn: 데이터 레이크 보안"))


def test_parse_listing_reads_the_facts_embedded_in_each_course_link():
    courses = aws.parse_listing(ENGLISH_PAGE, "en")

    assert [course["title"] for course in courses] == ["Introduction to Blockchain", "Amazon Bedrock Getting Started (Español LATAM)", "AWS SimuLearn: 데이터 레이크 보안"]  # three links, one record
    first = courses[0]
    assert first["url"] == "https://www.classcentral.com/course/course-3"
    assert (first["level"], first["is_free"], first["rating"], first["rating_count"], first["subject"], first["duration"]) == ("Beginner", True, 4.75, 8, "R&D", "1 hour")
    assert first["no_longer_offered"] is False
    assert aws.parse_listing(SPANISH_PAGE, "es")[1]["no_longer_offered"] is True
    assert aws.parse_listing(SPANISH_PAGE, "es")[1]["duration"] == "2 hours"


@pytest.mark.parametrize(
    ("title", "language", "expected"),
    [
        ("Introduction to Blockchain", "en", True),
        ("Introducción a AWS", "es", True),
        ("Cómo usar Amazon Bedrock (Español LATAM)", "es", True),
        ("Cómo usar Amazon Bedrock (Español LATAM)", "en", False),  # tagged English by Class Central
        ("Introduction to Amazon Route 53 Resolver (Korean)", "en", False),
        ("Principes de base de PostgreSQL : architecture (Français)", "en", False),
        ("AWS SimuLearn: 데이터 레이크 보안", "en", False),
        ("AWS SimuLearn: スパイドローンの検出", "en", False),
        ("Curso de inglés para developers (Español de España)", "es", True),
        ("", "en", False),
    ],
)
def test_is_in_language_judges_the_title_not_the_tag(title, language, expected):
    assert aws.is_in_language(title, language) is expected


def test_extract_reads_two_pages_of_each_listing_with_pauses(monkeypatch):
    pages = {("spanish", "created-up", 1): SPANISH_PAGE, ("spanish", "created-up", 2): SPANISH_PAGE, ("english", "rating-up", 1): ENGLISH_PAGE, ("english", "rating-up", 2): ENGLISH_PAGE}
    sleeps = []
    etl, calls = _aws_etl(monkeypatch, pages, sleeps)

    courses = etl.extract()

    assert calls == [("spanish", "created-up", 1), ("spanish", "created-up", 2), ("english", "rating-up", 1), ("english", "rating-up", 2)]
    assert sleeps == [aws.REQUEST_DELAY_SECONDS] * 3  # a pause between requests, none after the last one
    assert len(courses) == 10 and {course["language"] for course in courses} == {"es", "en"}


def test_extract_stops_at_a_rate_limit_and_keeps_what_it_read(monkeypatch):
    pages = {("spanish", "created-up", 1): SPANISH_PAGE, ("spanish", "created-up", 2): SPANISH_PAGE, ("english", "rating-up", 1): aws.ClassCentralRateLimited("429")}
    etl, calls = _aws_etl(monkeypatch, pages)

    assert len(etl.extract()) == 4  # the two Spanish pages; the English listing is left for the next run
    assert len(calls) == 3


def test_extract_fails_when_no_page_could_be_read(monkeypatch):
    etl, _ = _aws_etl(monkeypatch, {("spanish", "created-up", 1): aws.ClassCentralRateLimited("429")})

    with pytest.raises(aws.ClassCentralRateLimited):
        etl.extract()


def test_extract_fails_when_the_first_page_lists_no_course(monkeypatch):
    etl, _ = _aws_etl(monkeypatch, {("spanish", "created-up", 1): "<html>Just a moment...</html>"})

    with pytest.raises(ValueError, match="listed no AWS Skill Builder course"):
        etl.extract()


def test_transform_adds_the_new_courses_to_the_earlier_ones_and_keeps_their_detection_dates(tmp_path):
    previous = [
        {"url": "https://www.classcentral.com/course/course-1", "title": "Introducción a AWS", "language": "es", "first_detected_at": OLD_DETECTED},
        {"url": "https://www.classcentral.com/course/course-old", "title": "A course of an earlier run", "language": "en", "first_detected_at": OLD_DETECTED},
        {"url": "https://www.classcentral.com/course/course-legacy", "title": "AWS SimuLearn: 엣지에서의 ETL", "first_detected_at": OLD_DETECTED},
    ]
    courses_file = tmp_path / "data" / "courses" / "aws_skill_builder.json"
    courses_file.parent.mkdir(parents=True)
    courses_file.write_text(json.dumps(previous), encoding="utf-8")
    etl = aws.AwsSkillBuilderETL(name="aws_test")
    assert etl.courses_file == courses_file
    read = aws.parse_listing(SPANISH_PAGE, "es") + aws.parse_listing(ENGLISH_PAGE, "en")

    records = {record["url"]: record for record in etl.transform(read)}

    assert set(records) == {"https://www.classcentral.com/course/course-1", "https://www.classcentral.com/course/course-2", "https://www.classcentral.com/course/course-3", "https://www.classcentral.com/course/course-old"}  # the Korean one and the legacy record are out
    assert records["https://www.classcentral.com/course/course-1"]["first_detected_at"].startswith("2026-11-20T10:00:00")
    assert records["https://www.classcentral.com/course/course-3"]["first_detected_at"][:4] >= "2026"
    assert {records[url]["language"] for url in records} == {"es", "en"}


def test_description_is_one_readable_line():
    course = aws.parse_listing(_listing(_course(3, "Introduction to Blockchain", ratings=8, average=4.75, free=False, spans=("1 hour 15 minutes", "No Longer Offered"))), "en")[0]

    assert aws.describe(course) == "Beginner · 1 hour 15 minutes · 4.8/5 (8 ratings) · Paid · No longer offered"
    assert aws.describe(dict(course, level=None, duration=None, rating=None, rating_count=0, no_longer_offered=False, is_free=True)) == "Free"


def test_the_models_of_the_two_etls_carry_the_language():
    from src.models.course import AwsSkillBuilderModel, GcpSkillsBoostModel

    assert AwsSkillBuilderModel(title="t", url="https://example.org", language="es").language == "es"
    assert GcpSkillsBoostModel(title="t", url="https://example.org", language="en+es").language == "en+es"
    assert Path(get_settings().project_root).exists()
