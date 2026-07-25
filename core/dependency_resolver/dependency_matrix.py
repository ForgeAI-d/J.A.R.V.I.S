from __future__ import annotations

from typing import Any, Iterable

from .dependency_graph import DependencyGraph


class DependencyMatrix:
    """Builds deterministic adjacency matrices for dependency diagnostics."""

    @staticmethod
    def _types(values: Iterable[str]) -> tuple[str, ...]:
        normalized = tuple(sorted({str(v).strip().lower() for v in values if str(v).strip()}))
        return normalized or ("required",)

    def build(
        self,
        graph: DependencyGraph,
        dependency_types: Iterable[str] = ("required",),
    ) -> dict[str, Any]:
        types = self._types(dependency_types)
        nodes = sorted(node.component_id for node in graph.list_nodes())
        positions = {node: index for index, node in enumerate(nodes)}
        values = [[0 for _ in nodes] for _ in nodes]
        typed_values: list[list[list[str]]] = [[[] for _ in nodes] for _ in nodes]

        for edge in graph.list_edges():
            if edge.dependency_type not in types:
                continue
            row = positions[edge.source_id]
            column = positions[edge.target_id]
            values[row][column] = 1
            typed_values[row][column].append(edge.dependency_type)

        return {
            "graph_version": graph.version,
            "dependency_types": list(types),
            "nodes": nodes,
            "values": values,
            "typed_values": typed_values,
            "legend": "rows depend on columns",
        }

    def to_ascii(self, matrix: dict[str, Any]) -> str:
        nodes = matrix["nodes"]
        if not nodes:
            return "(empty dependency matrix)"
        width = max(3, max(len(node) for node in nodes))
        header = " " * (width + 2) + " ".join(f"{node:>{width}}" for node in nodes)
        rows = [header]
        for node, values in zip(nodes, matrix["values"]):
            cells = " ".join(f"{('X' if value else '.'):>{width}}" for value in values)
            rows.append(f"{node:>{width}}  {cells}")
        return "\n".join(rows)
