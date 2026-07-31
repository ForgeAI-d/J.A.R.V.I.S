from __future__ import annotations

from typing import Any


def validate_policy_manager(component: Any) -> dict[str, Any]:
    required = ("evaluate", "register_rule", "unregister_rule", "list_rules", "report")
    missing = [name for name in required if not callable(getattr(component, name, None))]
    validation = component.validate() if callable(getattr(component, "validate", None)) else {"valid": False}
    errors = list(validation.get("errors", [])) + [f"Missing callable: {name}" for name in missing]
    return {"valid": not errors, "errors": errors, "component_id": getattr(component, "component_id", None)}
