"""Compatibility namespace for the canonical ``core.dependency_resolver`` package."""
from __future__ import annotations

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parent.parent / "core" / "dependency_resolver")]

from core.dependency_resolver import *  # noqa: F401,F403,E402
from core.dependency_resolver import __all__  # noqa: E402
