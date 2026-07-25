from dependency_resolver.dependency_resolver import DependencyResolver


class DummyContext:
    def __init__(self):
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


def test_phase_1():
    context = DummyContext()
    resolver = DependencyResolver(context)

    assert resolver.initialize()
    assert resolver.start()

    assert resolver.register_component(
        component_id="core.logger",
        name="Logger",
        component_type="service",
    )

    assert resolver.register_component(
        component_id="core.event_bus",
        name="Event Bus",
        component_type="service",
    )

    assert resolver.register_component(
        component_id="core.module_manager",
        name="Module Manager",
        component_type="manager",
    )

    assert resolver.add_dependency(
        "core.module_manager",
        "core.logger",
        "required",
    )

    assert resolver.add_dependency(
        "core.module_manager",
        "core.event_bus",
        "required",
    )

    assert len(
        resolver.get_dependencies("core.module_manager")
    ) == 2

    assert len(
        resolver.get_dependents("core.logger")
    ) == 1

    validation = resolver.validate()
    assert validation["valid"]

    resolution = resolver.resolve()
    assert resolution["valid"]
    assert len(resolution["details"]["boot_order"]) == 3
    assert len(resolution["details"]["shutdown_order"]) == 3

    assert resolver.get_statistics()["node_count"] == 3
    assert resolver.get_statistics()["edge_count"] == 2
    assert context.get_service("dependencies") is resolver

    assert resolver.stop()
    assert resolver.status == "STOPPED"


if __name__ == "__main__":
    test_phase_1()
    print("DEPENDENCY RESOLVER PHASE 1: PASS")
