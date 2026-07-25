from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LifecycleContract(Protocol):
    def initialize(self) -> bool: ...
    def start(self) -> bool: ...
    def stop(self) -> bool: ...
