from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any, Iterable

from .dependency_edge import DependencyEdge
from .dependency_node import DependencyNode


class DependencyGraph:
    """Thread-safe directed graph for kernel components."""

    def __init__(self) -> None:
        self._nodes: dict[str, DependencyNode] = {}
        self._edges: dict[tuple[str, str, str], DependencyEdge] = {}
        self._outgoing: dict[str, set[tuple[str, str, str]]] = {}
        self._incoming: dict[str, set[tuple[str, str, str]]] = {}
        self._lock = RLock()
        self._version = 0
        self._last_change: dict[str, Any] | None = None

    @staticmethod
    def normalize_id(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("Component identifiers must be strings.")

        normalized = value.strip().lower()

        if not normalized:
            raise ValueError("Component identifiers must not be empty.")

        return normalized

    def add_node(self, node: DependencyNode, replace: bool = False) -> bool:
        if not isinstance(node, DependencyNode):
            raise TypeError("node must be a DependencyNode.")

        with self._lock:
            exists = node.component_id in self._nodes

            if exists and not replace:
                return False

            self._nodes[node.component_id] = node
            self._outgoing.setdefault(node.component_id, set())
            self._incoming.setdefault(node.component_id, set())
            self._touch(
                "NODE_REPLACED" if exists else "NODE_ADDED",
                {"component_id": node.component_id},
            )
            return True

    def remove_node(self, component_id: str) -> tuple[bool, list[DependencyEdge]]:
        component_id = self.normalize_id(component_id)

        with self._lock:
            if component_id not in self._nodes:
                return False, []

            edge_keys = (
                set(self._outgoing.get(component_id, set()))
                | set(self._incoming.get(component_id, set()))
            )

            removed_edges = [
                self._edges[key]
                for key in edge_keys
                if key in self._edges
            ]

            for key in list(edge_keys):
                self._remove_edge_by_key(key)

            self._nodes.pop(component_id, None)
            self._outgoing.pop(component_id, None)
            self._incoming.pop(component_id, None)
            self._touch(
                "NODE_REMOVED",
                {
                    "component_id": component_id,
                    "removed_edges": len(removed_edges),
                },
            )

            return True, removed_edges

    def get_node(self, component_id: str) -> DependencyNode | None:
        component_id = self.normalize_id(component_id)

        with self._lock:
            return self._nodes.get(component_id)

    def has_node(self, component_id: str) -> bool:
        return self.get_node(component_id) is not None

    def list_nodes(self) -> list[DependencyNode]:
        with self._lock:
            return list(self._nodes.values())

    def add_edge(self, edge: DependencyEdge, replace: bool = False) -> bool:
        if not isinstance(edge, DependencyEdge):
            raise TypeError("edge must be a DependencyEdge.")

        with self._lock:
            if edge.source_id not in self._nodes:
                raise LookupError(
                    f"Unknown source component: {edge.source_id}"
                )

            if edge.target_id not in self._nodes:
                raise LookupError(
                    f"Unknown target component: {edge.target_id}"
                )

            exists = edge.key in self._edges

            if exists and not replace:
                return False

            self._edges[edge.key] = edge
            self._outgoing.setdefault(edge.source_id, set()).add(edge.key)
            self._incoming.setdefault(edge.target_id, set()).add(edge.key)
            self._touch(
                "EDGE_REPLACED" if exists else "EDGE_ADDED",
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "dependency_type": edge.dependency_type,
                },
            )
            return True

    def remove_edge(
        self,
        source_id: str,
        target_id: str,
        dependency_type: str | None = None,
    ) -> list[DependencyEdge]:
        source_id = self.normalize_id(source_id)
        target_id = self.normalize_id(target_id)

        with self._lock:
            candidates = [
                key
                for key in self._outgoing.get(source_id, set())
                if key[1] == target_id
                and (
                    dependency_type is None
                    or key[2] == dependency_type.strip().lower()
                )
            ]

            removed: list[DependencyEdge] = []

            for key in candidates:
                edge = self._edges.get(key)

                if edge is not None:
                    removed.append(edge)

                self._remove_edge_by_key(key)

            if removed:
                self._touch(
                    "EDGE_REMOVED",
                    {
                        "source_id": source_id,
                        "target_id": target_id,
                        "removed_count": len(removed),
                    },
                )

            return removed

    def _remove_edge_by_key(self, key: tuple[str, str, str]) -> None:
        edge = self._edges.pop(key, None)

        if edge is None:
            return

        self._outgoing.get(edge.source_id, set()).discard(key)
        self._incoming.get(edge.target_id, set()).discard(key)

    def get_dependencies(
        self,
        component_id: str,
        dependency_types: Iterable[str] | None = None,
    ) -> list[DependencyEdge]:
        component_id = self.normalize_id(component_id)
        allowed = (
            {item.strip().lower() for item in dependency_types}
            if dependency_types is not None
            else None
        )

        with self._lock:
            edges = [
                self._edges[key]
                for key in self._outgoing.get(component_id, set())
                if key in self._edges
            ]

            if allowed is not None:
                edges = [
                    edge
                    for edge in edges
                    if edge.dependency_type in allowed
                ]

            return sorted(
                edges,
                key=lambda edge: (
                    edge.dependency_type,
                    edge.target_id,
                ),
            )

    def get_dependents(
        self,
        component_id: str,
        dependency_types: Iterable[str] | None = None,
    ) -> list[DependencyEdge]:
        component_id = self.normalize_id(component_id)
        allowed = (
            {item.strip().lower() for item in dependency_types}
            if dependency_types is not None
            else None
        )

        with self._lock:
            edges = [
                self._edges[key]
                for key in self._incoming.get(component_id, set())
                if key in self._edges
            ]

            if allowed is not None:
                edges = [
                    edge
                    for edge in edges
                    if edge.dependency_type in allowed
                ]

            return sorted(
                edges,
                key=lambda edge: (
                    edge.dependency_type,
                    edge.source_id,
                ),
            )

    def list_edges(self) -> list[DependencyEdge]:
        with self._lock:
            return sorted(
                self._edges.values(),
                key=lambda edge: edge.key,
            )

    def clear(self) -> None:
        with self._lock:
            changed = bool(self._nodes or self._edges)
            self._nodes.clear()
            self._edges.clear()
            self._outgoing.clear()
            self._incoming.clear()
            if changed:
                self._touch("GRAPH_CLEARED", {})


    def restore(self, snapshot: dict[str, Any]) -> None:
        """Atomically restore a graph export and advance graph version."""
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be a dictionary.")

        nodes = snapshot.get("nodes", [])
        edges = snapshot.get("edges", [])

        rebuilt_nodes: dict[str, DependencyNode] = {}
        rebuilt_edges: dict[tuple[str, str, str], DependencyEdge] = {}
        outgoing: dict[str, set[tuple[str, str, str]]] = {}
        incoming: dict[str, set[tuple[str, str, str]]] = {}

        for data in nodes:
            node = DependencyNode(**deepcopy(data))
            rebuilt_nodes[node.component_id] = node
            outgoing[node.component_id] = set()
            incoming[node.component_id] = set()

        for data in edges:
            edge = DependencyEdge(**deepcopy(data))
            if edge.source_id not in rebuilt_nodes or edge.target_id not in rebuilt_nodes:
                raise ValueError("Snapshot contains an edge with an unknown node.")
            rebuilt_edges[edge.key] = edge
            outgoing[edge.source_id].add(edge.key)
            incoming[edge.target_id].add(edge.key)

        with self._lock:
            self._nodes = rebuilt_nodes
            self._edges = rebuilt_edges
            self._outgoing = outgoing
            self._incoming = incoming
            self._touch("GRAPH_RESTORED", {
                "node_count": len(rebuilt_nodes),
                "edge_count": len(rebuilt_edges),
                "restored_from_version": snapshot.get("version"),
            })

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    @property
    def last_change(self) -> dict[str, Any] | None:
        with self._lock:
            return deepcopy(self._last_change)

    def _touch(
        self,
        change_type: str,
        payload: dict[str, Any],
    ) -> None:
        self._version += 1
        self._last_change = {
            "change_type": change_type,
            "payload": deepcopy(payload),
            "graph_version": self._version,
        }

    def export(self) -> dict[str, Any]:
        with self._lock:
            return {
                "version": self._version,
                "last_change": deepcopy(self._last_change),
                "nodes": [
                    node.to_dict()
                    for node in sorted(
                        self._nodes.values(),
                        key=lambda item: item.component_id,
                    )
                ],
                "edges": [
                    edge.to_dict()
                    for edge in sorted(
                        self._edges.values(),
                        key=lambda item: item.key,
                    )
                ],
            }

    def statistics(self) -> dict[str, int]:
        with self._lock:
            isolated = sum(
                1
                for component_id in self._nodes
                if not self._outgoing.get(component_id)
                and not self._incoming.get(component_id)
            )

            return {
                "graph_version": self._version,
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "isolated_node_count": isolated,
            }
