from __future__ import annotations

from collections import deque
from typing import Any, Iterable

from .dependency_graph import DependencyGraph
from .graph_traverser import GraphTraverser


class DependencyInspector:
    """Produces deterministic direct and transitive component diagnostics."""

    def __init__(self) -> None:
        self.traverser = GraphTraverser()

    @staticmethod
    def _types(values: Iterable[str]) -> tuple[str, ...]:
        normalized = tuple(sorted({str(v).strip().lower() for v in values if str(v).strip()}))
        return normalized or ("required",)

    @staticmethod
    def _reachable(start: str, adjacency: dict[str, tuple[str, ...]]) -> list[str]:
        seen: set[str] = set()
        queue = deque(adjacency.get(start, ()))
        while queue:
            node = queue.popleft()
            if node in seen:
                continue
            seen.add(node)
            queue.extend(adjacency.get(node, ()))
        return sorted(seen)

    @staticmethod
    def _depth(start: str, adjacency: dict[str, tuple[str, ...]]) -> int | None:
        memo: dict[str, int] = {}
        visiting: set[str] = set()

        def walk(node: str) -> int:
            if node in memo:
                return memo[node]
            if node in visiting:
                raise ValueError("Depth is undefined for cyclic dependency graphs.")
            visiting.add(node)
            value = 0
            for target in adjacency.get(node, ()):
                value = max(value, 1 + walk(target))
            visiting.remove(node)
            memo[node] = value
            return value

        try:
            return walk(start)
        except ValueError:
            return None

    def inspect(
        self,
        graph: DependencyGraph,
        component_id: str,
        dependency_types: Iterable[str] = ("required",),
        critical_threshold: int | None = None,
    ) -> dict[str, Any]:
        component_id = graph.normalize_id(component_id)
        node = graph.get_node(component_id)
        if node is None:
            raise LookupError(f"Unknown component: {component_id}")

        types = self._types(dependency_types)
        adjacency = self.traverser.adjacency(graph, types)
        reverse = self.traverser.reverse_adjacency(graph, types)
        direct_dependencies = list(adjacency[component_id])
        direct_dependents = list(reverse[component_id])
        transitive_dependencies = self._reachable(component_id, adjacency)
        transitive_dependents = self._reachable(component_id, reverse)
        threshold = critical_threshold if critical_threshold is not None else max(2, (len(adjacency) + 3) // 4)

        return {
            "graph_version": graph.version,
            "dependency_types": list(types),
            "component": node.to_dict(),
            "direct_dependencies": direct_dependencies,
            "transitive_dependencies": transitive_dependencies,
            "direct_dependents": direct_dependents,
            "transitive_dependents": transitive_dependents,
            "direct_dependency_count": len(direct_dependencies),
            "transitive_dependency_count": len(transitive_dependencies),
            "direct_dependent_count": len(direct_dependents),
            "transitive_dependent_count": len(transitive_dependents),
            "depth": self._depth(component_id, adjacency),
            "root": not direct_dependencies,
            "leaf": not direct_dependents,
            "isolated": not direct_dependencies and not direct_dependents,
            "critical_threshold": threshold,
            "critical": len(transitive_dependents) >= threshold,
        }
