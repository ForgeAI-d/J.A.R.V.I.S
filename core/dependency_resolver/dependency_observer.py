from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from threading import RLock
from typing import Any, Callable

ObserverCallback = Callable[[dict[str, Any]], None]


class DependencyObserver:
    """Thread-safe event observer for runtime dependency changes."""

    WILDCARD = "*"

    def __init__(self) -> None:
        self._callbacks: dict[str, list[ObserverCallback]] = defaultdict(list)
        self._lock = RLock()
        self._events_emitted = 0
        self._callback_errors = 0

    @staticmethod
    def normalize_event(event_type: str) -> str:
        value = str(event_type).strip().upper()
        if not value:
            raise ValueError("event_type must not be empty.")
        return value

    def subscribe(self, event_type: str, callback: ObserverCallback) -> bool:
        if not callable(callback):
            raise TypeError("callback must be callable.")
        event = self.normalize_event(event_type)
        with self._lock:
            if callback in self._callbacks[event]:
                return False
            self._callbacks[event].append(callback)
            return True

    def unsubscribe(self, event_type: str, callback: ObserverCallback) -> bool:
        event = self.normalize_event(event_type)
        with self._lock:
            callbacks = self._callbacks.get(event, [])
            if callback not in callbacks:
                return False
            callbacks.remove(callback)
            if not callbacks:
                self._callbacks.pop(event, None)
            return True

    def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = self.normalize_event(event_type)
        message = {"event_type": event, "payload": deepcopy(payload or {})}
        with self._lock:
            callbacks = list(self._callbacks.get(event, []))
            callbacks.extend(self._callbacks.get(self.WILDCARD, []))
            self._events_emitted += 1

        errors: list[str] = []
        for callback in callbacks:
            try:
                callback(deepcopy(message))
            except Exception as exc:  # observers must never break the kernel
                errors.append(f"{exc.__class__.__name__}: {exc}")

        if errors:
            with self._lock:
                self._callback_errors += len(errors)

        return {
            "event_type": event,
            "delivered": len(callbacks) - len(errors),
            "errors": errors,
        }

    def statistics(self) -> dict[str, int]:
        with self._lock:
            return {
                "observer_event_types": len(self._callbacks),
                "observer_subscriptions": sum(len(v) for v in self._callbacks.values()),
                "observer_events_emitted": self._events_emitted,
                "observer_callback_errors": self._callback_errors,
            }
