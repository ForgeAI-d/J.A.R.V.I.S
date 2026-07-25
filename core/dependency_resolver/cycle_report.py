from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from copy import deepcopy
from typing import Any

@dataclass(slots=True)
class CycleReport:
    has_cycles: bool
    cycles: list[list[str]]
    dependency_types: tuple[str, ...]
    graph_version: int
    analyzed_nodes: int
    analyzed_edges: int
    duration_seconds: float
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def cycle_count(self) -> int:
        return len(self.cycles)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_cycles": self.has_cycles,
            "cycle_count": self.cycle_count,
            "cycles": deepcopy(self.cycles),
            "dependency_types": list(self.dependency_types),
            "graph_version": self.graph_version,
            "analyzed_nodes": self.analyzed_nodes,
            "analyzed_edges": self.analyzed_edges,
            "duration_seconds": self.duration_seconds,
            "suggestions": deepcopy(self.suggestions),
            "created_at": self.created_at,
        }
