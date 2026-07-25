from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Projektpfad automatisch erkennen
# ---------------------------------------------------------------------------

def find_project_root() -> Path:
    """Findet den J.A.R.V.I.S.-Projektstamm unabhängig vom Startordner."""

    current_file = Path(__file__).resolve()
    candidates = [
        current_file.parent,
        *current_file.parents,
        Path.cwd(),
        *Path.cwd().parents,
    ]

    checked: set[Path] = set()

    for candidate in candidates:
        candidate = candidate.resolve()

        if candidate in checked:
            continue

        checked.add(candidate)

        dependency_package = (
            candidate
            / "core"
            / "dependency_resolver"
            / "__init__.py"
        )

        if dependency_package.is_file():
            return candidate

    raise RuntimeError(
        "Der J.A.R.V.I.S.-Projektstamm wurde nicht gefunden. "
        "Die Datei muss im Projekt oder im Ordner tests/ liegen. "
        "Erwartet wird: core/dependency_resolver/__init__.py"
    )


PROJECT_ROOT = find_project_root()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from core.dependency_resolver import DependencyResolver  # noqa: E402


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def build_resolver() -> DependencyResolver:
    resolver = DependencyResolver()

    assert resolver.initialize() is True
    assert resolver.start() is True

    return resolver


def register_component(
    resolver: DependencyResolver,
    component_id: str,
    priority: int = 100,
) -> None:
    registered = resolver.register_component(
        component_id=component_id,
        name=component_id,
        priority=priority,
    )

    assert registered is True, (
        f"Komponente '{component_id}' konnte nicht registriert werden."
    )


# ---------------------------------------------------------------------------
# Phase 2 – Regressionstests
# ---------------------------------------------------------------------------

def test_phase2_linear_graph() -> None:
    resolver = build_resolver()

    for component_id in (
        "config",
        "logger",
        "event_bus",
        "modules",
    ):
        register_component(resolver, component_id)

    assert resolver.add_dependency("logger", "config")
    assert resolver.add_dependency("event_bus", "logger")
    assert resolver.add_dependency("modules", "event_bus")

    report = resolver.resolve(force=True)

    assert report["valid"] is True
    assert report["details"]["boot_order"] == [
        "config",
        "logger",
        "event_bus",
        "modules",
    ]
    assert report["details"]["shutdown_order"] == [
        "modules",
        "event_bus",
        "logger",
        "config",
    ]


def test_phase2_priority_and_determinism() -> None:
    resolver = build_resolver()

    register_component(resolver, "late", priority=50)
    register_component(resolver, "first", priority=1)
    register_component(resolver, "middle", priority=20)

    first_result = resolver.get_boot_order(force=True)
    second_result = resolver.get_boot_order(force=True)

    assert first_result == ["first", "middle", "late"]
    assert second_result == first_result


def test_phase2_independent_subgraphs() -> None:
    resolver = build_resolver()

    register_component(resolver, "a", priority=10)
    register_component(resolver, "b", priority=20)
    register_component(resolver, "c", priority=5)
    register_component(resolver, "d", priority=15)

    assert resolver.add_dependency("b", "a")
    assert resolver.add_dependency("d", "c")

    order = resolver.get_boot_order(force=True)

    assert order == ["c", "a", "d", "b"]
    assert order.index("a") < order.index("b")
    assert order.index("c") < order.index("d")


def test_phase2_cache_and_graph_version() -> None:
    resolver = build_resolver()

    register_component(resolver, "a")
    register_component(resolver, "b")

    assert resolver.add_dependency("b", "a")

    first_report = resolver.resolve()
    second_report = resolver.resolve()

    assert first_report["details"]["cached"] is False
    assert second_report["details"]["cached"] is True

    previous_version = resolver.graph.version

    register_component(resolver, "c")

    assert resolver.graph.version == previous_version + 1

    third_report = resolver.resolve()

    assert third_report["details"]["cached"] is False
    assert "c" in third_report["details"]["boot_order"]

    statistics = resolver.get_statistics()

    assert statistics["cache_hits"] >= 1
    assert statistics["cache_misses"] >= 2


def test_phase2_dependency_policies() -> None:
    resolver = build_resolver()

    register_component(resolver, "a", priority=100)
    register_component(resolver, "b", priority=1)

    assert resolver.add_dependency(
        "b",
        "a",
        dependency_type="optional",
    )

    required_only = resolver.get_boot_order(force=True)

    with_optional = resolver.get_boot_order(
        dependency_types=("required", "optional"),
        force=True,
    )

    assert required_only == ["b", "a"]
    assert with_optional == ["a", "b"]


# ---------------------------------------------------------------------------
# Phase 3 – Cycle Detection und Graphanalyse
# ---------------------------------------------------------------------------

def test_phase3_acyclic_graph() -> None:
    resolver = build_resolver()

    for component_id in ("a", "b", "c"):
        register_component(resolver, component_id)

    assert resolver.add_dependency("b", "a")
    assert resolver.add_dependency("c", "b")

    report = resolver.get_cycle_report()

    assert report["has_cycles"] is False
    assert report["cycle_count"] == 0
    assert report["cycles"] == []


