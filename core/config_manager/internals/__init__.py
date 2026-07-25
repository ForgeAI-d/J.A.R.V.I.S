"""Private implementation modules for :mod:`core.config_manager`.

Public consumers should import from ``core.config_manager``.  The modules in
this package are intentionally internal so the Config Manager can evolve
without spreading implementation-specific imports across the kernel.
"""

from .cache import ConfigCache
from .config_transaction import ConfigTransaction
from .config_validator import ConfigValidator
from .defaults import CONFIG_VERSION, DEFAULT_CONFIGS
from .event_dispatcher import ConfigEvents
from .migrator import ConfigMigrator
from .models import (
    BootConfig,
    ConfigModel,
    DatabaseConfig,
    KernelConfig,
    LoggerConfig,
    NetworkConfig,
    build_typed_config,
)
from .sources import ConfigSourceResolver
from .storage import ConfigStorage
from .watcher import ConfigWatcher

__all__ = [
    "BootConfig",
    "CONFIG_VERSION",
    "ConfigCache",
    "ConfigEvents",
    "ConfigMigrator",
    "ConfigModel",
    "ConfigSourceResolver",
    "ConfigStorage",
    "ConfigTransaction",
    "ConfigValidator",
    "ConfigWatcher",
    "DEFAULT_CONFIGS",
    "DatabaseConfig",
    "KernelConfig",
    "LoggerConfig",
    "NetworkConfig",
    "build_typed_config",
]
