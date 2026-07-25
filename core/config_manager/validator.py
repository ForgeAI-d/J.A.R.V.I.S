"""Component validation adapter."""
from typing import Any

def validate_component(component: Any) -> dict[str, Any]:
    validate = getattr(component, "validate", None)
    if callable(validate):
        result = validate()
        if isinstance(result, dict):
            return result
    missing = [name for name in ("component_id", "initialize", "start", "stop") if not hasattr(component, name)]
    return {"valid": not missing, "errors": missing, "component_id": getattr(component, "component_id", None)}
