"""The repositories' cache ends when the file changes, not only when its hour is over (T-197).

Measured on 2026-11-27: BaseRepository cached for 3600 s by the clock alone (CacheEntry.is_expired() asked datetime.utcnow() and
nothing else; get_last_modified() was never consulted), so after a cycle rewrote a file the tab kept the previous data for up to an
hour. Knowledge Garden puts a 60 s cache on top and Tech Radar a 300 s one; Games, Scavenging, Valencia Events, Aid, Shortcuts and
4chan read the repositories directly. The entry now remembers the version of the file it was read from (mtime in nanoseconds and
size) and a different one ends it early. A file that is gone keeps the cache until the TTL, as before.
Fixtures only: files written under tmp_path, the clock in the test's hand, nothing under data/.
"""

import json
import os
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.repositories import base_repository
from src.repositories.base_repository import BaseRepository, DataFrameRepository, RepositoryError


class ListRepository(BaseRepository[list]):
    """The smallest concrete repository: a JSON list read as it is, counting its reads."""

    def __init__(self, path, **kwargs):
        super().__init__(data_path=path, **kwargs)
        self.reads = 0

    def transform_data(self, raw_data):
        """The list as it came from the file."""
        return raw_data

    def _load_from_file(self):
        self.reads += 1
        return super()._load_from_file()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The module's clock in the test's hand: it asks ``datetime.utcnow()`` for the time."""
    hand = SimpleNamespace(now=datetime(2026, 11, 27, 23, 0, 0))
    monkeypatch.setattr(base_repository, "datetime", SimpleNamespace(utcnow=lambda: hand.now))
    return hand


def _write(path, rows) -> None:
    path.write_text(json.dumps(rows), encoding="utf-8")


def _write_same_time(path, before, rows) -> None:
    """Rewrite the file and put its modification time back where it was."""
    _write(path, rows)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))


def test_a_rewritten_file_is_read_again_within_the_hour(tmp_path) -> None:
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path)
    assert repo.get() == [{"title": "Old deal"}]

    _write(path, [{"title": "Old deal"}, {"title": "New deal"}])  # the cycle wrote the file

    assert repo.get() == [{"title": "Old deal"}, {"title": "New deal"}]
    assert repo.reads == 2


def test_an_untouched_file_is_read_once(tmp_path) -> None:
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path)

    first = repo.get()

    assert repo.get() is first
    assert repo.reads == 1


def test_the_time_alone_tells_a_rewritten_file_apart(tmp_path) -> None:
    """A pipeline may write the same bytes: the size would not move, the modification time does."""
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path)
    first = repo.get()

    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000_000))

    second = repo.get()
    assert second == first and second is not first
    assert repo.reads == 2


def test_the_size_alone_tells_a_rewritten_file_apart(tmp_path) -> None:
    """A file system that keeps the same time when a file is rewritten within one tick still changes the size."""
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path)
    first = repo.get()

    _write_same_time(path, path.stat(), [{"title": "Old deal"}, {"title": "New deal"}])

    second = repo.get()
    assert len(second) == 2 and second is not first
    assert repo.reads == 2


def test_a_deleted_file_keeps_serving_what_was_read_until_the_hour(tmp_path, clock) -> None:
    """Gone is not changed: the last good data is shown until the TTL, as before."""
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path)
    first = repo.get()

    path.unlink()

    assert repo.get() is first
    assert repo.reads == 1
    clock.now += timedelta(hours=2)
    with pytest.raises(RepositoryError):
        repo.get()


def test_the_hour_still_ends_the_cache(tmp_path, clock) -> None:
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path)
    first = repo.get()

    clock.now += timedelta(hours=2)

    second = repo.get()
    assert second == first and second is not first
    assert repo.reads == 2


def test_the_refresh_button_still_reads_again(tmp_path) -> None:
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path)

    repo.get()
    repo.get(force_refresh=True)

    assert repo.reads == 2


def test_without_cache_nothing_is_kept(tmp_path) -> None:
    path = tmp_path / "deals.json"
    _write(path, [{"title": "Old deal"}])
    repo = ListRepository(path, enable_cache=False)

    first = repo.get()
    second = repo.get()

    assert second == first and second is not first
    assert repo.reads == 2


def test_a_csv_repository_is_told_apart_the_same_way(tmp_path) -> None:
    """The subclasses inherit it: a DataFrame repository over CSV."""
    path = tmp_path / "coins.csv"
    path.write_text("name\nBitcoin\n", encoding="utf-8")
    repo = DataFrameRepository(path)
    assert len(repo.get()) == 1

    path.write_text("name\nBitcoin\nEther\n", encoding="utf-8")

    assert len(repo.get()) == 2
