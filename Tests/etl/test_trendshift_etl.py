"""Tests for the Trendshift ETL (T-134).

All tests are fixture-based: nothing here touches the network (a real
``requests.get`` fails the test). The pages under ``Tests/etl/fixtures/`` are
the four ranking pages of trendshift.io (daily, weekly, monthly, yearly)
captured on 2026-11-28 and trimmed to five repositories each: the markup, the
encoding of the embedded payload and every kept entry are the pages' own.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from src.constants.etl import SCRAPER_BRANDED_USER_AGENT
from src.etl.github import trendshift_etl as etl
from src.models.github import TrendshiftRepoModel

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PERIODS = ("daily", "weekly", "monthly", "yearly")
SNAPSHOT = datetime(2026, 11, 28, 6, 0, tzinfo=timezone.utc)
SNAPSHOT_TEXT = "2026-11-28T06:00:00Z"

# The rankings of the fixtures: (rank, full name) in page order.
RANKINGS = {
    "daily": [(1, "trustno1-coder/VIctory-NVIDIA"), (5, "openBitFun/OpenBitFun"), (11, "CSJianYang/Industrial-Coder"), (14, "google-gemini/demolab"), (18, "m-bain/whisperX")],
    "weekly": [(1, "ItsNotRexed/Leonida"), (5, "pingdotgg/t3code"), (10, "google-gemini/gemini-api-cli"), (18, "LadybirdBrowser/ladybird"), (20, "firecrawl/firecrawl")],
    "monthly": [(1, "pingdotgg/t3code"), (5, "GoogleChrome/modern-web-guidance"), (18, "D4Vinci/Scrapling"), (20, "anthropics/skills"), (22, "mattpocock/skills")],
    "yearly": [(1, "openclaw/openclaw"), (2, "obra/superpowers"), (8, "multica-ai/andrej-karpathy-skills"), (23, "TauricResearch/TradingAgents"), (24, "anthropics/claude-code")],
}
PERIOD_STARTS = {"daily": "2026-11-28T00:00:00Z", "weekly": "2026-11-23T00:00:00Z", "monthly": "2026-11-01T00:00:00Z", "yearly": "2026-01-01T00:00:00Z"}

_PUSH = "self.__next_f.push([1,"
_DATA = '"initialData":'


def _page(period: str) -> str:
    with open(FIXTURES_DIR / f"trendshift_{period}.html", encoding="utf-8") as f:
        return f.read()


def _entries(period: str = "daily") -> list[dict[str, Any]]:
    return etl.parse_trendshift_page(_page(period))


def _entry(period: str, full_name: str) -> dict[str, Any]:
    return next(entry for entry in _entries(period) if entry["full_name"] == full_name)


def _push_literal(chunk: str) -> str:
    """The payload as the page writes it: a JSON string literal with <, > and & escaped."""
    escaped = json.dumps(chunk, ensure_ascii=False)
    return escaped.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _page_with(entries: list[dict[str, Any]]) -> str:
    """The daily fixture with its ranking replaced by ``entries``."""
    html = _page("daily")
    decoder = json.JSONDecoder()
    start = html.index(_PUSH) + len(_PUSH)
    chunk, end = decoder.raw_decode(html, start)
    at = chunk.index(_DATA) + len(_DATA)
    _, array_end = decoder.raw_decode(chunk, at)
    rebuilt = chunk[:at] + json.dumps(entries, ensure_ascii=False, separators=(",", ":")) + chunk[array_end:]
    return html[:start] + _push_literal(rebuilt) + html[end:]


def _response(body: str = "", status: int = 200, headers: dict[str, str] | None = None) -> Mock:
    """A fake ``requests.Response`` carrying an HTML body."""
    response = Mock()
    response.status_code = status
    response.content = body.encode("utf-8")
    response.headers = headers or {}
    if status >= 500:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status} Server Error")
    else:
        response.raise_for_status.return_value = None
    return response


def _serve(monkeypatch: pytest.MonkeyPatch, *answers: Mock | Exception) -> list[dict[str, Any]]:
    """Make ``requests.get`` answer with ``answers`` in order (the last one repeats); returns the calls."""
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, **kwargs: Any) -> Mock:
        calls.append({"url": url, **kwargs})
        answer = answers[min(len(calls), len(answers)) - 1]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


def _records(period: str) -> list[dict[str, Any]]:
    return etl.build_records(_entries(period), period, snapshot_at=SNAPSHOT)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refused(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("The Trendshift ETL tests never touch the network")

    monkeypatch.setattr(requests, "get", refused)


@pytest.fixture(autouse=True)
def _retry_without_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(etl._get.retry, "sleep", lambda seconds: None)


class TestFlightChunks:
    """The payload of a page: its ``self.__next_f.push`` strings, decoded."""

    @pytest.mark.parametrize("period", PERIODS)
    def test_decodes_the_two_payloads_of_a_page(self, period: str):
        chunks = etl.flight_chunks(_page(period))

        assert len(chunks) == 2
        assert '"initialData":[' in chunks[0]
        assert '"initialMentions":[' in chunks[1]
        assert _DATA not in chunks[1]

    def test_page_without_payload_gives_nothing(self):
        assert etl.flight_chunks("<html><body>Nothing embedded</body></html>") == []

    def test_unreadable_pushes_are_skipped_without_hanging(self):
        html = '<script>self.__next_f.push([1,not json])</script><script>self.__next_f.push([1,42])</script><script>self.__next_f.push([1,"kept"])</script>'

        assert etl.flight_chunks(html) == ["kept"]

    def test_next_escapes_are_undone(self):
        html = r'<script>self.__next_f.push([1,"a\u0026b \"quoted\" \n line &lt; \u003ctag\u003e café"])</script>'

        assert etl.flight_chunks(html) == ['a&b "quoted" \n line &lt; <tag> café']


class TestParseTrendshiftPage:
    """One entry per repository, in rank order, out of the page's ranking."""

    @pytest.mark.parametrize("period", PERIODS)
    def test_each_period_yields_its_repositories_in_rank_order(self, period: str):
        entries = _entries(period)

        assert [(entry["rank"], entry["full_name"]) for entry in entries] == RANKINGS[period]

    def test_entries_keep_what_the_source_says(self):
        first = _entry("daily", "trustno1-coder/VIctory-NVIDIA")

        assert first["repository_stars"] == 3466
        assert first["repository_stars_gained"] == 603
        assert first["repository_forks"] == 116
        assert first["repository_language"] == "Rust"
        assert first["repository_created_at"] == "2026-11-25T23:35:29Z"
        assert first["date"] == "2026-11-28T00:00:00Z"
        assert first["repository_description"].startswith("VIctory (Xbox Series compatibility layer)")

    def test_a_repository_listed_twice_is_kept_once(self):
        entries = _entries("daily")

        parsed = etl.parse_trendshift_page(_page_with([entries[0], entries[1], entries[0]]))

        assert [entry["full_name"] for entry in parsed] == ["trustno1-coder/VIctory-NVIDIA", "openBitFun/OpenBitFun"]

    def test_entries_without_a_usable_name_are_left_out_and_counted(self, caplog: pytest.LogCaptureFixture):
        good = _entries("daily")[0]
        broken = [{**good, "full_name": name} for name in ("no-owner", "owner/", "a/b/c", "ow ner/repo", "/repo")]
        broken += [{"rank": 30}, "a string", None]

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            parsed = etl.parse_trendshift_page(_page_with([good, *broken]))

        assert [entry["full_name"] for entry in parsed] == ["trustno1-coder/VIctory-NVIDIA"]
        # Five names that are not "owner/repo" and one entry without a name; the bare values never reach the count.
        assert "6 trendshift entries without a usable full name" in caplog.text

    def test_the_schema_org_block_is_not_read_as_a_second_ranking(self):
        assert _DATA in "".join(etl.flight_chunks(_page("daily")))
        assert len(_entries("daily")) == 5

    def test_a_page_without_the_ranking_gives_nothing(self):
        assert etl.parse_trendshift_page("<html><body><h1>Moved</h1></body></html>") == []


