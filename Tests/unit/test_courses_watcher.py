"""Unit tests for the Courses Watcher (T-066)."""

import json
import re

from src.watchers.courses_watcher import COURSE_SOURCES, KEYWORDS, CoursesWatcher, assess_new_courses, load_catalogs

# Synthetic Hugging Face catalog shaped like the real hf_learn.json output
# (titles deliberately free of every KEYWORD substring except where intended).
HF_V1 = [
    {"title": "Deep Learning course", "url": "https://huggingface.co/learn/deep-learning-course"},
    {"title": "Natural Language Processing", "url": "https://huggingface.co/learn/nlp-course"},
]
MATCHING_NEW = {"title": "Building LLM Agents with MCP", "url": "https://huggingface.co/learn/llm-agents-mcp"}
NON_MATCHING_NEW = {"title": "Woodworking for Beginners", "url": "https://huggingface.co/learn/woodworking"}


def test_first_run_is_baseline_without_events():
    result = assess_new_courses(None, {"hf_learn": list(HF_V1)})
    assert result["first_run"] is True
    assert result["new_matching_courses"] == []
    assert result["state"]["providers"]["hf_learn"] == {"label": "Hugging Face", "status": "ok", "count": 2}
    assert result["state"]["keywords"] == list(KEYWORDS)
    assert result["state"]["last_check"]


def test_new_matching_course_emits_exactly_one_event():
    result = assess_new_courses({"hf_learn": list(HF_V1)}, {"hf_learn": [*HF_V1, MATCHING_NEW]})
    assert result["first_run"] is False
    assert len(result["new_matching_courses"]) == 1
    event = result["new_matching_courses"][0]
    assert event["provider"] == "Hugging Face"
    assert event["provider_key"] == "hf_learn"
    assert event["title"] == "Building LLM Agents with MCP"
    assert event["url"] == "https://huggingface.co/learn/llm-agents-mcp"
    assert event["matched_keywords"] == ["llm", "agent", "mcp"]
    assert event["message"] == "nuevo curso de Hugging Face que matchea keywords llm, agent, mcp"
    assert result["state"]["providers"]["hf_learn"]["count"] == 3


def test_new_course_not_matching_keywords_no_event_but_counted():
    result = assess_new_courses({"hf_learn": list(HF_V1)}, {"hf_learn": [*HF_V1, NON_MATCHING_NEW]})
    assert result["new_matching_courses"] == []
    assert result["state"]["providers"]["hf_learn"]["count"] == 3


def test_identity_is_url_not_title():
    renamed = {"title": "RENAMED TITLE", "url": HF_V1[0]["url"]}
    result = assess_new_courses({"hf_learn": list(HF_V1)}, {"hf_learn": [HF_V1[1], renamed]})
    assert result["new_matching_courses"] == []  # same URL => same course even if the title was re-worded


def test_title_fallback_identity_when_url_missing():
    previous = {"hf_learn": [{"title": "Agents Course", "url": ""}]}
    current = {"hf_learn": [{"title": "  agents   course  ", "url": None}]}
    result = assess_new_courses(previous, current)
    assert result["new_matching_courses"] == []  # normalized-title fallback: same course
    assert result["state"]["providers"]["hf_learn"]["count"] == 1


def test_missing_provider_skipped_and_noted_in_state():
    result = assess_new_courses({"hf_learn": list(HF_V1)}, {"ms_applied_skills": [{"title": "LLM course", "url": "https://learn.microsoft.com/x"}]})
    providers = result["state"]["providers"]
    assert providers["hf_learn"] == {"label": "Hugging Face", "status": "missing", "count": None}
    assert providers["ms_applied_skills"] == {"label": "Microsoft Learn", "status": "ok", "count": 1}
    assert result["new_matching_courses"] == []  # provider absent from the previous snapshot => re-baseline


