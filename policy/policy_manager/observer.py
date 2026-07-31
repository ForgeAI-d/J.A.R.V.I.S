from __future__ import annotations

from typing import Any, Callable

PolicyObserver = Callable[[dict[str, Any]], Any]
