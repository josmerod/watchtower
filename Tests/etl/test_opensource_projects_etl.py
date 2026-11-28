"""opensourceprojects.dev, one record per repository (T-204).

Covers the four parsers, the walk of the listing, the merge into ``latest.json`` and the two
completion steps (post page, GitHub). Every payload is a trimmed copy of what the site served
on 2026-11-28 (``Tests/etl/fixtures/opensource_*``); no test touches the network.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

from src.config.settings import get_settings
from src.etl.opensource import opensource_projects_etl as m
from src.etl.opensource.opensource_projects_etl import BASE_URL, FEED_URL, GITHUB_API, RSS_URL, OpenSourceProjectsETL
from src.exceptions.etl import ETLError
from src.models.opensource_model import OpenSourceProjectItem
from src.watchers.data_freshness_watcher import newest_item_epoch

FIXTURES = Path(__file__).parent / "fixtures"
TRILIUM = "https://github.com/triliumnext/trilium"
MYGO = "https://github.com/egoist/mygo"

# The same card the listing serves, with the classes the parser reads.
CARD = """<article class="project-card postcard-card bento-sm"><div class="postcard-tags"><span class="postcard-tag boxed">{tag}</span><span class="postcard-tag plain">Open Source</span></div>
<div class="card-content"><h3 class="card-title postcard-title"><a href="/post/{slug}">{title}</a></h3><p class="card-excerpt postcard-excerpt">By @<!-- -->githubprojects<!-- --> — <!-- -->{title}</p></div>
<div class="card-footer postcard-footer"><a href="{url}" class="postcard-repo-link"><span>↳</span><span>{name}</span></a><div class="postcard-meta-line"><span>@<!-- -->githubprojects<!-- --></span><span>·</span><span>OSS</span><span>·</span><time datetime="{date}">{date}</time></div></div>
<div class="postcard-actions"><div title="{views} views" class="postcard-impressions-stamp"><span>Views</span><strong>{views}</strong></div></div></div></article>"""

OPENING = "The opening of the article. It says what the project does and why it matters."


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def listing(*repos: dict) -> str:
    """A listing page holding the given repositories, plus the sponsored slot."""
    sponsor = '<article class="project-card sponsor-card"><h3 class="card-title sponsor-title"><a href="/sponsor-us">Showcase Your Project Here</a></h3></article>'
    cards = "".join(CARD.format(tag="CLI", views="7", **repo) for repo in repos)
    return f"<html><body><div>{sponsor}{cards}</div></body></html>"


def post_page(url: str, title: str, opening: str = OPENING, date: str | None = None) -> str:
    """A post page: the repository link with tracking parameters, the date, the views, the article."""
    moment = f'<time class="project-date" datetime="{date}">x</time>' if date else ""
    return (
        '<html><body><nav><a href="/">Home</a></nav><main><div class="project-hero"><div class="project-meta">'
        f'{moment}<span class="project-impressions"><span class="impressions-value">31</span></span></div></div>'
        f'<article class="project-article"><div class="article-actions"><a class="github-repo-link" href="{url}?utm_source=x&amp;ref=y">View on GitHub</a></div>'
        f'<div class="markdown-content"><h1 class="markdown-h1">{title}</h1><p class="markdown-paragraph">{opening}</p><h2 class="markdown-h2">What it does</h2><p class="markdown-paragraph">The second paragraph.</p></div></article></main></body></html>'
    )


def repo(owner: str, name: str, date: str, title: str | None = None) -> dict:
    """What a card needs: a repository posted on a date (the site's clock, no zone)."""
    return {"owner": owner, "name": name, "slug": f"{owner}-{name}", "url": f"https://github.com/{owner}/{name}", "date": date, "title": title or f"{owner}/{name}"}


def post_url(repo: dict) -> str:
    return f"https://www.opensourceprojects.dev/post/{repo['slug']}"


class FakeResponse:
    def __init__(self, status_code: int = 200, headers: dict | None = None, payload: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("no body")
        return self._payload


class FakeWeb:
    """Pages of opensourceprojects.dev and answers of GitHub, by URL; every request is recorded in order.

    A listing page nobody defined is empty (the walk ends there); a post page nobody
    defined carries ``OPENING`` and no date.
    """

    def __init__(self):
        self.pages: dict[str, str | Exception] = {}
        self.down: set[str] = set()
        self.github: dict[str, FakeResponse] = {}
        self.remaining: list[int] = []
        self.requests: list[str] = []

    def install(self, etl: OpenSourceProjectsETL, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(etl, "_get", self.page)
        monkeypatch.setattr(etl, "_github_request", self.github_answer)
        etl.listing_delay_seconds = 0

    def page(self, url: str) -> str:
        self.requests.append(url)
        if url in self.down:
            raise requests.ConnectionError(f"{url} did not answer")
        if url in self.pages:
            page = self.pages[url]
            if isinstance(page, Exception):
                raise page
            return page
        if "/post/" in url:
            return post_page(url, url.rsplit("/", 1)[-1])
        if url == BASE_URL or url.startswith(f"{BASE_URL}/?page="):
            return "<html><body></body></html>"
        raise AssertionError(f"no page for {url}")

    def github_answer(self, url: str) -> FakeResponse:
        owner, name = url.rstrip("/").rsplit("/", 2)[-2:]
        api = f"{GITHUB_API}/{owner}/{name}"
        self.requests.append(api)
        if api in self.github:
            return self.github[api]
        remaining = self.remaining.pop(0) if self.remaining else 59
        return FakeResponse(
            200,
            {"X-RateLimit-Remaining": str(remaining)},
            {
                "full_name": f"{owner}/{name}",
                "description": f"  What {name} does,\n in one line.  ",
                "stargazers_count": 1200,
                "forks_count": 34,
                "language": "Go",
                "topics": ["cli", 7, "tools"],
                "pushed_at": "2026-11-20T10:00:00Z",
            },
        )

    def asked_github(self) -> list[str]:
        return [url for url in self.requests if url.startswith(GITHUB_API)]

    def asked_listing(self) -> list[str]:
        return [url for url in self.requests if url == BASE_URL or url.startswith(f"{BASE_URL}/?page=")]


@pytest.fixture()
def etl(tmp_path, monkeypatch) -> OpenSourceProjectsETL:
    """The ETL with its files under pytest's tmp_path (BaseETL resolves every path from the cached settings)."""
    monkeypatch.setattr(get_settings(), "project_root", str(tmp_path))
    instance = OpenSourceProjectsETL(max_retries=0)
    instance.github_token = None
    return instance


def checked_now() -> str:
    return datetime.utcnow().isoformat(sep=" ")


def stored_record(owner: str, name: str, date: str, **extra) -> dict:
    """A record as the runs before T-204 wrote it: the description repeats the title, GitHub was never asked."""
    record = {
        "id": f"id-{owner}-{name}",
        "created_at": "2026-01-10 08:00:00",
        "updated_at": "2026-01-10 08:00:00",
        "title": f"{owner}/{name}",
        "description": f"{owner}/{name}",
        "url": f"https://github.com/{owner}/{name}",
        "source": "opensourceprojects.dev",
        "tags": [],
        "published_at": date,
    }
    return {**record, **extra}


def stored(etl: OpenSourceProjectsETL, *records: dict) -> None:
    """Write what a previous run left in latest.json."""
    etl.output_dir.mkdir(parents=True, exist_ok=True)
    (etl.output_dir / "latest.json").write_text(json.dumps(records, default=str), encoding="utf-8")


def latest(etl: OpenSourceProjectsETL) -> list[dict]:
    return json.loads((etl.output_dir / "latest.json").read_text(encoding="utf-8"))


# --- keys and URLs -------------------------------------------------------------------------
def test_normalize_repo_url_spells_a_repository_one_way():
    assert m.normalize_repo_url("https://github.com/TriliumNext/Trilium") == "github.com/triliumnext/trilium"
    assert m.normalize_repo_url("https://github.com/triliumnext/trilium/") == "github.com/triliumnext/trilium"
    assert m.normalize_repo_url("https://github.com/a/b.git") == "github.com/a/b"
    assert m.normalize_repo_url("https://github.com/a/b/issues/1?utm_source=x#y") == "github.com/a/b"
    assert m.normalize_repo_url("https://GitLab.com/A/B") == "gitlab.com/a/b"
    assert m.normalize_repo_url("https://www.google.com/x") == "www.google.com/x"
    assert m.normalize_repo_url("https://www.google.com") == "www.google.com/"
    assert m.normalize_repo_url("") == ""
    assert m.normalize_repo_url(None) == ""


def test_clean_repo_url_keeps_scheme_host_and_path_only():
    assert m.clean_repo_url("https://github.com/a/b/issues/1?utm_source=x#y") == "https://github.com/a/b/issues/1"
    assert m.clean_repo_url("https://github.com/a/b/") == "https://github.com/a/b"
    assert m.clean_repo_url("javascript:alert(1)") is None
    assert m.clean_repo_url("") is None


SEARCH_LINK = "https://www.google.com/search?q=https://github.com/jxroot/nahpet"


def test_a_link_to_a_web_search_stands_for_the_repository_it_searched_for():
    """Two records written before T-204 kept the site's "search for it" link instead of the repository."""
    assert m.normalize_repo_url(SEARCH_LINK) == "github.com/jxroot/nahpet"
    assert m.clean_repo_url(SEARCH_LINK) == "https://github.com/jxroot/nahpet"
    assert m.repository_of_search(SEARCH_LINK) == "https://github.com/jxroot/nahpet"
    assert m.repository_of_search("https://github.com/a/b") is None
    assert m.repository_of_search("https://www.google.com/search?q=nahpet") is None
    assert m.repository_of_search(None) is None


# --- parsers -------------------------------------------------------------------------------
class TestParseFeed:
    def test_atom_entries_carry_article_repository_post_and_date(self):
        items = m.parse_feed(fixture("opensource_feed.xml"))

        assert [item["url"] for item in items] == [TRILIUM, MYGO]
        assert items[0]["title"] == "A hierarchical note-taking app for building large personal knowledge bases"
        assert items[0]["post_url"] == "https://www.opensourceprojects.dev/post/trilium"
        # The feed's clock is UTC and says so.
        assert items[0]["published_at"] == datetime(2026, 11, 28, 1, 50, 2, tzinfo=timezone.utc)
        assert items[1]["published_at"] == datetime(2026, 11, 28, 1, 49, 39, tzinfo=timezone.utc)
        assert items[0]["detail_fetched"] is True

    def test_excerpt_is_the_opening_without_the_repository_line(self):
        description = m.parse_feed(fixture("opensource_feed.xml"))[0]["description"]

        assert description.startswith("You've probably tried to build a personal knowledge base")
        assert "GitHub Repository" not in description
        assert "github.com" not in description
        assert description.endswith("the stru...")  # the feed's own cut, not ours

    def test_rss_is_read_too_with_the_repository_from_the_line_under_the_excerpt(self):
        items = m.parse_feed(fixture("opensource_rss.xml"))

        assert len(items) == 2
        assert items[0]["url"] == TRILIUM
        assert items[0]["post_url"] == "https://www.opensourceprojects.dev/post/trilium"
        assert items[0]["published_at"] == datetime(2026, 11, 28, 1, 50, 2, tzinfo=timezone.utc)
        assert items[0]["description"] == m.parse_feed(fixture("opensource_feed.xml"))[0]["description"]

    def test_feed_without_entry_gives_nothing(self):
        assert m.parse_feed("<feed></feed>") == []
        assert m.parse_feed("<rss><channel><title>x</title></channel></rss>") == []
        assert m.parse_feed("not xml at all") == []


class TestParseListing:
    def test_cards_skip_the_sponsored_slot(self):
        items = m.parse_listing(fixture("opensource_listing_p1.html"))

        assert len(items) == 2
        assert all("Sponsor" not in item["title"] for item in items)

    def test_card_gives_headline_repository_tags_date_and_views(self):
        first, second = m.parse_listing(fixture("opensource_listing_p1.html"))

        assert first["title"] == "A hierarchical note-taking app for building large personal knowledge bases"
        assert first["url"] == TRILIUM
        assert first["post_url"] == "https://www.opensourceprojects.dev/post/trilium"
        assert first["tags"] == ["UI"]
        assert first["views_count"] == 5
        assert first["description"] is None
        assert first["detail_fetched"] is False
        # Printed 02:50:02 on the site's clock, Madrid: the post the feed stamps 01:50:02Z.
        assert first["published_at"] == datetime(2026, 11, 28, 1, 50, 2, 108000, tzinfo=timezone.utc)
        assert second["tags"] == ["UI", "Go"]
        assert second["views_count"] == 6

    def test_generic_tags_are_dropped(self):
        for item in m.parse_listing(fixture("opensource_listing_p1.html")) + m.parse_listing(fixture("opensource_listing_p2.html")):
            assert not {"Open Source", "Project"} & set(item["tags"])
        assert m.parse_listing(listing(repo("o", "r", "2026-11-01T02:00:00")))[0]["tags"] == ["CLI"]

    def test_the_sites_clock_is_madrid_in_summer_too(self):
        assert m.parse_listing(listing(repo("o", "r", "2026-07-01T12:00:00")))[0]["published_at"] == datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)

    def test_page_without_cards_gives_nothing(self):
        assert m.parse_listing("<html><body><h1>Maintenance</h1></body></html>") == []
        assert m.parse_listing("") == []


class TestParsePostPage:
    def test_post_page_gives_the_opening_the_repository_the_date_and_the_views(self):
        page = m.parse_post_page(fixture("opensource_post.html"))

        assert page["description"].startswith("You've probably tried to build a personal knowledge base before.")
        assert page["description"].endswith("…")
        assert len(page["description"]) <= 500
        assert "What It Does" not in page["description"]  # headings stay out
        assert page["url"] == TRILIUM
        assert page["published_at"] == datetime(2026, 11, 28, 1, 50, 2, 108000, tzinfo=timezone.utc)
        assert page["views_count"] == 0

    def test_post_page_without_article_gives_no_description(self):
        assert m.parse_post_page("<html><body><p>Nothing here</p></body></html>")["description"] is None


class TestParseGithubRepo:
    def test_counts_language_topics_and_the_date_come_from_the_answer(self):
        info = m.parse_github_repo(
            {
                "stargazers_count": 1200,
                "forks_count": 34,
                "language": "Go",
                "topics": ["cli", 7, "tools"],
                "pushed_at": "2026-11-20T10:00:00Z",
                "description": "  What it does,\n in one line.  ",
                "full_name": "a/b",
            }
        )

        assert info == {
            "stars_count": 1200,
            "forks_count": 34,
            "language": "Go",
            "topics": ["cli", "tools"],
            "last_push_at": datetime(2026, 11, 20, 10, 0, 0),
            "repo_description": "What it does, in one line.",
            "full_name": "a/b",
        }

    def test_what_the_answer_lacks_stays_empty(self):
        info = m.parse_github_repo({"stargazers_count": None, "forks_count": "34", "language": "", "topics": None})

        assert info["stars_count"] is None
        assert info["forks_count"] is None
        assert info["language"] is None
        assert info["topics"] == []
        assert info["last_push_at"] is None
        assert info["repo_description"] is None
        assert info["full_name"] is None


# --- extract: feed and listing -------------------------------------------------------------
class TestExtractFeedAndListing:
    def test_first_run_reads_the_feed_then_the_listing_until_an_empty_page(self, etl, monkeypatch):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.pages[BASE_URL] = fixture("opensource_listing_p1.html")
        web.pages[f"{BASE_URL}/?page=2"] = fixture("opensource_listing_p2.html")
        web.pages[f"{BASE_URL}/?page=3"] = "<html><body>nothing more</body></html>"

        records = etl.extract()

        assert sorted(r["url"] for r in records) == sorted([TRILIUM, MYGO, "https://github.com/antfu/node-modules-inspector", "https://github.com/phone-harness/phone-harness"])
        # The feed and the first page name the same two posts: one record each, the feed's.
        by_url = {r["url"]: r for r in records}
        assert by_url[TRILIUM]["description"].startswith("You've probably tried")
        assert by_url["https://github.com/antfu/node-modules-inspector"]["description"].startswith(OPENING)
        assert web.asked_listing() == [BASE_URL, f"{BASE_URL}/?page=2", f"{BASE_URL}/?page=3"]

    def test_nothing_new_and_no_gap_reads_the_feed_only(self, etl, monkeypatch):
        up_to_date = {"description": "Already read.", "detail_fetched": True, "github_checked_at": checked_now(), "stars_count": 9}
        stored(
            etl,
            stored_record("triliumnext", "trilium", "2026-11-28 01:50:02", post_url="https://www.opensourceprojects.dev/post/trilium", **up_to_date),
            stored_record("egoist", "mygo", "2026-11-28 01:49:39", post_url="https://www.opensourceprojects.dev/post/mygo", **up_to_date),
        )
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")

        assert etl.extract() == []
        assert web.requests == [FEED_URL]

    def test_days_without_a_run_are_taken_from_the_listing_down_to_the_known_page(self, etl, monkeypatch):
        # The file stops on the 25th; the feed holds the 27th and the 28th: the 26th is only in the listing.
        checked = checked_now()
        stored(etl, stored_record("old", "one", "2026-11-25 02:00:00", github_checked_at=checked), stored_record("old", "two", "2026-11-25 01:00:00", github_checked_at=checked))
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.pages[BASE_URL] = fixture("opensource_listing_p1.html")
        web.pages[f"{BASE_URL}/?page=2"] = listing(repo("antfu", "node-modules-inspector", "2026-11-27T02:47:25.430000"), repo("mid", "missed", "2026-11-26T02:47:25.430000"))
        web.pages[f"{BASE_URL}/?page=3"] = listing(repo("old", "one", "2026-11-25T02:00:00.000000"), repo("old", "two", "2026-11-25T01:00:00.000000"))
        web.pages[f"{BASE_URL}/?page=4"] = listing(repo("older", "still", "2026-11-24T02:00:00.000000"))

        records = etl.extract()

        assert sorted(r["url"] for r in records) == sorted([TRILIUM, MYGO, "https://github.com/antfu/node-modules-inspector", "https://github.com/mid/missed"])
        # Page 1 repeats the feed and still counts as unseen; page 3 is entirely known and ends the walk.
        assert web.asked_listing() == [BASE_URL, f"{BASE_URL}/?page=2", f"{BASE_URL}/?page=3"]

    def test_a_month_old_file_is_completed_from_the_whole_listing(self, etl, monkeypatch):
        """The file as found on 2026-11-28 ended in April; the scraper that built it left holes under pages it knew."""
        checked = checked_now()
        stored(etl, stored_record("old", "one", "2026-04-29 07:26:03", github_checked_at=checked), stored_record("old", "two", "2026-04-28 07:26:03", github_checked_at=checked))
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.pages[BASE_URL] = fixture("opensource_listing_p1.html")
        web.pages[f"{BASE_URL}/?page=2"] = listing(repo("mid", "missed", "2026-11-26T02:47:25.430000"))
        web.pages[f"{BASE_URL}/?page=3"] = listing(repo("old", "one", "2026-04-29T02:00:00.000000"), repo("old", "two", "2026-04-28T02:00:00.000000"))
        web.pages[f"{BASE_URL}/?page=4"] = listing(repo("older", "never-seen", "2026-04-27T02:00:00.000000"))

        records = etl.extract()

        assert sorted(r["url"] for r in records) == sorted([TRILIUM, MYGO, "https://github.com/mid/missed", "https://github.com/older/never-seen"])
        # Page 3 is known entirely; a month-old file does not stop there, the last page (empty) does.
        assert web.asked_listing() == [BASE_URL, f"{BASE_URL}/?page=2", f"{BASE_URL}/?page=3", f"{BASE_URL}/?page=4", f"{BASE_URL}/?page=5"]

    def test_a_repository_posted_again_is_not_a_second_record(self, etl, monkeypatch):
        checked = checked_now()
        stored(etl, stored_record("antfu", "node-modules-inspector", "2026-11-20 02:00:00", github_checked_at=checked), stored_record("old", "two", "2026-11-19 01:00:00", github_checked_at=checked))
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        # The same repository under another spelling, the same post as the feed's.
        web.pages[BASE_URL] = listing(
            repo("ANTFU", "Node-Modules-Inspector", "2026-11-27T02:47:25.430000"), repo("TriliumNext", "Trilium", "2026-11-28T02:50:02.108000"), repo("old", "two", "2026-11-19T01:00:00.000000")
        )

        records = etl.extract()

        assert sorted(r["url"] for r in records) == sorted([TRILIUM, MYGO])
        # Today's post is not in the file yet, so the page counts as unseen and the walk ends at the next one.
        assert web.asked_listing() == [BASE_URL, f"{BASE_URL}/?page=2"]

    def test_the_walk_stops_at_the_page_cap(self, etl, monkeypatch):
        etl.max_listing_pages = 3
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        for page in range(1, 6):
            web.pages[BASE_URL if page == 1 else f"{BASE_URL}/?page={page}"] = listing(repo("o", f"r{page}a", f"2026-11-0{page}T02:00:00"), repo("o", f"r{page}b", f"2026-11-0{page}T01:00:00"))

        records = etl.extract()

        assert {r["url"] for r in records if "/o/r" in r["url"]} == {f"https://github.com/o/r{page}{letter}" for page in (1, 2, 3) for letter in "ab"}
        assert f"{BASE_URL}/?page=4" not in web.requests

    def test_a_feed_without_entry_is_an_error_not_an_empty_day(self, etl, monkeypatch):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = "<feed></feed>"
        web.pages[RSS_URL] = "<rss><channel></channel></rss>"

        with pytest.raises(ETLError, match="no feed entry"):
            etl.extract()
        assert web.requests == [FEED_URL, RSS_URL]

    def test_feed_posts_that_name_no_repository_are_an_error_not_an_empty_day(self, etl, monkeypatch):
        """A feed whose repository link the parser loses would end every cycle at zero, as between April and November 2026."""
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = (
            '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Open Source Projects</title>'
            '<entry><title>A project</title><link href="https://www.opensourceprojects.dev/post/a-b"/><updated>2026-11-28T01:50:02Z</updated>'
            '<content type="html">The opening of the article, with no repository under it.</content></entry></feed>'
        )
        web.pages[RSS_URL] = web.pages[FEED_URL]

        with pytest.raises(ETLError, match="None of the 1 feed posts names a repository"):
            etl.extract()
        assert web.requests == [FEED_URL]

    def test_a_site_that_does_not_answer_is_an_error(self, etl, monkeypatch):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.down = {FEED_URL, RSS_URL}

        with pytest.raises(ETLError, match="did not answer"):
            etl.extract()

    def test_rss_is_the_fallback_when_the_atom_feed_has_no_entry(self, etl, monkeypatch):
        checked = checked_now()
        stored(etl, stored_record("triliumnext", "trilium", "2026-11-28 01:50:02", github_checked_at=checked), stored_record("egoist", "mygo", "2026-11-28 01:49:39", github_checked_at=checked))
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = "<html><body>not a feed</body></html>"
        web.pages[RSS_URL] = fixture("opensource_rss.xml")

        assert etl.extract() == []
        assert web.requests == [FEED_URL, RSS_URL]

    def test_a_broken_listing_ends_the_walk_and_is_logged_not_raised(self, etl, monkeypatch, caplog):
        stored(etl, stored_record("old", "one", "2026-11-01 02:00:00", github_checked_at=checked_now()))
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.pages[BASE_URL] = '<html><body><div class="something-new">No card here</div></body></html>'

        with caplog.at_level(logging.ERROR, logger=etl.logger.name):
            records = etl.extract()

        assert sorted(r["url"] for r in records) == sorted([TRILIUM, MYGO])  # the feed's posts still come through
        assert "markup changed" in caplog.text

    def test_a_listing_page_that_cannot_be_read_ends_the_walk(self, etl, monkeypatch):
        stored(etl, stored_record("old", "one", "2026-11-01 02:00:00", github_checked_at=checked_now()))
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.down = {BASE_URL}

        assert len(etl.extract()) == 2


# --- extract: completion -------------------------------------------------------------------
class TestExtractCompletion:
    def test_post_pages_are_read_newest_first_within_the_budget(self, etl, monkeypatch):
        etl.post_details_per_run = 2
        older = [repo("o", f"r{index}", f"2026-11-2{index}T02:00:00") for index in (3, 4, 5, 6)]
        stored(etl, *[stored_record(r["owner"], r["name"], r["date"].replace("T", " "), post_url=post_url(r), detail_fetched=False, github_checked_at=checked_now()) for r in older])
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        for r in older:
            web.pages[post_url(r)] = post_page(r["url"], r["title"], date=r["date"])

        records = [r for r in etl.extract() if r["url"].startswith("https://github.com/o/")]

        # The 26th and the 25th are read now; the 24th and the 23rd wait for the next run.
        assert sorted(r["url"] for r in records) == ["https://github.com/o/r5", "https://github.com/o/r6"]
        assert all(r["detail_fetched"] is True and r["description"].startswith(OPENING) and r["views_count"] == 31 for r in records)
        assert [url for url in web.requests if "/post/o-r" in url] == ["https://www.opensourceprojects.dev/post/o-r6", "https://www.opensourceprojects.dev/post/o-r5"]

    def test_a_stored_record_keeps_its_id_and_the_date_it_was_first_seen(self, etl, monkeypatch):
        etl.post_details_per_run = 1
        r = repo("antfu", "node-modules-inspector", "2026-11-27T02:47:25.430000")
        old = stored_record("antfu", "node-modules-inspector", "2026-11-27 02:00:00", post_url=post_url(r), detail_fetched=False, github_checked_at=checked_now())
        stored(etl, old)
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.pages[post_url(r)] = post_page(r["url"], r["title"], date=r["date"])

        (raw,) = [item for item in etl.extract() if item["url"] == r["url"]]

        assert raw["id"] == old["id"]
        assert raw["created_at"] == old["created_at"]
        assert raw["published_at"] == datetime(2026, 11, 27, 1, 47, 25, 430000, tzinfo=timezone.utc)  # the post page's date replaces the older one

    def test_github_is_asked_newest_first_within_the_budget(self, etl, monkeypatch):
        etl.github_lookups_per_run = 2
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.pages[BASE_URL] = listing(repo("a", "third", "2026-11-20T03:50:02"))

        by_url = {r["url"]: r for r in etl.extract()}

        assert web.asked_github() == [f"{GITHUB_API}/triliumnext/trilium", f"{GITHUB_API}/egoist/mygo"]
        assert by_url[TRILIUM]["stars_count"] == 1200
        assert by_url[TRILIUM]["forks_count"] == 34
        assert by_url[TRILIUM]["language"] == "Go"
        assert by_url[TRILIUM]["topics"] == ["cli", "tools"]
        assert by_url[TRILIUM]["last_push_at"] == datetime(2026, 11, 20, 10, 0, 0)
        assert by_url[TRILIUM]["github_checked_at"]
        assert "stars_count" not in by_url["https://github.com/a/third"]
        # The feed already carried the opening of the article: GitHub's one-liner does not replace it.
        assert by_url[TRILIUM]["description"].startswith("You've probably tried")

    def test_github_fills_a_description_that_repeated_the_title_and_leaves_a_real_one(self, etl, monkeypatch):
        stored(
            etl,
            stored_record("o", "repeated", "2026-11-26 02:00:00"),
            stored_record("o", "real", "2026-11-25 02:00:00", description="What the post said about it."),
            stored_record("o", "placeholder", "2026-11-24 02:00:00", title="Open Source Project", description="Open Source Project"),
        )
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.github[f"{GITHUB_API}/o/placeholder"] = FakeResponse(200, {}, {"full_name": "o/placeholder", "description": None, "stargazers_count": 5})

        by_url = {r["url"]: r for r in etl.extract()}

        assert by_url["https://github.com/o/repeated"]["description"] == "What repeated does, in one line."
        assert by_url["https://github.com/o/real"]["description"] == "What the post said about it."
        assert by_url["https://github.com/o/real"]["stars_count"] == 1200
        assert by_url["https://github.com/o/placeholder"]["title"] == "o/placeholder"
        assert by_url["https://github.com/o/placeholder"]["stars_count"] == 5

    def test_github_stops_while_the_hour_is_almost_spent(self, etl, monkeypatch):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.remaining = [4, 3]

        records = etl.extract()

        assert len(web.asked_github()) == 1
        assert sum(1 for r in records if r.get("stars_count") is not None) == 1

    def test_a_github_refusal_leaves_the_records_as_they_are(self, etl, monkeypatch, caplog):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.github[f"{GITHUB_API}/triliumnext/trilium"] = FakeResponse(403, {"X-RateLimit-Remaining": "0"}, {})

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            records = etl.extract()

        assert len(records) == 2
        assert all("stars_count" not in r and "github_checked_at" not in r for r in records)
        assert "answered 403" in caplog.text
        assert web.asked_github() == [f"{GITHUB_API}/triliumnext/trilium"]

    def test_a_github_that_does_not_answer_ends_the_step_and_not_the_run(self, etl, monkeypatch):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        monkeypatch.setattr(etl, "_github_request", lambda url: None)

        records = etl.extract()

        assert sorted(r["url"] for r in records) == sorted([TRILIUM, MYGO])
        assert all("stars_count" not in r for r in records)

    def test_a_repository_gone_from_github_is_not_asked_about_again(self, etl, monkeypatch):
        stored(etl, stored_record("o", "gone", "2026-11-26 02:00:00"))
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.github[f"{GITHUB_API}/o/gone"] = FakeResponse(404, {}, {})

        by_url = {r["url"]: r for r in etl.extract()}
        gone = by_url["https://github.com/o/gone"]
        assert gone["github_checked_at"]
        assert "stars_count" not in gone
        stored(etl, *latest_after(etl, list(by_url.values())))
        web.requests.clear()

        assert etl.extract() == []
        assert f"{GITHUB_API}/o/gone" not in web.requests

    def test_a_token_raises_the_budget(self, etl, monkeypatch):
        etl.github_token = "not-a-real-token"
        assert etl.github_lookups_per_run * 10 == 300


def latest_after(etl: OpenSourceProjectsETL, records: list[dict]) -> list[dict]:
    """The records as load() writes them, for a stored() call that simulates the next run."""
    etl.load(etl.transform(records))
    return latest(etl)


class TestGithubDue:
    def test_never_asked_is_due_and_an_old_post_is_asked_once(self):
        now = datetime(2026, 11, 28, 6)
        assert m._github_due({"published_at": "2026-08-01 02:00:00"}, now) is True
        assert m._github_due({"published_at": "2026-08-01 02:00:00", "github_checked_at": "2026-11-20 02:00:00"}, now) is False

    def test_a_recent_post_is_asked_again_after_a_week(self):
        now = datetime(2026, 11, 28, 6)
        recent = {"published_at": now.isoformat(sep=" ")}
        assert m._github_due({**recent, "github_checked_at": (now - timedelta(days=6, hours=23)).isoformat(sep=" ")}, now) is False
        assert m._github_due({**recent, "github_checked_at": (now - timedelta(days=7)).isoformat(sep=" ")}, now) is True


# --- transform and load --------------------------------------------------------------------
class TestTransformAndLoad:
    def test_a_record_that_does_not_fit_is_dropped_with_its_url(self, etl, caplog):
        good = {"title": "A project", "url": "https://github.com/a/b", "published_at": datetime(2026, 11, 28)}
        bad = {"title": "No url", "url": None, "_key": "x"}

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            transformed = etl.transform([good, bad])

        assert [item.url for item in transformed] == ["https://github.com/a/b"]
        assert "does not fit the model (None)" in caplog.text

    def test_load_merges_newest_first_and_keeps_what_it_did_not_touch(self, etl):
        stored(etl, stored_record("old", "one", "2026-04-01 07:26:03.537000"), stored_record("old", "two", "2026-03-01 07:26:03"), {"not": "a record"}, ["a", "list"])
        new = OpenSourceProjectItem(title="New", url="https://github.com/new/one", published_at=datetime(2026, 11, 28, 1, 50, 2), description="Read from the feed.")
        again = OpenSourceProjectItem(title="old/one", url="https://GitHub.com/old/one/", published_at=datetime(2026, 4, 1, 7, 26, 3, 537000), description="Completed later.")

        etl.load([new, again])

        records = latest(etl)
        assert [r["url"] for r in records if isinstance(r, dict) and "url" in r] == ["https://github.com/new/one", "https://GitHub.com/old/one/", "https://github.com/old/two"]
        assert records[0]["description"] == "Read from the feed."
        assert records[1]["description"] == "Completed later."
        assert records[2]["created_at"] == "2026-01-10 08:00:00"  # the other stored record, untouched
        assert len(records) == 5
        assert all(junk in records[3:] for junk in ({"not": "a record"}, ["a", "list"]))  # what is not a record stays at the end
        assert sorted(path.name for path in etl.output_dir.iterdir()) == ["latest.json"]  # one file: no copy per run
        assert not list(etl.output_dir.glob("*.tmp"))

    def test_stored_records_that_repeat_a_repository_collapse_into_the_first_one_and_it_is_reported(self, etl, caplog):
        newest = stored_record("danielmiessler", "fabric", "2026-04-22 08:13:25.257000", title="Fabric: 200+ reusable AI prompts")
        older = stored_record("danielmiessler", "fabric", "2025-07-01 02:45:39", title="Fabric is an open-source framework", url="https://github.com/DanielMiessler/fabric/", id="id-older")
        stored(etl, newest, older)

        with caplog.at_level(logging.INFO, logger=etl.logger.name):
            etl.load([])

        assert [(r["id"], r["title"]) for r in latest(etl)] == [("id-danielmiessler-fabric", "Fabric: 200+ reusable AI prompts")]
        assert "repeat a repository already in the file: 1 (the first one of each is kept)" in caplog.text

    def test_a_stored_link_to_a_web_search_is_repaired_and_the_repository_asked_about(self, etl, monkeypatch, caplog):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.github[f"{GITHUB_API}/jxroot/nahpet"] = FakeResponse(200, {"X-RateLimit-Remaining": "59"}, {"full_name": "jxroot/nahpet", "description": "A clean, private URL shortener.", "stargazers_count": 410})
        stored(etl, stored_record("jxroot", "nahpet", "2025-12-31 16:29:20.904000", url=SEARCH_LINK), stored_record("pwned-check", "little-rat", "2025-12-28 04:36:56.706000", url="https://www.google.com/search?q=https://github.com/pwned-check/little-rat"))

        with caplog.at_level(logging.INFO, logger=etl.logger.name):
            etl.load(etl.transform(etl.extract()))

        by_url = {r["url"]: r for r in latest(etl)}
        assert by_url["https://github.com/jxroot/nahpet"]["stars_count"] == 410
        assert by_url["https://github.com/jxroot/nahpet"]["description"] == "A clean, private URL shortener."
        assert by_url["https://github.com/pwned-check/little-rat"]["id"] == "id-pwned-check-little-rat"  # the same record, its link repaired
        assert by_url["https://github.com/pwned-check/little-rat"]["stars_count"] == 1200
        assert "linked to a web search instead of their repository: 2 (repaired)" in caplog.text

    def test_an_older_layout_survives_the_merge(self, etl, caplog):
        stored(etl, {**stored_record("old", "legacy", "2026-01-05 07:26:03"), "extra_key": "kept"}, {"title": "Broken", "url": None})
        new = OpenSourceProjectItem(title="New", url="https://github.com/new/one", published_at=datetime(2026, 11, 28))

        with caplog.at_level(logging.WARNING, logger=etl.logger.name):
            etl.load([new])

        records = latest(etl)
        assert [r["url"] for r in records][:2] == ["https://github.com/new/one", "https://github.com/old/legacy"]
        assert records[2] == {"title": "Broken", "url": None}
        assert "not records" in caplog.text

    def test_a_missing_or_damaged_file_starts_over(self, etl):
        (etl.output_dir / "latest.json").write_text("{not json", encoding="utf-8")

        assert etl._read_latest() == ({}, [])
        (etl.output_dir / "latest.json").unlink()
        assert etl._read_latest() == ({}, [])

    def test_a_date_is_stored_with_its_zone_and_sorts_with_the_older_ones(self, etl):
        """The records before T-204 carry the site's clock without a zone, a new one carries UTC: both order by the instant."""
        stored(etl, stored_record("old", "one", "2026-11-28 01:40:00"), stored_record("old", "two", "2026-11-28 03:10:00"))
        new = OpenSourceProjectItem(title="New", url="https://github.com/new/one", published_at=datetime(2026, 11, 28, 2, 50, tzinfo=timezone.utc))  # 03:50 on the site's clock

        etl.load([new])

        records = latest(etl)
        assert [r["url"] for r in records] == ["https://github.com/new/one", "https://github.com/old/two", "https://github.com/old/one"]
        assert records[0]["published_at"] == "2026-11-28 02:50:00+00:00"
        assert records[1]["published_at"] == "2026-11-28 03:10:00"  # as it was written, not touched

    def test_a_title_or_description_that_kept_an_entity_is_decoded_once(self, etl):
        """The site escapes some of its text twice: the parsers decode it once, this decodes what is left. A "<" is text by then, not a tag."""
        plain, angled, untouched = etl.transform(
            [
                {"title": "Lib &amp; tool", "description": "Fast &#8217;n light", "url": "https://example.invalid/lib"},
                {"title": "Replace &lt;img&gt; with &lt;picture&gt;", "description": "A <b> literal bracket", "url": "https://example.invalid/img"},
                {"title": "Plain & simple", "description": "Nothing to decode", "url": "https://example.invalid/plain"},
            ]
        )

        assert (plain.title, plain.description) == ("Lib & tool", "Fast ’n light")
        assert (angled.title, angled.description) == ("Replace <img> with <picture>", "A <b> literal bracket")
        assert (untouched.title, untouched.description) == ("Plain & simple", "Nothing to decode")

    def test_stored_records_that_kept_an_entity_are_decoded_and_it_is_reported(self, etl, caplog):
        """No run wrote the file again between T-164 (2026-11-27) and T-204: the records that kept an entity are decoded with the first write."""
        legacy = stored_record("old", "lib", "2026-04-01 07:26:03.537000", title="Lib &amp; tool", description="Fast &#8217;n light")
        clean = stored_record("old", "plain", "2026-03-01 07:26:03", title="Plain & simple")
        stored(etl, legacy, clean)

        with caplog.at_level(logging.INFO, logger=etl.logger.name):
            etl.load([])

        records = {record["url"]: record for record in latest(etl)}
        assert (records["https://github.com/old/lib"]["title"], records["https://github.com/old/lib"]["description"]) == ("Lib & tool", "Fast ’n light")
        assert records["https://github.com/old/lib"]["id"] == legacy["id"] and records["https://github.com/old/lib"]["created_at"] == legacy["created_at"]
        assert records["https://github.com/old/plain"]["title"] == "Plain & simple"
        assert "kept an HTML entity: 1 (decoded)" in caplog.text

        caplog.clear()
        etl.load([])

        assert "HTML entity" not in caplog.text  # written decoded: nothing left to report

    def test_the_freshness_watcher_can_date_the_file(self, etl):
        etl.load([OpenSourceProjectItem(title="New", url="https://github.com/new/one", published_at=datetime(2026, 11, 28, 1, 50, 2))])

        assert newest_item_epoch(etl.output_dir / "latest.json", "published_at") == datetime(2026, 11, 28, 1, 50, 2, tzinfo=timezone.utc).timestamp()


# --- run -----------------------------------------------------------------------------------
class TestRun:
    def test_a_run_writes_the_file_and_a_run_without_news_does_not_touch_it(self, etl, monkeypatch):
        web = FakeWeb()
        web.install(etl, monkeypatch)
        web.pages[FEED_URL] = fixture("opensource_feed.xml")
        web.pages[BASE_URL] = listing(repo("triliumnext", "trilium", "2026-11-28T02:50:02.108000"), repo("egoist", "mygo", "2026-11-28T02:49:39.427000"))

        metrics = etl.run()

        assert metrics.records_extracted == 2
        assert metrics.records_loaded == 2
        assert metrics.error_count == 0
        path = etl.output_dir / "latest.json"
        first_write = path.stat().st_mtime_ns
        records = latest(etl)
        assert [r["url"] for r in records] == [TRILIUM, MYGO]
        assert all(r["title"] and r["url"] for r in records)  # what the Knowledge Garden reads
        assert records[0]["stars_count"] == 1200
        web.requests.clear()

        metrics = etl.run()

        assert metrics.records_extracted == 0
        assert path.stat().st_mtime_ns == first_write
        assert web.requests == [FEED_URL]
