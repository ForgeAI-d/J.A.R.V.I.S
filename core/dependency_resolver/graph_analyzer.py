from __future__ import annotations
from collections import deque
from typing import Iterable, Any
from .dependency_graph import DependencyGraph
from .graph_traverser import GraphTraverser
from .cycle_detector import CycleDetector

class GraphAnalyzer:
    def __init__(self) -> None:
        self.traverser = GraphTraverser()
        self.cycle_detector = CycleDetector()

    def analyze(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> dict[str, Any]:
        types = tuple(sorted({str(x).strip().lower() for x in dependency_types if str(x).strip()})) or ("required",)
        adj = self.traverser.adjacency(graph, types)
        rev = self.traverser.reverse_adjacency(graph, types)
        cycle_report = self.cycle_detector.analyze(graph, types)

        isolated = sorted(n for n in adj if not adj[n] and not rev[n])
        roots = sorted(n for n in adj if not adj[n])
        leaves = sorted(n for n in rev if not rev[n])

        weak = {n: set() for n in adj}
        for n, targets in adj.items():
            for t in targets:
                weak[n].add(t)
                weak[t].add(n)

        seen, groups = set(), []
        for start in sorted(weak):
            if start in seen:
                continue
            q, group = deque([start]), []
            seen.add(start)
            while q:
                n = q.popleft()
                group.append(n)
                for x in sorted(weak[n]):
                    if x not in seen:
                        seen.add(x)
                        q.append(x)
            groups.append(sorted(group))

        longest = []
        if not cycle_report.has_cycles:
            memo = {}
            def longest_from(node):
                if node in memo:
                    return memo[node]
                best = [node]
                for nxt in adj[node]:
                    cand = [node] + longest_from(nxt)
                    if len(cand) > len(best) or (len(cand) == len(best) and tuple(cand) < tuple(best)):
                        best = cand
                memo[node] = best
                return best
            for node in sorted(adj):
                cand = longest_from(node)
                if len(cand) > len(longest) or (len(cand) == len(longest) and tuple(cand) < tuple(longest)):
                    longest = cand

        return {
            "graph_version": graph.version,
            "dependency_types": list(types),
            "node_count": len(adj),
            "edge_count": sum(1 for e in graph.list_edges() if e.dependency_type in types),
            "root_nodes": roots,
            "leaf_nodes": leaves,
            "isolated_nodes": isolated,
            "independent_graph_count": len(groups),
            "independent_graphs": groups,
            "longest_chain": longest,
            "maximum_depth": max(len(longest) - 1, 0),
            "cycle_report": cycle_report.to_dict(),
        }
