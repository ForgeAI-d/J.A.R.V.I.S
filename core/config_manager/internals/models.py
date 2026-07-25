from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, ClassVar, Mapping, TypeVar

T = TypeVar("T", bound="ConfigModel")

@dataclass(frozen=True, slots=True)
class ConfigModel:
    namespace: ClassVar[str] = ""

    @classmethod
    def from_mapping(cls: type[T], data: Mapping[str, Any]) -> T:
        allowed = {field.name for field in fields(cls)}
        return cls(**{key: data[key] for key in allowed if key in data})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True, slots=True)
class BootConfig(ConfigModel):
    namespace: ClassVar[str] = "boot"
    version: int = 1
    boot_mode: str = "development"
    safe_mode: bool = False
    parallel_boot: bool = False
    strict_dependencies: bool = False
    fallback_boot_order: bool = True

@dataclass(frozen=True, slots=True)
class KernelConfig(ConfigModel):
    namespace: ClassVar[str] = "kernel"
    version: int = 1
    kernel_name: str = "Velthor Kernel"
    kernel_version: str = "1.0.0-alpha"
    system_name: str = "J.A.R.V.I.S."
    environment: str = "development"

@dataclass(frozen=True, slots=True)
class LoggerConfig(ConfigModel):
    namespace: ClassVar[str] = "logger"
    version: int = 1
    log_path: str = "logs"
    level: str = "INFO"
    console_logging: bool = True
    file_logging: bool = True
    json_logging: bool = True

@dataclass(frozen=True, slots=True)
class NetworkConfig(ConfigModel):
    namespace: ClassVar[str] = "network"
    version: int = 1
    allow_remote_access: bool = False
    api_enabled: bool = False
    api_host: str = "127.0.0.1"
    api_port: int = 8000

@dataclass(frozen=True, slots=True)
class DatabaseConfig(ConfigModel):
    namespace: ClassVar[str] = "database"
    version: int = 1
    database_path: str = "data/jarvis.db"
    auto_migrate: bool = True
    backup_before_migration: bool = True

MODEL_BY_NAMESPACE: dict[str, type[ConfigModel]] = {
    model.namespace: model for model in (BootConfig, KernelConfig, LoggerConfig, NetworkConfig, DatabaseConfig)
}

def build_typed_config(namespace: str, data: Mapping[str, Any]) -> ConfigModel:
    try:
        model = MODEL_BY_NAMESPACE[namespace]
    except KeyError as exc:
        raise KeyError(f"No typed config model registered for namespace {namespace!r}.") from exc
    return model.from_mapping(data)
