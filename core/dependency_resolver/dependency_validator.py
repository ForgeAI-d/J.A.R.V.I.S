from __future__ import annotations

from .dependency_graph import DependencyGraph
from .dependency_report import DependencyReport


class DependencyValidator:
    """Phase 1 structural validator.

    Advanced cycle and ordering validation is added in later phases.
    """

    def validate(self, graph: DependencyGraph) -> DependencyReport:
        errors: list[dict] = []
        warnings: list[dict] = []

        nodes = {
            node.component_id: node
            for node in graph.list_nodes()
        }

        for edge in graph.list_edges():
            if edge.source_id not in nodes:
                errors.append(
                    {
                        "code": "MISSING_SOURCE",
                        "message": (
                            f"Dependency source '{edge.source_id}' is missing."
                        ),
                        "edge": edge.to_dict(),
                    }
                )

            if edge.target_id not in nodes:
                errors.append(
                    {
                        "code": "MISSING_TARGET",
                        "message": (
                            f"Dependency target '{edge.target_id}' is missing."
                        ),
                        "edge": edge.to_dict(),
                    }
                )

        for node in nodes.values():
            dependencies = graph.get_dependencies(node.component_id)
            dependents = graph.get_dependents(node.component_id)

            if not dependencies and not dependents:
                warnings.append(
                    {
                        "code": "ISOLATED_COMPONENT",
                        "message": (
                            f"Component '{node.component_id}' is isolated."
                        ),
                        "component_id": node.component_id,
                    }
                )

        valid = not errors

        return DependencyReport(
            report_type="STRUCTURAL_VALIDATION",
            valid=valid,
            summary=(
                "Dependency graph is structurally valid."
                if valid
                else "Dependency graph contains structural errors."
            ),
            errors=errors,
            warnings=warnings,
            details=graph.statistics(),
        )
