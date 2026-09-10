"""Alert system for Megalith Watchtower.

This package provides the shared alert-rule store (``rules_store``) that both
the Notifications tab and the watchers/security ETLs read and write, plus the
Pydantic models for rules and events.
"""

from . import rules_store

__all__ = ["rules_store"]
