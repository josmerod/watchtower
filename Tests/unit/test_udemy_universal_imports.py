"""Regression tests for imports of the src/miners/udemy-universal package.

The miner directory name contains a hyphen, so it cannot be imported through
the normal ``src.miners`` dotted path. These tests load it under the synthetic
package name ``udemy_universal`` and assert that every module of the package
imports cleanly WITHOUT the optional browser/credential libraries
(browser_cookie3, browserforge, keyring, rookiepy).

Those four libraries are intentionally NOT project dependencies (the miner is
optional by design and the repo policy is lean/keyless deps): each module that
uses them must guard the import at module level with a ``HAS_<LIB>`` flag and
degrade gracefully at runtime.
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
}

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


def test_package_init_imports(udemy_package):
    """The package __init__ (config, domain, infrastructure, scrapers, services) imports cleanly."""
    assert getattr(udemy_package, "__version__", None)


@pytest.mark.usefixtures("udemy_package")
def test_all_modules_import_without_optional_libs():
    """Every module in the package imports cleanly with the four optional libs absent."""
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
def test_optional_lib_flags_present_and_false_when_absent():
    """Each module using an optional lib exposes a HAS_* flag, False when the lib is missing."""
    for lib, (module_name, flag) in OPTIONAL_LIBS.items():
        module = importlib.import_module(module_name)
        assert hasattr(module, flag), f"{module_name} must define {flag} for optional lib {lib}"
        if importlib.util.find_spec(lib) is None:
            assert getattr(module, flag) is False, f"{flag} must be False when {lib} is not installed"
