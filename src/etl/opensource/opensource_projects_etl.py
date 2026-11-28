"""Open-source projects published on opensourceprojects.dev, one record per repository.

The site publishes a batch of about twelve projects a day. Two of its pages are read,
both keyless and static:

* the Atom feed (``/feed.xml``; ``/rss`` is the fallback) carries the latest batch with the
  opening of every article and the repository link;
* the listing (``/?page=N``, twelve posts per page, newest first) carries every post with
  its headline, repository, tags and date.

A repository first seen in the listing gets the opening of its article from its own post
page in a later run, a few dozen per run. Stars, forks, language and topics come from the
GitHub API, anonymously (60 requests an hour) or with ``GITHUB_TOKEN`` when it is set; a
lookup that fails leaves the record as it is.

``latest.json`` is the file the Knowledge Garden reads: every repository ever seen, newest
first, each keeping the ``created_at`` of the run that first saw it. The dates written from
here on are in UTC and say so; the site prints the dates of its listing on the Madrid clock
without saying so, and every record written before T-204 (2026-11-28) keeps that clock.
Titles and descriptions are plain text (T-164): the parsers decode the markup once, and an
entity left (the site escapes some of its text twice) is decoded once more, in the records
of a run and in the stored ones that kept one.
"""

import calendar
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlparse
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from src.etl.base import BaseETL
from src.exceptions.etl import ETLError
from src.models.opensource_model import OpenSourceProjectItem
from src.utils.text import plain_excerpt

BASE_URL = "https://www.opensourceprojects.dev"
FEED_URL = f"{BASE_URL}/feed.xml"
RSS_URL = f"{BASE_URL}/rss"
GITHUB_API = "https://api.github.com/repos"

# The listing prints a tag or two on every post; these say nothing about the project.
_GENERIC_TAGS = {"open source", "project", "oss", "github"}
_REPO_LINE = re.compile(r"GitHub Repository:\s*(https?://github\.com/[\w.-]+/[\w.-]+)", re.IGNORECASE)
_PLACEHOLDER_TITLES = {"open source project", "unknown title"}
_EXCERPT_LIMIT = 500
# Requests left in the hour below which a run stops asking GitHub for more.
_GITHUB_SAFETY = 10
# Stars move; a repository is asked about again a week later, while its post is two months old at most.
_GITHUB_RECHECK_AFTER = timedelta(days=7)
_GITHUB_RECHECK_WHILE = timedelta(days=60)
# More than a day between the newest stored post and the oldest one in the feed: the
# batches in between are still in the listing.
GAP_DAYS = 1
# More than a month between them: the stored file is completed from the whole listing,
# because a page it knows entirely can hide older posts it never saw.
BACKFILL_DAYS = 30
# The clock the site prints its dates on, without saying so: on 2026-11-28 the listing
# stamped a post 02:50:02 and its feed said 01:50:02Z. The dashboard reads a date without
# a zone as Madrid time too, so the records written before T-204 need no repair.
SITE_ZONE = ZoneInfo("Europe/Madrid")
# The first scraper kept a few "search the web for it" links instead of the repository; the
# address it searched for is in the link's ``q`` parameter.
_WEB_SEARCH = re.compile(r"^https?://(?:www\.)?google\.[a-z.]+/search\?", re.IGNORECASE)
# An entity left in a text the parsers already decoded once: the site escapes some of its text twice.
_ENTITY = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);")


