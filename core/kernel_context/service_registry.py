from __future__ import annotations

from copy import deepcopy
from threading import Condition, RLock

class KernelServiceRegistry:
    DEFAULT_SERVICES = ("config", "logger", "event_bus", "registry", "health", "tasks", "modules", "dependencies")
    DEFAULT_ALIASES = {
        "configuration": "config", "configuration_manager": "config", "config_manager": "config",
        "log": "logger", "logging": "logger", "events": "event_bus", "eventbus": "event_bus",
        "registry_manager": "registry", "health_monitor": "health", "task_manager": "tasks",
        "module_manager": "modules", "dependency_resolver": "dependencies",
    }
    def __init__(self, lock: RLock | None = None) -> None:
        self.lock = lock or RLock()
        self.condition = Condition(self.lock)
        self.services = {name: None for name in self.DEFAULT_SERVICES}
        self.metadata: dict[str, dict] = {}
        self.aliases = dict(self.DEFAULT_ALIASES)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "services": {name: service is not None for name, service in self.services.items()},
                "metadata": deepcopy(self.metadata),
                "aliases": deepcopy(self.aliases),
            }