class TestBuildRecords:
    """The stored record: the ranking's facts, and dates that claim nothing."""

    def test_a_complete_record(self):
        record = _records("daily")[0]

        assert record == {
            "source": "Trendshift",
            "title": "trustno1-coder/VIctory-NVIDIA",
            "full_name": "trustno1-coder/VIctory-NVIDIA",
            "url": "https://github.com/trustno1-coder/VIctory-NVIDIA",
            "description": "VIctory (Xbox Series compatibility layer) made to draw everything on NVIDIA cards: no skipped draws on capped descriptor heaps, Series S interface plane, half-scale Series S at about 20-22 fps on an RTX 5070. Fork of VIctory-7900XTX. No game files.",
            "language": "Rust",
            "stars": 3466,
            "forks": 116,
            "stars_gained": 603,
            "forks_gained": 0,
            "rank": 1,
            "score": 2501,
            "trend_period": "daily",
            "period_starts_at": "2026-11-28T00:00:00Z",
            "tags": [],
            "social_mention_platforms": ["x"],
            "repo_created_at": "2026-11-25T23:35:29Z",
            "trendshift_id": 380324,
            "trendshift_url": "https://trendshift.io/repositories/380324",
            "snapshot_at": SNAPSHOT_TEXT,
            "first_seen": SNAPSHOT_TEXT,
            "platform": "github",
            "content_type": "trending_repo",
        }

    @pytest.mark.parametrize("period", PERIODS)
    def test_every_record_validates_against_the_model(self, period: str):
        records = _records(period)

        assert len(records) == 5
        assert [TrendshiftRepoModel.model_validate(record).model_dump(mode="json") for record in records] == records
        assert [record["rank"] for record in records] == [rank for rank, _ in RANKINGS[period]]
        assert {record["url"] for record in records} == {f"https://github.com/{name}" for _, name in RANKINGS[period]}

    @pytest.mark.parametrize("period", PERIODS)
    def test_no_field_claims_a_publication_date(self, period: str):
        # Keys the dashboard's date chain reads before ``first_seen``: none may be there, or it would win.
        earlier_in_the_chain = {
            "published_at",
            "published",
            "published_date",
            "publication_date",
            "created_at",
            "created_utc",
            "updated_at",
            "updated",
            "time",
            "pubDate",
            "release_date",
            "fetched_at",
            "extracted_at",
            "date",
        }
        for record in _records(period):
            assert sorted(record) == sorted(TrendshiftRepoModel.model_fields)
            assert [key for key in record if key.startswith("published") or key in earlier_in_the_chain] == []
            # What the record dates: the snapshot, the first detection, the period and the repository.
            assert record["snapshot_at"] == SNAPSHOT_TEXT
            assert record["period_starts_at"] == PERIOD_STARTS[period]
            assert record["repo_created_at"] is not None

    def test_snapshot_at_is_the_time_of_the_run(self):
        naive = etl.build_records(_entries("daily"), "daily", snapshot_at=datetime(2026, 11, 28, 6, 0, 0, 987654))
        aware = etl.build_records(_entries("daily"), "daily", snapshot_at=datetime(2026, 11, 28, 7, 0, tzinfo=timezone.utc))

        assert {record["snapshot_at"] for record in naive} == {SNAPSHOT_TEXT}
        assert {record["first_seen"] for record in naive} == {SNAPSHOT_TEXT}
        assert {record["snapshot_at"] for record in aware} == {"2026-11-28T07:00:00Z"}

    def test_first_seen_comes_from_the_previous_file_when_it_has_one(self):
        seen = datetime(2026, 11, 20, 8, 30, tzinfo=timezone.utc)

        records = etl.build_records(_entries("daily"), "daily", snapshot_at=SNAPSHOT, first_seen={"m-bain/whisperX": seen})

        assert records[-1]["first_seen"] == "2026-11-20T08:30:00Z"
        assert {record["first_seen"] for record in records[:-1]} == {SNAPSHOT_TEXT}
        assert records[-1]["snapshot_at"] == SNAPSHOT_TEXT

    def test_what_the_source_leaves_empty_stays_empty(self):
        records = {record["full_name"]: record for record in _records("daily")}

        assert records["CSJianYang/Industrial-Coder"]["description"] == ""
        assert records["google-gemini/demolab"]["language"] == ""
        assert records["m-bain/whisperX"]["stars_gained"] == 63

    def test_values_that_are_not_what_a_field_expects_are_not_invented(self):
        entry = {
            **_entry("daily", "m-bain/whisperX"),
            "repository_stars": "25.9k",
            "rank": None,
            "tags": "speech",
            "social_mention_platforms": None,
            "repository_created_at": "yesterday",
            "repository_id": "2487",
            "repository_description": 42,
        }

        (record,) = etl.build_records([entry], "daily", snapshot_at=SNAPSHOT)

        assert record["stars"] is None
        assert record["rank"] is None
        assert record["tags"] == []
        assert record["social_mention_platforms"] == []
        assert record["repo_created_at"] is None
        assert record["trendshift_id"] is None
        assert record["trendshift_url"] == ""
        assert record["description"] == ""
        assert record["url"] == "https://github.com/m-bain/whisperX"

    def test_language_falls_back_to_the_short_field_and_never_beyond(self):
        (record,) = etl.build_records([{**_entry("daily", "m-bain/whisperX"), "repository_language": " ", "language": " Python "}], "daily", snapshot_at=SNAPSHOT)

        assert record["language"] == "Python"

    def test_tags_are_the_display_names_in_order(self):
        records = {record["full_name"]: record for record in _records("daily")}

        assert records["openBitFun/OpenBitFun"]["tags"] == ["AI agent", "AI coding assistant"]
        assert records["m-bain/whisperX"]["tags"] == ["Speech to text"]
        assert records["m-bain/whisperX"]["social_mention_platforms"] == ["reddit", "x"]
        assert records["CSJianYang/Industrial-Coder"]["social_mention_platforms"] == []

    @pytest.mark.parametrize(("period", "expected"), list(PERIOD_STARTS.items()))
    def test_period_start_is_how_the_source_dates_the_period(self, period: str, expected: str):
        assert {record["period_starts_at"] for record in _records(period)} == {expected}

    def test_period_start_is_empty_when_the_source_gives_no_usable_one(self):
        base = _entry("daily", "m-bain/whisperX")
        daily = {key: value for key, value in base.items() if key != "date"}
        weekly = {**base, "week_start": "not a date"}
        no_year = {key: value for key, value in base.items() if key not in {"year", "month"}}
        odd_month = {**base, "year": 2026, "month": 13}

        assert etl.period_starts_at(daily, "daily") is None
        assert etl.period_starts_at(weekly, "weekly") is None
        assert etl.period_starts_at(no_year, "monthly") is None
        assert etl.period_starts_at(no_year, "yearly") is None
        assert etl.period_starts_at(odd_month, "monthly") is None

    def test_text_keeps_its_non_ascii_characters(self):
        record = _records("yearly")[0]

        assert record["description"] == "The AI that really does things. Any OS. Any Platform. The lobster way. \U0001f99e"