def test_phase3_simple_cycle() -> None:
    resolver = build_resolver()

    register_component(resolver, "a")
    register_component(resolver, "b")

    assert resolver.add_dependency("a", "b")
    assert resolver.add_dependency("b", "a")

    report = resolver.get_cycle_report()

    assert report["has_cycles"] is True
    assert report["cycle_count"] == 1
    assert report["cycles"] == [["a", "b", "a"]]

    validation = resolver.validate_cycles()

    assert validation["valid"] is False
    assert validation["errors"][0]["code"] == "DEPENDENCY_CYCLE"


def test_phase3_large_cycle() -> None:
    resolver = build_resolver()

    for component_id in ("a", "b", "c", "d"):
        register_component(resolver, component_id)

    assert resolver.add_dependency("a", "b")
    assert resolver.add_dependency("b", "c")
    assert resolver.add_dependency("c", "d")
    assert resolver.add_dependency("d", "a")

    report = resolver.get_cycle_report()

    assert report["has_cycles"] is True
    assert ["a", "b", "c", "d", "a"] in report["cycles"]


def test_phase3_multiple_cycles() -> None:
    resolver = build_resolver()

    for component_id in ("a", "b", "x", "y", "z"):
        register_component(resolver, component_id)

    assert resolver.add_dependency("a", "b")
    assert resolver.add_dependency("b", "a")

    assert resolver.add_dependency("x", "y")
    assert resolver.add_dependency("y", "z")
    assert resolver.add_dependency("z", "x")

    report = resolver.get_cycle_report()

    assert report["cycle_count"] == 2
    assert ["a", "b", "a"] in report["cycles"]
    assert ["x", "y", "z", "x"] in report["cycles"]
    assert len(report["suggestions"]) == 2


def test_phase3_dependency_policy() -> None:
    resolver = build_resolver()

    register_component(resolver, "a")
    register_component(resolver, "b")

    assert resolver.add_dependency(
        "a",
        "b",
        dependency_type="optional",
    )
    assert resolver.add_dependency(
        "b",
        "a",
        dependency_type="optional",
    )

    assert resolver.has_cycles() is False
    assert resolver.has_cycles(
        ("required", "optional")
    ) is True


def test_phase3_graph_analysis() -> None:
    resolver = build_resolver()

    for component_id in (
        "config",
        "logger",
        "event_bus",
        "isolated",
    ):
        register_component(resolver, component_id)

    assert resolver.add_dependency("logger", "config")
    assert resolver.add_dependency("event_bus", "logger")

    report = resolver.analyze_graph()

    assert report["node_count"] == 4
    assert report["edge_count"] == 2
    assert report["isolated_nodes"] == ["isolated"]
    assert report["independent_graph_count"] == 2
    assert report["longest_chain"] == [
        "event_bus",
        "logger",
        "config",
    ]
    assert report["maximum_depth"] == 2
    assert report["cycle_report"]["has_cycles"] is False


def test_phase3_resolve_rejects_cycle() -> None:
    resolver = build_resolver()

    register_component(resolver, "a")
    register_component(resolver, "b")

    assert resolver.add_dependency("a", "b")
    assert resolver.add_dependency("b", "a")

    report = resolver.resolve(force=True)

    assert report["valid"] is False
    assert report["errors"][0]["code"] == (
        "TOPOLOGICAL_RESOLUTION_FAILED"
    )


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def run_test(
    name: str,
    test_function: Callable[[], None],
) -> bool:
    try:
        test_function()
    except Exception as error:
        print(f"{name}: FAIL")
        print(
            f"  {error.__class__.__name__}: {error}"
        )
        return False

    print(f"{name}: PASS")
    return True


def main() -> int:
    tests: list[tuple[str, Callable[[], None]]] = [
        ("Phase 2 – Linearer Graph", test_phase2_linear_graph),
        (
            "Phase 2 – Prioritäten und Determinismus",
            test_phase2_priority_and_determinism,
        ),
        (
            "Phase 2 – Unabhängige Teilgraphen",
            test_phase2_independent_subgraphs,
        ),
        (
            "Phase 2 – Cache und Graph-Version",
            test_phase2_cache_and_graph_version,
        ),
        (
            "Phase 2 – Dependency-Policies",
            test_phase2_dependency_policies,
        ),
        (
            "Phase 3 – Graph ohne Zyklus",
            test_phase3_acyclic_graph,
        ),
        (
            "Phase 3 – Einfacher Zyklus",
            test_phase3_simple_cycle,
        ),
        (
            "Phase 3 – Großer Zyklus",
            test_phase3_large_cycle,
        ),
        (
            "Phase 3 – Mehrere Zyklen",
            test_phase3_multiple_cycles,
        ),
        (
            "Phase 3 – Dependency-Policy",
            test_phase3_dependency_policy,
        ),
        (
            "Phase 3 – Graphanalyse",
            test_phase3_graph_analysis,
        ),
        (
            "Phase 3 – Resolve lehnt Zyklus ab",
            test_phase3_resolve_rejects_cycle,
        ),
    ]

    print("=== DEPENDENCY RESOLVER PHASE 2 + 3 ===")
    print(f"Projektstamm: {PROJECT_ROOT}")
    print()

    results = [
        run_test(name, test_function)
        for name, test_function in tests
    ]

    passed = sum(results)
    total = len(results)

    print()
    print(f"Bestanden: {passed}/{total}")
    print("RESULT:", "PASS" if all(results) else "FAIL")

    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
