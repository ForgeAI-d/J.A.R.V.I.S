from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.common import BaseKernelComponent
from core.types import ComponentKind


class BaseManager(BaseKernelComponent):
    """KAS-compatible base class for manager components."""

    COMPONENT_ID = "base.manager"
    MANAGER_ID = "base.manager"
    NAME = "Base Manager"
    VERSION = "1.0.0"
    AUTHOR = "Velthor Technologies"
    MISSION = "Basis-Klasse für alle J.A.R.V.I.S. Manager."
    KIND = ComponentKind.MANAGER
    AUTO_START = True
    PRIORITY = 100
    REQUIRES = []
    OPTIONAL = []
    CAPABILITIES = [
        "manager_lifecycle",
        "engine_registration",
        "status_reporting",
        "health_reporting",
    ]

    def __init__(self, context: Any | None = None) -> None:
        self.COMPONENT_ID = self.MANAGER_ID
        super().__init__(context=context)
        self.manager_id = self.MANAGER_ID
        self.component_id = self.manager_id
        self.status = "OFFLINE"
        self.engines: dict[str, Any] = {}

    def initialize(self) -> bool:
        with self.lock:
            if self.lifecycle["initialized"]:
                return True
            now = self._now()
            self._statistics["initialize_calls"] += 1
            self.lifecycle["initialized"] = True
            self.last_initialized = now
            self.initialized_at = now
            self.last_activity = now
            self.status = "OFFLINE"
        self.add_timeline_event("MANAGER_INITIALIZED")
        return True

    def start(self) -> bool:
        if not self.lifecycle["initialized"] and not self.initialize():
            return False
        with self.lock:
            if self.lifecycle["started"]:
                return True
            self._statistics["start_calls"] += 1
            self.status = "ONLINE"
            self.health = 100
            self.start_count += 1
            now = self._now()
            self.last_started = now
            self.started_at = now
            self.last_activity = now
            self.last_error = None
            self.lifecycle["started"] = True
            self.lifecycle["healthy"] = True
        self.add_timeline_event("MANAGER_STARTED")
        for engine in sorted(self.engines.values(), key=lambda item: item.priority):
            if engine.auto_start:
                if self.context is not None and getattr(engine, "context", None) is None:
                    engine.set_context(self.context)
                if not engine.initialize() or not engine.start():
                    self.set_health(50)
                    return False
        return True

    def stop(self) -> bool:
        all_stopped = True
        for engine in reversed(sorted(self.engines.values(), key=lambda item: item.priority)):
            all_stopped = bool(engine.stop()) and all_stopped
        with self.lock:
            self._statistics["stop_calls"] += 1
            self.status = "OFFLINE"
            self.health = 0
            self.stop_count += 1
            now = self._now()
            self.last_stopped = now
            self.stopped_at = now
            self.last_activity = now
            self.lifecycle["started"] = False
            self.lifecycle["healthy"] = False
        self.add_timeline_event("MANAGER_STOPPED")
        return all_stopped

    def restart(self) -> bool:
        if not self.stop() or not self.start():
            return False
        with self.lock:
            self.restart_count += 1
            self.last_activity = self._now()
        self.add_timeline_event("MANAGER_RESTARTED")
        return True

    def register_engine(self, engine: Any) -> bool:
        engine_id = getattr(engine, "engine_id", None)
        if not engine_id:
            return False
        with self.lock:
            if engine_id in self.engines:
                return False
            self.engines[engine_id] = engine
            if hasattr(engine, "mark_registered"):
                engine.mark_registered(True)
            elif hasattr(engine, "lifecycle"):
                engine.lifecycle["registered"] = True
            if self.context is not None and getattr(engine, "context", None) is None:
                engine.set_context(self.context)
            self.last_activity = self._now()
        self.add_timeline_event("ENGINE_REGISTERED", {"engine_id": engine_id, "engine_name": engine.name})
        return True

    def unregister_engine(self, engine_id: str) -> bool:
        with self.lock:
            engine = self.engines.get(engine_id)
            if engine is None:
                return False
            if getattr(engine, "lifecycle", {}).get("started"):
                engine.stop()
            del self.engines[engine_id]
            if hasattr(engine, "mark_registered"):
                engine.mark_registered(False)
            self.last_activity = self._now()
        self.add_timeline_event("ENGINE_UNREGISTERED", {"engine_id": engine_id})
        return True

    def get_engine(self, engine_id: str) -> Any | None:
        with self.lock:
            return self.engines.get(engine_id)

    def list_engines(self) -> list[dict[str, Any]]:
        with self.lock:
            engines = tuple(self.engines.values())
        return [engine.get_status() for engine in engines]

    def set_error(self, error: BaseException | str) -> bool:
        super().set_error(error)
        with self.lock:
            self.status = "ERROR"
            self.lifecycle["healthy"] = False
        return False

    def health_check(self) -> dict[str, Any]:
        with self.lock:
            if self.status == "ERROR":
                score = 0
            elif self.lifecycle["started"]:
                engine_health = [e.health_check().get("health", 0) for e in self.engines.values()]
                score = min(engine_health, default=100)
            else:
                score = 0
        self.set_health(score)
        return self.get_health()

    def add_timeline_event(self, event_type: str, payload: dict[str, Any] | None = None) -> bool:
        event = {
            "event_type": event_type,
            "component_id": self.component_id,
            "manager_id": self.manager_id,
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
        manifest["manager_id"] = self.manager_id
        return manifest

    def get_statistics(self) -> dict[str, Any]:
        statistics = super().get_statistics()
        statistics["engine_count"] = len(self.engines)
        return statistics

    def get_status(self) -> dict[str, Any]:
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "lifecycle": deepcopy(self.lifecycle),
            "statistics": self.get_statistics(),
            "engine_count": len(self.engines),
            "engines": self.list_engines(),
            "last_started": self.last_started,
            "last_stopped": self.last_stopped,
            "last_error": self.last_error,
        }

    def get_health(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "manager_id": self.manager_id,
            "status": self.status,
            "health": self.health,
            "healthy": self.lifecycle["healthy"],
            "engine_count": len(self.engines),
            "last_error": self.last_error,
        }
