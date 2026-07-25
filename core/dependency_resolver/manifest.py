"""Static KAS manifest metadata for Dependency Resolver."""
MANIFEST = {
    "component_id": "core.dependency_resolver",
    "name": "Dependency Resolver",
    "version": "0.5.0",
    "kind": "service",
    "priority": 15,
    "auto_start": True,
    "schema_version": "1.0",
    "requires": [],
    "optional": ["core.event_bus", "core.logger"],
}
