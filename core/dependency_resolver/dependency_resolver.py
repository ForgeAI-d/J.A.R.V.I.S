from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any

from core.common import BaseKernelComponent

from .analysis_report import AnalysisReport
from .cycle_detector import CycleDetector
from .dependency_inspector import DependencyInspector
from .dependency_matrix import DependencyMatrix
from .graph_analyzer import GraphAnalyzer
from .dependency_edge import DependencyEdge
from .dependency_graph import DependencyGraph
from .graph_cache import GraphCache
from .graph_exporter import GraphExporter
from .graph_metrics import GraphMetrics
from .graph_visualizer import GraphVisualizer
from .resolve_engine import ResolveEngine
from .resolve_result import ResolveResult
from .dependency_observer import DependencyObserver
from .runtime_dependency_manager import RuntimeDependencyManager
from .dependency_node import DependencyNode
from .dependency_report import DependencyReport
from .dependency_validator import DependencyValidator


class DependencyResolver(BaseKernelComponent):
    """Central dependency coordinator for the J.A.R.V.I.S. kernel."""

    VERSION = "0.5.0"
    BUILD_STATUS = "PHASE_5"
    COMPONENT_ID = "core.dependency_resolver"

    VALID_STATES = {
        "CREATED",
        "INITIALIZING",
        "READY",
        "RUNNING",
        "STOPPING",
        "STOPPED",
        "DEGRADED",
        "ERROR",
    }

    def __init__(self, context: Any | None = None) -> None:
        self.name = "Dependency Resolver"
        self.component_id = self.COMPONENT_ID
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Verwaltet den gerichteten Abhängigkeitsgraphen des "
            "J.A.R.V.I.S.-Kernels und stellt dessen konsistente "
            "Auflösung, Validierung und Berichterstattung sicher."
        )

        self.context = context
        self.graph = DependencyGraph()
        self.validator = DependencyValidator()
        self.cycle_detector = CycleDetector()
        self.graph_analyzer = GraphAnalyzer()
        self.inspector = DependencyInspector()
        self.matrix_builder = DependencyMatrix()
        self.metrics_engine = GraphMetrics()
        self.visualizer = GraphVisualizer()
        self.exporter = GraphExporter()
        self.resolve_engine = ResolveEngine()
        self.cache = GraphCache()
        self.last_resolve_result: dict[str, Any] | None = None
        self.observer = DependencyObserver()
        self.runtime_manager = RuntimeDependencyManager(self)

        self.status = "CREATED"
        self.health = 100
        self.last_error: dict[str, Any] | None = None

        self.created_at = datetime.now(UTC).isoformat()
        self.initialized_at: str | None = None
        self.started_at: str | None = None
        self.stopped_at: str | None = None

        self.lifecycle = {
            "registered": False,
            "dependencies_resolved": True,
            "initialized": False,
            "started": False,
            "healthy": True,
        }

        self.timeline: list[dict[str, Any]] = []
        self.last_validation_report: dict[str, Any] | None = None

        self._lock = RLock()

        self._statistics = {
            "components_registered": 0,
            "components_replaced": 0,
            "components_unregistered": 0,
            "dependencies_added": 0,
            "dependencies_replaced": 0,
            "dependencies_removed": 0,
            "validations": 0,
            "resolve_calls": 0,
            "resolve_successes": 0,
            "resolve_failures": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_resolve_time_seconds": 0.0,
            "fastest_resolve_time_seconds": None,
            "slowest_resolve_time_seconds": None,
            "last_resolve_time_seconds": None,
            "cycle_checks": 0,
            "cycles_detected_total": 0,
            "graph_analyses": 0,
            "component_inspections": 0,
            "matrix_builds": 0,
            "metrics_calculations": 0,
            "visualizations_created": 0,
            "analysis_reports_created": 0,
            "exports_created": 0,
            "runtime_transactions_started": 0,
            "runtime_transactions_committed": 0,
            "runtime_transactions_rolled_back": 0,
            "runtime_changes": 0,
            "hot_reloads": 0,
            "observer_notifications": 0,
            "errors_recorded": 0,
            "timeline_events": 0,
        }

        self.capabilities = [
            "component_registration",
            "component_unregistration",
            "dependency_registration",
            "dependency_removal",
            "dependency_queries",
            "graph_export",
            "structural_validation",
            "topological_sort",
            "priority_aware_resolution",
            "deterministic_boot_order",
            "shutdown_order_generation",
            "graph_versioning",
            "resolve_cache",
            "resolve_performance_metrics",
            "cycle_detection",
            "multi_cycle_reporting",
            "graph_analysis",
            "component_inspection",
            "dependency_matrix",
            "graph_metrics",
            "critical_component_detection",
            "ascii_visualization",
            "json_export",
            "graphviz_dot_export",
            "analysis_reporting",
            "runtime_transactions",
            "atomic_graph_mutation",
            "automatic_rollback",
            "runtime_validation",
            "dependency_observers",
            "component_hot_reload",
            "kernel_context_integration",
            "timeline",
            "health",
            "statistics",
            "thread_safe_access",
        ]

    # =====================================================
    # Lifecycle
    # =====================================================

    def initialize(self) -> bool:
        with self._lock:
            if self.lifecycle["initialized"]:
                return True

            self._set_state("INITIALIZING")
            self.initialized_at = datetime.now(UTC).isoformat()
            self.lifecycle["initialized"] = True
            self.lifecycle["healthy"] = True

        if self.context is not None:
            self.bind_context(self.context)

        self._set_state("READY")
        self._timeline("DEPENDENCY_RESOLVER_INITIALIZED")
        return True

    def start(self) -> bool:
        if not self.lifecycle["initialized"] and not self.initialize():
            return False

        with self._lock:
            if self.lifecycle["started"]:
                return True

            self.started_at = datetime.now(UTC).isoformat()
            self.stopped_at = None
            self.lifecycle["started"] = True

        self._set_state("RUNNING")
        self._timeline("DEPENDENCY_RESOLVER_STARTED")
        return True

    def stop(self) -> bool:
        with self._lock:
            if not self.lifecycle["started"]:
                self._set_state("STOPPED")
                return True

            self._set_state("STOPPING")
            self.lifecycle["started"] = False
            self.stopped_at = datetime.now(UTC).isoformat()

        self._set_state("STOPPED")
        self._timeline("DEPENDENCY_RESOLVER_STOPPED")
        return True

    def bind_context(self, context: Any) -> bool:
        if context is None:
            return self._set_error(
                "KernelContext instance cannot be None.",
                critical=False,
            )

        self.context = context

        register_service = getattr(context, "register_service", None)

        if callable(register_service):
            existing = getattr(context, "get_service", lambda _name: None)(
                "dependencies"
            )

            if existing is not self:
                registered = register_service(
                    "dependencies",
                    self,
                    replace=existing is not None,
                    protected=True,
                    metadata={
                        "bound_by": self.component_id,
                        "version": self.version,
                    },
                )

                if not registered:
                    return self._set_error(
                        "Could not register DependencyResolver in KernelContext.",
                        critical=False,
                    )

        self.lifecycle["registered"] = True
        self._timeline("KERNEL_CONTEXT_BOUND")
        return True

    # =====================================================
    # Component Registration
    # =====================================================

    def register_component(
        self,
        component: Any | None = None,
        *,
        component_id: str | None = None,
        name: str | None = None,
        component_type: str | None = None,
        version: str | None = None,
        status: str = "REGISTERED",
        priority: int = 100,
        metadata: dict[str, Any] | None = None,
        replace: bool = False,
    ) -> bool:
        try:
            resolved_id = component_id or self._extract_component_id(component)

            if resolved_id is None:
                return self._set_error(
                    "A component_id or identifiable component is required.",
                    critical=False,
                )

            node = DependencyNode(
                component_id=resolved_id,
                name=(
                    name
                    or getattr(component, "name", None)
                    or resolved_id
                ),
                component_type=(
                    component_type
                    or self._extract_component_type(component)
                ),
                version=(
                    version
                    or getattr(component, "version", None)
                    or "0.1.0"
                ),
                status=(
                    getattr(component, "status", None)
                    or status
                ),
                priority=priority,
                metadata={
                    **deepcopy(metadata or {}),
                    "python_class": (
                        component.__class__.__name__
                        if component is not None
                        else None
                    ),
                },
            )

            existed = self.graph.has_node(node.component_id)
            registered = self.graph.add_node(node, replace=replace)

            if not registered:
                return self._set_error(
                    f"Component '{node.component_id}' is already registered.",
                    critical=False,
                )

            with self._lock:
                if existed:
                    self._statistics["components_replaced"] += 1
                else:
                    self._statistics["components_registered"] += 1

            self.cache.invalidate()
            payload = {
                "component_id": node.component_id,
                "component_type": node.component_type,
                "replaced": existed,
            }
            self._timeline("DEPENDENCY_COMPONENT_REGISTERED", payload)
            self._record_runtime_change("COMPONENT_REGISTERED", payload)
            return True

        except (TypeError, ValueError, LookupError) as exc:
            return self._set_error(str(exc), critical=False)

    def unregister_component(
        self,
        component_id: str,
    ) -> bool:
        try:
            removed, removed_edges = self.graph.remove_node(component_id)

            if not removed:
                return False

            with self._lock:
                self._statistics["components_unregistered"] += 1
                self._statistics["dependencies_removed"] += len(removed_edges)

            self.cache.invalidate()
            payload = {
                "component_id": component_id,
                "removed_dependency_count": len(removed_edges),
            }
            self._timeline("DEPENDENCY_COMPONENT_UNREGISTERED", payload)
            self._record_runtime_change("COMPONENT_UNREGISTERED", payload)
            return True

        except (TypeError, ValueError) as exc:
            return self._set_error(str(exc), critical=False)

    def has_component(self, component_id: str) -> bool:
        try:
            return self.graph.has_node(component_id)
        except (TypeError, ValueError):
            return False

    def get_component(
        self,
        component_id: str,
    ) -> dict[str, Any] | None:
        try:
            node = self.graph.get_node(component_id)
            return node.to_dict() if node is not None else None
        except (TypeError, ValueError):
            return None

    def list_components(self) -> list[dict[str, Any]]:
        return [
            node.to_dict()
            for node in sorted(
                self.graph.list_nodes(),
                key=lambda item: (
                    item.priority,
                    item.component_id,
                ),
            )
        ]

    # =====================================================
    # Dependencies
    # =====================================================

    def add_dependency(
        self,
        component_id: str,
        depends_on: str,
        dependency_type: str = "required",
        metadata: dict[str, Any] | None = None,
        replace: bool = False,
    ) -> bool:
        try:
            edge = DependencyEdge(
                source_id=component_id,
                target_id=depends_on,
                dependency_type=dependency_type,
                metadata=metadata or {},
            )

            existed = edge.key in {
                item.key
                for item in self.graph.list_edges()
            }

            added = self.graph.add_edge(edge, replace=replace)

            if not added:
                return self._set_error(
                    (
                        f"Dependency '{component_id}' -> '{depends_on}' "
                        f"({dependency_type}) already exists."
                    ),
                    critical=False,
                )

            with self._lock:
                if existed:
                    self._statistics["dependencies_replaced"] += 1
                else:
                    self._statistics["dependencies_added"] += 1

            self.cache.invalidate()
            payload = edge.to_dict()
            self._timeline("DEPENDENCY_ADDED", payload)
            self._record_runtime_change("DEPENDENCY_ADDED", payload)
            return True

        except (TypeError, ValueError, LookupError) as exc:
            return self._set_error(str(exc), critical=False)

    def remove_dependency(
        self,
        component_id: str,
        depends_on: str,
        dependency_type: str | None = None,
    ) -> bool:
        try:
            removed = self.graph.remove_edge(
                component_id,
                depends_on,
                dependency_type,
            )

            if not removed:
                return False

            with self._lock:
                self._statistics["dependencies_removed"] += len(removed)

            self.cache.invalidate()
            payload = {
                "component_id": component_id,
                "depends_on": depends_on,
                "dependency_type": dependency_type,
                "removed_count": len(removed),
            }
            self._timeline("DEPENDENCY_REMOVED", payload)
            self._record_runtime_change("DEPENDENCY_REMOVED", payload)
            return True

        except (TypeError, ValueError) as exc:
            return self._set_error(str(exc), critical=False)

    def get_dependencies(
        self,
        component_id: str,
        dependency_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return [
                edge.to_dict()
                for edge in self.graph.get_dependencies(
                    component_id,
                    dependency_types,
                )
            ]
        except (TypeError, ValueError):
            return []

    def get_dependents(
        self,
        component_id: str,
        dependency_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return [
                edge.to_dict()
                for edge in self.graph.get_dependents(
                    component_id,
                    dependency_types,
                )
            ]
        except (TypeError, ValueError):
            return []

    def list_dependencies(self) -> list[dict[str, Any]]:
        return [
            edge.to_dict()
            for edge in self.graph.list_edges()
        ]

    # =====================================================
    # Validation and Resolution Interfaces
    # =====================================================

    def validate(self) -> dict[str, Any]:
        report = self.validator.validate(self.graph)

        with self._lock:
            self._statistics["validations"] += 1
            self.last_validation_report = report.to_dict()

            if report.valid:
                self.health = 100
                self.lifecycle["healthy"] = True
            else:
                self.health = 50
                self.lifecycle["healthy"] = False
                self._set_state("DEGRADED")

        self._timeline(
            "DEPENDENCY_GRAPH_VALIDATED",
            {
                "valid": report.valid,
                "error_count": len(report.errors),
                "warning_count": len(report.warnings),
            },
        )
        return report.to_dict()


    def resolve(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        force: bool = False,
    ) -> dict[str, Any]:
        normalized_types = tuple(
            sorted(
                {
                    str(item).strip().lower()
                    for item in dependency_types
                    if str(item).strip()
                }
            )
        )

        if not normalized_types:
            normalized_types = ("required",)

        with self._lock:
            self._statistics["resolve_calls"] += 1

        self._timeline(
            "RESOLVE_STARTED",
            {
                "graph_version": self.graph.version,
                "dependency_types": list(normalized_types),
                "force": force,
            },
        )

        validation = self.validate()

        if not validation["valid"]:
            with self._lock:
                self._statistics["resolve_failures"] += 1

            report = DependencyReport(
                report_type="RESOLUTION",
                valid=False,
                summary="Resolution aborted because validation failed.",
                errors=validation["errors"],
                warnings=validation["warnings"],
                details={
                    "boot_order": [],
                    "shutdown_order": [],
                    "graph_version": self.graph.version,
                    "algorithm": self.resolve_engine.ALGORITHM,
                    "cached": False,
                },
            ).to_dict()

            self.last_resolve_result = deepcopy(report)
            self._timeline("RESOLVE_FAILED", report["details"])
            return report

        if not force:
            cached = self.cache.get(
                self.graph.version,
                normalized_types,
            )

            if cached is not None:
                with self._lock:
                    self._statistics["cache_hits"] += 1
                    self._statistics["resolve_successes"] += 1

                cached_result = ResolveResult(
                    boot_order=cached.boot_order,
                    shutdown_order=cached.shutdown_order,
                    graph_version=cached.graph_version,
                    duration_seconds=0.0,
                    algorithm=cached.algorithm,
                    cached=True,
                    component_count=cached.component_count,
                    edge_count=cached.edge_count,
                )

                report = DependencyReport(
                    report_type="RESOLUTION",
                    valid=True,
                    summary="Dependency graph resolved from cache.",
                    warnings=validation["warnings"],
                    details=cached_result.to_dict(),
                ).to_dict()

                self.last_resolve_result = deepcopy(report)
                self._timeline(
                    "RESOLVE_CACHE_HIT",
                    {
                        "graph_version": self.graph.version,
                        "component_count": cached.component_count,
                    },
                )
                self._timeline(
                    "RESOLVE_FINISHED",
                    report["details"],
                )
                return report

        with self._lock:
            self._statistics["cache_misses"] += 1

        self._timeline(
            "RESOLVE_CACHE_MISS",
            {"graph_version": self.graph.version},
        )

        try:
            result = self.resolve_engine.resolve(
                self.graph,
                normalized_types,
            )
        except ValueError as exc:
            with self._lock:
                self._statistics["resolve_failures"] += 1

            self._set_error(str(exc), critical=False)

            report = DependencyReport(
                report_type="RESOLUTION",
                valid=False,
                summary="Topological resolution failed.",
                errors=[
                    {
                        "code": "TOPOLOGICAL_RESOLUTION_FAILED",
                        "message": str(exc),
                    }
                ],
                warnings=validation["warnings"],
                details={
                    "boot_order": [],
                    "shutdown_order": [],
                    "graph_version": self.graph.version,
                    "algorithm": self.resolve_engine.ALGORITHM,
                    "cached": False,
                },
            ).to_dict()

            self.last_resolve_result = deepcopy(report)
            self._timeline("RESOLVE_FAILED", report["details"])
            return report

        self.cache.put(
            self.graph.version,
            normalized_types,
            result,
        )
        self._record_resolve_performance(result.duration_seconds)

        with self._lock:
            self._statistics["resolve_successes"] += 1

        report = DependencyReport(
            report_type="RESOLUTION",
            valid=True,
            summary="Dependency graph resolved successfully.",
            warnings=validation["warnings"],
            details=result.to_dict(),
        ).to_dict()

        self.last_resolve_result = deepcopy(report)

        self._timeline(
            "GRAPH_ANALYZED",
            {
                "graph_version": result.graph_version,
                "component_count": result.component_count,
                "edge_count": result.edge_count,
            },
        )
        self._timeline(
            "BOOT_ORDER_CREATED",
            {"boot_order": list(result.boot_order)},
        )
        self._timeline(
            "SHUTDOWN_ORDER_CREATED",
            {"shutdown_order": list(result.shutdown_order)},
        )
        self._timeline(
            "RESOLVE_FINISHED",
            result.to_dict(),
        )
        return report

    def get_boot_order(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        force: bool = False,
    ) -> list[str]:
        report = self.resolve(
            dependency_types=dependency_types,
            force=force,
        )
        return list(report.get("details", {}).get("boot_order", []))

    def get_shutdown_order(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        force: bool = False,
    ) -> list[str]:
        report = self.resolve(
            dependency_types=dependency_types,
            force=force,
        )
        return list(report.get("details", {}).get("shutdown_order", []))
    def get_cycle_report(self, dependency_types: tuple[str, ...] = ("required",)) -> dict[str, Any]:
        report = self.cycle_detector.analyze(self.graph, dependency_types).to_dict()
        with self._lock:
            self._statistics["cycle_checks"] += 1
            self._statistics["cycles_detected_total"] += report["cycle_count"]
        for cycle in report["cycles"]:
            self._timeline("CYCLE_FOUND", {"cycle": cycle})
        self._timeline("CYCLE_REPORT_CREATED", {
            "has_cycles": report["has_cycles"],
            "cycle_count": report["cycle_count"],
        })
        return report

    def has_cycles(self, dependency_types: tuple[str, ...] = ("required",)) -> bool:
        return self.get_cycle_report(dependency_types)["has_cycles"]

    def get_cycles(self, dependency_types: tuple[str, ...] = ("required",)) -> list[list[str]]:
        return self.get_cycle_report(dependency_types)["cycles"]

    def validate_cycles(self, dependency_types: tuple[str, ...] = ("required",)) -> dict[str, Any]:
        report = self.get_cycle_report(dependency_types)
        return {
            "valid": not report["has_cycles"],
            "errors": [
                {"code": "DEPENDENCY_CYCLE", "message": "A dependency cycle was detected.", "cycle": cycle}
                for cycle in report["cycles"]
            ],
            "warnings": [],
            "details": report,
        }

    def analyze_graph(self, dependency_types: tuple[str, ...] = ("required",)) -> dict[str, Any]:
        report = self.graph_analyzer.analyze(self.graph, dependency_types)
        with self._lock:
            self._statistics["graph_analyses"] += 1
        self._timeline("GRAPH_ANALYZED", {
            "node_count": report["node_count"],
            "edge_count": report["edge_count"],
            "cycle_count": report["cycle_report"]["cycle_count"],
        })
        return report

    # =====================================================
    # Phase 4: Analysis, Diagnostics and Export
    # =====================================================

    def inspect(
        self,
        component_id: str,
        dependency_types: tuple[str, ...] = ("required",),
        critical_threshold: int | None = None,
    ) -> dict[str, Any]:
        report = self.inspector.inspect(
            self.graph,
            component_id,
            dependency_types,
            critical_threshold,
        )
        with self._lock:
            self._statistics["component_inspections"] += 1
        self._timeline("INSPECTION_CREATED", {
            "component_id": report["component"]["component_id"],
            "critical": report["critical"],
        })
        return report

    def get_dependency_matrix(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        *,
        ascii_output: bool = False,
    ) -> dict[str, Any] | str:
        matrix = self.matrix_builder.build(self.graph, dependency_types)
        with self._lock:
            self._statistics["matrix_builds"] += 1
        self._timeline("DEPENDENCY_MATRIX_CREATED", {
            "node_count": len(matrix["nodes"]),
        })
        return self.matrix_builder.to_ascii(matrix) if ascii_output else matrix

    def get_metrics(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        critical_threshold: int | None = None,
    ) -> dict[str, Any]:
        self._timeline("ANALYSIS_STARTED", {
            "dependency_types": list(dependency_types),
        })
        metrics = self.metrics_engine.calculate(
            self.graph,
            dependency_types,
            critical_threshold,
        )
        with self._lock:
            self._statistics["metrics_calculations"] += 1
        self._timeline("METRICS_CREATED", {
            "node_count": metrics["node_count"],
            "edge_count": metrics["edge_count"],
            "critical_count": len(metrics["critical_components"]),
        })
        return metrics

    def visualize_graph(
        self,
        style: str = "tree",
        dependency_types: tuple[str, ...] = ("required",),
    ) -> str:
        normalized = style.strip().lower()
        if normalized == "tree":
            output = self.visualizer.tree(self.graph, dependency_types)
        elif normalized == "compact":
            output = self.visualizer.compact(self.graph, dependency_types)
        elif normalized in {"arrows", "arrow"}:
            output = self.visualizer.arrows(self.graph, dependency_types)
        else:
            raise ValueError(f"Unsupported graph visualization style: {style}")
        with self._lock:
            self._statistics["visualizations_created"] += 1
        self._timeline("GRAPH_VISUALIZED", {"style": normalized})
        return output

    def analysis_report(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        *,
        text: bool = False,
        critical_threshold: int | None = None,
    ) -> dict[str, Any] | str:
        metrics = self.get_metrics(dependency_types, critical_threshold)
        report = AnalysisReport(
            resolver_version=self.version,
            metrics=metrics,
        )
        with self._lock:
            self._statistics["analysis_reports_created"] += 1
        self._timeline("REPORT_CREATED", {
            "health": report.to_dict()["health"],
        })
        return report.to_text() if text else report.to_dict()

    def export_json(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        *,
        path: str | None = None,
        indent: int = 2,
    ) -> str:
        content = self.exporter.to_json(
            self.graph,
            dependency_types,
            indent=indent,
        )
        if path is not None:
            self.exporter.write(content, path)
        self._record_export("json", path)
        return content

    def export_dot(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        *,
        path: str | None = None,
    ) -> str:
        content = self.exporter.to_dot(self.graph, dependency_types)
        if path is not None:
            self.exporter.write(content, path)
        self._record_export("dot", path)
        return content

    def export_ascii(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        *,
        style: str = "tree",
        path: str | None = None,
    ) -> str:
        content = self.exporter.to_ascii(
            self.graph,
            dependency_types,
            style=style,
        )
        if path is not None:
            self.exporter.write(content, path)
        self._record_export("ascii", path, style=style)
        return content

    def _record_export(
        self,
        export_type: str,
        path: str | None,
        **details: Any,
    ) -> None:
        with self._lock:
            self._statistics["exports_created"] += 1
        self._timeline("EXPORT_CREATED", {
            "export_type": export_type,
            "path": path,
            **details,
        })

    # =====================================================
    # Runtime Dependency Management (Phase 5)
    # =====================================================

    def subscribe(self, event_type: str, callback: Any) -> bool:
        return self.observer.subscribe(event_type, callback)

    def unsubscribe(self, event_type: str, callback: Any) -> bool:
        return self.observer.unsubscribe(event_type, callback)

    def begin_transaction(self, label: str | None = None) -> dict[str, Any]:
        try:
            result = self.runtime_manager.begin(label)
        except (RuntimeError, TypeError, ValueError) as exc:
            return {"started": False, "error": str(exc)}
        with self._lock:
            self._statistics["runtime_transactions_started"] += 1
        payload = {**result, "started": True}
        self._timeline("TRANSACTION_STARTED", payload)
        self._notify("TRANSACTION_STARTED", payload)
        return payload

    def commit_transaction(
        self,
        dependency_types: tuple[str, ...] = ("required",),
        validate: bool = True,
    ) -> dict[str, Any]:
        try:
            result = self.runtime_manager.commit(dependency_types, validate)
        except RuntimeError as exc:
            return {"committed": False, "rolled_back": False, "error": str(exc)}

        if result["committed"]:
            with self._lock:
                self._statistics["runtime_transactions_committed"] += 1
            self._timeline("TRANSACTION_COMMITTED", result)
            self._notify("TRANSACTION_COMMITTED", result)
        else:
            with self._lock:
                self._statistics["runtime_transactions_rolled_back"] += 1
            self._timeline("TRANSACTION_ROLLED_BACK", result)
            self._notify("TRANSACTION_ROLLED_BACK", result)
        return result

    def rollback_transaction(self, reason: str = "manual") -> dict[str, Any]:
        try:
            result = self.runtime_manager.rollback(reason=reason)
        except RuntimeError as exc:
            return {"rolled_back": False, "error": str(exc)}
        with self._lock:
            self._statistics["runtime_transactions_rolled_back"] += 1
        self._timeline("TRANSACTION_ROLLED_BACK", result)
        self._notify("TRANSACTION_ROLLED_BACK", result)
        return result

    def get_transaction_status(self) -> dict[str, Any]:
        return self.runtime_manager.status()

    def get_transaction_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self.runtime_manager.history(limit)

    def apply_runtime_change(
        self,
        operation: str,
        *,
        validate: bool = True,
        dependency_types: tuple[str, ...] = ("required",),
        **kwargs: Any,
    ) -> dict[str, Any]:
        operation_name = str(operation).strip().lower()
        operations = {
            "register_component": self.register_component,
            "unregister_component": self.unregister_component,
            "add_dependency": self.add_dependency,
            "remove_dependency": self.remove_dependency,
        }
        target = operations.get(operation_name)
        if target is None:
            return {"success": False, "error": f"Unsupported runtime operation: {operation}"}

        started = self.begin_transaction(label=f"runtime:{operation_name}")
        if not started.get("started"):
            return {"success": False, "error": started.get("error")}

        try:
            changed = bool(target(**kwargs))
        except Exception as exc:
            self.rollback_transaction(reason=f"operation_error:{exc}")
            return {"success": False, "error": str(exc), "rolled_back": True}

        if not changed:
            self.rollback_transaction(reason="operation_rejected")
            return {"success": False, "rolled_back": True, "error": "Runtime operation was rejected."}

        result = self.commit_transaction(dependency_types, validate)
        return {
            "success": bool(result.get("committed")),
            "rolled_back": bool(result.get("rolled_back")),
            "operation": operation_name,
            "result": result,
        }

    def reload_component(
        self,
        component_id: str,
        replacement: Any | None = None,
        *,
        validate: bool = True,
    ) -> dict[str, Any]:
        existing = self.get_component(component_id)
        if existing is None:
            return {"reloaded": False, "error": f"Unknown component: {component_id}"}

        started = self.begin_transaction(label=f"reload:{component_id}")
        if not started.get("started"):
            return {"reloaded": False, "error": started.get("error")}

        try:
            if replacement is not None:
                stop = getattr(replacement, "stop", None)
                initialize = getattr(replacement, "initialize", None)
                start = getattr(replacement, "start", None)
                # Registration is replaced atomically; lifecycle calls are optional.
                changed = self.register_component(
                    replacement,
                    component_id=component_id,
                    priority=existing["priority"],
                    metadata={**existing.get("metadata", {}), "hot_reloaded": True},
                    replace=True,
                )
                if not changed:
                    raise RuntimeError("Replacement component could not be registered.")
                if callable(initialize) and initialize() is False:
                    raise RuntimeError("Replacement initialize() failed.")
                if callable(start) and start() is False:
                    raise RuntimeError("Replacement start() failed.")
            else:
                changed = self.register_component(
                    component_id=component_id,
                    name=existing["name"],
                    component_type=existing["component_type"],
                    version=existing["version"],
                    status="RELOADED",
                    priority=existing["priority"],
                    metadata={**existing.get("metadata", {}), "hot_reloaded": True},
                    replace=True,
                )
                if not changed:
                    raise RuntimeError("Component metadata reload failed.")

            result = self.commit_transaction(validate=validate)
            if not result.get("committed"):
                return {"reloaded": False, "rolled_back": True, "result": result}

            with self._lock:
                self._statistics["hot_reloads"] += 1
            payload = {"component_id": component_id, "replacement": replacement is not None}
            self._timeline("COMPONENT_RELOADED", payload)
            self._notify("COMPONENT_RELOADED", payload)
            return {"reloaded": True, "component_id": component_id, "result": result}
        except Exception as exc:
            if self.runtime_manager.active:
                self.rollback_transaction(reason=f"reload_error:{exc}")
            return {"reloaded": False, "rolled_back": True, "error": str(exc)}

    def _record_runtime_change(self, change_type: str, payload: dict[str, Any]) -> None:
        self.runtime_manager.record(change_type, payload)
        with self._lock:
            self._statistics["runtime_changes"] += 1
        self._notify(change_type, payload)

    def _notify(self, event_type: str, payload: dict[str, Any]) -> None:
        result = self.observer.emit(event_type, payload)
        with self._lock:
            self._statistics["observer_notifications"] += result["delivered"]

    # =====================================================
    # Information
    # =====================================================

    def export_graph(self) -> dict[str, Any]:
        return self.graph.export()

    def get_manifest(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "build_status": self.BUILD_STATUS,
            "author": self.author,
            "mission": self.mission,
            "manager": "KernelController",
            "requires": ["core.kernel_context"],
            "optional": ["core.event_bus", "core.logger"],
            "capabilities": deepcopy(self.capabilities),
        }

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            stats = deepcopy(self._statistics)
            measured = max(stats["resolve_successes"] - stats["cache_hits"], 0)
            stats["average_resolve_time_seconds"] = (
                stats["total_resolve_time_seconds"] / measured
                if measured
                else 0.0
            )

            return {
                **stats,
                **self.graph.statistics(),
                **self.cache.statistics(),
                **self.observer.statistics(),
                "transaction_active": self.runtime_manager.active,
                "transaction_history_count": len(self.runtime_manager.history()),
                "timeline_count": len(self.timeline),
                "created_at": self.created_at,
                "initialized_at": self.initialized_at,
                "started_at": self.started_at,
                "stopped_at": self.stopped_at,
            }

    def get_health(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "status": self.status,
            "health": self.health,
            "healthy": self.lifecycle["healthy"],
            "started": self.lifecycle["started"],
            "last_error": deepcopy(self.last_error),
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.get_health(),
            "lifecycle": deepcopy(self.lifecycle),
            "statistics": self.get_statistics(),
            "last_validation_report": deepcopy(
                self.last_validation_report
            ),
            "last_resolve_result": deepcopy(
                self.last_resolve_result
            ),
            "graph": self.export_graph(),
            "last_error": deepcopy(self.last_error),
        }

    def get_timeline(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            events = self.timeline if limit is None else self.timeline[-limit:]
            return deepcopy(events)

    # =====================================================
    # Internal Helpers
    # =====================================================


    def _record_resolve_performance(self, duration: float) -> None:
        with self._lock:
            stats = self._statistics
            stats["total_resolve_time_seconds"] += duration
            stats["last_resolve_time_seconds"] = duration

            fastest = stats["fastest_resolve_time_seconds"]
            slowest = stats["slowest_resolve_time_seconds"]

            if fastest is None or duration < fastest:
                stats["fastest_resolve_time_seconds"] = duration

            if slowest is None or duration > slowest:
                stats["slowest_resolve_time_seconds"] = duration
    def _set_state(self, state: str) -> bool:
        normalized = str(state).strip().upper()

        if normalized not in self.VALID_STATES:
            return self._set_error(
                f"Invalid resolver state: {state}",
                critical=False,
            )

        with self._lock:
            previous = self.status
            self.status = normalized

        self._timeline(
            "DEPENDENCY_RESOLVER_STATE_CHANGED",
            {
                "previous_state": previous,
                "current_state": normalized,
            },
        )
        return True

    def _set_error(
        self,
        error: Any,
        *,
        critical: bool = True,
    ) -> bool:
        error_data = {
            "message": str(error),
            "critical": bool(critical),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        with self._lock:
            self.last_error = error_data
            self._statistics["errors_recorded"] += 1

            if critical:
                self.status = "ERROR"
                self.health = 0
                self.lifecycle["healthy"] = False
            else:
                self.health = min(self.health, 80)

        self._timeline(
            "DEPENDENCY_RESOLVER_ERROR",
            error_data,
        )
        return False

    def clear_error(self) -> bool:
        with self._lock:
            self.last_error = None

            if self.status == "ERROR":
                self.status = "DEGRADED"
                self.health = 50

        return True

    def _timeline(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "event_type": event_type,
            "component_id": self.component_id,
            "payload": deepcopy(payload or {}),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        with self._lock:
            self.timeline.append(event)
            self._statistics["timeline_events"] += 1

        context = self.context

        if context is not None:
            add_timeline_event = getattr(
                context,
                "add_timeline_event",
                None,
            )

            if callable(add_timeline_event):
                try:
                    add_timeline_event(event_type, payload or {})
                except Exception:
                    pass

            event_bus = getattr(context, "event_bus", None)

            if event_bus is not None:
                for method_name in ("emit", "publish", "dispatch"):
                    method = getattr(event_bus, method_name, None)

                    if callable(method):
                        try:
                            method(event_type, deepcopy(payload or {}))
                        except TypeError:
                            try:
                                method(
                                    {
                                        "type": event_type,
                                        "payload": deepcopy(payload or {}),
                                    }
                                )
                            except Exception:
                                pass
                        except Exception:
                            pass
                        break

    @staticmethod
    def _extract_component_id(component: Any | None) -> str | None:
        if component is None:
            return None

        for attribute in (
            "component_id",
            "manager_id",
            "engine_id",
            "plugin_id",
            "service_id",
        ):
            value = getattr(component, attribute, None)

            if value:
                return str(value)

        return None

    @staticmethod
    def _extract_component_type(component: Any | None) -> str:
        if component is None:
            return "service"

        if getattr(component, "manager_id", None):
            return "manager"

        if getattr(component, "engine_id", None):
            return "engine"

        if getattr(component, "plugin_id", None):
            return "plugin"

        return "service"


if __name__ == "__main__":
    class DummyContext:
        def __init__(self) -> None:
            self.services = {}
            self.timeline = []

        def register_service(
            self,
            name,
            service,
            replace=False,
            protected=False,
            metadata=None,
        ):
            if name in self.services and not replace:
                return False
            self.services[name] = service
            return True

        def get_service(self, name):
            return self.services.get(name)

        def add_timeline_event(self, event_type, payload=None):
            self.timeline.append((event_type, payload or {}))
            return True

    class DummyComponent:
        def __init__(
            self,
            component_id,
            name,
            component_type="service",
        ):
            self.component_id = component_id
            self.name = name
            self.version = "1.0.0"
            self.status = "READY"

            if component_type == "manager":
                self.manager_id = component_id
            elif component_type == "engine":
                self.engine_id = component_id

    context = DummyContext()
    resolver = DependencyResolver(context=context)

    print("=== DEPENDENCY RESOLVER PHASE 1 TEST ===")
    print("Initialize:", resolver.initialize())
    print("Start:", resolver.start())

    logger = DummyComponent("core.logger", "Logger")
    event_bus = DummyComponent("core.event_bus", "Event Bus")
    modules = DummyComponent(
        "core.module_manager",
        "Module Manager",
        "manager",
    )

    print("Register Logger:", resolver.register_component(logger))
    print("Register EventBus:", resolver.register_component(event_bus))
    print("Register ModuleManager:", resolver.register_component(modules))

    print(
        "Add ModuleManager -> Logger:",
        resolver.add_dependency(
            "core.module_manager",
            "core.logger",
            "required",
        ),
    )

    print(
        "Add ModuleManager -> EventBus:",
        resolver.add_dependency(
            "core.module_manager",
            "core.event_bus",
            "required",
        ),
    )

    validation = resolver.validate()
    resolution = resolver.resolve()

    print("Validation valid:", validation["valid"])
    print("Warnings:", len(validation["warnings"]))
    print("Boot order:", resolution["details"]["boot_order"])
    print("Shutdown order:", resolution["details"]["shutdown_order"])
    print("Node count:", resolver.get_statistics()["node_count"])
    print("Edge count:", resolver.get_statistics()["edge_count"])
    print("Context binding:", context.get_service("dependencies") is resolver)
    print("Stop:", resolver.stop())

    success = all(
        [
            validation["valid"],
            resolver.get_statistics()["node_count"] == 3,
            resolver.get_statistics()["edge_count"] == 2,
            context.get_service("dependencies") is resolver,
            resolver.status == "STOPPED",
        ]
    )

    print("RESULT:", "PASS" if success else "FAIL")

    if not success:
        raise SystemExit(1)
