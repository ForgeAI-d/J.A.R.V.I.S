"""Validation helpers for MemoryManager."""
def validate_component(component):
    errors = []
    for name in ("initialize", "start", "stop", "get_manifest", "get_health", "get_status", "get_statistics", "report", "validate"):
        if not callable(getattr(component, name, None)):
            errors.append(f"missing callable: {name}")
    return {"valid": not errors, "errors": errors}
