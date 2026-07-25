from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

from .runtime_transaction import RuntimeTransaction


class RuntimeDependencyManager:
    """Coordinates atomic runtime mutations and automatic rollback."""

    def __init__(self, resolver: Any) -> None:
        self.resolver = resolver
        self._active: RuntimeTransaction | None = None
        self._history: list[dict[str, Any]] = []
        self._lock = RLock()

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active is not None

    def begin(self, label: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self._active is not None:
                raise RuntimeError("A runtime transaction is already active.")
            self._active = RuntimeTransaction(
                snapshot=self.resolver.graph.export(),
                label=str(label).strip() if label is not None else None,
            )
            return self._active.to_dict()

    def record(self, change_type: str, payload: dict[str, Any] | None = None) -> None:
        with self._lock:
            if self._active is not None:
                self._active.record_change(change_type, payload)

    def commit(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        validate: bool = True,
    ) -> dict[str, Any]:
        with self._lock:
            if self._active is None:
                raise RuntimeError("No runtime transaction is active.")
            transaction = self._active

        report = (
            self.resolver.resolve(dependency_types=dependency_types, force=True)
            if validate
            else {"valid": True, "summary": "Validation skipped.", "details": {}}
        )

        if not report.get("valid", False):
            rollback = self.rollback(reason="validation_failed", validation_report=report)
            return {
                "committed": False,
                "rolled_back": True,
                "transaction": rollback["transaction"],
                "validation": deepcopy(report),
            }

        with self._lock:
            transaction.complete("COMMITTED", report)
            result = transaction.to_dict()
            self._history.append(deepcopy(result))
            self._active = None

        return {
            "committed": True,
            "rolled_back": False,
            "transaction": result,
            "validation": deepcopy(report),
        }

    def rollback(
        self,
        reason: str = "manual",
        validation_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if self._active is None:
                raise RuntimeError("No runtime transaction is active.")
            transaction = self._active

        self.resolver.graph.restore(transaction.snapshot)
        self.resolver.cache.invalidate()

        with self._lock:
            transaction.record_change("ROLLBACK_REASON", {"reason": reason})
            transaction.complete("ROLLED_BACK", validation_report)
            result = transaction.to_dict()
            self._history.append(deepcopy(result))
            self._active = None

        return {"rolled_back": True, "transaction": result}

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._active is not None,
                "transaction": self._active.to_dict() if self._active else None,
                "history_count": len(self._history),
            }

    def history(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            items = self._history if limit is None else self._history[-limit:]
            return deepcopy(items)