class TestEmptyFieldCounts:
    def test_counts_the_records_that_leave_a_field_empty(self):
        counts = etl.empty_field_counts(_records("daily"))

        assert counts["description"] == 1
        assert counts["language"] == 1
        assert counts["social_mention_platforms"] == 1
        assert counts["tags"] == 1
        assert counts["stars"] == counts["forks"] == counts["stars_gained"] == counts["repo_created_at"] == 0

    def test_watches_own_fields_are_not_counted(self):
        counts = etl.empty_field_counts(_records("daily"))

        assert set(counts) == set(TrendshiftRepoModel.model_fields) - {"source", "title", "full_name", "url", "trend_period", "snapshot_at", "first_seen", "platform", "content_type"}


class TestLoadFirstDetected:
    def test_reads_the_stamps_of_previous_files(self, tmp_path: Path):
        older = tmp_path / "trendshift_weekly_latest.json"
        latest = tmp_path / "trendshift_daily_latest.json"
        older.write_text(json.dumps([{"full_name": "a/first", "first_seen": "2026-11-20T08:30:00Z"}, {"full_name": "a/second", "first_seen": "2026-11-21T08:30:00Z"}]), encoding="utf-8")
        latest.write_text(json.dumps([{"full_name": "a/first", "first_seen": "2026-11-27T08:30:00Z"}, {"full_name": "a/third", "first_seen": "not a date"}, "junk"]), encoding="utf-8")

        stamps = etl.load_first_seen([latest, older])

        assert stamps == {"a/first": datetime(2026, 11, 27, 8, 30, tzinfo=timezone.utc), "a/second": datetime(2026, 11, 21, 8, 30, tzinfo=timezone.utc)}

    def test_a_missing_file_contributes_nothing(self, tmp_path: Path):
        assert etl.load_first_seen([tmp_path / "trendshift_daily_latest.json"]) == {}

    def test_a_broken_file_contributes_nothing_but_warns(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        broken = tmp_path / "trendshift_daily_latest.json"
        broken.write_text("{not json", encoding="utf-8")
        odd = tmp_path / "trendshift_weekly_latest.json"
        odd.write_text(json.dumps({"records": []}), encoding="utf-8")

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            assert etl.load_first_seen([broken, odd]) == {}

        assert "Could not read trendshift_daily_latest.json to keep the first-seen dates" in caplog.text
        assert "trendshift_weekly_latest.json is not a list of records" in caplog.text


class TestSaveTrendshift:
    def test_writes_a_snapshot_and_the_latest_copy(self, tmp_path: Path):
        records = _records("daily")

        latest = etl.save_trendshift(records, "daily", tmp_path, now=SNAPSHOT)

        assert latest == tmp_path / "trendshift_daily_latest.json"
        snapshot = tmp_path / "trendshift_daily_20261128_060000.json"
        assert sorted(path.name for path in tmp_path.iterdir()) == [snapshot.name, latest.name]
        assert json.loads(latest.read_text(encoding="utf-8")) == records
        assert snapshot.read_text(encoding="utf-8") == latest.read_text(encoding="utf-8")
        assert not list(tmp_path.glob("*.tmp"))

    def test_keeps_non_ascii_text_readable(self, tmp_path: Path):
        etl.save_trendshift(_records("yearly"), "yearly", tmp_path, now=SNAPSHOT)

        assert "The lobster way. \U0001f99e" in (tmp_path / "trendshift_yearly_latest.json").read_text(encoding="utf-8")

    def test_writes_under_data_github_by_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))

        latest = etl.save_trendshift(_records("daily"), "daily")

        assert latest == tmp_path / "data" / "github" / "trendshift_daily_latest.json"
        assert latest.exists()


