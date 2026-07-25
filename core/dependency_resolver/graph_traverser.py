from __future__ import annotations
from collections import deque
from typing import Iterable
from .dependency_graph import DependencyGraph

class GraphTraverser:
    def adjacency(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> dict[str, tuple[str, ...]]:
        allowed = {str(x).strip().lower() for x in dependency_types if str(x).strip()}
        result = {n.component_id: set() for n in graph.list_nodes()}
        for edge in graph.list_edges():
            if edge.dependency_type in allowed:
                result[edge.source_id].add(edge.target_id)
        return {k: tuple(sorted(v)) for k, v in sorted(result.items())}

    def reverse_adjacency(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> dict[str, tuple[str, ...]]:
        adj = self.adjacency(graph, dependency_types)
        rev = {k: set() for k in adj}
        for source, targets in adj.items():
            for target in targets:
                rev[target].add(source)
        return {k: tuple(sorted(v)) for k, v in sorted(rev.items())}

    def dfs(self, graph: DependencyGraph, start_id: str, dependency_types: Iterable[str] = ("required",)) -> list[str]:
        adj = self.adjacency(graph, dependency_types)
        if start_id not in adj:
            return []
        seen, order, stack = set(), [], [start_id]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            order.append(node)
            stack.extend(reversed([x for x in adj[node] if x not in seen]))
        return order

    def bfs(self, graph: DependencyGraph, start_id: str, dependency_types: Iterable[str] = ("required",)) -> list[str]:
        adj = self.adjacency(graph, dependency_types)
        if start_id not in adj:
            return []
        seen, order, queue = {start_id}, [], deque([start_id])
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in adj[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return order
