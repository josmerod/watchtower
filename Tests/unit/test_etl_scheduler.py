"""Unit tests for deployment/etl_scheduler.py (T-114 interval handling)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from deployment import etl_scheduler


def test_interval_default_is_two_hours(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env set → today's effective cadence (7200 s), no behavior change."""
    monkeypatch.delenv("WATCHTOWER_ETL_INTERVAL", raising=False)
    assert etl_scheduler.get_interval() == 7200


def test_interval_honors_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The documented variable finally takes effect in the container (T-114)."""
    monkeypatch.setenv("WATCHTOWER_ETL_INTERVAL", "1800")
    assert etl_scheduler.get_interval() == 1800


def test_interval_invalid_value_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WATCHTOWER_ETL_INTERVAL", "two hours")
    assert etl_scheduler.get_interval() == 7200