class TestBlockedReason:
    """Answers that are not the page asked for."""

    def test_the_page_asked_for(self):
        assert etl.blocked_reason(_response(_page("daily"))) is None

    def test_cloudflare_challenge_by_header(self):
        response = _response("<html><body>Verifying you are human</body></html>", status=403, headers={"cf-mitigated": "challenge"})

        assert etl.blocked_reason(response) == "HTTP 403, Cloudflare challenge"

    def test_cloudflare_challenge_by_title(self):
        response = _response("<html><head><title>Just a moment...</title></head></html>", status=403)

        assert etl.blocked_reason(response) == "HTTP 403, Cloudflare challenge"

    def test_rate_limited_and_other_errors(self):
        assert etl.blocked_reason(_response(status=429)) == "HTTP 429, rate limited"
        assert etl.blocked_reason(_response(status=404)) == "HTTP 404"
        assert etl.blocked_reason(_response(status=500)) == "HTTP 500"


class TestFetchTrendshiftPeriod:
    """One polite GET per period, and no retry on a refusal."""

    def test_asks_for_the_page_with_the_branded_user_agent(self, monkeypatch: pytest.MonkeyPatch):
        calls = _serve(monkeypatch, _response(_page("daily")))

        assert len(etl.fetch_trendshift_period("daily")) == 5
        assert calls == [{"url": "https://trendshift.io/", "headers": {"User-Agent": SCRAPER_BRANDED_USER_AGENT}, "timeout": etl.REQUEST_TIMEOUT_SECONDS}]

    def test_asks_for_the_path_of_each_period(self, monkeypatch: pytest.MonkeyPatch):
        calls = _serve(monkeypatch, _response(_page("weekly")))

        etl.fetch_trendshift_period("weekly")

        assert calls[0]["url"] == "https://trendshift.io/weekly"
        assert etl.TRENDSHIFT_PERIOD_PATHS == {"daily": "/", "weekly": "/weekly", "monthly": "/monthly", "yearly": "/yearly"}

    def test_a_cloudflare_challenge_is_not_retried(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
        challenge = _response("<html><head><title>Just a moment...</title></head><body>Verifying</body></html>", status=403, headers={"cf-mitigated": "challenge", "Server": "cloudflare"})
        calls = _serve(monkeypatch, challenge)

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            assert etl.fetch_trendshift_period("daily") is None

        assert len(calls) == 1
        assert "trendshift.io did not answer the daily ranking (HTTP 403, Cloudflare challenge); not retrying this run" in caplog.text

    def test_rate_limited_and_missing_are_not_retried(self, monkeypatch: pytest.MonkeyPatch):
        calls = _serve(monkeypatch, _response(status=429))

        assert etl.fetch_trendshift_period("daily") is None
        assert len(calls) == 1

        calls = _serve(monkeypatch, _response(status=404))
        assert etl.fetch_trendshift_period("daily") is None
        assert len(calls) == 1

    def test_a_server_error_is_retried_then_reported(self, monkeypatch: pytest.MonkeyPatch):
        calls = _serve(monkeypatch, _response("Internal Server Error", status=503))

        assert etl.fetch_trendshift_period("daily") is None
        assert len(calls) == 4

    def test_a_network_error_is_retried_then_reported(self, monkeypatch: pytest.MonkeyPatch):
        calls = _serve(monkeypatch, requests.ConnectionError("Name or service not known"))

        assert etl.fetch_trendshift_period("daily") is None
        assert len(calls) == 4

    def test_a_page_that_lost_its_ranking_is_nothing_usable(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
        _serve(monkeypatch, _response("<html><body><h1>Trendshift</h1>A redesigned page</body></html>"))

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            entries = etl.fetch_trendshift_period("daily")

        assert entries == []
        assert "carries no repository list: the page changed or is blocked" in caplog.text


class TestRun:
    """A whole run against the saved pages."""

    def test_writes_one_snapshot_and_the_latest_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _serve(monkeypatch, _response(_page("daily")))

        assert etl.run(now=SNAPSHOT, output_dir=tmp_path) == {"daily": 5}
        latest = tmp_path / "trendshift_daily_latest.json"
        assert sorted(path.name for path in tmp_path.iterdir()) == ["trendshift_daily_20261128_060000.json", latest.name]
        records = json.loads(latest.read_text(encoding="utf-8"))
        assert [(record["rank"], record["full_name"]) for record in records] == RANKINGS["daily"]
        assert {record["snapshot_at"] for record in records} == {SNAPSHOT_TEXT}

    def test_only_the_daily_ranking_is_fetched_by_default(self):
        assert etl.FETCH_PERIODS == ("daily",)

    def test_first_seen_survives_the_next_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        newcomer = {**_entry("daily", "m-bain/whisperX"), "rank": 18, "full_name": "owner/newcomer"}
        second = SNAPSHOT.replace(hour=8)
        _serve(monkeypatch, _response(_page("daily")), _response(_page_with(_entries("daily")[:-1] + [newcomer])))

        etl.run(now=SNAPSHOT, output_dir=tmp_path)
        etl.run(now=second, output_dir=tmp_path)

        latest = tmp_path / "trendshift_daily_latest.json"
        records = {record["full_name"]: record for record in json.loads(latest.read_text(encoding="utf-8"))}
        assert "m-bain/whisperX" not in records
        assert {record["snapshot_at"] for record in records.values()} == {"2026-11-28T08:00:00Z"}
        assert {record["first_seen"] for record in records.values()} == {SNAPSHOT_TEXT, "2026-11-28T08:00:00Z"}
        assert records["owner/newcomer"]["first_seen"] == "2026-11-28T08:00:00Z"
        assert records["trustno1-coder/VIctory-NVIDIA"]["first_seen"] == SNAPSHOT_TEXT
        # Every run leaves its own snapshot behind.
        assert sorted(path.name for path in tmp_path.glob("trendshift_daily_2026*.json")) == ["trendshift_daily_20261128_060000.json", "trendshift_daily_20261128_080000.json"]

    def test_a_repository_that_leaves_and_returns_is_dated_anew(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        later = SNAPSHOT.replace(hour=8)
        again = SNAPSHOT.replace(hour=10)
        _serve(monkeypatch, _response(_page("daily")), _response(_page_with(_entries("daily")[:-1])), _response(_page("daily")))

        for now in (SNAPSHOT, later, again):
            etl.run(now=now, output_dir=tmp_path)

        records = {record["full_name"]: record for record in json.loads((tmp_path / "trendshift_daily_latest.json").read_text(encoding="utf-8"))}

        assert records["m-bain/whisperX"]["first_seen"] == "2026-11-28T10:00:00Z"
        assert records["trustno1-coder/VIctory-NVIDIA"]["first_seen"] == SNAPSHOT_TEXT

    def test_nothing_usable_keeps_the_last_good_file_and_exits_cleanly(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        challenge = _response("<html><head><title>Just a moment...</title></head></html>", status=403, headers={"cf-mitigated": "challenge"})
        _serve(monkeypatch, _response(_page("daily")), challenge)
        etl.run(now=SNAPSHOT, output_dir=tmp_path / "data" / "github")
        latest = tmp_path / "data" / "github" / "trendshift_daily_latest.json"
        good, good_mtime = latest.read_bytes(), latest.stat().st_mtime_ns

        assert etl.run() == {"daily": 0}
        etl.main()
        etl.main()

        assert latest.read_bytes() == good
        assert latest.stat().st_mtime_ns == good_mtime
        assert sorted(path.name for path in latest.parent.iterdir()) == ["trendshift_daily_20261128_060000.json", latest.name]

    def test_a_blocked_run_warns(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
        _serve(monkeypatch, _response(status=429))

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            etl.run(now=SNAPSHOT, output_dir=tmp_path)

        assert "HTTP 429, rate limited" in caplog.text
        assert "trendshift_daily_latest.json is left as it was" in caplog.text
        assert list(tmp_path.iterdir()) == []

    def test_each_period_is_fetched_and_saved_apart(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        sleeps: list[float] = []
        monkeypatch.setattr(etl.time, "sleep", sleeps.append)
        calls = _serve(monkeypatch, _response(_page("daily")), _response(_page("yearly")))

        written = etl.run(now=SNAPSHOT, periods=("daily", "yearly"), output_dir=tmp_path)

        assert written == {"daily": 5, "yearly": 5}
        assert [call["url"] for call in calls] == ["https://trendshift.io/", "https://trendshift.io/yearly"]
        assert sleeps == [etl.REQUEST_DELAY_SECONDS]
        assert sorted(path.name for path in tmp_path.iterdir()) == [
            "trendshift_daily_20261128_060000.json",
            "trendshift_daily_latest.json",
            "trendshift_yearly_20261128_060000.json",
            "trendshift_yearly_latest.json",
        ]

    def test_the_run_logs_how_full_each_field_is(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
        _serve(monkeypatch, _response(_page("daily")))

        with caplog.at_level(logging.INFO, logger=etl.logger.name):
            etl.run(now=SNAPSHOT, output_dir=tmp_path)

        assert (
            "trendshift.io daily: 5 repositories. Filled per field: description 4/5, language 4/5, stars 5/5, forks 5/5, stars_gained 5/5, forks_gained 5/5, rank 5/5, score 5/5, period_starts_at 5/5, tags 4/5, social_mention_platforms 4/5, repo_created_at 5/5, trendshift_id 5/5, trendshift_url 5/5"
            in caplog.text
        )


class TestMain:
    def test_an_unexpected_error_is_logged_and_raised(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
        def boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("disk full")

        monkeypatch.setattr(etl, "run", boom)

        with caplog.at_level(logging.ERROR, logger=etl.logger.name), pytest.raises(RuntimeError, match="disk full"):
            etl.main()

        assert "Trendshift ETL failed: disk full" in caplog.text


class TestWiring:
    """What production needs so the ranking runs, is read and does not go stale unseen."""

    def test_the_orchestrator_runs_the_etl_once(self):
        import sys

        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root)) if str(repo_root) not in sys.path else None
        import run_all_etl_orchestrator as orchestrator

        assert orchestrator.ETL_SCRIPTS.count("src/etl/github/trendshift_etl.py") == 1

    def test_the_dashboard_reads_the_file_the_etl_writes(self):
        from src.services.data_loader import KNOWLEDGE_SOURCES_CONFIG

        source = KNOWLEDGE_SOURCES_CONFIG["trendshift"]

        assert source["name"] == "Trendshift"
        assert etl.latest_path(Path(source["path"]).parent, "daily") == Path(source["path"])
        assert etl.FETCH_PERIODS == ("daily",)

    def test_the_freshness_watcher_dates_the_file_by_its_snapshot(self, tmp_path: Path):
        from src.watchers.data_freshness_watcher import SOURCE_FILES, newest_item_epoch

        (entry,) = [source for source in SOURCE_FILES if source["key"] == "trendshift"]

        assert entry["path"] == "github/trendshift_daily_latest.json"
        assert (entry["warn_hours"], entry["critical_hours"]) == (26, 168)
        assert entry["content_date"] in TrendshiftRepoModel.model_fields
        # A stored file answers the question with the time of its snapshot.
        stored = tmp_path / entry["path"]
        stored.parent.mkdir(parents=True)
        stored.write_text(json.dumps(_records("daily")), encoding="utf-8")

        assert newest_item_epoch(stored, entry["content_date"]) == SNAPSHOT.timestamp()

    def test_the_api_lists_the_source(self):
        from fastapi.testclient import TestClient

        from src.api.main import app

        response = TestClient(app).get("/api/v1/sources")

        assert response.status_code == 200
        assert response.json()["knowledge_garden"]["trendshift"] == "Trendshift"
