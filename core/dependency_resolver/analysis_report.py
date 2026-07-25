from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


class AnalysisReport:
    """Immutable-style report formatter for Phase 4 diagnostics."""

    def __init__(self, *, resolver_version: str, metrics: dict[str, Any]) -> None:
        self.resolver_version = str(resolver_version)
        self.metrics = deepcopy(metrics)
        self.created_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        cycles = self.metrics["cycle_report"]["cycle_count"]
        isolated = len(self.metrics["isolated_nodes"])
        health = "GOOD" if cycles == 0 and isolated == 0 else "WARNING" if cycles == 0 else "CRITICAL"
        return {
            "report_type": "DEPENDENCY_ANALYSIS",
            "created_at": self.created_at,
            "resolver_version": self.resolver_version,
            "graph_version": self.metrics["graph_version"],
            "health": health,
            "summary": {
                "components": self.metrics["node_count"],
                "dependencies": self.metrics["edge_count"],
                "cycles": cycles,
                "roots": len(self.metrics["root_nodes"]),
                "leaves": len(self.metrics["leaf_nodes"]),
                "isolated": isolated,
                "independent_graphs": self.metrics["independent_graph_count"],
                "maximum_depth": self.metrics["maximum_depth"],
                "density": self.metrics["density"],
            },
            "critical_components": list(self.metrics["critical_components"]),
            "longest_chain": list(self.metrics["longest_chain"]),
            "metrics": deepcopy(self.metrics),
        }

    def to_text(self) -> str:
        report = self.to_dict()
        summary = report["summary"]
        critical = ", ".join(report["critical_components"]) or "None"
        chain = " -> ".join(report["longest_chain"]) or "None"
        return "\n".join([
            "Dependency Resolver Analysis",
            "============================",
            f"Resolver version: {report['resolver_version']}",
            f"Graph version: {report['graph_version']}",
            f"Health: {report['health']}",
            f"Components: {summary['components']}",
            f"Dependencies: {summary['dependencies']}",
            f"Cycles: {summary['cycles']}",
            f"Roots: {summary['roots']}",
            f"Leaves: {summary['leaves']}",
            f"Isolated: {summary['isolated']}",
            f"Independent graphs: {summary['independent_graphs']}",
            f"Maximum depth: {summary['maximum_depth']}",
            f"Density: {summary['density']}",
            f"Critical components: {critical}",
            f"Longest chain: {chain}",
        ])
