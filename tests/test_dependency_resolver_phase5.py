from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable


def locate_project_root() -> Path:
    candidates = [Path.cwd(), Path(__file__).resolve().parent]
    candidates.extend(Path(__file__).resolve().parents)
    for candidate in candidates:
        if (candidate / "core" / "dependency_resolver" / "__init__.py").is_file():
            return candidate
        if (candidate / "dependency_resolver" / "__init__.py").is_file():
            return candidate.parent if candidate.name == "core" else candidate
    raise RuntimeError("Projektwurzel mit core/dependency_resolver wurde nicht gefunden.")


PROJECT_ROOT = locate_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.dependency_resolver import DependencyResolver  # noqa: E402


class DummyComponent:
    def __init__(self, component_id: str, priority: int = 100) -> None:
        self.component_id = component_id
        self.name = component_id.replace("_", " ").title()
        self.version = "1.0.0"
        self.status = "READY"
        self.priority = priority
        self.initialized = False
        self.started = False

    def initialize(self) -> bool:
        self.initialized = True
        return True

    def start(self) -> bool:
        self.started = True
        return True


def build_resolver() -> DependencyResolver:
    resolver = DependencyResolver()
    assert resolver.initialize()
    assert resolver.start()
    return resolver


def register(resolver: DependencyResolver, component_id: str, priority: int = 100) -> None:
    assert resolver.register_component(
        DummyComponent(component_id, priority),
        priority=priority,
    )


# Phase 2 regression

def test_boot_order_and_cache() -> None:
    resolver = build_resolver()
    register(resolver, "config", 1)
    register(resolver, "logger", 10)
    register(resolver, "event_bus", 20)
    assert resolver.add_dependency("logger", "config")
    assert resolver.add_dependency("event_bus", "logger")
    first = resolver.resolve()
    second = resolver.resolve()
    assert first["valid"] is True
    assert first["details"]["boot_order"] == ["config", "logger", "event_bus"]
    assert second["details"]["cached"] is True


def test_optional_policy() -> None:
    resolver = build_resolver()
    register(resolver, "a", 100)
    register(resolver, "b", 1)
    assert resolver.add_dependency("b", "a", "optional")
    assert resolver.get_boot_order(force=True) == ["b", "a"]
    assert resolver.get_boot_order(("required", "optional"), True) == ["a", "b"]


# Phase 3 regression

def test_cycle_detection_and_analysis() -> None:
    resolver = build_resolver()
    for item in ("a", "b", "c", "isolated"):
        register(resolver, item)
    assert resolver.add_dependency("a", "b")
    assert resolver.add_dependency("b", "c")
    analysis = resolver.analyze_graph()
    assert analysis["maximum_depth"] == 2
    assert analysis["isolated_nodes"] == ["isolated"]
    assert resolver.add_dependency("c", "a")
    assert resolver.has_cycles() is True
    assert resolver.resolve(force=True)["valid"] is False


# Phase 4 regression

def test_phase4_diagnostics_and_exports() -> None:
    resolver = build_resolver()
    for item in ("config", "logger", "event_bus"):
        register(resolver, item)
    assert resolver.add_dependency("logger", "config")
    assert resolver.add_dependency("event_bus", "logger")
    inspection = resolver.inspect("logger")
    metrics = resolver.get_metrics()
    matrix = resolver.get_dependency_matrix()
    report = resolver.analysis_report()
    assert inspection["component"]["component_id"] == "logger"
    assert metrics["node_count"] == 3
    assert len(matrix["nodes"]) == 3
    assert report["metrics"]["edge_count"] == 2
    assert "digraph" in resolver.export_dot()
    assert '"nodes"' in resolver.export_json()
    assert "config" in resolver.export_ascii()


# Phase 5

def test_manual_transaction_commit() -> None:
    resolver = build_resolver()
    register(resolver, "a")
    register(resolver, "b")
    started = resolver.begin_transaction("valid-change")
    assert started["started"] is True
    assert resolver.add_dependency("b", "a")
    result = resolver.commit_transaction()
    assert result["committed"] is True
    assert resolver.get_dependencies("b")[0]["target_id"] == "a"
    assert resolver.get_transaction_status()["active"] is False


def test_manual_transaction_rollback() -> None:
    resolver = build_resolver()
    register(resolver, "a")
    register(resolver, "b")
    before = resolver.export_graph()
    assert resolver.begin_transaction("manual-rollback")["started"]
    assert resolver.add_dependency("a", "b")
    result = resolver.rollback_transaction("test")
    after = resolver.export_graph()
    assert result["rolled_back"] is True
    assert after["edges"] == before["edges"]
    assert resolver.get_dependencies("a") == []


def test_automatic_rollback_on_cycle() -> None:
    resolver = build_resolver()
    register(resolver, "a")
    register(resolver, "b")
    assert resolver.add_dependency("a", "b")
    assert resolver.begin_transaction("cycle")["started"]
    assert resolver.add_dependency("b", "a")
    result = resolver.commit_transaction()
    assert result["committed"] is False
    assert result["rolled_back"] is True
    assert resolver.has_cycles() is False
    assert resolver.get_dependencies("b") == []


