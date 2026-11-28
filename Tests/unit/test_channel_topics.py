"""Tests for the theme definition the goldigging YouTube ETL and the Videos tab share (T-138).

Reads the real ``src/etl/goldigging/channels.json`` — a tracked config file, not data — and nothing else: no
network. The tab used to tell a theme by the ``aa-``/``zz-`` prefix of the directory name, which left the ``z-``
themes out of its Tema dropdown; a theme is now a key of that file, whichever prefix it has. Its description
comes from the same file, for the label the dropdown shows.
"""

import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from src.etl.goldigging import channel_topics
from src.etl.goldigging.channel_topics import CHANNELS_JSON, _read_topics, is_theme, load_channel_topics, theme_description, theme_names

GOLDIGGING_DIR = Path(__file__).resolve().parents[2] / "src" / "etl" / "goldigging"


@pytest.fixture
def real_themes() -> Iterator[frozenset[str]]:
    """The theme keys read afresh from the real file, with the cache dropped again afterwards."""
    _read_topics.cache_clear()
    yield theme_names()
    _read_topics.cache_clear()


@contextmanager
def pinned_loader(monkeypatch: pytest.MonkeyPatch, loader) -> Iterator[None]:
    """Answer ``load_channel_topics`` from ``loader``, with the file cache dropped around it."""
    with monkeypatch.context() as patch:
        patch.setattr(channel_topics, "load_channel_topics", loader)
        _read_topics.cache_clear()
        try:
            yield
        finally:
            _read_topics.cache_clear()


# ---------------------------------------------------------------------------
# The real file
# ---------------------------------------------------------------------------


def test_the_config_file_sits_next_to_the_helper():
    assert CHANNELS_JSON == GOLDIGGING_DIR / "channels.json"
    assert CHANNELS_JSON.is_file()


def test_theme_names_are_the_keys_of_the_real_file(real_themes):
    assert real_themes == frozenset(load_channel_topics())
    assert len(real_themes) > 1


def test_every_listed_key_is_a_theme(real_themes):
    """Whatever the file lists today is a theme: the test follows the file, so a renamed theme stays covered."""
    assert all(is_theme(theme) for theme in real_themes)


def test_the_file_is_read_as_utf8():
    """The file holds non-ASCII handles: opened in a single-byte locale they come out mangled.

    The ETL used to open it without an encoding, which on Windows reads it as cp1252.
    """
    raw = CHANNELS_JSON.read_bytes()
    assert load_channel_topics() == json.loads(raw.decode("utf-8"))
    if any(byte > 127 for byte in raw):
        assert load_channel_topics() != json.loads(raw.decode("latin-1"))


# ---------------------------------------------------------------------------
# What makes a theme
# ---------------------------------------------------------------------------


def test_a_key_is_a_theme_whatever_its_prefix(monkeypatch):
    """The ETL writes one directory per key: the prefix orders the file and nothing reads it."""
    keys = {"aa-dev", "z-sleepcore", "zz-memes", "zzz-alotof", "sin-prefijo"}
    with pinned_loader(monkeypatch, lambda: {key: {"description": key, "channels": []} for key in keys}):
        assert theme_names() == frozenset(keys)
        assert all(is_theme(key) for key in keys)


def test_a_theme_is_recognised_by_its_whole_key(monkeypatch):
    with pinned_loader(monkeypatch, lambda: {"zz-memes": {"description": "Memes", "channels": []}}):
        assert is_theme("zz-memes") is True
        assert is_theme("zz-memes-videos") is False  # another directory, not a listed key
        assert is_theme("zz-mem") is False
        assert is_theme("ZZ-Memes") is False  # directory names are case-sensitive
        assert is_theme("") is False


def test_a_prefix_alone_makes_no_theme(real_themes):
    """The rule the prefix test replaced: a directory named like a theme is one only if the file lists it."""
    unlisted = [name for name in ("zz-unlisted", "z-unlisted", "aa-unlisted") if name not in real_themes]
    assert unlisted, "these names are listed in channels.json: pick other unlisted ones"
    assert not any(is_theme(name) for name in unlisted)


