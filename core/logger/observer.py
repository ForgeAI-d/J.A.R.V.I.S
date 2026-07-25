"""Observer protocol used by this KAS component."""
from typing import Any, Protocol

class ComponentObserver(Protocol):
    def __call__(self, event: dict[str, Any]) -> None: ...
