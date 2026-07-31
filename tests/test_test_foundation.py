from __future__ import annotations

import sys
from types import ModuleType

import pytest

from tests.common.optional import probe_module, require_module


def test_probe_existing_module() -> None:
    result = probe_module("json")
    assert result.available is True
    assert result.module is not None


def test_probe_missing_module_is_non_fatal() -> None:
    result = probe_module("jarvis_module_that_does_not_exist")
    assert result.available is False
    assert result.module is None


def test_require_missing_module_skips() -> None:
    with pytest.raises(pytest.skip.Exception):
        require_module("jarvis_module_that_does_not_exist")


def test_probe_catches_system_exit(tmp_path, monkeypatch) -> None:
    module_name = "jarvis_test_system_exit_import"
    (tmp_path / f"{module_name}.py").write_text("raise SystemExit()\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(module_name, None)

    result = probe_module(module_name)

    assert result.available is False
    assert result.reason == "SystemExit"


def test_probe_returns_module_type() -> None:
    result = probe_module("math")
    assert isinstance(result.module, ModuleType)