def _utc_now() -> datetime:
    """Now in UTC as a naive datetime, the form the records keep their dates in."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _linked_url(url: str) -> str:
    """The address a link carries: that of a "search for it" link is what it searched for."""
    if _WEB_SEARCH.match(url):
        query = dict(parse_qsl(urlparse(url).query)).get("q", "")
        if query.startswith(("http://", "https://")):
            return query
    return url


def repository_of_search(url: str | None) -> str | None:
    """The repository behind a "search for it" link, or ``None`` for a link to anything else."""
    text = (url or "").strip()
    if not _WEB_SEARCH.match(text):
        return None
    searched = _linked_url(text)
    return clean_repo_url(searched) if searched != text else None


def normalize_repo_url(url: str | None) -> str:
    """Key of a record: the repository's path on its host, in one spelling.

    Case, a trailing slash, ``.git``, tracking parameters and a deeper path (a file, an
    issue, a release) do not tell two records apart.
    """
    if not url:
        return ""
    parsed = urlparse(_linked_url(url.strip()))
    path = re.sub(r"\.git$", "", parsed.path.strip("/"), flags=re.IGNORECASE)
    if (parsed.hostname or "").lower() == "github.com":
        path = "/".join(path.split("/")[:2])
    return f"{(parsed.hostname or '').lower()}/{path}".lower()


def clean_repo_url(url: str | None) -> str | None:
    """The URL that is stored and shown: scheme, host and path, without tracking parameters."""
    if not url:
        return None
    parsed = urlparse(_linked_url(url.strip()))
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/') or '/'}"


def _utc(moment: Any) -> datetime | None:
    """A ``struct_time`` in UTC as a datetime that says so."""
    if not moment:
        return None
    return datetime.fromtimestamp(calendar.timegm(moment), tz=timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    """An ISO 8601 date as it is written: with its zone, or without one."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _naive_utc_text(value: Any) -> datetime | None:
    """The date as a naive datetime, for comparing records: one with a zone is taken to UTC, one without is kept as it comes."""
    moment = _parse_datetime(value)
    return moment.astimezone(timezone.utc).replace(tzinfo=None) if moment and moment.tzinfo else moment


def _site_clock(value: Any) -> datetime | None:
    """A date the site prints without a zone, read on the site's own clock, as a datetime in UTC."""
    moment = _parse_datetime(value)
    if moment is None:
        return None
    return (moment if moment.tzinfo else moment.replace(tzinfo=SITE_ZONE)).astimezone(timezone.utc)


def _decoded_once(value: Any) -> Any:
    """A text that still carries an entity, decoded once more; anything else is given back as it is.

    The parsers decode the markup once, so an entity left comes from text the site escapes
    twice (``&amp;amp;``). Nothing else is touched: by then a ``<`` is text, not a tag.
    """
    if isinstance(value, str) and _ENTITY.search(value):
        return " ".join(unescape(value).split())
    return value


def _attr(element: Tag | None, name: str) -> str:
    """An attribute of a tag as text (BeautifulSoup types attributes loosely)."""
    value = element.get(name) if element is not None else None
    return value if isinstance(value, str) else ""


def _views(element: Tag | None) -> int | None:
    """The view counter of a card (``title="5 views"``) or of a post page (its own number)."""
    if element is None:
        return None
    match = re.search(r"([\d,]+)\s*views?", _attr(element, "title"), re.IGNORECASE)
    raw = match.group(1) if match else None
    if raw is None:
        value = element.select_one(".impressions-value")
        raw = value.get_text(strip=True) if value else None
    try:
        return int(raw.replace(",", "")) if raw is not None else None
    except ValueError:
        return None


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _feed_excerpt(body: str) -> str | None:
    """The opening of the article as the feed carries it, without the repository line under it."""
    match = _REPO_LINE.search(body)
    excerpt = plain_excerpt(body[: match.start()] if match else body, _EXCERPT_LIMIT)
    return excerpt or None


