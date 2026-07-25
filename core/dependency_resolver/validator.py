from typing import Any


def validate_component(component: Any) -> dict:
    report = component.validate()
    return {"valid": bool(report.get("valid", False)), "details": report}
