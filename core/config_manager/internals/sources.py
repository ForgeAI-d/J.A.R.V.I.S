from __future__ import annotations

import json
import os
from copy import deepcopy
from threading import RLock
from typing import Any, Mapping

class ConfigSourceResolver:
    """Resolves non-persistent overrides without mutating stored configuration.

    Precedence: persisted config < environment < runtime override.
    Environment keys use JARVIS_<NAMESPACE>_<KEY>.
    """
    def __init__(self, env_prefix: str = "JARVIS") -> None:
        self.env_prefix = env_prefix.strip("_").upper()
        self._runtime: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def resolve(self, namespace: str, persisted: Mapping[str, Any]) -> dict[str, Any]:
        result = deepcopy(dict(persisted))
        result.update(self.environment_overrides(namespace, result))
        with self._lock:
            result.update(deepcopy(self._runtime.get(namespace, {})))
        return result

    def environment_overrides(self, namespace: str, template: Mapping[str, Any]) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        prefix = f"{self.env_prefix}_{namespace.upper()}_"
        for key, default in template.items():
            raw = os.environ.get(prefix + key.upper())
            if raw is not None:
                overrides[key] = self._coerce(raw, default)
        return overrides

    def set_runtime(self, namespace: str, key: str, value: Any) -> None:
        with self._lock:
            self._runtime.setdefault(namespace, {})[key] = deepcopy(value)

    def clear_runtime(self, namespace: str | None = None, key: str | None = None) -> None:
        with self._lock:
            if namespace is None:
                self._runtime.clear(); return
            if key is None:
                self._runtime.pop(namespace, None); return
            values = self._runtime.get(namespace)
            if values is not None:
                values.pop(key, None)
                if not values:
                    self._runtime.pop(namespace, None)

    def runtime_snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return deepcopy(self._runtime)

    @staticmethod
    def _coerce(raw: str, default: Any) -> Any:
        if isinstance(default, bool):
            value = raw.strip().lower()
            if value in {"1", "true", "yes", "on"}: return True
            if value in {"0", "false", "no", "off"}: return False
            raise ValueError(f"Invalid boolean environment value: {raw!r}")
        if isinstance(default, int) and not isinstance(default, bool): return int(raw)
        if isinstance(default, float): return float(raw)
        if isinstance(default, (dict, list)): return json.loads(raw)
        return raw
