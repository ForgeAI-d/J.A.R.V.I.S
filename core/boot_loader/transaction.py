from dataclasses import dataclass, field
from typing import Any


@dataclass
class BootTransaction:
    initialized: list[str] = field(default_factory=list)
    started: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
