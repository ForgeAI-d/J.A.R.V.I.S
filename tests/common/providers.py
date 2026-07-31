"""Provider test doubles shared by future AI tests."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FakeProvider:
    """Small deterministic provider double for manager integration tests."""

    provider_id: str = "test.fake_provider"
    available: bool = True
    responses: list[Any] = field(default_factory=list)
    requests: list[Any] = field(default_factory=list)

    def queue_response(self, response: Any) -> None:
        self.responses.append(response)

    def generate(self, request: Any) -> Any:
        self.requests.append(request)
        if not self.available:
            raise RuntimeError("Fake provider is unavailable")
        return self.responses.pop(0) if self.responses else None
