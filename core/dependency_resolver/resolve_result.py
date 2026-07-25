from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ResolveResult:
    boot_order: tuple[str, ...]
    shutdown_order: tuple[str, ...]
    graph_version: int
    duration_seconds: float
    algorithm: str
    cached: bool
    component_count: int
    edge_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "boot_order": list(self.boot_order),
            "shutdown_order": list(self.shutdown_order),
            "graph_version": self.graph_version,
            "duration_seconds": self.duration_seconds,
            "algorithm": self.algorithm,
            "cached": self.cached,
            "component_count": self.component_count,
            "edge_count": self.edge_count,
        }
