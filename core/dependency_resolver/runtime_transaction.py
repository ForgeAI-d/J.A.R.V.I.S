from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class RuntimeTransaction:
    """Snapshot-backed atomic runtime graph transaction."""

    snapshot: dict[str, Any]
    label: str | None = None
    transaction_id: str = field(default_factory=lambda: uuid4().hex)
    state: str = "ACTIVE"
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    changes: list[dict[str, Any]] = field(default_factory=list)
    validation_report: dict[str, Any] | None = None

    def record_change(self, change_type: str, payload: dict[str, Any] | None = None) -> None:
        if self.state != "ACTIVE":
            raise RuntimeError("Cannot modify a completed transaction.")
        self.changes.append({
            "change_type": str(change_type).strip().upper(),
            "payload": deepcopy(payload or {}),
            "recorded_at": datetime.now(UTC).isoformat(),
        })

    def complete(self, state: str, validation_report: dict[str, Any] | None = None) -> None:
        normalized = str(state).strip().upper()
        if normalized not in {"COMMITTED", "ROLLED_BACK"}:
            raise ValueError("Unsupported transaction completion state.")
        self.state = normalized
        self.validation_report = deepcopy(validation_report)
        self.completed_at = datetime.now(UTC).isoformat()

    def to_dict(self, include_snapshot: bool = False) -> dict[str, Any]:
        result = {
            "transaction_id": self.transaction_id,
            "label": self.label,
            "state": self.state,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "change_count": len(self.changes),
            "changes": deepcopy(self.changes),
            "validation_report": deepcopy(self.validation_report),
        }
        if include_snapshot:
            result["snapshot"] = deepcopy(self.snapshot)
        return result
