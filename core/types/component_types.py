from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ComponentKind(StrEnum):
    KERNEL = "kernel"
    SERVICE = "service"
    MANAGER = "manager"
    ENGINE = "engine"
    PLUGIN = "plugin"


class ComponentState(StrEnum):
    CREATED = "CREATED"
    INITIALIZING = "INITIALIZING"
    INITIALIZED = "INITIALIZED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class HealthStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class BuildStatus(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    COMPLETE = "COMPLETE"


class APIStatus(StrEnum):
    UNSTABLE = "UNSTABLE"
    STABLE = "STABLE"
    FROZEN = "FROZEN"


@dataclass(slots=True, frozen=True)
class ComponentManifest:
    component_id: str
    name: str
    version: str
    author: str
    mission: str
    kind: ComponentKind = ComponentKind.SERVICE
    manager: str | None = None
    requires: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    priority: int = 100
    auto_start: bool = True
    build_status: BuildStatus = BuildStatus.DEVELOPMENT
    api_status: APIStatus = APIStatus.UNSTABLE
    schema_version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.component_id.strip():
            raise ValueError("component_id must not be empty")
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.version.strip():
            raise ValueError("version must not be empty")
        if self.priority < 0:
            raise ValueError("priority must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["build_status"] = self.build_status.value
        data["api_status"] = self.api_status.value
        data["requires"] = list(self.requires)
        data["optional"] = list(self.optional)
        data["capabilities"] = list(self.capabilities)
        return data


@dataclass(slots=True, frozen=True)
class ComponentEvent:
    component_id: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    severity: str = "INFO"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ComponentHealth:
    component_id: str
    state: ComponentState
    status: HealthStatus
    score: int
    healthy: bool
    last_error: str | None = None
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.score = max(0, min(100, int(self.score)))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        data["status"] = self.status.value
        return data
