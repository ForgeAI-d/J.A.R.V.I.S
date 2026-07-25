from typing import Any


def build_report(component: Any) -> dict:
    return component.get_report() if hasattr(component, "get_report") else component.report()
