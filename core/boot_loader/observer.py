from typing import Callable, Any

BootObserver = Callable[[dict[str, Any]], None]

__all__ = ["BootObserver"]
