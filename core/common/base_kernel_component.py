from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from core.common.base_component import BaseComponent


class BaseKernelComponent(BaseComponent):
    """Shared KAS layer for kernel managers, engines and services.

    It extends :class:`BaseComponent` with the legacy lifecycle surface used by
    the existing J.A.R.V.I.S. codebase while keeping ``component_id`` as the
    canonical identity for the BootLoader.
    """

    def __init__(self, context: Any | None = None) -> None:
        super().__init__(context=context)
        self.lock = self._lock  # backwards-compatible public lock
        self.requires = deepcopy(list(self.REQUIRES))
        self.optional = deepcopy(list(self.OPTIONAL))
        self.capabilities = deepcopy(list(self.CAPABILITIES))
        self.start_count = 0
        self.stop_count = 0
        self.restart_count = 0
        self.error_count = 0
        self.last_initialized: str | None = None
        self.last_started: str | None = None
        self.last_stopped: str | None = None
        self.last_activity: str | None = None
        self.lifecycle = {
            "registered": False,
            "dependencies_resolved": False,
            "initialized": False,
            "started": False,
            "healthy": False,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def mark_registered(self, registered: bool = True) -> bool:
        with self.lock:
            self.lifecycle["registered"] = bool(registered)
            self.last_activity = self._now()
        return True

    def mark_dependencies_resolved(self, resolved: bool = True) -> bool:
        with self.lock:
            self.lifecycle["dependencies_resolved"] = bool(resolved)
            self.last_activity = self._now()
        return True

    def set_context(self, context: Any) -> bool:
        with self.lock:
            self.context = context
            self.last_activity = self._now()
        self.add_timeline_event("COMPONENT_CONTEXT_SET")
        return True

    def set_health(self, health: int | float) -> bool:
        with self.lock:
            self.health = max(0, min(100, int(health)))
            self.lifecycle["healthy"] = self.health > 0 and self.last_error is None
            self.last_activity = self._now()
        return True

    def set_error(self, error: BaseException | str) -> bool:
        with self.lock:
            self.error_count += 1
            self.lifecycle["healthy"] = False
            self.last_activity = self._now()
        return super().set_error(error)

    def restart(self) -> bool:
        if not self.stop():
            return False
        if not self.start():
            return False
        with self.lock:
            self.restart_count += 1
            self.last_activity = self._now()
        self.add_timeline_event("COMPONENT_RESTARTED")
        return True

    def shutdown(self) -> bool:
        return self.stop()

    def publish(self, event_type: str, payload: dict[str, Any] | None = None, severity: str = "INFO") -> bool:
        event_bus = getattr(self.context, "event_bus", None) if self.context is not None else None
        if event_bus is None:
            return False
        publish = getattr(event_bus, "publish", None)
        if not callable(publish):
            return False
        publish(
            event_type=event_type,
            payload={"component_id": self.component_id, **deepcopy(payload or {})},
            source=self.component_id,
            severity=severity,
        )
        return True

    def _log(self, level: str, message: str, payload: dict[str, Any] | None = None) -> bool:
        logger = getattr(self.context, "logger", None) if self.context is not None else None
        if logger is None:
            return False
        method = getattr(logger, level, None)
        if not callable(method):
            return False
        method(message=message, source=self.component_id, payload=deepcopy(payload or {}))
        return True

    def log_info(self, message: str, payload: dict[str, Any] | None = None) -> bool:
        return self._log("info", message, payload)

    def log_warning(self, message: str, payload: dict[str, Any] | None = None) -> bool:
        return self._log("warning", message, payload)

    def log_error(self, message: str, payload: dict[str, Any] | None = None) -> bool:
        return self._log("error", message, payload)

    def set_state(self, namespace: str, key: str, value: Any) -> Any:
        state_manager = getattr(self.context, "state_manager", None) if self.context is not None else None
        if state_manager is None:
            return False
        return state_manager.set(namespace=namespace, key=key, value=value)

    def get_state(self, namespace: str, key: str | None = None, default: Any = None) -> Any:
        state_manager = getattr(self.context, "state_manager", None) if self.context is not None else None
        if state_manager is None:
            return default
        return state_manager.get(namespace=namespace, key=key, default=default)

    def create_task(
        self,
        name: str,
        namespace: str | None = None,
        component: str | None = None,
        priority: int = 50,
        metadata: dict[str, Any] | None = None,
        queued: bool = False,
    ) -> Any:
        task_manager = getattr(self.context, "task_manager", None) if self.context is not None else None
        if task_manager is None:
            return None
        return task_manager.create_task(
            name=name,
            namespace=namespace or self.component_id,
            component=component or self.component_id,
            priority=priority,
            metadata=metadata,
            queued=queued,
        )

    def get_statistics(self) -> dict[str, Any]:
        base = super().get_statistics()
        with self.lock:
            base.update(
                {
                    "start_count": self.start_count,
                    "stop_count": self.stop_count,
                    "restart_count": self.restart_count,
                    "error_count": self.error_count,
                    "last_initialized": self.last_initialized,
                    "last_activity": self.last_activity,
                }
            )
        return base

    def get_status(self) -> dict[str, Any]:
        status = super().get_status()
        status.update(
            {
                "lifecycle": deepcopy(self.lifecycle),
                "last_started": self.last_started,
                "last_stopped": self.last_stopped,
                "context_connected": self.context is not None,
            }
        )
        return status
