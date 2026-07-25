from dependency_resolver import DependencyResolver


def build_resolver():
    resolver = DependencyResolver()
    assert resolver.initialize()
    assert resolver.start()
    return resolver


def register(resolver, component_id, priority=100):
    assert resolver.register_component(
        component_id=component_id,
        name=component_id,
        priority=priority,
    )


def test_linear_graph():
    resolver = build_resolver()

    register(resolver, "config")
    register(resolver, "logger")
    register(resolver, "event_bus")
    register(resolver, "modules")

    assert resolver.add_dependency("logger", "config")
    assert resolver.add_dependency("event_bus", "logger")
    assert resolver.add_dependency("modules", "event_bus")

    report = resolver.resolve()

    assert report["valid"]
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


def test_priority_and_determinism():
    resolver = build_resolver()

    register(resolver, "late", priority=50)
    register(resolver, "first", priority=1)
    register(resolver, "middle", priority=20)

    first = resolver.get_boot_order(force=True)
    second = resolver.get_boot_order(force=True)

    assert first == ["first", "middle", "late"]
    assert first == second


def test_independent_subgraphs():
    resolver = build_resolver()

    register(resolver, "a", priority=10)
    register(resolver, "b", priority=20)
    register(resolver, "c", priority=5)
    register(resolver, "d", priority=15)

    assert resolver.add_dependency("b", "a")
    assert resolver.add_dependency("d", "c")

    order = resolver.get_boot_order()

    assert order.index("a") < order.index("b")
    assert order.index("c") < order.index("d")
    assert order == ["c", "a", "d", "b"]


def test_cache_and_versioning():
    resolver = build_resolver()

    register(resolver, "a")
    register(resolver, "b")
    assert resolver.add_dependency("b", "a")

    first = resolver.resolve()
    second = resolver.resolve()

    assert first["details"]["cached"] is False
    assert second["details"]["cached"] is True

    old_version = resolver.graph.version
    register(resolver, "c")
    assert resolver.graph.version == old_version + 1

    third = resolver.resolve()
    assert third["details"]["cached"] is False
    assert "c" in third["details"]["boot_order"]

    stats = resolver.get_statistics()
    assert stats["cache_hits"] >= 1
    assert stats["cache_misses"] >= 2


def test_optional_dependencies_are_excluded_by_default():
    resolver = build_resolver()

    register(resolver, "a", priority=100)
    register(resolver, "b", priority=1)

    assert resolver.add_dependency(
        "b",
        "a",
        dependency_type="optional",
    )

    default_order = resolver.get_boot_order(force=True)
    optional_order = resolver.get_boot_order(
        dependency_types=("required", "optional"),
        force=True,
    )

    assert default_order == ["b", "a"]
    assert optional_order == ["a", "b"]


def test_cycle_is_rejected_by_engine():
    resolver = build_resolver()

    register(resolver, "a")
    register(resolver, "b")

    assert resolver.add_dependency("a", "b")
    assert resolver.add_dependency("b", "a")

    report = resolver.resolve(force=True)

    assert report["valid"] is False
    assert report["errors"][0]["code"] == "TOPOLOGICAL_RESOLUTION_FAILED"


def main():
    test_linear_graph()
    test_priority_and_determinism()
    test_independent_subgraphs()
    test_cache_and_versioning()
    test_optional_dependencies_are_excluded_by_default()
    test_cycle_is_rejected_by_engine()

    print("=== DEPENDENCY RESOLVER PHASE 2 ===")
    print("Topological sort: PASS")
    print("Priority handling: PASS")
    print("Determinism: PASS")
    print("Independent subgraphs: PASS")
    print("Graph versioning: PASS")
    print("Cache: PASS")
    print("Dependency policies: PASS")
    print("Cycle rejection: PASS")
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
