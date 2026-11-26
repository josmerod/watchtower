"""Unit tests for the saved-items file snapshot (T-136).

``is_saved()`` runs once per rendered row in every tab that shows a star
(Knowledge Garden, News "🔎 Global", Tech Radar, Markets), and each call used to
read and parse ``saved_items.json`` again: 514 reads for one Knowledge Garden
render. The list is now re-read only when the file changed. Fixtures only:
the file is a path-like stand-in, nothing touches data/.
"""

import json
from types import SimpleNamespace

import pytest

from src.web.dashboard.components import knowledge_garden_tab as tab
from src.web.dashboard.components import saved_items
from src.web.dashboard.components.saved_items import SAVE_CANDIDATES


class _FakeFile:
    """Path-like stand-in for saved_items.json that counts reads.

    ``stat()`` keeps reporting the size given at construction, so a rewrite
    that ends up with the same length keeps the same (mtime, size) stamp: the
    case the write counter exists for.
    """

    def __init__(self, text="[]"):
        self.text = text
        self.reads = 0
        self.mtime_ns = 1_000_000_000_000_000_000
        self.size = len(text)
        self.parent = self

    def stat(self):
        if self.text is None:
            raise OSError("no such file")
        return SimpleNamespace(st_mtime_ns=self.mtime_ns, st_size=self.size)

    def read_text(self, encoding="utf-8"):
        self.reads += 1
        if self.text is None:
            raise OSError("no such file")
        return self.text

    def mkdir(self, **_kwargs):
        return None

    def write_text(self, text, encoding="utf-8"):
        self.text = text
        return len(text)


@pytest.fixture
def saved_file(monkeypatch):
    """Point the saved-items store at a stand-in file with a clean registry."""
    fake = _FakeFile()
    monkeypatch.setattr(saved_items, "SAVED_FILE", fake)
    # Not only polite: the stand-in's stamp is its repr, and a reused memory
    # address would make a new file look like the previous test's.
    monkeypatch.setattr(saved_items, "_saved_stamp", None)
    SAVE_CANDIDATES.clear()
    yield fake
    SAVE_CANDIDATES.clear()


def _record(title):
    return {"hash": saved_items.item_hash(None, title), "title": title, "url": None, "source": "", "saved_at": "2026-08-28T10:00:00", "tab": "news"}


def _buttons(file, titles):
    return {title: saved_items.save_button({"title": title}, "kg-save-btn", tab="knowledge_garden").children for title in titles}


# ---------------------------------------------------------------------------
# One read per unchanged file
# ---------------------------------------------------------------------------


def test_many_lookups_read_the_file_once(saved_file):
    saved_file.text = json.dumps([_record("Saved one"), _record("Saved two")])

    stars = _buttons(saved_file, [f"Item {n}" for n in range(50)] + ["Saved one", "Saved two"])

    assert saved_file.reads == 1
    assert stars["Saved one"] == "★" and stars["Saved two"] == "★"
    assert all(stars[f"Item {n}"] == "☆" for n in range(50))
    assert all(saved_items.is_saved(_record(title)["hash"]) for title in ("Saved one", "Saved two"))
    assert saved_file.reads == 1


def test_missing_file_is_empty_until_something_is_saved(saved_file):
    saved_file.text = None

    assert saved_items.load_saved() == []
    assert _buttons(saved_file, ["Fresh"])["Fresh"] == "☆"
    assert saved_file.reads == 0  # nothing to read: stat() already says the file is not there
    assert saved_items.toggle_saved({"title": "New", "url": "http://example.com/new", "tab": "news"}) is True
    assert [s["title"] for s in saved_items.load_saved()] == ["New"]


def test_unreadable_file_is_empty_until_fixed(saved_file):
    saved_file.text = "{ not json"

    assert saved_items.load_saved() == []
    assert saved_items.load_saved() == []
    assert saved_file.reads == 2  # a broken file is never cached

    saved_file.text = json.dumps([_record("Fixed")])
    assert [s["title"] for s in saved_items.load_saved()] == ["Fixed"]


def test_non_list_file_is_empty(saved_file):
    saved_file.text = json.dumps({"not": "a list"})

    assert saved_items.load_saved() == []


