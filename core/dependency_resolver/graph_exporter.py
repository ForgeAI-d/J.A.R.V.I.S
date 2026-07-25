from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from .dependency_graph import DependencyGraph
from .graph_visualizer import GraphVisualizer


class GraphExporter:
    """Exports dependency graphs without mutating resolver state."""

    def __init__(self) -> None:
        self.visualizer = GraphVisualizer()

    @staticmethod
    def _types(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(sorted({str(v).strip().lower() for v in values if str(v).strip()})) or ("required",)

    def as_dict(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> dict[str, Any]:
        types = self._types(dependency_types)
        data = deepcopy(graph.export())
        data["dependency_types"] = list(types)
        data["edges"] = [edge for edge in data["edges"] if edge["dependency_type"] in types]
        return data

    def to_json(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",), *, indent: int = 2) -> str:
        return json.dumps(self.as_dict(graph, dependency_types), indent=indent, sort_keys=True, ensure_ascii=False)

    def to_dot(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> str:
        data = self.as_dict(graph, dependency_types)
        lines = ["digraph DependencyGraph {", "  rankdir=LR;"]
        for node in data["nodes"]:
            component_id = node["component_id"].replace('"', '\\"')
            label = node["name"].replace('"', '\\"')
            lines.append(f'  "{component_id}" [label="{label}"];')
        for edge in data["edges"]:
            source = edge["source_id"].replace('"', '\\"')
            target = edge["target_id"].replace('"', '\\"')
            edge_type = edge["dependency_type"].replace('"', '\\"')
            lines.append(f'  "{source}" -> "{target}" [label="{edge_type}"];')
        lines.append("}")
        return "\n".join(lines)

    def to_ascii(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",), *, style: str = "tree") -> str:
        normalized = style.strip().lower()
        if normalized == "tree":
            return self.visualizer.tree(graph, dependency_types)
        if normalized == "compact":
            return self.visualizer.compact(graph, dependency_types)
        if normalized in {"arrows", "arrow"}:
            return self.visualizer.arrows(graph, dependency_types)
        raise ValueError(f"Unsupported ASCII export style: {style}")

    @staticmethod
    def write(content: str, path: str | Path) -> str:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        return str(destination)
