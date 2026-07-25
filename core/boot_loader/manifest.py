"""Static KAS manifest metadata for BootLoader."""
MANIFEST = {
    "component_id": "core.boot_loader",
    "name": "BootLoader",
    "version": "1.0.0",
    "kind": "service",
    "priority": 0,
    "auto_start": False,
    "schema_version": "1.0",
    "requires": [],
    "optional": ["core.event_bus", "core.logger"],
}
