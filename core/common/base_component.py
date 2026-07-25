from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Callable

from core.types import (
    APIStatus,
    BuildStatus,
    ComponentEvent,
    ComponentHealth,
    ComponentKind,
    ComponentManifest,
    ComponentState,
    HealthStatus,
)

Observer = Callable[[dict[str, Any]], None]


class BaseComponent:
    """KAS v1 base facade for bootable J.A.R.V.I.S. components.

    Subclasses may keep legacy identifiers such as manager_id or engine_id;
    component_id remains the canonical BootLoader identifier.
    """

    COMPONENT_ID = "core.base_component"
    NAME = "Base Component"
    VERSION = "1.0.0"
    AUTHOR = "Velthor Technologies"
    MISSION = "Common base for J.A.R.V.I.S. kernel components."
    KIND = ComponentKind.SERVICE
    MANAGER: str | None = None
    REQUIRES: tuple[str, ...] | list[str] = ()
    OPTIONAL: tuple[str, ...] | list[str] = ()
    CAPABILITIES: tuple[str, ...] | list[str] = ()
    PRIORITY = 100
    AUTO_START = True
    BUILD_STATUS = BuildStatus.DEVELOPMENT
    API_STATUS = APIStatus.UNSTABLE
    SCHEMA_VERSION = "1.0"

    def __init__(self, context: Any | None = None) -> None:
        self.context = context
        self.component_id = self.COMPONENT_ID
        self.name = self.NAME
        self.version = self.VERSION
        self.author = self.AUTHOR
        self.mission = self.MISSION
        self.priority = self.PRIORITY
        self.auto_start = self.AUTO_START
        self.status = ComponentState.CREATED.value
        self.health = 0
        self.last_error: str | None = None
        self.created_at = datetime.now(UTC).isoformat()
        self.initialized_at: str | None = None
        self.started_at: str | None = None
        self.stopped_at: str | None = None
        self.timeline: list[dict[str, Any]] = []
        self._statistics = {
            "initialize_calls": 0,
            "start_calls": 0,
            "stop_calls": 0,
            "errors": 0,
            "events": 0,
        }
        self._observers: set[Observer] = set()
        self._lock = RLock()

    def initialize(self) -> bool:
        with self._lock:
            if self.status in {ComponentState.INITIALIZED.value, ComponentState.RUNNING.value}:
                return True
            self.status = ComponentState.INITIALIZING.value
            self._statistics["initialize_calls"] += 1
        try:
            self.on_initialize()
            with self._lock:
                self.status = ComponentState.INITIALIZED.value
                self.initialized_at = datetime.now(UTC).isoformat()
                self.health = 100
            self.add_timeline_event("COMPONENT_INITIALIZED")
            return True
        except Exception as exc:  # lifecycle boundary
            return self.set_error(exc)

    def start(self) -> bool:
        if self.status == ComponentState.CREATED.value and not self.initialize():
            return False
        with self._lock:
            if self.status == ComponentState.RUNNING.value:
                return True
            self.status = ComponentState.STARTING.value
            self._statistics["start_calls"] += 1
        try:
            self.on_start()
            with self._lock:
                self.status = ComponentState.RUNNING.value
                self.started_at = datetime.now(UTC).isoformat()
                self.health = 100
            self.add_timeline_event("COMPONENT_STARTED")
            return True
        except Exception as exc:
            return self.set_error(exc)

    def stop(self) -> bool:
        with self._lock:
            if self.status == ComponentState.STOPPED.value:
                return True
            self.status = ComponentState.STOPPING.value
            self._statistics["stop_calls"] += 1
        try:
            self.on_stop()
            with self._lock:
                self.status = ComponentState.STOPPED.value
                self.stopped_at = datetime.now(UTC).isoformat()
                self.health = 0
            self.add_timeline_event("COMPONENT_STOPPED")
            return True
        except Exception as exc:
            return self.set_error(exc)

    def on_initialize(self) -> None:
        pass

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    def set_context(self, context: Any) -> bool:
        self.context = context
        self.add_timeline_event("COMPONENT_CONTEXT_SET")
        return True

    def subscribe(self, observer: Observer) -> bool:
        if not callable(observer):
            return False
        with self._lock:
            self._observers.add(observer)
        return True

    def unsubscribe(self, observer: Observer) -> bool:
        with self._lock:
            if observer not in self._observers:
                return False
            self._observers.remove(observer)
        return True

    def add_timeline_event(self, event_type: str, payload: dict[str, Any] | None = None) -> bool:
        event = ComponentEvent(self.component_id, event_type, deepcopy(payload or {})).to_dict()
        with self._lock:
            self.timeline.append(event)
            self._statistics["events"] += 1
            observers = tuple(self._observers)
        for observer in observers:
            try:
                observer(deepcopy(event))
            except Exception:
                continue
        context_event = getattr(self.context, "add_timeline_event", None)
        if callable(context_event):
            try:
                context_event(event_type, {"source": self.component_id, **deepcopy(payload or {})})
            except Exception:
                pass
        return True

    def set_error(self, error: BaseException | str) -> bool:
        with self._lock:
            self.last_error = str(error)
            self.status = ComponentState.FAILED.value
            self.health = 0
            self._statistics["errors"] += 1
        self.add_timeline_event("COMPONENT_ERROR", {"error": self.last_error})
        return False

    def get_manifest(self) -> dict[str, Any]:
        return ComponentManifest(
            component_id=self.component_id,
            name=self.name,
            version=self.version,
            author=self.author,
            mission=self.mission,
            kind=ComponentKind(self.KIND),
            manager=self.MANAGER,
            requires=tuple(self.REQUIRES),
            optional=tuple(self.OPTIONAL),
            capabilities=tuple(self.CAPABILITIES),
            priority=self.priority,
            auto_start=self.auto_start,
            build_status=BuildStatus(self.BUILD_STATUS),
            api_status=APIStatus(self.API_STATUS),
            schema_version=self.SCHEMA_VERSION,
        ).to_dict()

    def get_statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                **deepcopy(self._statistics),
                "created_at": self.created_at,
                "initialized_at": self.initialized_at,
                "started_at": self.started_at,
                "stopped_at": self.stopped_at,
                "timeline_count": len(self.timeline),
            }

    def get_health(self) -> dict[str, Any]:
        healthy = self.status in {ComponentState.INITIALIZED.value, ComponentState.RUNNING.value}
        status = HealthStatus.HEALTHY if healthy else (
            HealthStatus.UNHEALTHY if self.status == ComponentState.FAILED.value else HealthStatus.UNKNOWN
        )
        return ComponentHealth(
            component_id=self.component_id,
            state=ComponentState(self.status),
            status=status,
            score=self.health,
            healthy=healthy,
            last_error=self.last_error,
        ).to_dict()

    def validate(self) -> dict[str, Any]:
        manifest = self.get_manifest()
        errors = [key for key in ("component_id", "name", "version") if not manifest.get(key)]
        return {"valid": not errors, "errors": errors, "component_id": self.component_id}

    def get_status(self) -> dict[str, Any]:
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.get_health(),
            "statistics": self.get_statistics(),
            "last_error": self.last_error,
        }

    def report(self) -> dict[str, Any]:
        return self.get_status()
