from __future__ import annotations
from time import perf_counter
from typing import Iterable
from .cycle_report import CycleReport
from .dependency_graph import DependencyGraph
from .graph_traverser import GraphTraverser

class CycleDetector:
    def __init__(self) -> None:
        self.traverser = GraphTraverser()

    def detect(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> list[list[str]]:
        return self.analyze(graph, dependency_types).cycles

    def analyze(self, graph: DependencyGraph, dependency_types: Iterable[str] = ("required",)) -> CycleReport:
        started = perf_counter()
        types = tuple(sorted({str(x).strip().lower() for x in dependency_types if str(x).strip()})) or ("required",)
        adj = self.traverser.adjacency(graph, types)
        state = {node: 0 for node in adj}
        stack, positions = [], {}
        found = set()

        def canonical(closed):
            body = closed[:-1]
            rotations = [tuple(body[i:] + body[:i]) for i in range(len(body))]
            best = min(rotations)
            return best + (best[0],)

        def visit(node):
            state[node] = 1
            positions[node] = len(stack)
            stack.append(node)
            for nxt in adj[node]:
                if state[nxt] == 0:
                    visit(nxt)
                elif state[nxt] == 1:
                    found.add(canonical(stack[positions[nxt]:] + [nxt]))
            stack.pop()
            positions.pop(node, None)
            state[node] = 2

        for node in sorted(adj):
            if state[node] == 0:
                visit(node)

        cycles = [list(x) for x in sorted(found)]
        edges = sum(1 for e in graph.list_edges() if e.dependency_type in types)
        suggestions = [{
            "cycle": cycle,
            "message": "Mindestens eine Kante dieses Zyklus muss entfernt oder nicht blockierend werden.",
            "candidate_edges": [
                {"source_id": cycle[i], "target_id": cycle[i + 1]}
                for i in range(len(cycle) - 1)
            ],
        } for cycle in cycles]

        return CycleReport(
            has_cycles=bool(cycles),
            cycles=cycles,
            dependency_types=types,
            graph_version=graph.version,
            analyzed_nodes=len(adj),
            analyzed_edges=edges,
            duration_seconds=perf_counter() - started,
            suggestions=suggestions,
        )
