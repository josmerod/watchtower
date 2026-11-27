"""FIRST DETECTED is shown in Madrid time (T-185).

The cloud course ETLs stamp ``first_detected_at`` in UTC. The loaders used to drop the zone without moving the
hour: a course found at 13:20 CET read 12:20, and one found after 23:00 CET got the day before. Fixtures only:
the loaders read a file written under tmp_path, never data/.
"""

import json

import pandas as pd
import pytest

from src.web.dashboard.components import courses_tab

# Late in UTC, already the next day in Spain (winter time, UTC+1).
LATE = "2026-11-26T23:30:00+00:00"
MIDDAY = "2026-11-27T12:20:00+00:00"


def _catalog(*stamps):
    return pd.DataFrame({"title": [f"Course {index}" for index in range(len(stamps))], "url": "https://example.invalid/course", "first_detected_at": list(stamps)})


def test_gcp_shows_the_madrid_hour_and_day():
    frame = courses_tab._sort_by_first_detected(_catalog(LATE, MIDDAY), with_time=True)

    assert frame["title"].tolist() == ["Course 1", "Course 0"]  # newest first
    assert frame["detected_str"].tolist() == ["2026-11-27 13:20", "2026-11-27 00:30"]


def test_the_day_only_catalogs_give_the_madrid_day():
    frame = courses_tab._sort_by_first_detected(_catalog("2026-11-26T22:30:00+00:00", LATE))

    assert frame["detected_str"].tolist() == ["2026-11-27", "2026-11-26"]


def test_summer_time_is_two_hours_ahead():
    frame = courses_tab._sort_by_first_detected(_catalog("2026-07-26T23:30:00+00:00"), with_time=True)

    assert frame["detected_str"].tolist() == ["2026-07-27 01:30"]


def test_a_stamp_without_a_zone_is_read_as_utc():
    """The loaders used to raise on it, which left the subtab without a table."""
    frame = courses_tab._sort_by_first_detected(_catalog("2026-11-26T23:30:00"), with_time=True)

    assert frame["detected_str"].tolist() == ["2026-11-27 00:30"]


def test_a_catalog_without_stamps_says_so():
    frame = courses_tab._sort_by_first_detected(pd.DataFrame({"title": ["Course 0"]}))

    assert frame["detected_str"].tolist() == ["N/A"]


@pytest.mark.parametrize(
    ("loader", "path_name", "key", "expected"),
    [
        (courses_tab.load_ms_applied_skills_data, "MS_APPLIED_SKILLS_DATA_PATH", "ms_skills", ["2026-11-27", "2026-11-27"]),
        (courses_tab.load_aws_skill_builder_data, "AWS_SKILL_BUILDER_DATA_PATH", "aws_skills", ["2026-11-27", "2026-11-27"]),
        (courses_tab.load_gcp_skills_boost_data, "GCP_SKILLS_BOOST_DATA_PATH", "gcp_skills", ["2026-11-27 13:20", "2026-11-27 00:30"]),
    ],
)
def test_each_cloud_loader_shows_the_madrid_time(monkeypatch: pytest.MonkeyPatch, tmp_path, loader, path_name, key, expected) -> None:
    """What the three loaders hand to their tables, from a file shaped like the ETL's output."""
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps([{"title": "Found late", "url": "https://example.invalid/1", "first_detected_at": LATE}, {"title": "Found at midday", "url": "https://example.invalid/2", "first_detected_at": MIDDAY}]), encoding="utf-8")
    monkeypatch.setattr(courses_tab, path_name, str(path))
    monkeypatch.setattr(courses_tab, "ALL_COURSES_DATA", {})
    monkeypatch.setattr(courses_tab, "COURSES_DATA_LOADED", {})

    loader()

    assert courses_tab.ALL_COURSES_DATA[key]["title"].tolist() == ["Found at midday", "Found late"]
    assert courses_tab.ALL_COURSES_DATA[key]["detected_str"].tolist() == expected