def test_provider_returning_after_missing_does_not_flood_events():
    # hf_learn was missing on the previous run (absent from the snapshot); even a
    # keyword-matching course in the returning catalog must not emit events.
    previous = {"ms_applied_skills": [{"title": "Existing", "url": "https://learn.microsoft.com/x"}]}
    current = {"ms_applied_skills": [{"title": "Existing", "url": "https://learn.microsoft.com/x"}], "hf_learn": [*HF_V1, MATCHING_NEW]}
    result = assess_new_courses(previous, current)
    assert result["new_matching_courses"] == []
    assert result["state"]["providers"]["hf_learn"] == {"label": "Hugging Face", "status": "ok", "count": 3}


def test_load_catalogs_skips_missing_malformed_and_empty(tmp_path):
    courses_dir = tmp_path / "courses"
    courses_dir.mkdir(parents=True)
    (courses_dir / "hf_learn.json").write_text(json.dumps([*HF_V1, "junk-entry"]), encoding="utf-8")  # non-dict entries filtered
    (courses_dir / "aws_skill_builder.json").write_text("{ not json", encoding="utf-8")  # malformed
    (courses_dir / "gcp_skills_boost.json").write_text("[]", encoding="utf-8")  # empty
    (courses_dir / "ms_applied_skills.json").write_text("{}", encoding="utf-8")  # not a list
    # udemy/udemy_courses.json simply absent

    catalogs, missing = load_catalogs(tmp_path)
    assert set(catalogs) == {"hf_learn"}
    assert catalogs["hf_learn"] == HF_V1
    assert set(missing) == set(COURSE_SOURCES) - {"hf_learn"}


def test_courses_watcher_end_to_end(tmp_path, monkeypatch):
    """Integration-style: watcher against tmp_path, two checks, event files on disk."""
    # Keep BaseWatcher fully hermetic: redirect its project root and neutralize
    # directory creation so nothing touches the real data/ dir.
    monkeypatch.setattr("src.watchers.base_watcher.get_project_root", lambda: str(tmp_path))
    monkeypatch.setattr("src.watchers.base_watcher.ensure_directories", lambda dirs: None)

    data_root = tmp_path / "data"
    courses_dir = data_root / "courses"
    courses_dir.mkdir(parents=True)
    hf_file = courses_dir / "hf_learn.json"
    hf_file.write_text(json.dumps(HF_V1), encoding="utf-8")

    watcher = CoursesWatcher()
    first = watcher.check_courses(data_dir=data_root)
    assert first["first_run"] is True
    assert first["new_matching_courses"] == []
    assert list(watcher.events_dir.glob("*.json")) == []
    assert watcher.state_file.exists()
    state = json.loads(watcher.state_file.read_text(encoding="utf-8"))
    assert state["providers"]["hf_learn"] == {"label": "Hugging Face", "status": "ok", "count": 2}
    assert state["providers"]["udemy"] == {"label": "Udemy", "status": "missing", "count": None}
    assert watcher.catalogs_file.exists()

    hf_file.write_text(json.dumps([*HF_V1, MATCHING_NEW]), encoding="utf-8")
    second = watcher.check_courses(data_dir=data_root)
    assert len(second["new_matching_courses"]) == 1

    events = list(watcher.events_dir.glob("*_new_matching_course*.json"))
    assert len(events) == 1
    assert re.fullmatch(r"\d{14}_new_matching_course_\d{3}\.json", events[0].name)
    payload = json.loads(events[0].read_text(encoding="utf-8"))
    assert payload["type"] == "new_matching_course"
    assert payload["watcher"] == "courses"
    assert payload["new_value"] == "Building LLM Agents with MCP"
    assert payload["details"]["message"] == "nuevo curso de Hugging Face que matchea keywords llm, agent, mcp"
    assert payload["details"]["provider"] == "Hugging Face"
    assert payload["details"]["url"] == "https://huggingface.co/learn/llm-agents-mcp"
    assert payload["details"]["matched_keywords"] == ["llm", "agent", "mcp"]

    state = json.loads(watcher.state_file.read_text(encoding="utf-8"))
    assert state["providers"]["hf_learn"]["count"] == 3
