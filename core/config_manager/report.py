"""Component report adapter."""
from typing import Any

def build_report(component: Any) -> dict[str, Any]:
    report = getattr(component, "report", None)
    if callable(report):
        value = report()
        if isinstance(value, dict):
            return value
    status = getattr(component, "get_status", None)
    return status() if callable(status) else {"component_id": getattr(component, "component_id", None)}
