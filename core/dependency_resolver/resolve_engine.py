from __future__ import annotations

import heapq
from time import perf_counter

from .dependency_graph import DependencyGraph
from .resolve_result import ResolveResult


class ResolveEngine:
    """Deterministic priority-aware Kahn topological sort."""

    ALGORITHM = "kahn_priority_v1"

    def resolve(
        self,
        graph: DependencyGraph,
        dependency_types: tuple[str, ...] = ("required",),
    ) -> ResolveResult:
        started = perf_counter()

        nodes = {
            node.component_id: node
            for node in graph.list_nodes()
        }
        allowed = set(dependency_types)

        # source depends on target:
        # target must therefore appear before source in the boot order.
        indegree = {component_id: 0 for component_id in nodes}
        dependents: dict[str, set[str]] = {
            component_id: set()
            for component_id in nodes
        }

        relevant_edges = [
            edge
            for edge in graph.list_edges()
            if edge.dependency_type in allowed
        ]

        for edge in relevant_edges:
            indegree[edge.source_id] += 1
            dependents[edge.target_id].add(edge.source_id)

        ready: list[tuple[int, str]] = []

        for component_id, degree in indegree.items():
            if degree == 0:
                node = nodes[component_id]
                heapq.heappush(
                    ready,
                    (node.priority, component_id),
                )

        ordered: list[str] = []

        while ready:
            _, component_id = heapq.heappop(ready)
            ordered.append(component_id)

            for dependent_id in sorted(dependents[component_id]):
                indegree[dependent_id] -= 1

                if indegree[dependent_id] == 0:
                    node = nodes[dependent_id]
                    heapq.heappush(
                        ready,
                        (node.priority, dependent_id),
                    )

        if len(ordered) != len(nodes):
            unresolved = sorted(
                component_id
                for component_id, degree in indegree.items()
                if degree > 0
            )
            raise ValueError(
                "Topological resolution failed. "
                "The graph contains at least one cycle or unresolved "
                f"dependency chain: {unresolved}"
            )

        duration = perf_counter() - started

        return ResolveResult(
            boot_order=tuple(ordered),
            shutdown_order=tuple(reversed(ordered)),
            graph_version=graph.version,
            duration_seconds=duration,
            algorithm=self.ALGORITHM,
            cached=False,
            component_count=len(nodes),
            edge_count=len(relevant_edges),
        )
