"""Readable assertions shared by component tests."""
from __future__ import annotations

from typing import Any


def _status_value(component: Any) -> str:
    status = getattr(component, "status", None)
    if status is None and callable(getattr(component, "get_status", None)):
        result = component.get_status()
        if isinstance(result, dict):
            status = result.get("status") or result.get("state")
    return str(status or "UNKNOWN").upper()


def assert_component_running(component: Any) -> None:
    status = _status_value(component)
    assert status in {"ONLINE", "RUNNING", "READY", "STARTED"}, (
        f"Komponente ist nicht aktiv; Status={status!r}"
    )


def assert_component_healthy(component: Any) -> None:
    getter = getattr(component, "get_health", None)
    health = getter() if callable(getter) else getattr(component, "health", None)
    if isinstance(health, dict):
        assert health.get("healthy", True), f"Komponente ist ungesund: {health!r}"
        value = health.get("health", health.get("score", 100))
        assert float(value) > 0, f"Ungültiger Health-Wert: {health!r}"
        return
    assert health is None or float(health) > 0, f"Ungültiger Health-Wert: {health!r}"
