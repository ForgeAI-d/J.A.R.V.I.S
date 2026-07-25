from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


VALID_DEPENDENCY_TYPES = {
    "required",
    "optional",
    "runtime",
    "weak",
}


@dataclass(slots=True)
class DependencyEdge:
    """Represents a directed dependency: source depends on target."""

    source_id: str
    target_id: str
    dependency_type: str = "required"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self) -> None:
        self.source_id = self._normalize_id(self.source_id)
        self.target_id = self._normalize_id(self.target_id)
        self.dependency_type = str(self.dependency_type).strip().lower()

        if self.dependency_type not in VALID_DEPENDENCY_TYPES:
            raise ValueError(
                f"Unsupported dependency type: {self.dependency_type}"
            )

        if self.source_id == self.target_id:
            raise ValueError("A component cannot depend on itself.")

        self.metadata = deepcopy(self.metadata)

    @staticmethod
    def _normalize_id(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("Dependency identifiers must be strings.")

        normalized = value.strip().lower()

        if not normalized:
            raise ValueError("Dependency identifiers must not be empty.")

        return normalized

    @property
    def key(self) -> tuple[str, str, str]:
        return (
            self.source_id,
            self.target_id,
            self.dependency_type,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "dependency_type": self.dependency_type,
            "metadata": deepcopy(self.metadata),
            "created_at": self.created_at,
        }
