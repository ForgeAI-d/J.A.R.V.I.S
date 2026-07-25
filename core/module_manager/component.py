from core.base_manager import BaseManager
from copy import deepcopy
from datetime import datetime, timedelta, UTC
from threading import RLock
from time import sleep


class ModuleManager(BaseManager):

    COMPONENT_ID = "core.module_manager"
    MANAGER_ID = "core.module_manager"
    NAME = "Module Manager"
    PRIORITY = 80
    AUTO_START = True

    VERSION = "1.0.0"

    MODULE_TYPES = {
        "manager",
        "engine",
        "service",
        "plugin",
        "component"
    }

    DEFAULT_PRIORITIES = {
        "manager": 0,
        "service": 50,
        "component": 75,
        "engine": 100,
        "plugin": 200
    }

    def __init__(
        self,
        registry=None,
        dependency_resolver=None,
        event_bus=None,
        logger=None,
        health_monitor=None,
        config_manager=None
    ):
        BaseManager.__init__(self)
        # -------------------------------------------------
        # Identity
        # -------------------------------------------------

        self.name = "Module Manager"
        self.component_id = "core.module_manager"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Verwaltet den vollständigen Lebenszyklus aller "
            "J.A.R.V.I.S.-Module während der Laufzeit."
        )

        # -------------------------------------------------
        # Kernel Connections
        # -------------------------------------------------

        self.registry = registry
        self.dependency_resolver = dependency_resolver
        self.event_bus = event_bus
        self.logger = logger
        self.health_monitor = health_monitor
        self.config_manager = config_manager

        # -------------------------------------------------
        # Runtime
        # -------------------------------------------------

        self.status = "OFFLINE"
        self.health = 0

        self.modules = {}

        self.module_types = {
            module_type: set()
            for module_type in self.MODULE_TYPES
        }

        self.lock = RLock()
        self.timeline = []

        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        self.modules_registered = 0
        self.modules_unregistered = 0
        self.registration_failures = 0
        self.duplicate_registrations = 0

        self.initialize_count = 0
        self.start_count = 0
        self.stop_count = 0
        self.restart_count = 0
        self.enable_count = 0
        self.disable_count = 0
        self.reload_count = 0

        self.operation_failures = 0

        self.crash_count = 0
        self.recovery_attempts = 0
        self.recovery_successes = 0
        self.recovery_failures = 0
        self.modules_auto_disabled = 0

        self.boot_plans_generated = 0
        self.group_start_count = 0
        self.group_stop_count = 0
        self.group_restart_count = 0
        self.delayed_start_count = 0
        self.delayed_start_seconds = 0.0

        self.maintenance_mode_count = 0
        self.runtime_updates = 0
        self.tag_start_count = 0
        self.tag_stop_count = 0
        self.tag_restart_count = 0

        # -------------------------------------------------
        # Runtime Information
        # -------------------------------------------------

        self.created_at = datetime.now(UTC).isoformat()

        self.last_registered_at = None
        self.last_unregistered_at = None
        self.last_operation_at = None
        self.last_started = None
        self.last_stopped = None
        self.last_error = None

        # -------------------------------------------------
        # Lifecycle
        # -------------------------------------------------

        self.lifecycle = {
            "registered": False,
            "dependencies_resolved": True,
            "initialized": False,
            "started": False,
            "healthy": False
        }

        # -------------------------------------------------
        # Capabilities
        # -------------------------------------------------

        self.capabilities = [
            "module_registration",
            "module_unregistration",
            "module_lookup",
            "module_listing",
            "module_type_index",
            "module_initialization",
            "module_start",
            "module_stop",
            "module_enable",
            "module_disable",
            "module_restart",
            "module_reload",
            "bulk_module_initialization",
            "bulk_module_start",
            "bulk_module_stop",
            "bulk_module_restart",
            "bulk_module_reload",
            "module_lifecycle_management",
            "dependency_order",
            "reverse_shutdown_order",
            "reload_fallback",
            "module_dependency_validation",
            "missing_dependency_detection",
            "running_dependency_validation",
            "error_isolation",
            "continue_on_error",
            "module_crash_tracking",
            "module_auto_recovery",
            "module_restart_limits",
            "module_recovery_cooldown",
            "module_auto_disable",
            "module_recovery_reporting",
            "module_priorities",
            "startup_groups",
            "delayed_start",
            "boot_plan_generation",
            "group_start",
            "group_stop",
            "group_restart",
            "module_maintenance_mode",
            "module_runtime_configuration",
            "module_tags",
            "tag_start",
            "tag_stop",
            "tag_restart",
            "final_integration_test_ready",
            "dependency_resolver_compatible",
            "registry_compatible",
            "health_monitor_compatible",
            "config_manager_compatible",
            "event_bus_compatible",
            "logger_compatible",
            "thread_safe_access"
        ]

    # =====================================================
    # Lifecycle
    # =====================================================

    def initialize(self):
        with self.lock:
            self.lifecycle["initialized"] = True
            self.last_error = None

        self.add_timeline_event(
            "MODULE_MANAGER_INITIALIZED"
        )

        self._emit_event(
            event_type="MODULE_MANAGER_INITIALIZED",
            payload={}
        )

        return True

    def start(self):
        if not self.lifecycle["initialized"]:
            self.initialize()

        with self.lock:
            self.status = "ONLINE"
            self.health = 100
            self.last_started = datetime.now(UTC).isoformat()
            self.last_error = None

            self.lifecycle["started"] = True
            self.lifecycle["healthy"] = True

        self.add_timeline_event(
            "MODULE_MANAGER_STARTED"
        )

        self._emit_event(
            event_type="MODULE_MANAGER_STARTED",
            payload={
                "registered_modules": len(self.modules)
            }
        )

        return True

    def stop(self):
        with self.lock:
            self.status = "OFFLINE"
            self.health = 0
            self.last_stopped = datetime.now(UTC).isoformat()

            self.lifecycle["started"] = False
            self.lifecycle["healthy"] = False

        self.add_timeline_event(
            "MODULE_MANAGER_STOPPED"
        )

        self._emit_event(
            event_type="MODULE_MANAGER_STOPPED",
            payload={}
        )

        return True

    # =====================================================
    # Registration
    # =====================================================

    def register_module(
        self,
        module,
        module_type=None,
        enabled=True,
        replace=False
    ):
        module_id = self._get_module_id(module)

        if module_id is None:
            return self._registration_error(
                "Module has no component_id, manager_id or engine_id."
            )

        normalized_type = self._normalize_module_type(
            module=module,
            module_type=module_type
        )

        if normalized_type not in self.MODULE_TYPES:
            return self._registration_error(
                f"Unsupported module type: {normalized_type}"
            )

        with self.lock:
            if module_id in self.modules and not replace:
                self.duplicate_registrations += 1
                self.last_error = (
                    f"Module '{module_id}' is already registered."
                )

                return False

            if module_id in self.modules and replace:
                old_type = self.modules[module_id]["type"]

                if old_type in self.module_types:
                    self.module_types[old_type].discard(
                        module_id
                    )

            self.modules[module_id] = {
                "instance": module,
                "type": normalized_type,
                "enabled": bool(enabled),
                "registered_at": datetime.now(UTC).isoformat(),
                "last_initialized_at": None,
                "last_started_at": None,
                "last_stopped_at": None,
                "last_restarted_at": None,
                "last_reloaded_at": None,
                "last_error": None,
                "operation_count": 0,
                "crash_count": 0,
                "recovery_attempts": 0,
                "recovery_successes": 0,
                "recovery_failures": 0,
                "last_crash_at": None,
                "last_recovery_at": None,
                "restart_history": [],
                "auto_restart": bool(
                    getattr(module, "auto_restart", True)
                ),
                "max_restart_attempts": int(
                    getattr(module, "max_restart_attempts", 3)
                ),
                "restart_delay": float(
                    getattr(module, "restart_delay", 1.0)
                ),
                "cooldown_seconds": float(
                    getattr(module, "cooldown_seconds", 30.0)
                ),
                "cooldown_until": None,
                "priority": int(
                    getattr(
                        module,
                        "priority",
                        self.DEFAULT_PRIORITIES[normalized_type]
                    )
                ),
                "startup_group": str(
                    getattr(module, "startup_group", "default")
                ).strip() or "default",
                "startup_delay": max(
                    0.0,
                    float(getattr(module, "startup_delay", 0.0))
                ),
                "lazy_load": bool(
                    getattr(module, "lazy_load", False)
                ),
                "maintenance_mode": bool(
                    getattr(module, "maintenance_mode", False)
                ),
                "tags": sorted({
                    str(tag).strip().lower()
                    for tag in getattr(module, "tags", [])
                    if str(tag).strip()
                })
            }

            self.module_types[
                normalized_type
            ].add(module_id)

            self.modules_registered += 1
            self.last_registered_at = datetime.now(UTC).isoformat()
            self.last_error = None

        self._register_with_connected_systems(
            module=module,
            module_type=normalized_type
        )

        self.add_timeline_event(
            event_type="MODULE_REGISTERED",
            payload={
                "module_id": module_id,
                "module_type": normalized_type,
                "enabled": bool(enabled),
                "replace": bool(replace)
            }
        )

        self._emit_event(
            event_type="MODULE_REGISTERED",
            payload={
                "module_id": module_id,
                "module_type": normalized_type,
                "enabled": bool(enabled)
            }
        )

        return True

    def unregister_module(
        self,
        module_id,
        stop_module=True
    ):
        with self.lock:
            module_data = self.modules.get(
                module_id
            )

        if module_data is None:
            return False

        module = module_data["instance"]
        module_type = module_data["type"]

        if stop_module:
            module_status = getattr(
                module,
                "status",
                None
            )

            if (
                module_status not in [None, "OFFLINE"]
                and hasattr(module, "stop")
            ):
                try:
                    module.stop()

                except Exception as error:
                    self._record_module_error(
                        module_id=module_id,
                        error=error
                    )

        self._unregister_from_connected_systems(
            module_id=module_id,
            module_type=module_type
        )

        with self.lock:
            self.modules.pop(
                module_id,
                None
            )

            self.module_types[
                module_type
            ].discard(module_id)

            self.modules_unregistered += 1
            self.last_unregistered_at = datetime.now(UTC).isoformat()

        self.add_timeline_event(
            event_type="MODULE_UNREGISTERED",
            payload={
                "module_id": module_id,
                "module_type": module_type
            }
        )

        self._emit_event(
            event_type="MODULE_UNREGISTERED",
            payload={
                "module_id": module_id,
                "module_type": module_type
            }
        )

        return True

    def register_manager(
        self,
        manager,
        enabled=True,
        replace=False
    ):
        return self.register_module(
            module=manager,
            module_type="manager",
            enabled=enabled,
            replace=replace
        )

    def register_engine(
        self,
        engine,
        enabled=True,
        replace=False
    ):
        return self.register_module(
            module=engine,
            module_type="engine",
            enabled=enabled,
            replace=replace
        )

    def register_service(
        self,
        service,
        enabled=True,
        replace=False
    ):
        return self.register_module(
            module=service,
            module_type="service",
            enabled=enabled,
            replace=replace
        )

    def register_plugin(
        self,
        plugin,
        enabled=True,
        replace=False
    ):
        return self.register_module(
            module=plugin,
            module_type="plugin",
            enabled=enabled,
            replace=replace
        )

    # =====================================================
    # Lookup
    # =====================================================

    def get_module(
        self,
        module_id
    ):
        with self.lock:
            module_data = self.modules.get(
                module_id
            )

            if module_data is None:
                return None

            return module_data["instance"]

    def get_module_record(
        self,
        module_id
    ):
        with self.lock:
            module_data = self.modules.get(
                module_id
            )

            if module_data is None:
                return None

            return self._serialize_module_record(
                module_id=module_id,
                module_data=module_data
            )

    def has_module(
        self,
        module_id
    ):
        with self.lock:
            return module_id in self.modules

    def list_modules(
        self,
        module_type=None,
        enabled_only=False
    ):
        with self.lock:
            records = []

            for module_id, module_data in self.modules.items():
                if (
                    module_type is not None
                    and module_data["type"] != module_type
                ):
                    continue

                if (
                    enabled_only
                    and not module_data["enabled"]
                ):
                    continue

                records.append(
                    self._serialize_module_record(
                        module_id=module_id,
                        module_data=module_data
                    )
                )

            return sorted(
                records,
                key=lambda item: item["module_id"]
            )

    def list_module_ids(
        self,
        module_type=None,
        enabled_only=False
    ):
        return [
            record["module_id"]
            for record in self.list_modules(
                module_type=module_type,
                enabled_only=enabled_only
            )
        ]

    # =====================================================
    # Enable / Disable Preparation
    # =====================================================

    def is_enabled(
        self,
        module_id
    ):
        with self.lock:
            module_data = self.modules.get(
                module_id
            )

            if module_data is None:
                return False

            return module_data["enabled"]

    def set_enabled_state(
        self,
        module_id,
        enabled
    ):
        with self.lock:
            module_data = self.modules.get(
                module_id
            )

            if module_data is None:
                return False

            module_data["enabled"] = bool(enabled)
            module_data["operation_count"] += 1
            self.last_operation_at = datetime.now(UTC).isoformat()

        self.add_timeline_event(
            event_type="MODULE_ENABLED_STATE_CHANGED",
            payload={
                "module_id": module_id,
                "enabled": bool(enabled)
            }
        )

        self._emit_event(
            event_type="MODULE_ENABLED_STATE_CHANGED",
            payload={
                "module_id": module_id,
                "enabled": bool(enabled)
            }
        )

        return True

    # =====================================================
    # Module Lifecycle Operations
    # =====================================================

    def initialize_module(
        self,
        module_id
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return False

        if not module_data["enabled"]:
            return False

        dependency_report = (
            self.validate_module_dependencies(
                module_id=module_id,
                require_running=False
            )
        )

        if not dependency_report["valid"]:
            return self._record_module_error(
                module_id=module_id,
                error={
                    "message": (
                        "Required dependencies are missing."
                    ),
                    "dependency_report": dependency_report
                }
            )

        module = module_data["instance"]

        if not hasattr(
            module,
            "initialize"
        ):
            return self._record_module_error(
                module_id=module_id,
                error="Module has no initialize method."
            )

        try:
            result = module.initialize()

            if result is False:
                raise RuntimeError(
                    "Module initialization returned False."
                )

            timestamp = datetime.now(
                UTC
            ).isoformat()

            with self.lock:
                module_data[
                    "last_initialized_at"
                ] = timestamp

                module_data[
                    "operation_count"
                ] += 1

                module_data[
                    "last_error"
                ] = None

                self.initialize_count += 1
                self.last_operation_at = timestamp

            self.add_timeline_event(
                event_type="MODULE_INITIALIZED",
                payload={
                    "module_id": module_id
                }
            )

            self._emit_event(
                event_type="MODULE_INITIALIZED",
                payload={
                    "module_id": module_id
                }
            )

            return True

        except Exception as error:
            return self._record_module_error(
                module_id=module_id,
                error=error
            )

    def start_module(
        self,
        module_id
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return False

        if not module_data["enabled"]:
            return False

        if module_data.get("maintenance_mode", False):
            return self._record_module_error(
                module_id=module_id,
                error="Module is in maintenance mode."
            )

        dependency_report = (
            self.validate_module_dependencies(
                module_id=module_id,
                require_running=True
            )
        )

        if not dependency_report["valid"]:
            return self._record_module_error(
                module_id=module_id,
                error={
                    "message": (
                        "Required dependencies are not ready."
                    ),
                    "dependency_report": dependency_report
                }
            )

        module = module_data["instance"]

        if not hasattr(
            module,
            "start"
        ):
            return self._record_module_error(
                module_id=module_id,
                error="Module has no start method."
            )

        try:
            auto_start = getattr(
                module,
                "auto_start",
                True
            )

            if not auto_start:
                return False

            startup_delay = float(
                module_data.get("startup_delay", 0.0)
            )

            if startup_delay > 0:
                self.add_timeline_event(
                    event_type="MODULE_START_DELAYED",
                    payload={
                        "module_id": module_id,
                        "delay_seconds": startup_delay
                    }
                )

                with self.lock:
                    self.delayed_start_count += 1
                    self.delayed_start_seconds += startup_delay

                sleep(startup_delay)

            result = module.start()

            if result is False:
                raise RuntimeError(
                    "Module start returned False."
                )

            timestamp = datetime.now(
                UTC
            ).isoformat()

            with self.lock:
                module_data[
                    "last_started_at"
                ] = timestamp

                module_data[
                    "operation_count"
                ] += 1

                module_data[
                    "last_error"
                ] = None

                self.start_count += 1
                self.last_operation_at = timestamp

            self.add_timeline_event(
                event_type="MODULE_STARTED",
                payload={
                    "module_id": module_id
                }
            )

            self._emit_event(
                event_type="MODULE_STARTED",
                payload={
                    "module_id": module_id
                }
            )

            return True

        except Exception as error:
            return self._record_module_error(
                module_id=module_id,
                error=error
            )

    def stop_module(
        self,
        module_id
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return False

        module = module_data["instance"]

        if not hasattr(
            module,
            "stop"
        ):
            return self._record_module_error(
                module_id=module_id,
                error="Module has no stop method."
            )

        try:
            result = module.stop()

            if result is False:
                raise RuntimeError(
                    "Module stop returned False."
                )

            timestamp = datetime.now(
                UTC
            ).isoformat()

            with self.lock:
                module_data[
                    "last_stopped_at"
                ] = timestamp

                module_data[
                    "operation_count"
                ] += 1

                module_data[
                    "last_error"
                ] = None

                self.stop_count += 1
                self.last_operation_at = timestamp

            self.add_timeline_event(
                event_type="MODULE_STOPPED",
                payload={
                    "module_id": module_id
                }
            )

            self._emit_event(
                event_type="MODULE_STOPPED",
                payload={
                    "module_id": module_id
                }
            )

            return True

        except Exception as error:
            return self._record_module_error(
                module_id=module_id,
                error=error
            )

    # =====================================================
    # Bulk Lifecycle Operations
    # =====================================================

    def initialize_all(
        self,
        module_type=None,
        dependency_order=True
    ):
        module_ids = self._get_operation_order(
            reverse=False,
            module_type=module_type,
            dependency_order=dependency_order
        )

        results = {}

        for module_id in module_ids:
            results[module_id] = (
                self.initialize_module(
                    module_id
                )
            )

        self.add_timeline_event(
            event_type="ALL_MODULES_INITIALIZED",
            payload={
                "module_type": module_type,
                "module_count": len(module_ids),
                "successful": sum(
                    1
                    for result in results.values()
                    if result
                )
            }
        )

        return results

    def start_all(
        self,
        module_type=None,
        dependency_order=True,
        continue_on_error=True
    ):
        module_ids = self._get_operation_order(
            reverse=False,
            module_type=module_type,
            dependency_order=dependency_order
        )

        results = {}

        for module_id in module_ids:
            result = self.start_module(
                module_id
            )

            results[module_id] = result

            if (
                not result
                and not continue_on_error
            ):
                break

        successful = sum(
            1
            for result in results.values()
            if result
        )

        failed = (
            len(results) - successful
        )

        self.add_timeline_event(
            event_type="ALL_MODULES_STARTED",
            payload={
                "module_type": module_type,
                "module_count": len(results),
                "successful": successful,
                "failed": failed,
                "continue_on_error": bool(
                    continue_on_error
                )
            }
        )

        self._emit_event(
            event_type="ALL_MODULES_STARTED",
            payload={
                "module_type": module_type,
                "module_count": len(results),
                "successful": successful,
                "failed": failed
            },
            severity=(
                "WARNING"
                if failed > 0
                else "INFO"
            )
        )

        return results

    def stop_all(
        self,
        module_type=None,
        dependency_order=True
    ):
        module_ids = self._get_operation_order(
            reverse=True,
            module_type=module_type,
            dependency_order=dependency_order
        )

        results = {}

        for module_id in module_ids:
            results[module_id] = (
                self.stop_module(
                    module_id
                )
            )

        self.add_timeline_event(
            event_type="ALL_MODULES_STOPPED",
            payload={
                "module_type": module_type,
                "module_count": len(module_ids),
                "successful": sum(
                    1
                    for result in results.values()
                    if result
                )
            }
        )

        return results

    # =====================================================
    # Enable / Disable Operations
    # =====================================================

    def enable_module(
        self,
        module_id,
        initialize=True,
        start=True
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return False

        if module_data["enabled"]:
            return True

        with self.lock:
            module_data["enabled"] = True
            module_data["operation_count"] += 1

            self.enable_count += 1
            self.last_operation_at = datetime.now(
                UTC
            ).isoformat()

        self.add_timeline_event(
            event_type="MODULE_ENABLED",
            payload={
                "module_id": module_id
            }
        )

        self._emit_event(
            event_type="MODULE_ENABLED",
            payload={
                "module_id": module_id
            }
        )

        if initialize:
            if not self.initialize_module(
                module_id
            ):
                return False

        if start:
            module = module_data["instance"]

            if getattr(
                module,
                "auto_start",
                True
            ):
                if not self.start_module(
                    module_id
                ):
                    return False

        return True

    def disable_module(
        self,
        module_id,
        stop=True
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return False

        if not module_data["enabled"]:
            return True

        module = module_data["instance"]

        if (
            stop
            and self._module_is_running(module)
        ):
            if not self.stop_module(
                module_id
            ):
                return False

        with self.lock:
            module_data["enabled"] = False
            module_data["operation_count"] += 1

            self.disable_count += 1
            self.last_operation_at = datetime.now(
                UTC
            ).isoformat()

        self.add_timeline_event(
            event_type="MODULE_DISABLED",
            payload={
                "module_id": module_id
            }
        )

        self._emit_event(
            event_type="MODULE_DISABLED",
            payload={
                "module_id": module_id
            }
        )

        return True

    # =====================================================
    # Restart Operations
    # =====================================================

    def restart_module(
        self,
        module_id,
        reinitialize=False
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return False

        if not module_data["enabled"]:
            return False

        module = module_data["instance"]

        try:
            if self._module_is_running(module):
                if not self.stop_module(
                    module_id
                ):
                    return False

            if reinitialize:
                if not self.initialize_module(
                    module_id
                ):
                    return False

            if not self.start_module(
                module_id
            ):
                return False

            timestamp = datetime.now(
                UTC
            ).isoformat()

            with self.lock:
                module_data[
                    "last_restarted_at"
                ] = timestamp

                module_data[
                    "operation_count"
                ] += 1

                self.restart_count += 1
                self.last_operation_at = timestamp

            self.add_timeline_event(
                event_type="MODULE_RESTARTED",
                payload={
                    "module_id": module_id,
                    "reinitialized": bool(
                        reinitialize
                    )
                }
            )

            self._emit_event(
                event_type="MODULE_RESTARTED",
                payload={
                    "module_id": module_id,
                    "reinitialized": bool(
                        reinitialize
                    )
                }
            )

            return True

        except Exception as error:
            return self._record_module_error(
                module_id=module_id,
                error=error
            )

    def restart_all(
        self,
        module_type=None,
        dependency_order=True,
        reinitialize=False
    ):
        module_ids = self._get_operation_order(
            reverse=False,
            module_type=module_type,
            dependency_order=dependency_order
        )

        results = {}

        for module_id in module_ids:
            results[module_id] = (
                self.restart_module(
                    module_id=module_id,
                    reinitialize=reinitialize
                )
            )

        self.add_timeline_event(
            event_type="ALL_MODULES_RESTARTED",
            payload={
                "module_type": module_type,
                "module_count": len(module_ids),
                "successful": sum(
                    1
                    for result in results.values()
                    if result
                ),
                "reinitialized": bool(
                    reinitialize
                )
            }
        )

        return results

    # =====================================================
    # Reload Operations
    # =====================================================

    def reload_module(
        self,
        module_id
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return False

        if not module_data["enabled"]:
            return False

        module = module_data["instance"]

        try:
            reload_method = getattr(
                module,
                "reload",
                None
            )

            if reload_method is not None:
                result = reload_method()

                if result is False:
                    raise RuntimeError(
                        "Module reload returned False."
                    )

            else:
                if not self.restart_module(
                    module_id=module_id,
                    reinitialize=True
                ):
                    return False

            timestamp = datetime.now(
                UTC
            ).isoformat()

            with self.lock:
                module_data[
                    "last_reloaded_at"
                ] = timestamp

                module_data[
                    "operation_count"
                ] += 1

                self.reload_count += 1
                self.last_operation_at = timestamp

            self.add_timeline_event(
                event_type="MODULE_RELOADED",
                payload={
                    "module_id": module_id,
                    "native_reload": (
                        reload_method is not None
                    )
                }
            )

            self._emit_event(
                event_type="MODULE_RELOADED",
                payload={
                    "module_id": module_id,
                    "native_reload": (
                        reload_method is not None
                    )
                }
            )

            return True

        except Exception as error:
            return self._record_module_error(
                module_id=module_id,
                error=error
            )

    def reload_all(
        self,
        module_type=None,
        dependency_order=True
    ):
        module_ids = self._get_operation_order(
            reverse=False,
            module_type=module_type,
            dependency_order=dependency_order
        )

        results = {}

        for module_id in module_ids:
            results[module_id] = (
                self.reload_module(
                    module_id
                )
            )

        self.add_timeline_event(
            event_type="ALL_MODULES_RELOADED",
            payload={
                "module_type": module_type,
                "module_count": len(module_ids),
                "successful": sum(
                    1
                    for result in results.values()
                    if result
                )
            }
        )

        return results

    # =====================================================
    # Dependency Validation
    # =====================================================

    def validate_module_dependencies(
        self,
        module_id,
        require_running=False
    ):
        module_data = self._get_module_data(
            module_id
        )

        if module_data is None:
            return {
                "valid": False,
                "module_id": module_id,
                "required": [],
                "optional": [],
                "missing_required": [],
                "missing_optional": [],
                "not_running_required": [],
                "error": "Module is not registered."
            }

        module = module_data["instance"]

        required_dependencies = list(
            getattr(
                module,
                "requires",
                []
            )
        )

        optional_dependencies = list(
            getattr(
                module,
                "optional",
                []
            )
        )

        missing_required = []
        missing_optional = []
        not_running_required = []

        for dependency_id in required_dependencies:
            dependency = self.get_module(
                dependency_id
            )

            if dependency is None:
                missing_required.append(
                    dependency_id
                )
                continue

            if (
                require_running
                and not self._module_is_running(
                    dependency
                )
            ):
                not_running_required.append(
                    dependency_id
                )

        for dependency_id in optional_dependencies:
            if not self.has_module(
                dependency_id
            ):
                missing_optional.append(
                    dependency_id
                )

        valid = (
            not missing_required
            and not not_running_required
        )

        report = {
            "valid": valid,
            "module_id": module_id,
            "required": required_dependencies,
            "optional": optional_dependencies,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "not_running_required": not_running_required,
            "error": None
        }

        if not valid:
            report["error"] = (
                f"Dependency validation failed for "
                f"'{module_id}'."
            )

        return report

    def validate_all_dependencies(
        self,
        module_type=None,
        require_running=False
    ):
        reports = {}

        for module_id in self.list_module_ids(
            module_type=module_type,
            enabled_only=True
        ):
            reports[module_id] = (
                self.validate_module_dependencies(
                    module_id=module_id,
                    require_running=require_running
                )
            )

        valid_count = sum(
            1
            for report in reports.values()
            if report["valid"]
        )

        self.add_timeline_event(
            event_type="MODULE_DEPENDENCIES_VALIDATED",
            payload={
                "module_type": module_type,
                "module_count": len(reports),
                "valid_count": valid_count,
                "invalid_count": (
                    len(reports) - valid_count
                ),
                "require_running": bool(
                    require_running
                )
            }
        )

        return reports


    # =====================================================
    # Recovery and Crash Management
    # =====================================================

    def configure_recovery(
        self,
        module_id,
        auto_restart=None,
        max_restart_attempts=None,
        restart_delay=None,
        cooldown_seconds=None
    ):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        try:
            with self.lock:
                if auto_restart is not None:
                    module_data["auto_restart"] = bool(auto_restart)

                if max_restart_attempts is not None:
                    max_restart_attempts = int(max_restart_attempts)

                    if max_restart_attempts < 0:
                        raise ValueError(
                            "max_restart_attempts must be >= 0."
                        )

                    module_data[
                        "max_restart_attempts"
                    ] = max_restart_attempts

                if restart_delay is not None:
                    restart_delay = float(restart_delay)

                    if restart_delay < 0:
                        raise ValueError(
                            "restart_delay must be >= 0."
                        )

                    module_data[
                        "restart_delay"
                    ] = restart_delay

                if cooldown_seconds is not None:
                    cooldown_seconds = float(cooldown_seconds)

                    if cooldown_seconds < 0:
                        raise ValueError(
                            "cooldown_seconds must be >= 0."
                        )

                    module_data[
                        "cooldown_seconds"
                    ] = cooldown_seconds

                module_data["operation_count"] += 1
                self.last_operation_at = datetime.now(
                    UTC
                ).isoformat()

            self.add_timeline_event(
                event_type="MODULE_RECOVERY_CONFIGURED",
                payload={
                    "module_id": module_id,
                    "auto_restart": module_data[
                        "auto_restart"
                    ],
                    "max_restart_attempts": module_data[
                        "max_restart_attempts"
                    ],
                    "restart_delay": module_data[
                        "restart_delay"
                    ],
                    "cooldown_seconds": module_data[
                        "cooldown_seconds"
                    ]
                }
            )

            return True

        except Exception as error:
            return self._record_module_error(
                module_id=module_id,
                error=error
            )

    def mark_module_crashed(
        self,
        module_id,
        error=None,
        auto_recover=True
    ):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        module = module_data["instance"]
        timestamp = datetime.now(UTC).isoformat()
        error_data = (
            deepcopy(error)
            if error is not None
            else "Module crash detected."
        )

        with self.lock:
            module_data["crash_count"] += 1
            module_data["last_crash_at"] = timestamp
            module_data["last_error"] = error_data
            module_data["operation_count"] += 1

            self.crash_count += 1
            self.last_error = str(error_data)
            self.last_operation_at = timestamp

        try:
            setattr(module, "status", "CRASHED")
            setattr(module, "health", 0)
        except Exception:
            pass

        self.add_timeline_event(
            event_type="MODULE_CRASHED",
            payload={
                "module_id": module_id,
                "error": deepcopy(error_data),
                "crash_count": module_data[
                    "crash_count"
                ]
            }
        )

        self._emit_event(
            event_type="MODULE_CRASHED",
            payload={
                "module_id": module_id,
                "error": deepcopy(error_data),
                "crash_count": module_data[
                    "crash_count"
                ]
            },
            severity="ERROR"
        )

        if auto_recover and module_data["auto_restart"]:
            return self.recover_module(module_id)

        return True

    def can_restart(self, module_id):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return {
                "allowed": False,
                "module_id": module_id,
                "reason": "Module is not registered."
            }

        if not module_data["enabled"]:
            return {
                "allowed": False,
                "module_id": module_id,
                "reason": "Module is disabled."
            }

        if not module_data["auto_restart"]:
            return {
                "allowed": False,
                "module_id": module_id,
                "reason": "Automatic restart is disabled."
            }

        cooldown_until = module_data.get(
            "cooldown_until"
        )

        if cooldown_until is not None:
            cooldown_time = datetime.fromisoformat(
                cooldown_until
            )

            if datetime.now(UTC) < cooldown_time:
                return {
                    "allowed": False,
                    "module_id": module_id,
                    "reason": "Module is in recovery cooldown.",
                    "cooldown_until": cooldown_until
                }

            with self.lock:
                module_data["cooldown_until"] = None
                module_data["recovery_attempts"] = 0

        attempts = module_data["recovery_attempts"]
        maximum = module_data["max_restart_attempts"]

        if attempts >= maximum:
            return {
                "allowed": False,
                "module_id": module_id,
                "reason": "Maximum restart attempts reached.",
                "attempts": attempts,
                "maximum": maximum
            }

        return {
            "allowed": True,
            "module_id": module_id,
            "reason": None,
            "attempts": attempts,
            "maximum": maximum
        }

    def recover_module(
        self,
        module_id,
        reinitialize=True,
        disable_on_failure=True
    ):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        permission = self.can_restart(module_id)

        if not permission["allowed"]:
            if (
                disable_on_failure
                and permission.get("reason")
                == "Maximum restart attempts reached."
            ):
                self._enter_recovery_cooldown(
                    module_id=module_id,
                    disable_module=True
                )

            return False

        timestamp = datetime.now(UTC).isoformat()

        with self.lock:
            module_data["recovery_attempts"] += 1
            module_data["last_recovery_at"] = timestamp
            module_data["operation_count"] += 1

            self.recovery_attempts += 1
            self.last_operation_at = timestamp

        delay = module_data["restart_delay"]

        if delay > 0:
            sleep(delay)

        success = self.restart_module(
            module_id=module_id,
            reinitialize=reinitialize
        )

        history_entry = {
            "timestamp": timestamp,
            "attempt": module_data[
                "recovery_attempts"
            ],
            "success": bool(success),
            "reinitialized": bool(reinitialize)
        }

        with self.lock:
            module_data["restart_history"].append(
                history_entry
            )

            if success:
                module_data["recovery_successes"] += 1
                module_data["last_error"] = None
                module_data["cooldown_until"] = None

                self.recovery_successes += 1
            else:
                module_data["recovery_failures"] += 1
                self.recovery_failures += 1

        if success:
            self.add_timeline_event(
                event_type="MODULE_RECOVERED",
                payload={
                    "module_id": module_id,
                    "attempt": history_entry["attempt"]
                }
            )

            self._emit_event(
                event_type="MODULE_RECOVERED",
                payload={
                    "module_id": module_id,
                    "attempt": history_entry["attempt"]
                }
            )

            return True

        remaining = self.can_restart(module_id)

        if not remaining["allowed"]:
            self._enter_recovery_cooldown(
                module_id=module_id,
                disable_module=disable_on_failure
            )

        self.add_timeline_event(
            event_type="MODULE_RECOVERY_FAILED",
            payload={
                "module_id": module_id,
                "attempt": history_entry["attempt"]
            }
        )

        self._emit_event(
            event_type="MODULE_RECOVERY_FAILED",
            payload={
                "module_id": module_id,
                "attempt": history_entry["attempt"]
            },
            severity="ERROR"
        )

        return False

    def recover_failed_modules(
        self,
        module_type=None,
        reinitialize=True
    ):
        results = {}

        for record in self.list_modules(
            module_type=module_type,
            enabled_only=True
        ):
            if record["status"] not in {
                "CRASHED",
                "ERROR",
                "FAILED"
            }:
                continue

            module_id = record["module_id"]
            results[module_id] = self.recover_module(
                module_id=module_id,
                reinitialize=reinitialize
            )

        return results

    def get_recovery_report(self, module_id=None):
        if module_id is not None:
            module_data = self._get_module_data(
                module_id
            )

            if module_data is None:
                return None

            return self._serialize_recovery_record(
                module_id=module_id,
                module_data=module_data
            )

        with self.lock:
            return {
                current_id: self._serialize_recovery_record(
                    module_id=current_id,
                    module_data=module_data
                )
                for current_id, module_data
                in self.modules.items()
            }

    # =====================================================
    # Startup Orchestration
    # =====================================================

    def configure_module_startup(
        self,
        module_id,
        priority=None,
        startup_group=None,
        startup_delay=None,
        lazy_load=None
    ):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        with self.lock:
            if priority is not None:
                module_data["priority"] = int(priority)

            if startup_group is not None:
                group = str(startup_group).strip()
                module_data["startup_group"] = group or "default"

            if startup_delay is not None:
                module_data["startup_delay"] = max(
                    0.0,
                    float(startup_delay)
                )

            if lazy_load is not None:
                module_data["lazy_load"] = bool(lazy_load)

            module_data["operation_count"] += 1
            self.last_operation_at = datetime.now(UTC).isoformat()

        self.add_timeline_event(
            event_type="MODULE_STARTUP_CONFIGURATION_CHANGED",
            payload={
                "module_id": module_id,
                "priority": module_data["priority"],
                "startup_group": module_data["startup_group"],
                "startup_delay": module_data["startup_delay"],
                "lazy_load": module_data["lazy_load"]
            }
        )

        return True

    def list_startup_groups(self):
        with self.lock:
            groups = {}

            for module_id, module_data in self.modules.items():
                group = module_data["startup_group"]
                groups.setdefault(group, []).append(module_id)

        return {
            group: sorted(module_ids)
            for group, module_ids in sorted(groups.items())
        }

    def get_boot_plan(
        self,
        module_type=None,
        startup_group=None,
        include_disabled=False,
        include_lazy=False,
        dependency_order=True
    ):
        with self.lock:
            candidate_ids = [
                module_id
                for module_id, module_data in self.modules.items()
                if (
                    (module_type is None or module_data["type"] == module_type)
                    and (
                        startup_group is None
                        or module_data["startup_group"] == startup_group
                    )
                    and (include_disabled or module_data["enabled"])
                    and (include_lazy or not module_data["lazy_load"])
                )
            ]

        ordered_ids = self._order_module_ids(
            candidate_ids,
            dependency_order=dependency_order
        )

        plan = []

        for position, module_id in enumerate(ordered_ids, start=1):
            module_data = self._get_module_data(module_id)
            module = module_data["instance"]

            plan.append(
                {
                    "position": position,
                    "module_id": module_id,
                    "name": getattr(
                        module,
                        "name",
                        module.__class__.__name__
                    ),
                    "type": module_data["type"],
                    "priority": module_data["priority"],
                    "startup_group": module_data["startup_group"],
                    "startup_delay": module_data["startup_delay"],
                    "lazy_load": module_data["lazy_load"],
                    "enabled": module_data["enabled"],
                    "requires": deepcopy(
                        getattr(module, "requires", [])
                    )
                }
            )

        with self.lock:
            self.boot_plans_generated += 1

        self.add_timeline_event(
            event_type="MODULE_BOOT_PLAN_GENERATED",
            payload={
                "module_count": len(plan),
                "module_type": module_type,
                "startup_group": startup_group,
                "include_disabled": bool(include_disabled),
                "include_lazy": bool(include_lazy)
            }
        )

        return plan

    def print_boot_plan(
        self,
        module_type=None,
        startup_group=None,
        include_disabled=False,
        include_lazy=False,
        dependency_order=True
    ):
        plan = self.get_boot_plan(
            module_type=module_type,
            startup_group=startup_group,
            include_disabled=include_disabled,
            include_lazy=include_lazy,
            dependency_order=dependency_order
        )

        print("=== J.A.R.V.I.S. MODULE BOOT PLAN ===")

        if not plan:
            print("No modules in boot plan.")
            return plan

        current_priority = None

        for entry in plan:
            if entry["priority"] != current_priority:
                current_priority = entry["priority"]
                print()
                print(f"[Priority {current_priority}]")

            delay = entry["startup_delay"]
            delay_text = (
                f", delay={delay:g}s"
                if delay > 0
                else ""
            )

            print(
                f" {entry['position']:>2}. "
                f"{entry['module_id']} "
                f"(group={entry['startup_group']}{delay_text})"
            )

        return plan

    def start_group(
        self,
        startup_group,
        initialize=True,
        dependency_order=True,
        continue_on_error=True
    ):
        plan = self.get_boot_plan(
            startup_group=startup_group,
            include_disabled=False,
            include_lazy=False,
            dependency_order=dependency_order
        )

        results = {}

        for entry in plan:
            module_id = entry["module_id"]

            if initialize:
                initialized = self.initialize_module(module_id)

                if not initialized:
                    results[module_id] = False

                    if not continue_on_error:
                        break

                    continue

            result = self.start_module(module_id)
            results[module_id] = result

            if not result and not continue_on_error:
                break

        with self.lock:
            self.group_start_count += 1

        self.add_timeline_event(
            event_type="MODULE_GROUP_STARTED",
            payload={
                "startup_group": startup_group,
                "results": deepcopy(results)
            }
        )

        return results

    def stop_group(
        self,
        startup_group,
        dependency_order=True,
        continue_on_error=True
    ):
        plan = self.get_boot_plan(
            startup_group=startup_group,
            include_disabled=True,
            include_lazy=True,
            dependency_order=dependency_order
        )

        results = {}

        for entry in reversed(plan):
            module_id = entry["module_id"]
            result = self.stop_module(module_id)
            results[module_id] = result

            if not result and not continue_on_error:
                break

        with self.lock:
            self.group_stop_count += 1

        self.add_timeline_event(
            event_type="MODULE_GROUP_STOPPED",
            payload={
                "startup_group": startup_group,
                "results": deepcopy(results)
            }
        )

        return results

    def restart_group(
        self,
        startup_group,
        dependency_order=True,
        reinitialize=False,
        continue_on_error=True
    ):
        plan = self.get_boot_plan(
            startup_group=startup_group,
            include_disabled=False,
            include_lazy=False,
            dependency_order=dependency_order
        )

        results = {}

        for entry in plan:
            module_id = entry["module_id"]
            result = self.restart_module(
                module_id=module_id,
                reinitialize=reinitialize
            )
            results[module_id] = result

            if not result and not continue_on_error:
                break

        with self.lock:
            self.group_restart_count += 1

        self.add_timeline_event(
            event_type="MODULE_GROUP_RESTARTED",
            payload={
                "startup_group": startup_group,
                "results": deepcopy(results),
                "reinitialized": bool(reinitialize)
            }
        )

        return results

    # =====================================================
    # Maintenance Mode
    # =====================================================

    def set_maintenance_mode(
        self,
        module_id,
        enabled,
        stop_module=True
    ):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        enabled = bool(enabled)
        module = module_data["instance"]

        if (
            enabled
            and stop_module
            and self._module_is_running(module)
        ):
            if not self.stop_module(module_id):
                return False

        with self.lock:
            module_data["maintenance_mode"] = enabled
            module_data["operation_count"] += 1
            self.maintenance_mode_count += 1
            self.last_operation_at = datetime.now(UTC).isoformat()

        self.add_timeline_event(
            event_type="MODULE_MAINTENANCE_CHANGED",
            payload={
                "module_id": module_id,
                "maintenance_mode": enabled
            }
        )

        self._emit_event(
            event_type="MODULE_MAINTENANCE_CHANGED",
            payload={
                "module_id": module_id,
                "maintenance_mode": enabled
            }
        )

        return True

    def is_in_maintenance(self, module_id):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        return bool(module_data.get("maintenance_mode", False))

    # =====================================================
    # Runtime Configuration
    # =====================================================

    def update_module_runtime(
        self,
        module_id,
        **changes
    ):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        allowed = {
            "priority",
            "startup_group",
            "startup_delay",
            "lazy_load",
            "auto_restart",
            "max_restart_attempts",
            "restart_delay",
            "cooldown_seconds"
        }

        unknown = sorted(set(changes) - allowed)

        if unknown:
            return self._record_module_error(
                module_id=module_id,
                error={
                    "message": "Unsupported runtime settings.",
                    "settings": unknown
                }
            )

        normalized = {}

        try:
            for key, value in changes.items():
                if key == "priority":
                    normalized[key] = int(value)

                elif key == "startup_group":
                    normalized[key] = (
                        str(value).strip() or "default"
                    )

                elif key in {
                    "startup_delay",
                    "restart_delay",
                    "cooldown_seconds"
                }:
                    normalized[key] = max(0.0, float(value))

                elif key == "max_restart_attempts":
                    normalized[key] = max(0, int(value))

                elif key in {
                    "lazy_load",
                    "auto_restart"
                }:
                    normalized[key] = bool(value)

            with self.lock:
                for key, value in normalized.items():
                    module_data[key] = value

                module_data["operation_count"] += 1
                self.runtime_updates += 1
                self.last_operation_at = datetime.now(UTC).isoformat()

            self.add_timeline_event(
                event_type="MODULE_RUNTIME_UPDATED",
                payload={
                    "module_id": module_id,
                    "changes": deepcopy(normalized)
                }
            )

            self._emit_event(
                event_type="MODULE_RUNTIME_UPDATED",
                payload={
                    "module_id": module_id,
                    "changes": deepcopy(normalized)
                }
            )

            return True

        except (TypeError, ValueError) as error:
            return self._record_module_error(
                module_id=module_id,
                error=error
            )

    def get_module_runtime(self, module_id):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return None

        return {
            "priority": module_data["priority"],
            "startup_group": module_data["startup_group"],
            "startup_delay": module_data["startup_delay"],
            "lazy_load": module_data["lazy_load"],
            "auto_restart": module_data["auto_restart"],
            "max_restart_attempts": module_data[
                "max_restart_attempts"
            ],
            "restart_delay": module_data["restart_delay"],
            "cooldown_seconds": module_data["cooldown_seconds"],
            "maintenance_mode": module_data[
                "maintenance_mode"
            ],
            "tags": deepcopy(module_data["tags"])
        }

    # =====================================================
    # Tags
    # =====================================================

    def add_module_tags(self, module_id, *tags):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        normalized = {
            str(tag).strip().lower()
            for tag in tags
            if str(tag).strip()
        }

        with self.lock:
            current = set(module_data.get("tags", []))
            current.update(normalized)
            module_data["tags"] = sorted(current)
            module_data["operation_count"] += 1
            self.last_operation_at = datetime.now(UTC).isoformat()

        self.add_timeline_event(
            event_type="MODULE_TAGS_ADDED",
            payload={
                "module_id": module_id,
                "tags": sorted(normalized)
            }
        )

        return True

    def remove_module_tags(self, module_id, *tags):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        normalized = {
            str(tag).strip().lower()
            for tag in tags
            if str(tag).strip()
        }

        with self.lock:
            current = set(module_data.get("tags", []))
            current.difference_update(normalized)
            module_data["tags"] = sorted(current)
            module_data["operation_count"] += 1
            self.last_operation_at = datetime.now(UTC).isoformat()

        self.add_timeline_event(
            event_type="MODULE_TAGS_REMOVED",
            payload={
                "module_id": module_id,
                "tags": sorted(normalized)
            }
        )

        return True

    def list_tags(self):
        with self.lock:
            return sorted({
                tag
                for module_data in self.modules.values()
                for tag in module_data.get("tags", [])
            })

    def list_modules_by_tag(
        self,
        tag,
        enabled_only=False
    ):
        normalized = str(tag).strip().lower()

        with self.lock:
            module_ids = [
                module_id
                for module_id, module_data in self.modules.items()
                if normalized in module_data.get("tags", [])
                and (
                    not enabled_only
                    or module_data["enabled"]
                )
            ]

        return sorted(module_ids)

    def start_tag(
        self,
        tag,
        initialize=True,
        dependency_order=True,
        continue_on_error=True
    ):
        module_ids = self.list_modules_by_tag(
            tag,
            enabled_only=True
        )
        module_ids = self._order_module_ids(
            module_ids,
            dependency_order=dependency_order
        )

        results = {}

        for module_id in module_ids:
            module_data = self._get_module_data(module_id)

            if module_data.get("maintenance_mode", False):
                results[module_id] = False
            else:
                if initialize:
                    initialized = self.initialize_module(module_id)
                    if not initialized:
                        results[module_id] = False
                        if not continue_on_error:
                            break
                        continue

                results[module_id] = self.start_module(module_id)

            if not results[module_id] and not continue_on_error:
                break

        with self.lock:
            self.tag_start_count += 1

        self.add_timeline_event(
            event_type="MODULE_TAG_STARTED",
            payload={
                "tag": str(tag).strip().lower(),
                "results": deepcopy(results)
            }
        )

        return results

    def stop_tag(
        self,
        tag,
        dependency_order=True,
        continue_on_error=True
    ):
        module_ids = self.list_modules_by_tag(tag)
        module_ids = self._order_module_ids(
            module_ids,
            dependency_order=dependency_order
        )
        module_ids.reverse()

        results = {}

        for module_id in module_ids:
            results[module_id] = self.stop_module(module_id)

            if not results[module_id] and not continue_on_error:
                break

        with self.lock:
            self.tag_stop_count += 1

        self.add_timeline_event(
            event_type="MODULE_TAG_STOPPED",
            payload={
                "tag": str(tag).strip().lower(),
                "results": deepcopy(results)
            }
        )

        return results

    def restart_tag(
        self,
        tag,
        dependency_order=True,
        reinitialize=False,
        continue_on_error=True
    ):
        module_ids = self.list_modules_by_tag(
            tag,
            enabled_only=True
        )
        module_ids = self._order_module_ids(
            module_ids,
            dependency_order=dependency_order
        )

        results = {}

        for module_id in module_ids:
            module_data = self._get_module_data(module_id)

            if module_data.get("maintenance_mode", False):
                results[module_id] = False
            else:
                results[module_id] = self.restart_module(
                    module_id=module_id,
                    reinitialize=reinitialize
                )

            if not results[module_id] and not continue_on_error:
                break

        with self.lock:
            self.tag_restart_count += 1

        self.add_timeline_event(
            event_type="MODULE_TAG_RESTARTED",
            payload={
                "tag": str(tag).strip().lower(),
                "results": deepcopy(results),
                "reinitialized": bool(reinitialize)
            }
        )

        return results

    # =====================================================
    # Information
    # =====================================================

    def get_manifest(self):
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "mission": self.mission,
            "requires": [
                "core.component_registry",
                "core.dependency_resolver"
            ],
            "optional": [
                "core.event_bus",
                "core.logger",
                "core.health_monitor",
                "core.config_manager"
            ],
            "capabilities": deepcopy(
                self.capabilities
            )
        }

    def get_statistics(self):
        with self.lock:
            type_counts = {
                module_type: len(module_ids)
                for module_type, module_ids
                in self.module_types.items()
            }

            enabled_count = sum(
                1
                for module_data in self.modules.values()
                if module_data["enabled"]
            )

            return {
                "registered_module_count": len(self.modules),
                "enabled_module_count": enabled_count,
                "disabled_module_count": (
                    len(self.modules) - enabled_count
                ),
                "module_type_counts": type_counts,
                "modules_registered": self.modules_registered,
                "modules_unregistered": self.modules_unregistered,
                "registration_failures": self.registration_failures,
                "duplicate_registrations": (
                    self.duplicate_registrations
                ),
                "initialize_count": self.initialize_count,
                "start_count": self.start_count,
                "stop_count": self.stop_count,
                "restart_count": self.restart_count,
                "enable_count": self.enable_count,
                "disable_count": self.disable_count,
                "reload_count": self.reload_count,
                "operation_failures": self.operation_failures,
                "crash_count": self.crash_count,
                "recovery_attempts": self.recovery_attempts,
                "recovery_successes": self.recovery_successes,
                "recovery_failures": self.recovery_failures,
                "modules_auto_disabled": self.modules_auto_disabled,
                "boot_plans_generated": self.boot_plans_generated,
                "group_start_count": self.group_start_count,
                "group_stop_count": self.group_stop_count,
                "group_restart_count": self.group_restart_count,
                "delayed_start_count": self.delayed_start_count,
                "delayed_start_seconds": self.delayed_start_seconds,
                "maintenance_mode_count": self.maintenance_mode_count,
                "runtime_updates": self.runtime_updates,
                "tag_start_count": self.tag_start_count,
                "tag_stop_count": self.tag_stop_count,
                "tag_restart_count": self.tag_restart_count,
                "timeline_count": len(self.timeline),
                "created_at": self.created_at,
                "last_registered_at": self.last_registered_at,
                "last_unregistered_at": self.last_unregistered_at,
                "last_operation_at": self.last_operation_at
            }

    def get_status(self):
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "lifecycle": deepcopy(
                self.lifecycle
            ),
            "statistics": self.get_statistics(),
            "modules": self.list_modules(),
            "last_started": self.last_started,
            "last_stopped": self.last_stopped,
            "last_error": self.last_error
        }

    def get_health(self):
        return {
            "component_id": self.component_id,
            "status": self.status,
            "health": self.health,
            "healthy": self.lifecycle["healthy"],
            "last_error": self.last_error
        }

    # =====================================================
    # Timeline
    # =====================================================

    def add_timeline_event(
        self,
        event_type,
        payload=None
    ):
        if payload is None:
            payload = {}

        with self.lock:
            self.timeline.append(
                {
                    "event_type": event_type,
                    "component_id": self.component_id,
                    "payload": deepcopy(payload),
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        return True

    # =====================================================
    # Connected Systems
    # =====================================================

    def _register_with_connected_systems(
        self,
        module,
        module_type
    ):
        module_id = self._get_module_id(module)

        try:
            if self.registry is not None:
                if module_type == "manager":
                    self.registry.register_manager(
                        module
                    )

                elif module_type == "engine":
                    manager_id = getattr(
                        module,
                        "manager",
                        None
                    )

                    try:
                        self.registry.register_engine(
                            engine=module,
                            manager_id=manager_id
                        )

                    except TypeError:
                        self.registry.register_engine(
                            module
                        )

                elif module_type == "plugin":
                    self.registry.register_plugin(
                        module
                    )

                elif module_type == "service":
                    self.registry.register_service(
                        module
                    )

            if self.dependency_resolver is not None:
                self.dependency_resolver.register_component(
                    module
                )

            if self.health_monitor is not None:
                self.health_monitor.register_component(
                    component=module,
                    component_type=module_type
                )

        except Exception as error:
            self._record_module_error(
                module_id=module_id,
                error=error
            )

    def _unregister_from_connected_systems(
        self,
        module_id,
        module_type
    ):
        try:
            if self.dependency_resolver is not None:
                unregister_dependency = getattr(
                    self.dependency_resolver,
                    "unregister_component",
                    None
                )

                if unregister_dependency is not None:
                    unregister_dependency(
                        module_id
                    )

            if self.health_monitor is not None:
                self.health_monitor.unregister_component(
                    module_id
                )

            if self.registry is not None:
                unregister_method = getattr(
                    self.registry,
                    f"unregister_{module_type}",
                    None
                )

                if unregister_method is not None:
                    unregister_method(
                        module_id
                    )

        except Exception as error:
            self._record_module_error(
                module_id=module_id,
                error=error
            )

    # =====================================================
    # Internal Helpers
    # =====================================================


    def _enter_recovery_cooldown(
        self,
        module_id,
        disable_module=False
    ):
        module_data = self._get_module_data(module_id)

        if module_data is None:
            return False

        cooldown_until = (
            datetime.now(UTC)
            + timedelta(
                seconds=module_data[
                    "cooldown_seconds"
                ]
            )
        ).isoformat()

        with self.lock:
            module_data["cooldown_until"] = (
                cooldown_until
            )

            if disable_module:
                module_data["enabled"] = False
                self.modules_auto_disabled += 1

        self.add_timeline_event(
            event_type="MODULE_RECOVERY_COOLDOWN",
            payload={
                "module_id": module_id,
                "cooldown_until": cooldown_until,
                "disabled": bool(disable_module)
            }
        )

        self._emit_event(
            event_type="MODULE_RECOVERY_COOLDOWN",
            payload={
                "module_id": module_id,
                "cooldown_until": cooldown_until,
                "disabled": bool(disable_module)
            },
            severity="WARNING"
        )

        return True

    def _serialize_recovery_record(
        self,
        module_id,
        module_data
    ):
        return {
            "module_id": module_id,
            "enabled": module_data["enabled"],
            "status": getattr(
                module_data["instance"],
                "status",
                "UNKNOWN"
            ),
            "crash_count": module_data["crash_count"],
            "recovery_attempts": module_data[
                "recovery_attempts"
            ],
            "recovery_successes": module_data[
                "recovery_successes"
            ],
            "recovery_failures": module_data[
                "recovery_failures"
            ],
            "last_crash_at": module_data[
                "last_crash_at"
            ],
            "last_recovery_at": module_data[
                "last_recovery_at"
            ],
            "auto_restart": module_data[
                "auto_restart"
            ],
            "max_restart_attempts": module_data[
                "max_restart_attempts"
            ],
            "restart_delay": module_data[
                "restart_delay"
            ],
            "cooldown_seconds": module_data[
                "cooldown_seconds"
            ],
            "cooldown_until": module_data[
                "cooldown_until"
            ],
            "priority": module_data["priority"],
            "startup_group": module_data["startup_group"],
            "startup_delay": module_data["startup_delay"],
            "lazy_load": module_data["lazy_load"],
            "restart_history": deepcopy(
                module_data["restart_history"]
            ),
            "last_error": deepcopy(
                module_data["last_error"]
            )
        }

    def _get_module_data(
        self,
        module_id
    ):
        with self.lock:
            return self.modules.get(
                module_id
            )

    def _get_operation_order(
        self,
        reverse=False,
        module_type=None,
        dependency_order=True
    ):
        module_ids = self.list_module_ids(
            module_type=module_type,
            enabled_only=True
        )

        module_ids = self._order_module_ids(
            module_ids,
            dependency_order=dependency_order
        )

        if reverse:
            module_ids.reverse()

        return module_ids

    def _order_module_ids(
        self,
        module_ids,
        dependency_order=True
    ):
        module_ids = list(dict.fromkeys(module_ids))
        module_id_set = set(module_ids)

        def sort_key(module_id):
            module_data = self._get_module_data(module_id)

            if module_data is None:
                return (999999, module_id)

            return (
                int(module_data.get("priority", 100)),
                module_id
            )

        if not dependency_order:
            return sorted(module_ids, key=sort_key)

        if self.dependency_resolver is not None:
            resolved_order = list(
                getattr(
                    self.dependency_resolver,
                    "boot_order",
                    []
                )
            )

            if not resolved_order:
                try:
                    resolved_order = (
                        self.dependency_resolver
                        .generate_boot_order()
                    )
                except Exception:
                    resolved_order = []

            ordered = [
                module_id
                for module_id in resolved_order
                if module_id in module_id_set
            ]

            missing = [
                module_id
                for module_id in module_ids
                if module_id not in ordered
            ]

            if ordered:
                return ordered + self._internal_dependency_order(
                    missing,
                    sort_key
                )

        return self._internal_dependency_order(
            module_ids,
            sort_key
        )

    def _internal_dependency_order(
        self,
        module_ids,
        sort_key
    ):
        module_id_set = set(module_ids)
        indegree = {
            module_id: 0
            for module_id in module_ids
        }
        dependents = {
            module_id: set()
            for module_id in module_ids
        }

        for module_id in module_ids:
            module = self.get_module(module_id)
            requires = getattr(module, "requires", [])

            for dependency_id in requires:
                if dependency_id not in module_id_set:
                    continue

                indegree[module_id] += 1
                dependents[dependency_id].add(module_id)

        ready = sorted(
            (
                module_id
                for module_id, count in indegree.items()
                if count == 0
            ),
            key=sort_key
        )
        ordered = []

        while ready:
            module_id = ready.pop(0)
            ordered.append(module_id)

            for dependent_id in sorted(
                dependents[module_id],
                key=sort_key
            ):
                indegree[dependent_id] -= 1

                if indegree[dependent_id] == 0:
                    ready.append(dependent_id)
                    ready.sort(key=sort_key)

        unresolved = [
            module_id
            for module_id in module_ids
            if module_id not in ordered
        ]

        return ordered + sorted(unresolved, key=sort_key)

    def _module_is_running(
        self,
        module
    ):
        status = str(
            getattr(
                module,
                "status",
                ""
            )
        ).upper()

        return status in {
            "ONLINE",
            "RUNNING",
            "STARTED",
            "READY"
        }

    def _get_module_id(
        self,
        module
    ):
        for attribute in [
            "component_id",
            "manager_id",
            "engine_id",
            "plugin_id",
            "service_id"
        ]:
            module_id = getattr(
                module,
                attribute,
                None
            )

            if module_id:
                return module_id

        return None

    def _normalize_module_type(
        self,
        module,
        module_type=None
    ):
        if module_type is not None:
            return str(
                module_type
            ).strip().lower()

        if hasattr(
            module,
            "manager_id"
        ):
            return "manager"

        if hasattr(
            module,
            "engine_id"
        ):
            return "engine"

        if hasattr(
            module,
            "plugin_id"
        ):
            return "plugin"

        if hasattr(
            module,
            "service_id"
        ):
            return "service"

        return "component"

    def _serialize_module_record(
        self,
        module_id,
        module_data
    ):
        module = module_data["instance"]

        return {
            "module_id": module_id,
            "name": getattr(
                module,
                "name",
                module.__class__.__name__
            ),
            "class_name": module.__class__.__name__,
            "version": getattr(
                module,
                "version",
                None
            ),
            "type": module_data["type"],
            "enabled": module_data["enabled"],
            "status": getattr(
                module,
                "status",
                "UNKNOWN"
            ),
            "health": getattr(
                module,
                "health",
                None
            ),
            "requires": deepcopy(
                getattr(
                    module,
                    "requires",
                    []
                )
            ),
            "optional": deepcopy(
                getattr(
                    module,
                    "optional",
                    []
                )
            ),
            "registered_at": module_data["registered_at"],
            "last_initialized_at": (
                module_data["last_initialized_at"]
            ),
            "last_started_at": (
                module_data["last_started_at"]
            ),
            "last_stopped_at": (
                module_data["last_stopped_at"]
            ),
            "last_restarted_at": (
                module_data["last_restarted_at"]
            ),
            "last_reloaded_at": (
                module_data["last_reloaded_at"]
            ),
            "last_error": module_data["last_error"],
            "operation_count": module_data["operation_count"],
            "crash_count": module_data["crash_count"],
            "recovery_attempts": module_data["recovery_attempts"],
            "recovery_successes": module_data["recovery_successes"],
            "recovery_failures": module_data["recovery_failures"],
            "last_crash_at": module_data["last_crash_at"],
            "last_recovery_at": module_data["last_recovery_at"],
            "auto_restart": module_data["auto_restart"],
            "max_restart_attempts": module_data[
                "max_restart_attempts"
            ],
            "restart_delay": module_data["restart_delay"],
            "cooldown_seconds": module_data[
                "cooldown_seconds"
            ],
            "cooldown_until": module_data["cooldown_until"],
            "priority": module_data["priority"],
            "startup_group": module_data["startup_group"],
            "startup_delay": module_data["startup_delay"],
            "lazy_load": module_data["lazy_load"],
            "maintenance_mode": module_data["maintenance_mode"],
            "tags": deepcopy(module_data["tags"])
        }

    def _registration_error(
        self,
        error
    ):
        with self.lock:
            self.registration_failures += 1
            self.last_error = str(error)

        self.add_timeline_event(
            event_type="MODULE_REGISTRATION_FAILED",
            payload={
                "error": str(error)
            }
        )

        self._log(
            level="error",
            message=str(error)
        )

        return False

    def _record_module_error(
        self,
        module_id,
        error
    ):
        error_text = str(error)

        with self.lock:
            self.operation_failures += 1
            self.last_error = error_text

            if module_id in self.modules:
                self.modules[module_id][
                    "last_error"
                ] = deepcopy(error)

        self.add_timeline_event(
            event_type="MODULE_OPERATION_FAILED",
            payload={
                "module_id": module_id,
                "error": deepcopy(error)
            }
        )

        self._emit_event(
            event_type="MODULE_OPERATION_FAILED",
            payload={
                "module_id": module_id,
                "error": deepcopy(error)
            },
            severity="ERROR"
        )

        self._log(
            level="error",
            message=error_text,
            payload={
                "module_id": module_id,
                "error": deepcopy(error)
            }
        )

        return False

    # =====================================================
    # Optional Integrations
    # =====================================================

    def _emit_event(
        self,
        event_type,
        payload=None,
        severity="INFO"
    ):
        if self.event_bus is None:
            return False

        self.event_bus.publish(
            event_type=event_type,
            payload=payload or {},
            source=self.component_id,
            severity=severity
        )

        return True

    def _log(
        self,
        level,
        message,
        payload=None
    ):
        if self.logger is None:
            return False

        log_method = getattr(
            self.logger,
            level,
            None
        )

        if log_method is None:
            return False

        log_method(
            message=message,
            source=self.component_id,
            payload=payload or {}
        )

        return True


if __name__ == "__main__":

    class CoreManager:
        manager_id = "core.manager"
        name = "Core Manager"
        version = "1.0.0"
        status = "OFFLINE"
        health = 0
        requires = []
        optional = []
        auto_start = True
        priority = 0
        startup_group = "core"
        startup_delay = 0
        tags = ["core", "system"]

        def initialize(self):
            self.status = "INITIALIZED"
            self.health = 100
            return True

        def start(self):
            self.status = "ONLINE"
            self.health = 100
            return True

        def stop(self):
            self.status = "OFFLINE"
            self.health = 0
            return True

    class VisionEngine:
        engine_id = "vision.engine"
        name = "Vision Engine"
        version = "1.0.0"
        status = "OFFLINE"
        health = 0
        requires = ["core.manager"]
        optional = []
        auto_start = True
        priority = 100
        startup_group = "vision"
        startup_delay = 0.01
        tags = ["vision", "gpu"]

        def initialize(self):
            self.status = "INITIALIZED"
            self.health = 100
            return True

        def start(self):
            self.status = "ONLINE"
            self.health = 100
            return True

        def stop(self):
            self.status = "OFFLINE"
            self.health = 0
            return True

    class VisionPlugin:
        plugin_id = "vision.plugin"
        name = "Vision Plugin"
        version = "1.0.0"
        status = "OFFLINE"
        health = 0
        requires = ["vision.engine"]
        optional = []
        auto_start = True
        priority = 200
        startup_group = "vision"
        startup_delay = 0
        tags = ["vision", "experimental"]

        def initialize(self):
            self.status = "INITIALIZED"
            self.health = 100
            return True

        def start(self):
            self.status = "ONLINE"
            self.health = 100
            return True

        def stop(self):
            self.status = "OFFLINE"
            self.health = 0
            return True

    class RecoverableEngine:
        engine_id = "recoverable.engine"
        name = "Recoverable Engine"
        version = "1.0.0"
        status = "OFFLINE"
        health = 0
        requires = ["core.manager"]
        optional = []
        auto_start = True
        priority = 120
        startup_group = "recovery"
        tags = ["recovery", "test"]
        auto_restart = True
        max_restart_attempts = 2
        restart_delay = 0
        cooldown_seconds = 0

        def __init__(self):
            self.fail_next_start = True

        def initialize(self):
            self.status = "INITIALIZED"
            self.health = 100
            return True

        def start(self):
            if self.fail_next_start:
                self.fail_next_start = False
                self.status = "ERROR"
                self.health = 0
                return False
            self.status = "ONLINE"
            self.health = 100
            return True

        def stop(self):
            self.status = "OFFLINE"
            self.health = 0
            return True

    module_manager = ModuleManager()
    module_manager.initialize()
    module_manager.start()

    module_manager.register_manager(CoreManager())
    module_manager.register_engine(VisionEngine())
    module_manager.register_plugin(VisionPlugin())
    module_manager.register_engine(RecoverableEngine())

    print("=== MODULE MANAGER FINAL INTEGRATION TEST ===")
    print()

    print("Boot Plan:")
    module_manager.print_boot_plan()

    print()
    print("Initialize All:")
    print(module_manager.initialize_all(dependency_order=True))

    print()
    print("Start Core:")
    print(module_manager.start_group("core"))

    print()
    print("Start Vision Tag:")
    print(module_manager.start_tag("vision"))

    print()
    print("Maintenance Mode:")
    print(
        module_manager.set_maintenance_mode(
            "vision.plugin",
            True
        )
    )
    print(module_manager.is_in_maintenance("vision.plugin"))

    print()
    print("Runtime Update:")
    print(
        module_manager.update_module_runtime(
            "vision.engine",
            priority=80,
            startup_group="perception",
            startup_delay=0,
            auto_restart=True
        )
    )
    print(module_manager.get_module_runtime("vision.engine"))

    print()
    print("Tag Management:")
    print(
        module_manager.add_module_tags(
            "vision.engine",
            "camera",
            "perception"
        )
    )
    print(module_manager.list_tags())
    print(module_manager.list_modules_by_tag("camera"))

    print()
    print("Recovery Test:")
    print(module_manager.start_module("recoverable.engine"))
    module_manager.mark_module_crashed(
        "recoverable.engine",
        error="Simulated crash",
        auto_recover=True
    )
    print(module_manager.get_recovery_report("recoverable.engine"))

    print()
    print("Tag Stop:")
    print(module_manager.stop_tag("vision"))

    print()
    print("Final Status:")
    print(module_manager.get_status())

    module_manager.stop_all(dependency_order=True)
    module_manager.stop()