def test_the_keys_do_not_nest():
    """No key may start with another key and a dash: the tab folds ``<theme>-*`` directories into that theme."""
    keys = sorted(load_channel_topics())
    nested = [(outer, inner) for outer in keys for inner in keys if inner.startswith(f"{outer}-")]
    assert nested == []


# ---------------------------------------------------------------------------
# A file that cannot be read
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failure", [OSError("cannot read channels.json"), ValueError("Expecting value")], ids=["missing", "malformed"])
def test_an_unreadable_file_yields_no_themes_and_a_warning(monkeypatch, caplog, failure):
    """The dashboard must keep working: no themes, and a warning that says why."""

    def broken():
        raise failure

    with pinned_loader(monkeypatch, broken), caplog.at_level(logging.WARNING, logger=channel_topics.__name__):
        assert theme_names() == frozenset()
        assert is_theme("aa-dev") is False
        assert theme_description("aa-dev") == ""
    assert "Channel topics could not be read" in caplog.text
    assert "channels.json" in caplog.text


def test_the_keys_are_read_once_per_process(monkeypatch):
    """Four lookups, one read: the tab asks per directory on every render."""
    reads = []

    def counting():
        reads.append(1)
        return {"aa-dev": {"description": "dev", "channels": []}}

    with pinned_loader(monkeypatch, counting):
        assert is_theme("aa-dev") and is_theme("MatthewBerman") is False and theme_names() == frozenset({"aa-dev"})
        assert theme_description("aa-dev") == "dev"
    assert len(reads) == 1


# ---------------------------------------------------------------------------
# The description of a theme
# ---------------------------------------------------------------------------


def test_every_listed_key_has_its_own_description(real_themes):
    """The Tema dropdown shows it: a theme without one would read as its key, a directory name."""
    descriptions = {theme: theme_description(theme) for theme in real_themes}

    assert all(descriptions.values())
    assert len(set(descriptions.values())) == len(descriptions), "two themes share a description"


def test_a_description_is_read_from_the_file():
    assert theme_description("zz-anime") == "Anime"  # pinned: what the tab shows next to the key


@pytest.mark.parametrize("theme", ["zz-unlisted", "zz-anime-videos", "", "ZZ-Anime"])
def test_a_key_that_is_no_theme_has_no_description(monkeypatch, theme):
    with pinned_loader(monkeypatch, lambda: {"zz-anime": {"description": "Anime", "channels": []}}):
        assert theme_description(theme) == ""


def test_a_description_is_trimmed(monkeypatch):
    with pinned_loader(monkeypatch, lambda: {"zz-food": {"description": "  Food Reviews\n", "channels": []}}):
        assert theme_description("zz-food") == "Food Reviews"


@pytest.mark.parametrize(
    "topic", [{"channels": []}, {"description": ""}, {"description": None}, {"description": "  "}, "not a mapping", None], ids=["absent", "empty", "null", "blank", "not-a-mapping", "null-entry"]
)
def test_no_description_is_invented_for_a_key_that_has_none(monkeypatch, topic):
    with pinned_loader(monkeypatch, lambda: {"zz-food": topic}):
        assert theme_description("zz-food") == ""


# ---------------------------------------------------------------------------
# The ETL reads the same definition
# ---------------------------------------------------------------------------


def test_the_etl_loads_its_topics_through_the_shared_helper():
    """The ETL must not grow a second loader: one definition, next to the file."""
    source = (GOLDIGGING_DIR / "goldigging_youtube_posts.py").read_text(encoding="utf-8")
    assert "from src.etl.goldigging.channel_topics import load_channel_topics" in source
    assert not re.search(r"^def load_channel_topics", source, flags=re.MULTILINE)
    assert "CHANNEL_TOPICS = load_channel_topics()" in source
