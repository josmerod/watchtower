"""Unit tests for the LinkedIn Learning ETL."""

from __future__ import annotations

from src.etl.courses.linkedin_learning_etl import LinkedInLearningETL
from src.models.course import LinkedInLearningCourseModel


def test_transform_validates_course_data() -> None:
    """Transform should produce LinkedInLearningCourseModel from raw dicts."""
    etl = LinkedInLearningETL(max_pages=1)

    transformed = etl.transform(
        [
            {
                "title": "Python Essential Training",
                "url": "https://www.classcentral.com/course/linkedin-learning-python",
                "provider": "LinkedIn Learning",
                "duration": "3h 20m",
                "subject": "Software Development",
                "language": "English",
                "rating": 4.5,
                "is_free": False,
            }
        ]
    )

    assert len(transformed) == 1
    course = transformed[0]
    assert isinstance(course, LinkedInLearningCourseModel)
    assert course.title == "Python Essential Training"
    assert course.provider == "LinkedIn Learning"
    assert course.subject == "Software Development"
    assert course.rating == 4.5


def test_transform_skips_missing_title_or_url() -> None:
    """Courses without title or URL should be silently dropped."""
    etl = LinkedInLearningETL(max_pages=1)

    transformed = etl.transform(
        [
            {"url": "https://example.com/no-title"},
            {"title": "No URL Course"},
            {"title": "Valid", "url": "https://example.com/valid"},
        ]
    )

    assert len(transformed) == 1
    assert transformed[0].title == "Valid"


def test_transform_rejects_bad_rating() -> None:
    """Ratings outside 0-5 should be clamped to None."""
    etl = LinkedInLearningETL(max_pages=1)

    transformed = etl.transform(
        [{"title": "Bad Rating", "url": "https://example.com", "rating": 9.0}]
    )

    assert len(transformed) == 1
    assert transformed[0].rating is None


def test_parse_provider_page_extracts_courses() -> None:
    """_parse_provider_page should extract courses from Class Central HTML."""
    etl = LinkedInLearningETL(max_pages=1)

    html = """
    <html><body>
      <div class="catalog-grid__results">
        <li class="course-list-course">
          <a href="/course/linkedin-learning-python-essential">
            <h2 class="text-1">Python Essential Training</h2>
          </a>
          <a href="/institution/linkedin">LinkedIn Learning</a>
          <p class="text-2">Learn Python from scratch</p>
          <ul>
            <li><i class="icon-clock-charcoal"></i>3h 20m</li>
            <li><i class="icon-calendar-charcoal"></i>Self-Paced</li>
            <li><i class="icon-tag-red"></i>Free</li>
          </ul>
        </li>
      </div>
    </body></html>
    """

    courses = etl._parse_provider_page(html, page_num=1)

    assert len(courses) == 1
    c = courses[0]
    assert c["title"] == "Python Essential Training"
    assert c["url"] == "https://www.classcentral.com/course/linkedin-learning-python-essential"
    assert c["duration"] == "3h 20m"
    assert c["is_free"] is True
    assert "published_date" not in c


def test_parse_filters_non_date_calendar_values() -> None:
    """Non-date calendar text like 'No Longer Offered' should not be published_date."""
    etl = LinkedInLearningETL(max_pages=1)

    html = """
    <html><body>
      <li class="course-list-course">
        <a href="/course/x"><h2 class="text-1">Old Course</h2></a>
        <ul>
          <li><i class="icon-calendar-charcoal"></i>No Longer Offered</li>
        </ul>
      </li>
    </body></html>
    """

    courses = etl._parse_provider_page(html, page_num=1)
    assert len(courses) == 1
    assert "published_date" not in courses[0]


def test_parse_empty_page_returns_empty_list() -> None:
    """Pages with no course elements should return an empty list."""
    etl = LinkedInLearningETL(max_pages=1)

    courses = etl._parse_provider_page("<html><body>No courses here</body></html>", page_num=5)
    assert courses == []


def test_load_creates_output_file(tmp_path) -> None:
    """Load should write JSON with course data."""
    import json

    etl = LinkedInLearningETL(max_pages=1)
    etl.data_dir = tmp_path / "linkedin_learning"
    etl.output_dir = etl.data_dir / "output"
    etl.data_dir.mkdir(parents=True, exist_ok=True)
    etl.output_dir.mkdir(parents=True, exist_ok=True)

    courses = [
        LinkedInLearningCourseModel(title="Course A", url="https://example.com/a"),
        LinkedInLearningCourseModel(title="Course B", url="https://example.com/b"),
    ]

    etl.load(courses)

    output_file = etl.data_dir / "linkedin_learning_courses.json"
    assert output_file.exists()

    data = json.loads(output_file.read_text())
    assert len(data) == 2
    titles = {d["title"] for d in data}
    assert titles == {"Course A", "Course B"}

    last_run = etl.data_dir / "last_run_info.json"
    assert last_run.exists()
    run_info = json.loads(last_run.read_text())
    assert run_info["courses_count"] == 2


def test_load_deduplicates_by_url(tmp_path) -> None:
    """Load should merge with existing data and dedupe by URL."""
    import json

    etl = LinkedInLearningETL(max_pages=1)
    etl.data_dir = tmp_path / "linkedin_learning"
    etl.output_dir = etl.data_dir / "output"
    etl.data_dir.mkdir(parents=True, exist_ok=True)
    etl.output_dir.mkdir(parents=True, exist_ok=True)

    output_file = etl.data_dir / "linkedin_learning_courses.json"
    existing = [
        {"title": "Old Course", "url": "https://example.com/a", "scraped_at": "2020-01-01T00:00:00"},
    ]
    output_file.write_text(json.dumps(existing))

    new_courses = [
        LinkedInLearningCourseModel(title="New Course A", url="https://example.com/a"),
        LinkedInLearningCourseModel(title="Course B", url="https://example.com/b"),
    ]

    etl.load(new_courses)

    data = json.loads(output_file.read_text())
    assert len(data) == 2
    course_a = next(d for d in data if d["url"] == "https://example.com/a")
    assert course_a["title"] == "New Course A"
