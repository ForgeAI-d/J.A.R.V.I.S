from __future__ import annotations

from typing import Any


def get_policy_statistics(manager: Any) -> dict[str, Any]:
    return manager.get_statistics()