def parse_feed(text: str) -> list[dict[str, Any]]:
    """Entries of the feed (Atom or RSS) as raw records.

    Each carries the headline, the opening of the article, the repository, the post and
    the date. The repository comes from the entry's related link, or from the line the
    feed prints under every excerpt.
    """
    items: list[dict[str, Any]] = []
    for entry in feedparser.parse(text).entries:
        body = next((block.get("value") or "" for block in entry.get("content") or [] if block.get("value")), "")
        body = body or entry.get("summary") or entry.get("description") or ""
        repo = next((link.get("href") for link in entry.get("links", []) if link.get("rel") == "related"), None)
        match = _REPO_LINE.search(body)
        if match:
            repo = match.group(1)
        items.append(
            {
                "title": " ".join((entry.get("title") or "").split()),
                "description": _feed_excerpt(body),
                "url": clean_repo_url(repo),
                "post_url": entry.get("link") or None,
                "published_at": _utc(entry.get("updated_parsed") or entry.get("published_parsed")),
                "detail_fetched": True,
            }
        )
    return items


def parse_listing(html_text: str, base_url: str = BASE_URL) -> list[dict[str, Any]]:
    """The project cards of one listing page as raw records, without the sponsored slot.

    A card gives the headline, the repository, the tags, the date and the view counter; the
    excerpt under the headline only repeats it, so the description waits for the post page.
    The date is printed on the site's clock without a zone and is taken to UTC from it.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    items: list[dict[str, Any]] = []
    for card in soup.select("article.project-card"):
        if "sponsor-card" in (card.get("class") or []):
            continue
        title = card.select_one("h3.card-title")
        title_link = title.select_one("a[href]") if title else None
        repo = card.select_one("a.postcard-repo-link[href]") or card.select_one("a[href*='github.com/']")
        moment = card.select_one("time[datetime]")
        items.append(
            {
                "title": title.get_text(" ", strip=True) if title else "",
                "description": None,
                "url": clean_repo_url(_attr(repo, "href")) if repo else None,
                "post_url": urljoin(base_url, _attr(title_link, "href")) if title_link else None,
                "published_at": _site_clock(_attr(moment, "datetime")) if moment else None,
                "tags": [tag.get_text(strip=True) for tag in card.select("span.postcard-tag") if tag.get_text(strip=True).lower() not in _GENERIC_TAGS],
                "views_count": _views(card.select_one(".postcard-impressions-stamp")),
                "detail_fetched": False,
            }
        )
    return items


def parse_post_page(html_text: str) -> dict[str, Any]:
    """What a post page adds to its record: the opening of the article, the repository, the date, the views."""
    soup = BeautifulSoup(html_text, "html.parser")
    content = soup.select_one(".markdown-content")
    paragraphs = content.find_all("p", recursive=False) if content else []
    if not paragraphs and content:
        paragraphs = content.find_all("p")
    opening = plain_excerpt(" ".join(paragraph.get_text(" ", strip=True) for paragraph in paragraphs), _EXCERPT_LIMIT)
    repo = soup.select_one("a.github-repo-link[href]")
    moment = soup.select_one("time.project-date[datetime]")
    return {
        "description": opening or None,
        "url": clean_repo_url(_attr(repo, "href")) if repo else None,
        "published_at": _site_clock(_attr(moment, "datetime")) if moment else None,
        "views_count": _views(soup.select_one(".project-impressions")),
    }


def parse_github_repo(payload: dict[str, Any]) -> dict[str, Any]:
    """What the GitHub API adds to a record. A count the answer lacks stays ``None``.

    ``repo_description`` and ``full_name`` are not fields of the record: they fill the
    description and replace a placeholder title, and are dropped after that.
    """
    return {
        "stars_count": _int(payload.get("stargazers_count")),
        "forks_count": _int(payload.get("forks_count")),
        "language": payload.get("language") or None,
        "topics": [topic for topic in payload.get("topics") or [] if isinstance(topic, str)],
        "last_push_at": _naive_utc_text(payload.get("pushed_at")),
        "repo_description": " ".join(str(payload.get("description") or "").split()) or None,
        "full_name": payload.get("full_name") or None,
    }


def _is_placeholder(text: Any) -> bool:
    return not text or " ".join(str(text).split()).lower() in _PLACEHOLDER_TITLES


def _github_due(record: dict[str, Any], now: datetime) -> bool:
    """Whether GitHub is asked about a repository in this run: never asked, or asked a week ago while the post is recent."""
    checked = _naive_utc_text(record.get("github_checked_at"))
    if checked is None:
        return True
    published = _naive_utc_text(record.get("published_at")) or _naive_utc_text(record.get("created_at"))
    if published is None or now - published > _GITHUB_RECHECK_WHILE:
        return False
    return now - checked >= _GITHUB_RECHECK_AFTER


def _sort_key(item: OpenSourceProjectItem) -> datetime:
    """The date a record sorts by, in UTC. One written without a zone is on the site's clock (every record before T-204)."""
    if not item.published_at:
        created = item.created_at
        return (created if created.tzinfo else created.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    published = item.published_at
    return (published if published.tzinfo else published.replace(tzinfo=SITE_ZONE)).astimezone(timezone.utc)


def _write_atomically(path: Path, text: str) -> None:
    """Replace a file whole: a reader never sees it half written."""
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


class OpenSourceProjectsETL(BaseETL[dict, OpenSourceProjectItem]):
    """Every repository opensourceprojects.dev has posted about, newest first, in ``latest.json``."""

    def __init__(self, **kwargs: Any):
        # No deduplication by title: a repository is identified by its URL, and two
        # repositories can share a headline.
        super().__init__(name="open_source_intelligence", description="ETL for opensourceprojects.dev", enable_enrichment=False, enable_deduplication=False, **kwargs)
        self.base_url = BASE_URL
        self.max_listing_pages = 300  # the whole site is about 260 pages of twelve posts
        self.listing_delay_seconds = 0.4
        self.post_details_per_run = 40
        self.github_lookups_per_run = 30
        # Optional: with a token GitHub answers 5,000 times an hour instead of 60.
        self.github_token = os.environ.get("GITHUB_TOKEN") or None
        # Filled by _read_latest, for load to report: stored records that repeat a
        # repository already in the file, links to a web search repaired, and texts
        # that kept an entity.
        self.repeated_stored = 0
        self.repaired_stored = 0
        self.decoded_stored = 0

    # -- pages -------------------------------------------------------------------------
    def _get(self, url: str) -> str:
        """Text of a page; a network error or a bad status raises."""
        return self.fetch_url(url).text

    def _github_request(self, url: str) -> requests.Response | None:
        """Ask GitHub about the repository of a URL; ``None`` when the request itself failed."""
        owner_repo = "/".join(urlparse(url).path.strip("/").split("/")[:2])
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        try:
            return self.http_session.get(f"{GITHUB_API}/{owner_repo}", headers=headers, timeout=15)
        except requests.RequestException as error:
            self.logger.warning(f"GitHub could not be asked about {owner_repo}: {error}")
            return None

    # -- stored records ----------------------------------------------------------------
    def _read_latest(self) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """The records of ``latest.json`` by key (the first spelling of a repository wins) and the entries that are not a record.

        Entries that are not a record are handed back untouched so that ``load`` can keep
        them at the end of the file.
        """
        path = self.output_dir / "latest.json"
        self.repeated_stored = 0
        self.repaired_stored = 0
        self.decoded_stored = 0
        if not path.exists():
            return {}, []
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            self.logger.warning(f"{path.name} could not be read, starting over: {error}")
            return {}, []
        stored: dict[str, dict[str, Any]] = {}
        kept: list[dict[str, Any]] = []
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                kept.append(entry)
                continue
            # Written before T-164 (2026-11-27) decoded the texts, and never written again since.
            text = {field: _decoded_once(entry.get(field)) for field in ("title", "description")}
            if text != {field: entry.get(field) for field in ("title", "description")}:
                entry = {**entry, **text}
                self.decoded_stored += 1
            repository = repository_of_search(str(entry.get("url") or ""))
            if repository:
                entry = {**entry, "url": repository}
                self.repaired_stored += 1
            key = normalize_repo_url(str(entry.get("url") or ""))
            if key in stored:
                self.repeated_stored += 1
            else:
                stored[key] = entry
        return stored, kept

    # -- extract -----------------------------------------------------------------------
    def extract(self) -> list[dict[str, Any]]:
        """The records this run adds or completes: new ones from the feed and the listing, then the ones a page or GitHub can finish."""
        stored, _ = self._read_latest()
        work: dict[str, dict[str, Any]] = {}
        feed_items = self._read_feed()
        for item in feed_items:
            self._add(work, stored, item)
        self.logger.info(f"Feed: {len(feed_items)} posts, {len(work)} new repositories")
        if feed_items and not any(normalize_repo_url(item.get("url")) for item in feed_items):
            # A run that ends at zero every cycle looks like a quiet day: fail it instead.
            raise ETLError(f"None of the {len(feed_items)} feed posts names a repository: the feed's markup changed", etl_name=self.name, phase="extract")
        if self._has_gap(stored, feed_items):
            self._read_listing(stored, work, backfill=self._is_backfill(stored, feed_items))
        self._complete_details(stored, work)
        self._complete_github(stored, work)
        return list(work.values())

    def _add(self, work: dict[str, dict[str, Any]], stored: dict[str, dict[str, Any]], item: dict[str, Any]) -> bool:
        """Take a raw record into the run unless it names no repository or one already known."""
        key = normalize_repo_url(item.get("url"))
        if not key or key in stored or key in work:
            return False
        item["_key"] = key
        work[key] = item
        return True

    def _touch(self, work: dict[str, dict[str, Any]], record: dict[str, Any]) -> None:
        """Mark a stored record as changed in this run, keeping its identity and its first-seen date."""
        record.setdefault("_key", normalize_repo_url(record.get("url")))
        record["updated_at"] = _utc_now()
        work[record["_key"]] = record

    def _read_feed(self) -> list[dict[str, Any]]:
        """The latest posts from the Atom feed, or from the RSS one; a site that offers neither is an error, not an empty day."""
        failures: list[str] = []
        for url in (FEED_URL, RSS_URL):
            try:
                items = parse_feed(self._get(url))
            except requests.RequestException as error:
                failures.append(f"{url}: {error}")
                continue
            if items:
                return items
            failures.append(f"{url}: no entry")
        raise ETLError(f"opensourceprojects.dev gave no feed entry: {'; '.join(failures)}", etl_name=self.name, phase="extract")

    def _boundaries(self, stored: dict[str, dict[str, Any]], feed_items: list[dict[str, Any]]) -> tuple[datetime | None, datetime | None]:
        """The date of the newest stored post and of the oldest one in the feed, both naive in UTC."""
        feed_dates = [date for date in (_naive_utc_text(item.get("published_at")) for item in feed_items) if date]
        oldest_feed = min(feed_dates, default=None)
        newest_stored = max((_naive_utc_text(record.get("published_at")) for record in stored.values()), key=lambda moment: moment or datetime.min, default=None)
        return newest_stored, oldest_feed

    def _has_gap(self, stored: dict[str, dict[str, Any]], feed_items: list[dict[str, Any]]) -> bool:
        """Whether the listing has posts newer than every stored one: a first run, or days without a run."""
        newest_stored, oldest_feed = self._boundaries(stored, feed_items)
        return oldest_feed is not None and (newest_stored is None or newest_stored < oldest_feed - timedelta(days=GAP_DAYS))

    def _is_backfill(self, stored: dict[str, dict[str, Any]], feed_items: list[dict[str, Any]]) -> bool:
        """Whether the stored posts are so old that the listing is read to its last page.

        The walk normally stops at the first page it knows entirely. That page can sit above
        older ones that were never seen (the scraper before T-204 left holes), so a file
        whose newest post is a month behind, or no file at all, is completed from everything.
        """
        newest_stored, oldest_feed = self._boundaries(stored, feed_items)
        return oldest_feed is not None and (newest_stored is None or newest_stored < oldest_feed - timedelta(days=BACKFILL_DAYS))

    def _read_listing(self, stored: dict[str, dict[str, Any]], work: dict[str, dict[str, Any]], backfill: bool = False) -> int:
        """Walk the listing from the newest page until one holds nothing new (or to the last page when ``backfill``); returns the repositories added.

        A page that cannot be read, or whose cards are no longer recognised, only ends
        the walk: the feed is the source that must work.
        """
        added = 0
        pages = 0
        started = _utc_now()
        for page in range(1, self.max_listing_pages + 1):
            pages = page
            url = f"{self.base_url}/?page={page}" if page > 1 else self.base_url
            try:
                items = parse_listing(self._get(url), self.base_url)
            except requests.RequestException as error:
                self.logger.error(f"Listing page {page} could not be read, the walk stops here: {error}")
                break
            if not items:
                if page == 1:
                    self.logger.error("The listing holds no project card: its markup changed, and the backlog cannot be read until the parser follows.")
                break
            # Judged against what the file holds, not against this run's feed: the
            # feed and the newest page name the same posts, and the pages under
            # them hold the batches missed while no run happened.
            unseen = [item for item in items if normalize_repo_url(item.get("url")) not in stored]
            added += sum(self._add(work, stored, item) for item in unseen)
            if not unseen and not backfill:
                break  # a page entirely known: everything under it was read before
            time.sleep(self.listing_delay_seconds)
        self.logger.info(f"Listing: {added} repositories added from {pages} pages in {(_utc_now() - started).total_seconds():.0f} s" + (" (the whole listing)" if backfill else ""))
        return added

    def _complete_details(self, stored: dict[str, dict[str, Any]], work: dict[str, dict[str, Any]]) -> int:
        """Read the post page of the records that have none yet, newest first, up to the run's budget."""
        pending = [record for record in work.values() if record.get("post_url") and not record.get("detail_fetched")]
        pending += sorted(
            (record for key, record in stored.items() if key not in work and record.get("post_url") and not record.get("detail_fetched")),
            key=lambda record: _naive_utc_text(record.get("published_at")) or datetime.min,
            reverse=True,
        )
        done = 0
        for record in pending:
            if done >= self.post_details_per_run:
                break
            try:
                page = parse_post_page(self._get(record["post_url"]))
            except requests.RequestException as error:
                self.logger.warning(f"Post page {record['post_url']} could not be read, the rest waits for the next run: {error}")
                break
            record["detail_fetched"] = True
            for field in ("description", "views_count", "published_at"):
                if page.get(field) is not None:
                    record[field] = page[field]
            self._touch(work, record)
            done += 1
        if pending:
            self.logger.info(f"Post pages: {done} read, {max(0, len(pending) - done)} waiting")
        return done

    def _complete_github(self, stored: dict[str, dict[str, Any]], work: dict[str, dict[str, Any]], now: datetime | None = None) -> int:
        """Ask GitHub about the repositories that are due, newest first, while the hour's budget lasts."""
        now = now or _utc_now()

        def is_github(record: dict[str, Any]) -> bool:
            return (urlparse(str(record.get("url") or "")).hostname or "").lower() == "github.com"

        candidates = [*work.values(), *(record for key, record in stored.items() if key not in work)]
        pending = sorted(
            (record for record in candidates if record.get("url") and is_github(record) and _github_due(record, now)),
            key=lambda record: _naive_utc_text(record.get("published_at")) or datetime.min,
            reverse=True,
        )
        budget = self.github_lookups_per_run * (10 if self.github_token else 1)
        done = 0
        for record in pending:
            if done >= budget:
                break
            response = self._github_request(record["url"])
            if response is None:
                break
            # The header is text ("59"); anything else is no answer.
            raw_remaining = response.headers.get("X-RateLimit-Remaining")
            remaining = int(raw_remaining) if isinstance(raw_remaining, str) and raw_remaining.strip().isdigit() else None
            if response.status_code == 404:
                record["github_checked_at"] = now  # deleted, renamed or made private: nothing to ask again
                self._touch(work, record)
                continue
            try:
                payload = response.json()
            except ValueError:
                payload = None
            if response.status_code != 200 or not isinstance(payload, dict):
                self.logger.warning(f"GitHub answered {response.status_code} for {record['url']}; the rest waits for the next run")
                break
            done += 1
            info = parse_github_repo(payload)
            record.update({field: value for field, value in info.items() if field not in ("repo_description", "full_name")})
            if info["repo_description"] and (_is_placeholder(record.get("description")) or str(record.get("description")).strip() == str(record.get("title")).strip()):
                record["description"] = plain_excerpt(info["repo_description"], _EXCERPT_LIMIT)
            if info["full_name"] and _is_placeholder(record.get("title")):
                record["title"] = info["full_name"]
            record["github_checked_at"] = now
            self._touch(work, record)
            if remaining is not None and remaining < _GITHUB_SAFETY:
                self.logger.info(f"GitHub has {remaining} requests left this hour; the rest waits for the next run")
                break
        if pending:
            self.logger.info(f"GitHub: {done} repositories asked, {max(0, len(pending) - done)} waiting")
        return done

    # -- transform ---------------------------------------------------------------------
    def transform(self, data: list[dict[str, Any]]) -> list[OpenSourceProjectItem]:
        """Raw records as models, their title and description plain text; one that does not fit is dropped with its URL in the log. A date keeps the zone it came with."""
        transformed: list[OpenSourceProjectItem] = []
        for raw in data:
            fields = {field: value for field, value in raw.items() if not field.startswith("_")}
            for field in ("title", "description"):
                if field in fields:
                    fields[field] = _decoded_once(fields[field])
            try:
                transformed.append(OpenSourceProjectItem(**fields))
            except ValidationError as error:
                self.logger.warning(f"Record dropped, it does not fit the model ({raw.get('url')}): {error.error_count()} invalid field(s)")
        return transformed

    # -- load --------------------------------------------------------------------------
    def load(self, data: list[OpenSourceProjectItem]) -> None:
        """Merge this run's records into ``latest.json``, newest first.

        This run's record replaces the stored one of the same repository; every other
        stored record stays as it was; an entry that is not a record is kept at the end.
        """
        stored, kept = self._read_latest()
        if self.repeated_stored:
            self.logger.info(f"Stored records that repeat a repository already in the file: {self.repeated_stored} (the first one of each is kept)")
        if self.repaired_stored:
            self.logger.info(f"Stored records that linked to a web search instead of their repository: {self.repaired_stored} (repaired)")
        if self.decoded_stored:
            self.logger.info(f"Stored records whose title or description kept an HTML entity: {self.decoded_stored} (decoded)")
        merged: dict[str, OpenSourceProjectItem] = {}
        unreadable = 0
        for key, entry in stored.items():
            try:
                merged[key] = OpenSourceProjectItem(**entry)
            except ValidationError:
                kept.append(entry)
                unreadable += 1
        for item in data:
            merged[normalize_repo_url(item.url)] = item
        if unreadable:
            self.logger.warning(f"{unreadable} stored entries are not records; they are kept at the end of the file untouched")
        ordered = sorted(merged.values(), key=_sort_key, reverse=True)
        payload = [item.dict_without_none() for item in ordered] + kept
        text = json.dumps(payload, indent=2, default=str)
        # Only latest.json: a copy per run would be 2 MB every cycle, kept ninety days.
        _write_atomically(self.output_dir / "latest.json", text)
        self.logger.info(f"Saved {len(payload)} items ({len(data)} from this run) to latest.json")


if __name__ == "__main__":
    OpenSourceProjectsETL().run()
