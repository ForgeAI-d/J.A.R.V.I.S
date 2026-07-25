from __future__ import annotations
from copy import deepcopy
from threading import RLock

class KernelDataStore:
    """Owns mutable context dictionaries while preserving legacy dict access."""
    def __init__(self, lock: RLock | None = None) -> None:
        self.lock = lock or RLock()
        self.flags: dict = {}
        self.shared: dict = {}
        self.metadata: dict = {}
    def snapshot(self) -> dict:
        with self.lock:
            return {"flags": deepcopy(self.flags), "shared": deepcopy(self.shared), "metadata": deepcopy(self.metadata)}
