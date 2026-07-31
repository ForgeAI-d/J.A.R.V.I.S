"""Safe handling of optional Python dependencies in tests.

Some third-party packages terminate the interpreter with ``SystemExit`` during
import instead of raising ``ImportError``. These helpers convert such behaviour
into a normal pytest skip and suppress installation hints printed by imports.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from importlib import import_module
from io import StringIO
from types import ModuleType
from typing import Final

import pytest


@dataclass(frozen=True, slots=True)
class OptionalDependency:
    """Result of a non-fatal optional dependency probe."""

    name: str
    available: bool
    module: ModuleType | None = None
    reason: str | None = None
    output: str = ""


_IMPORT_FAILURES: Final = (ImportError, ModuleNotFoundError, SystemExit)


def probe_module(module_name: str) -> OptionalDependency:
    """Import *module_name* without allowing it to abort test collection."""

    if not isinstance(module_name, str) or not module_name.strip():
        raise ValueError("module_name must be a non-empty string")

    stdout = StringIO()
    stderr = StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            module = import_module(module_name)
    except _IMPORT_FAILURES as exc:
        output = "\n".join(part for part in (stdout.getvalue(), stderr.getvalue()) if part).strip()
        reason = str(exc).strip() or exc.__class__.__name__
        return OptionalDependency(
            name=module_name,
            available=False,
            reason=reason,
            output=output,
        )

    return OptionalDependency(
        name=module_name,
        available=True,
        module=module,
        output="\n".join(
            part for part in (stdout.getvalue(), stderr.getvalue()) if part
        ).strip(),
    )


def require_module(module_name: str, *, purpose: str | None = None) -> ModuleType:
    """Return an optional module or skip the current test/module safely."""

    result = probe_module(module_name)
    if result.available and result.module is not None:
        return result.module

    description = f" für {purpose}" if purpose else ""
    detail = f": {result.reason}" if result.reason else ""
    pytest.skip(
        f"Optionale Abhängigkeit '{module_name}'{description} ist nicht verfügbar{detail}",
        allow_module_level=True,
    )
    raise AssertionError("pytest.skip() must not return")
