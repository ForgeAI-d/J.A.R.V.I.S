from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PolicyTransaction:
    transaction_id: str
    changes: list[dict[str, Any]] = field(default_factory=list)
    committed: bool = False
    rolled_back: bool = False

    def add(self, change: dict[str, Any]) -> None:
        if self.committed or self.rolled_back:
            raise RuntimeError("Transaction is closed")
        self.changes.append(dict(change))

    def commit(self) -> None:
        if self.rolled_back:
            raise RuntimeError("Rolled-back transaction cannot be committed")
        self.committed = True

    def rollback(self) -> None:
        if self.committed:
            raise RuntimeError("Committed transaction cannot be rolled back")
        self.rolled_back = True
        self.changes.clear()
