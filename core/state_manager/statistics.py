"""Component statistics adapter."""
from typing import Any

def collect_statistics(component: Any) -> dict[str, Any]:
    getter = getattr(component, "get_statistics", None)
    return getter() if callable(getter) else {}
