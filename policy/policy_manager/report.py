from __future__ import annotations

from typing import Any


def build_policy_report(manager: Any) -> dict[str, Any]:
    return manager.report()
