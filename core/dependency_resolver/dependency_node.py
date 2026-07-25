from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class DependencyNode:
    """Represents one component in the dependency graph."""

    component_id: str
    name: str
    component_type: str = "service"
    version: str = "0.1.0"
    status: str = "REGISTERED"
    priority: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def __post_init__(self) -> None:
        self.component_id = self._normalize_id(self.component_id)
        self.name = str(self.name).strip() or self.component_id
        self.component_type = str(self.component_type).strip().lower() or "service"
        self.version = str(self.version).strip() or "0.1.0"
        self.status = str(self.status).strip().upper() or "REGISTERED"
        self.priority = int(self.priority)
        self.metadata = deepcopy(self.metadata)

    @staticmethod
    def _normalize_id(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("component_id must be a string.")

        normalized = value.strip().lower()

        if not normalized:
            raise ValueError("component_id must not be empty.")

        return normalized

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "component_type": self.component_type,
            "version": self.version,
            "status": self.status,
            "priority": self.priority,
            "metadata": deepcopy(self.metadata),
            "registered_at": self.registered_at,
        }
