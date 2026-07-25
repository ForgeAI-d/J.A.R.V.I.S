from typing import Any


def collect_statistics(component: Any) -> dict:
    return component.get_statistics()
