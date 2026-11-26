"""Regression tests for imports of the src/miners/udemy-universal package.

The miner directory name contains a hyphen, so it cannot be imported through
the normal ``src.miners`` dotted path. These tests load it under the synthetic
package name ``udemy_universal`` and assert that every module of the package
imports cleanly WITHOUT the optional libraries.

Four of them are the optional browser/credential libraries (browser_cookie3,
browserforge, keyring, rookiepy): intentionally NOT project dependencies (the
miner is optional by design and the repo policy is lean/keyless deps). The
fifth is colorama: in ``uv.lock`` it is only a Windows dependency, so it is
present on a Windows checkout and absent on Linux — the CI runner and the
production image. Each module that uses one of them must guard the import at
module level with a ``HAS_<LIB>`` flag and degrade gracefully at runtime.

The tests block all five for real (``sys.modules[name] = None`` makes
``import name`` raise ImportError) instead of trusting the machine they run
on: a Windows checkout has colorama, which is how that gap reached CI.
"""

import importlib
import importlib.util
import pkgutil
import sys
from pathlib import Path

import pytest

PACKAGE_NAME = "udemy_universal"
PACKAGE_DIR = Path(__file__).resolve().parents[2] / "src" / "miners" / "udemy-universal"

# Minimum number of importable names expected in the package tree (top-level
# modules + subpackages + submodules). Guards against discovery silently
# returning an empty/partial list.
EXPECTED_MIN_MODULES = 25

# Optional libraries mapped to (module, flag) that must expose a HAS_* flag.
# The flag must be False whenever the library is not installed.
OPTIONAL_LIBS = {
    "browser_cookie3": ("udemy_universal.cookie_manager", "HAS_BROWSER_COOKIE3"),
    "browserforge": ("udemy_universal.cookie_manager", "HAS_BROWSERFORGE"),
    "keyring": ("udemy_universal.cookie_manager", "HAS_KEYRING"),
    "rookiepy": ("udemy_universal.base", "HAS_ROOKIEPY"),
    "colorama": ("udemy_universal.colors", "HAS_COLORAMA"),
}

# Every shorthand colors.py defines (foreground, background, style).
COLOR_SHORTHANDS = ("fc", "fg", "fw", "fr", "fb", "flb", "fbl", "fy", "fm", "flg", "bc", "bg", "bw", "br", "bb", "by", "bm", "sd", "sn", "sb")

pytestmark = pytest.mark.skipif(not PACKAGE_DIR.is_dir(), reason="src/miners/udemy-universal package not present")


@pytest.fixture(scope="module")
def udemy_package():
    """Import the hyphen-named miner package under a synthetic module name.

    Yields:
        module: The imported ``udemy_universal`` package module.
    """
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        PACKAGE_DIR / "__init__.py",
        submodule_search_locations=[str(PACKAGE_DIR)],
    )
    assert spec is not None, f"could not build import spec for {PACKAGE_DIR}"
    assert spec.loader is not None, f"spec for {PACKAGE_DIR} has no loader"
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        del sys.modules[PACKAGE_NAME]
        for name in [n for n in sys.modules if n.startswith(f"{PACKAGE_NAME}.")]:
            del sys.modules[name]


def _without_optional_libs(monkeypatch: pytest.MonkeyPatch, libs: tuple[str, ...]) -> None:
    """Make each library in ``libs`` unimportable and forget the package's submodules, so they are imported again."""
    for lib in libs:
        monkeypatch.setitem(sys.modules, lib, None)  # importlib raises ImportError for a None entry
    for name in [n for n in sys.modules if n.startswith(f"{PACKAGE_NAME}.")]:
        monkeypatch.delitem(sys.modules, name)


@pytest.mark.usefixtures("udemy_package")
def test_all_modules_import_without_optional_libs(monkeypatch: pytest.MonkeyPatch):
    """Every module in the package imports cleanly with every optional lib absent."""
    _without_optional_libs(monkeypatch, tuple(OPTIONAL_LIBS))
    package = importlib.import_module(PACKAGE_NAME)
    discovered = [name for _, name, _ in pkgutil.walk_packages(package.__path__, prefix=f"{PACKAGE_NAME}.")]
    assert len(discovered) >= EXPECTED_MIN_MODULES, f"module discovery looks broken, found only: {discovered}"

    failures = []
    for name in discovered:
        try:
            importlib.import_module(name)
        except Exception as exc:  # Collect every import failure for the report.
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    assert not failures, "modules failed to import:\n" + "\n".join(sorted(failures))


@pytest.mark.usefixtures("udemy_package")
def test_optional_lib_flags_present_and_false_when_absent(monkeypatch: pytest.MonkeyPatch):
    """Each module using an optional lib exposes a HAS_* flag, False when the lib is missing."""
    _without_optional_libs(monkeypatch, tuple(OPTIONAL_LIBS))
    for lib, (module_name, flag) in OPTIONAL_LIBS.items():
        module = importlib.import_module(module_name)
        assert hasattr(module, flag), f"{module_name} must define {flag} for optional lib {lib}"
        assert getattr(module, flag) is False, f"{flag} must be False when {lib} is not installed"


@pytest.mark.usefixtures("udemy_package")
def test_colors_degrade_to_plain_text_without_colorama(monkeypatch: pytest.MonkeyPatch):
    """Without colorama every shorthand is an empty string: the CLI prints, just uncolored."""
    _without_optional_libs(monkeypatch, ("colorama",))
    colors = importlib.import_module(f"{PACKAGE_NAME}.colors")
    assert colors.HAS_COLORAMA is False
    plain = {name: getattr(colors, name) for name in COLOR_SHORTHANDS}
    assert all(value == "" for value in plain.values()), f"shorthands must be empty without colorama, got: {plain!r}"
    assert importlib.import_module(f"{PACKAGE_NAME}.base").VERSION  # base imports eight of them at module level
