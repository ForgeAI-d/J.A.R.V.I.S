"""Minimal rollback transaction for component-local mutations."""
from collections.abc import Callable

class ComponentTransaction:
    def __init__(self) -> None:
        self._rollbacks: list[Callable[[], None]] = []
        self._committed = False

    def add_rollback(self, callback: Callable[[], None]) -> None:
        self._rollbacks.append(callback)

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        for callback in reversed(self._rollbacks):
            callback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None or not self._committed:
            self.rollback()
        return False