# ---------------------------------------------------------------------------
# Every way the file can change is noticed
# ---------------------------------------------------------------------------


def test_another_file_at_the_same_stamp_is_read_again(monkeypatch):
    first, second = _FakeFile(json.dumps([_record("In the first file")])), _FakeFile(json.dumps([_record("In the second file")]))
    monkeypatch.setattr(saved_items, "SAVED_FILE", first)
    SAVE_CANDIDATES.clear()

    stars_one = _buttons(first, ["In the first file"])
    monkeypatch.setattr(saved_items, "SAVED_FILE", second)
    stars_two = _buttons(second, ["In the first file", "In the second file"])

    assert stars_one == {"In the first file": "★"}
    assert stars_two == {"In the first file": "☆", "In the second file": "★"}
    assert (first.reads, second.reads) == (1, 1)


def test_external_change_is_read_again(saved_file):
    saved_file.text = json.dumps([_record("Before")])
    assert saved_items.is_saved(_record("Before")["hash"]) is True

    saved_file.text = json.dumps([_record("Before"), _record("After")])  # e.g. restored from a backup
    saved_file.size = len(saved_file.text)

    assert saved_items.is_saved(_record("After")["hash"]) is True
    assert saved_file.reads == 2


def test_write_with_an_unchanged_stamp_is_read_again(saved_file):
    # stat() reports the same (mtime, size) before and after each write: only
    # the write counter can tell the star toggles happened.
    saved_file.text = json.dumps([_record("Anna")])
    assert saved_items.is_saved(_record("Anna")["hash"]) is True
    reads = saved_file.reads

    assert saved_items.toggle_saved({"title": "Otto", "url": None, "tab": "news"}) is True
    assert saved_items.is_saved(_record("Otto")["hash"]) is True
    assert saved_file.reads == reads + 1

    assert saved_items.toggle_saved({"title": "Otto", "url": None, "tab": "news"}) is False
    assert saved_items.is_saved(_record("Otto")["hash"]) is False
    assert saved_items.is_saved(_record("Anna")["hash"]) is True
    assert saved_file.reads == reads + 2


def test_records_come_back_newest_first_after_every_change(saved_file):
    saved_items.toggle_saved({"title": "First", "tab": "news"})
    saved_items.toggle_saved({"title": "Second", "tab": "news"})

    assert [s["title"] for s in saved_items.load_saved()] == ["Second", "First"]


# ---------------------------------------------------------------------------
# The list handed out stays private
# ---------------------------------------------------------------------------


def test_each_caller_gets_its_own_list(saved_file):
    saved_file.text = json.dumps([_record("Kept")])

    first = saved_items.load_saved()
    first.append(_record("Added by a caller"))
    first[0]["title"] = "Renamed by a caller"

    assert [s["title"] for s in saved_items.load_saved()] == ["Kept"]


# ---------------------------------------------------------------------------
# What it buys: one table render
# ---------------------------------------------------------------------------


def test_one_table_render_reads_the_file_once(saved_file, monkeypatch):
    items = [{"title": f"Item {n:02d}", "url": f"http://example.com/{n:02d}", "source": "LessWrong", "published": f"2026-08-{1 + n // 24:02d}T{n % 24:02d}:00:00"} for n in range(60)]
    monkeypatch.setattr(tab, "get_all_knowledge_data", lambda force_refresh=False: {"lesswrong": [dict(item) for item in items]})
    saved_items.toggle_saved({"title": "Item 40", "url": "http://example.com/40", "tab": "knowledge_garden"})  # on the first page (newest first)
    saved_file.reads = 0

    content, _page = tab.build_knowledge_table("lesswrong", display_name="LessWrong")

    buttons = [n for n in _walk(content) if getattr(n, "data-kg-hash", None)]  # the garden's stars are plain buttons (T-136)
    assert len(buttons) == tab.MAX_ARTICLES_PER_SOURCE
    assert [b.children for b in buttons].count("★") == 1
    assert saved_file.reads == 1


def _walk(node):
    """Yield every node of a Dash component tree."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    for child in children if isinstance(children, (list, tuple)) else [children]:
        yield from _walk(child)
