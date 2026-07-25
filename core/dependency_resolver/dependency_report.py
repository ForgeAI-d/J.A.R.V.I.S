from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class DependencyReport:
    """Generic report container used by the resolver."""

    report_type: str
    valid: bool
    summary: str
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "valid": self.valid,
            "summary": self.summary,
            "errors": deepcopy(self.errors),
            "warnings": deepcopy(self.warnings),
            "details": deepcopy(self.details),
            "created_at": self.created_at,
        }
