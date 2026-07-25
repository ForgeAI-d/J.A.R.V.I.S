from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.common import BaseKernelComponent
from core.types import ComponentKind, ComponentState


class BaseEngine(BaseKernelComponent):
    """KAS-compatible base class for all J.A.R.V.I.S. engines.

    The legacy engine API is intentionally preserved for existing subclasses.
    """

    COMPONENT_ID = "base.engine"
    ENGINE_ID = "base.engine"
    NAME = "Base Engine"
    VERSION = "1.0.0"
    AUTHOR = "Velthor Technologies"
    MANAGER = "UNKNOWN"
    MISSION = "Basis-Klasse für alle J.A.R.V.I.S. Engines."
    KIND = ComponentKind.ENGINE
    AUTO_START = True
    PRIORITY = 100
    REQUIRES = []
    OPTIONAL = []
    CAPABILITIES = [
        "engine_lifecycle",
        "status_reporting",
        "health_reporting",
        "kernel_context_support",
        "hook_system",
    ]

    def __init__(self, context: Any | None = None) -> None:
        # Existing engines often override ENGINE_ID only.
        self.COMPONENT_ID = self.ENGINE_ID
        super().__init__(context=context)
        self.engine_id = self.ENGINE_ID
        self.component_id = self.engine_id
        self.manager = self.MANAGER
        self.status = "OFFLINE"

    def initialize(self) -> bool:
        with self.lock:
            if self.lifecycle["initialized"]:
                return True
            self.status = "INITIALIZING"
            self._statistics["initialize_calls"] += 1
            self.last_activity = self._now()
        self.add_timeline_event("ENGINE_INITIALIZING")
        try:
            self.on_initialize()
            with self.lock:
                now = self._now()
                self.lifecycle["initialized"] = True
                self.last_initialized = now
                self.initialized_at = now
                self.last_activity = now
                self.last_error = None
                self.status = "OFFLINE"
                self.health = 0
            self.add_timeline_event("ENGINE_INITIALIZED")
            return True
        except Exception as error:
            return self.set_error(error)

    def start(self) -> bool:
        if not self.lifecycle["initialized"] and not self.initialize():
            return False
        with self.lock:
            if self.lifecycle["started"]:
                return True
            self.status = "STARTING"
            self._statistics["start_calls"] += 1
            self.last_activity = self._now()
        self.add_timeline_event("ENGINE_STARTING")
        try:
            self.on_start()
            with self.lock:
                now = self._now()
                self.status = "ONLINE"
                self.health = 100
                self.start_count += 1
                self.last_started = now
                self.started_at = now
                self.last_activity = now
                self.last_error = None
                self.lifecycle["started"] = True
                self.lifecycle["healthy"] = True
            self.add_timeline_event("ENGINE_STARTED")
            return True
        except Exception as error:
            return self.set_error(error)

    def stop(self) -> bool:
        with self.lock:
            if not self.lifecycle["started"]:
                self.status = "OFFLINE"
                return True
            self.status = "STOPPING"
            self._statistics["stop_calls"] += 1
            self.last_activity = self._now()
        self.add_timeline_event("ENGINE_STOPPING")
        try:
            self.on_stop()
            with self.lock:
                now = self._now()
                self.status = "OFFLINE"
                self.health = 0
                self.stop_count += 1
                self.last_stopped = now
                self.stopped_at = now
                self.last_activity = now
                self.lifecycle["started"] = False
                self.lifecycle["healthy"] = False
            self.add_timeline_event("ENGINE_STOPPED")
            return True
        except Exception as error:
            return self.set_error(error)

    def restart(self) -> bool:
        if not self.stop():
            return False
        try:
            self.on_restart()
        except Exception as error:
            return self.set_error(error)
        if not self.start():
            return False
        with self.lock:
            self.restart_count += 1
            self.last_activity = self._now()
        self.add_timeline_event("ENGINE_RESTARTED")
        return True

    def pause(self) -> bool:
        with self.lock:
            if not self.lifecycle["started"] or self.status != "ONLINE":
                return False
            self.status = "PAUSED"
            self.last_activity = self._now()
        try:
            self.on_pause()
            self.add_timeline_event("ENGINE_PAUSED")
            return True
        except Exception as error:
            return self.set_error(error)

    def resume(self) -> bool:
        with self.lock:
            if self.status != "PAUSED":
                return False
            self.status = "STARTING"
            self.last_activity = self._now()
        try:
            self.on_resume()
            with self.lock:
                self.status = "ONLINE"
                self.last_activity = self._now()
            self.add_timeline_event("ENGINE_RESUMED")
            return True
        except Exception as error:
            return self.set_error(error)

    def shutdown(self) -> bool:
        result = self.stop()
        try:
            self.on_shutdown()
            self.add_timeline_event("ENGINE_SHUTDOWN")
            return result
        except Exception as error:
            return self.set_error(error)

    def health_check(self) -> dict[str, Any]:
        try:
            custom_health = self.on_health_check()
            self.set_health(custom_health if custom_health is not None else (100 if self.lifecycle["started"] else 0))
        except Exception as error:
            self.set_error(error)
        return self.get_health()

    def set_error(self, error: BaseException | str) -> bool:
        super().set_error(error)
        with self.lock:
            self.status = "ERROR"
            self.lifecycle["healthy"] = False
        return False

    def add_timeline_event(self, event_type: str, payload: dict[str, Any] | None = None) -> bool:
        event = {
            "event_type": event_type,
            "component_id": self.component_id,
            "engine_id": self.engine_id,
            "payload": deepcopy(payload or {}),
            "timestamp": self._now(),
        }
        with self.lock:
            self.timeline.append(event)
            self._statistics["events"] += 1
            observers = tuple(self._observers)
        for observer in observers:
            try:
                observer(deepcopy(event))
            except Exception:
                pass
        self.publish(event_type, payload)
        return True

    def get_manifest(self) -> dict[str, Any]:
        manifest = super().get_manifest()
        manifest.update({"engine_id": self.engine_id, "manager": self.manager})
        return manifest

    def get_status(self) -> dict[str, Any]:
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "lifecycle": deepcopy(self.lifecycle),
            "statistics": self.get_statistics(),
            "last_started": self.last_started,
            "last_stopped": self.last_stopped,
            "last_error": self.last_error,
            "context_connected": self.context is not None,
        }

    def get_health(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "engine_id": self.engine_id,
            "status": self.status,
            "health": self.health,
            "healthy": self.lifecycle["healthy"],
            "last_error": self.last_error,
        }

    # Hooks for child engines
    def on_initialize(self) -> bool: return True
    def on_start(self) -> bool: return True
    def on_stop(self) -> bool: return True
    def on_restart(self) -> bool: return True
    def on_pause(self) -> bool: return True
    def on_resume(self) -> bool: return True
    def on_shutdown(self) -> bool: return True
    def on_health_check(self) -> int | None: return None
