from __future__ import annotations

from copy import deepcopy
from threading import RLock

from .resolve_result import ResolveResult


class GraphCache:
    """Thread-safe cache keyed by graph version and dependency policy."""

    def __init__(self) -> None:
        self._entries: dict[tuple[int, tuple[str, ...]], ResolveResult] = {}
        self._lock = RLock()

    def get(
        self,
        graph_version: int,
        dependency_types: tuple[str, ...],
    ) -> ResolveResult | None:
        with self._lock:
            return self._entries.get((graph_version, dependency_types))

    def put(
        self,
        graph_version: int,
        dependency_types: tuple[str, ...],
        result: ResolveResult,
    ) -> None:
        with self._lock:
            self._entries[(graph_version, dependency_types)] = result

    def invalidate(self) -> None:
        with self._lock:
            self._entries.clear()

    def statistics(self) -> dict[str, int]:
        with self._lock:
            return {"cache_entry_count": len(self._entries)}
