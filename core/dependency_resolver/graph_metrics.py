from __future__ import annotations

from typing import Any, Iterable

from .dependency_graph import DependencyGraph
from .graph_analyzer import GraphAnalyzer
from .graph_traverser import GraphTraverser


class GraphMetrics:
    """Calculates structural metrics and criticality scores."""

    def __init__(self) -> None:
        self.analyzer = GraphAnalyzer()
        self.traverser = GraphTraverser()

    def calculate(
        self,
        graph: DependencyGraph,
        dependency_types: Iterable[str] = ("required",),
        critical_threshold: int | None = None,
    ) -> dict[str, Any]:
        types = tuple(sorted({str(v).strip().lower() for v in dependency_types if str(v).strip()})) or ("required",)
        analysis = self.analyzer.analyze(graph, types)
        adjacency = self.traverser.adjacency(graph, types)
        reverse = self.traverser.reverse_adjacency(graph, types)
        node_count = len(adjacency)
        edge_count = analysis["edge_count"]
        threshold = critical_threshold if critical_threshold is not None else max(2, (node_count + 3) // 4)

        def reachable(start: str, mapping: dict[str, tuple[str, ...]]) -> set[str]:
            seen: set[str] = set()
            stack = list(mapping[start])
            while stack:
                item = stack.pop()
                if item in seen:
                    continue
                seen.add(item)
                stack.extend(mapping[item])
            return seen

        criticality = []
        for component_id in sorted(adjacency):
            transitive = reachable(component_id, reverse)
            criticality.append({
                "component_id": component_id,
                "direct_dependents": len(reverse[component_id]),
                "transitive_dependents": len(transitive),
                "score": round(len(transitive) / max(node_count - 1, 1), 6),
                "critical": len(transitive) >= threshold,
            })
        criticality.sort(key=lambda item: (-item["transitive_dependents"], -item["direct_dependents"], item["component_id"]))

        max_possible = node_count * (node_count - 1)
        dependencies = [len(adjacency[node]) for node in adjacency]
        dependents = [len(reverse[node]) for node in reverse]
        return {
            **analysis,
            "density": round(edge_count / max_possible, 6) if max_possible else 0.0,
            "average_dependencies": round(sum(dependencies) / node_count, 6) if node_count else 0.0,
            "maximum_dependencies": max(dependencies, default=0),
            "average_dependents": round(sum(dependents) / node_count, 6) if node_count else 0.0,
            "maximum_dependents": max(dependents, default=0),
            "critical_threshold": threshold,
            "critical_components": [item["component_id"] for item in criticality if item["critical"]],
            "criticality": criticality,
        }