def test_apply_runtime_change_success() -> None:
    resolver = build_resolver()
    register(resolver, "a")
    register(resolver, "b")
    result = resolver.apply_runtime_change(
        "add_dependency",
        component_id="b",
        depends_on="a",
    )
    assert result["success"] is True
    assert resolver.get_boot_order(force=True) == ["a", "b"]


def test_apply_runtime_change_rejected_and_rolled_back() -> None:
    resolver = build_resolver()
    register(resolver, "a")
    result = resolver.apply_runtime_change(
        "add_dependency",
        component_id="a",
        depends_on="missing",
    )
    assert result["success"] is False
    assert result["rolled_back"] is True
    assert resolver.list_dependencies() == []


def test_observer_delivery_and_unsubscribe() -> None:
    resolver = build_resolver()
    events: list[dict] = []

    def callback(event: dict) -> None:
        events.append(event)

    assert resolver.subscribe("DEPENDENCY_ADDED", callback)
    register(resolver, "a")
    register(resolver, "b")
    assert resolver.add_dependency("b", "a")
    assert events[-1]["event_type"] == "DEPENDENCY_ADDED"
    assert events[-1]["payload"]["source_id"] == "b"
    assert resolver.unsubscribe("DEPENDENCY_ADDED", callback)
    assert resolver.remove_dependency("b", "a")
    assert len(events) == 1


def test_observer_error_is_isolated() -> None:
    resolver = build_resolver()

    def broken(_event: dict) -> None:
        raise RuntimeError("observer failure")

    assert resolver.subscribe("COMPONENT_REGISTERED", broken)
    register(resolver, "safe")
    assert resolver.has_component("safe") is True
    assert resolver.get_statistics()["observer_callback_errors"] == 1


def test_hot_reload_metadata() -> None:
    resolver = build_resolver()
    register(resolver, "service")
    result = resolver.reload_component("service")
    component = resolver.get_component("service")
    assert result["reloaded"] is True
    assert component["status"] == "RELOADED"
    assert component["metadata"]["hot_reloaded"] is True


def test_hot_reload_replacement_lifecycle() -> None:
    resolver = build_resolver()
    register(resolver, "service")
    replacement = DummyComponent("service")
    replacement.version = "2.0.0"
    result = resolver.reload_component("service", replacement)
    assert result["reloaded"] is True
    assert replacement.initialized is True
    assert replacement.started is True
    assert resolver.get_component("service")["version"] == "2.0.0"


def test_nested_transaction_rejected() -> None:
    resolver = build_resolver()
    first = resolver.begin_transaction("one")
    second = resolver.begin_transaction("two")
    assert first["started"] is True
    assert second["started"] is False
    assert "already active" in second["error"]
    assert resolver.rollback_transaction()["rolled_back"] is True


def test_transaction_history_and_statistics() -> None:
    resolver = build_resolver()
    register(resolver, "a")
    assert resolver.begin_transaction("history")["started"]
    register(resolver, "b")
    assert resolver.commit_transaction()["committed"]
    history = resolver.get_transaction_history()
    stats = resolver.get_statistics()
    assert len(history) == 1
    assert history[0]["state"] == "COMMITTED"
    assert history[0]["change_count"] >= 1
    assert stats["runtime_transactions_started"] == 1
    assert stats["runtime_transactions_committed"] == 1


TESTS: list[tuple[str, Callable[[], None]]] = [
    ("Phase 2 – Boot order/cache", test_boot_order_and_cache),
    ("Phase 2 – Optional policy", test_optional_policy),
    ("Phase 3 – Cycles/analysis", test_cycle_detection_and_analysis),
    ("Phase 4 – Diagnostics/exports", test_phase4_diagnostics_and_exports),
    ("Phase 5 – Transaction commit", test_manual_transaction_commit),
    ("Phase 5 – Manual rollback", test_manual_transaction_rollback),
    ("Phase 5 – Automatic cycle rollback", test_automatic_rollback_on_cycle),
    ("Phase 5 – Runtime change", test_apply_runtime_change_success),
    ("Phase 5 – Rejected runtime change", test_apply_runtime_change_rejected_and_rolled_back),
    ("Phase 5 – Observer", test_observer_delivery_and_unsubscribe),
    ("Phase 5 – Observer isolation", test_observer_error_is_isolated),
    ("Phase 5 – Metadata reload", test_hot_reload_metadata),
    ("Phase 5 – Replacement reload", test_hot_reload_replacement_lifecycle),
    ("Phase 5 – Nested transaction", test_nested_transaction_rejected),
    ("Phase 5 – History/statistics", test_transaction_history_and_statistics),
]


def main() -> int:
    passed = 0
    print("=== DEPENDENCY RESOLVER PHASE 5 REGRESSION ===")
    for name, test in TESTS:
        try:
            test()
        except Exception as exc:
            print(f"{name}: FAIL")
            print(f"  {exc.__class__.__name__}: {exc}")
        else:
            passed += 1
            print(f"{name}: PASS")
    print(f"RESULT: {passed}/{len(TESTS)} PASS")
    return 0 if passed == len(TESTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
