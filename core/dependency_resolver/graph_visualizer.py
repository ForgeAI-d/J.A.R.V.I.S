from __future__ import annotations

from typing import Iterable

from .dependency_graph import DependencyGraph
from .graph_traverser import GraphTraverser


class GraphVisualizer:
    """Creates deterministic human-readable graph representations."""

    def __init__(self) -> None:
        self.traverser = GraphTraverser()

    @staticmethod
    def _types(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(sorted({str(v).strip().lower() for v in values if str(v).strip()})) or ("required",)

    def compact(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> str:
        types = self._types(dependency_types)
        lines = [f"{edge.source_id} -> {edge.target_id} [{edge.dependency_type}]" for edge in graph.list_edges() if edge.dependency_type in types]
        return "\n".join(lines) if lines else "(no dependencies)"

    def tree(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> str:
        types = self._types(dependency_types)
        reverse = self.traverser.reverse_adjacency(graph, types)
        adjacency = self.traverser.adjacency(graph, types)
        roots = sorted(node for node in adjacency if not adjacency[node])
        if not roots:
            roots = sorted(adjacency)
        lines: list[str] = []
        rendered: set[str] = set()

        def draw(node: str, prefix: str, is_last: bool, path: set[str], root: bool = False) -> None:
            connector = "" if root else ("└── " if is_last else "├── ")
            lines.append(prefix + connector + node)
            if node in path:
                lines[-1] += " (cycle)"
                return
            rendered.add(node)
            children = list(reverse[node])
            next_prefix = prefix if root else prefix + ("    " if is_last else "│   ")
            for index, child in enumerate(children):
                draw(child, next_prefix, index == len(children) - 1, path | {node})

        for index, root_node in enumerate(roots):
            if index:
                lines.append("")
            draw(root_node, "", True, set(), root=True)
        for node in sorted(set(adjacency) - rendered):
            lines.append("")
            draw(node, "", True, set(), root=True)
        return "\n".join(lines) if lines else "(empty graph)"

    def arrows(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> str:
        types = self._types(dependency_types)
        adjacency = self.traverser.adjacency(graph, types)
        lines: list[str] = []
        for source in sorted(adjacency):
            targets = adjacency[source]
            if not targets:
                lines.append(source)
            else:
                for target in targets:
                    lines.extend([source, "   │", "   ▼", target, ""])
        return "\n".join(lines).rstrip() if lines else "(empty graph)"
