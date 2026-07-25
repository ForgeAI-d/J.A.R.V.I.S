from core.base_manager import BaseManager
from copy import deepcopy
from datetime import datetime, UTC
from threading import RLock


class HealthMonitor(BaseManager):

    COMPONENT_ID = "core.health_monitor"
    MANAGER_ID = "core.health_monitor"
    NAME = "Health Monitor"
    PRIORITY = 70
    AUTO_START = True

    VERSION = "0.1.0"

    HEALTH_INFO = 100
    HEALTH_WARNING = 80
    HEALTH_CRITICAL = 50
    HEALTH_OFFLINE = 0

    def __init__(
        self,
        registry=None,
        event_bus=None,
        logger=None
    ):
        BaseManager.__init__(self)
        self.name = "Health Monitor"
        self.component_id = "core.health_monitor"
        self.version = self.VERSION
        self.author = "Velthor Technologies"
        self.mission = (
            "Überwacht den Gesundheitszustand aller J.A.R.V.I.S. "
            "Kernel-Komponenten, Manager, Engines, Plugins und Services."
        )

        self.registry = registry
        self.event_bus = event_bus
        self.logger = logger

        self.status = "OFFLINE"
        self.health = 0

        self.components = {}
        self.history = []
        self.timeline = []

        self.lock = RLock()

        self.check_count = 0
        self.components_checked = 0
        self.warnings_created = 0
        self.criticals_created = 0
        self.offline_detected = 0
        self.errors_detected = 0

        self.last_check_at = None
        self.last_warning_at = None
        self.last_critical_at = None
        self.last_started = None
        self.last_stopped = None
        self.last_error = None

        self.lifecycle = {
            "registered": False,
            "dependencies_resolved": True,
            "initialized": False,
            "started": False,
            "healthy": False
        }

        self.capabilities = [
            "component_registration",
            "health_check",
            "health_summary",
            "health_history",
            "warning_detection",
            "critical_detection",
            "offline_detection",
            "timeline",
            "registry_compatible",
            "event_bus_compatible",
            "logger_compatible",
            "thread_safe_access"
        ]

    def initialize(self):
        with self.lock:
            self.lifecycle["initialized"] = True

        self.add_timeline_event("HEALTH_MONITOR_INITIALIZED")
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

        self.add_timeline_event("HEALTH_MONITOR_STARTED")
        return True

    def stop(self):
        with self.lock:
            self.status = "OFFLINE"
            self.health = 0
            self.last_stopped = datetime.now(UTC).isoformat()
            self.lifecycle["started"] = False
            self.lifecycle["healthy"] = False

        self.add_timeline_event("HEALTH_MONITOR_STOPPED")
        return True

    def register_component(
        self,
        component,
        component_type="component"
    ):
        component_id = self._get_component_id(component)

        if component_id is None:
            return False

        with self.lock:
            self.components[component_id] = {
                "instance": component,
                "type": component_type,
                "registered_at": datetime.now(UTC).isoformat(),
                "last_health": None
            }

        self.add_timeline_event(
            event_type="COMPONENT_REGISTERED",
            payload={
                "component_id": component_id,
                "component_type": component_type
            }
        )

        return True

    def unregister_component(self, component_id):
        with self.lock:
            if component_id not in self.components:
                return False

            del self.components[component_id]

        self.add_timeline_event(
            event_type="COMPONENT_UNREGISTERED",
            payload={
                "component_id": component_id
            }
        )

        return True

    def register_manager(self, manager):
        return self.register_component(
            component=manager,
            component_type="manager"
        )

    def register_engine(self, engine):
        return self.register_component(
            component=engine,
            component_type="engine"
        )

    def register_plugin(self, plugin):
        return self.register_component(
            component=plugin,
            component_type="plugin"
        )

    def register_service(self, service):
        return self.register_component(
            component=service,
            component_type="service"
        )

    def register_from_registry(self):
        if self.registry is None:
            return False

        managers = getattr(self.registry, "managers", {})
        engines = getattr(self.registry, "engines", {})
        plugins = getattr(self.registry, "plugins", {})
        services = getattr(self.registry, "services", {})

        for manager_data in managers.values():
            manager = manager_data.get("instance")

            if manager is not None:
                self.register_manager(manager)

        for engine_data in engines.values():
            engine = engine_data.get("instance")

            if engine is not None:
                self.register_engine(engine)

        for plugin_data in plugins.values():
            plugin = plugin_data.get("instance")

            if plugin is not None:
                self.register_plugin(plugin)

        for service_data in services.values():
            service = service_data.get("instance")

            if service is not None:
                self.register_service(service)

        return True

    def health_check(self):
        self.add_timeline_event("HEALTH_CHECK_STARTED")

        if self.registry is not None:
            self.register_from_registry()

        results = {}

        with self.lock:
            components_snapshot = list(self.components.items())

        for component_id, component_data in components_snapshot:
            component = component_data["instance"]
            component_type = component_data["type"]

            health_data = self.check_component(
                component=component,
                component_id=component_id,
                component_type=component_type
            )

            results[component_id] = health_data

        summary = self.build_summary(results)

        with self.lock:
            self.history.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "summary": summary,
                    "results": results
                }
            )

            self.check_count += 1
            self.components_checked += len(results)
            self.last_check_at = datetime.now(UTC).isoformat()
            self.health = summary["average_health"]

            if summary["critical_count"] > 0:
                self.status = "WARNING"
            elif summary["offline_count"] > 0:
                self.status = "WARNING"
            else:
                self.status = "ONLINE"

            self.lifecycle["healthy"] = self.health > 0

        self.add_timeline_event(
            event_type="HEALTH_CHECK_COMPLETED",
            payload=summary
        )

        return {
            "summary": summary,
            "results": results
        }

    def check_component(
        self,
        component,
        component_id,
        component_type
    ):
        try:
            if hasattr(component, "health_check"):
                health_data = component.health_check()
            elif hasattr(component, "get_health"):
                health_data = component.get_health()
            else:
                health_data = {
                    "component_id": component_id,
                    "status": "UNKNOWN",
                    "health": 0,
                    "healthy": False,
                    "last_error": "No health method available"
                }

            normalized = self.normalize_health(
                health_data=health_data,
                component_id=component_id,
                component_type=component_type
            )

            severity = self.get_severity(
                normalized["health"],
                normalized["status"]
            )

            normalized["severity"] = severity

            self.handle_severity(
                component_id=component_id,
                severity=severity,
                health_data=normalized
            )

            with self.lock:
                if component_id in self.components:
                    self.components[component_id]["last_health"] = normalized

            return normalized

        except Exception as error:
            with self.lock:
                self.errors_detected += 1
                self.last_error = str(error)

            error_health = {
                "component_id": component_id,
                "component_type": component_type,
                "status": "ERROR",
                "health": 0,
                "healthy": False,
                "last_error": str(error),
                "severity": "CRITICAL",
                "checked_at": datetime.now(UTC).isoformat()
            }

            self.handle_severity(
                component_id=component_id,
                severity="CRITICAL",
                health_data=error_health
            )

            return error_health

    def normalize_health(
        self,
        health_data,
        component_id,
        component_type
    ):
        if health_data is None:
            health_data = {}

        health_value = health_data.get("health", 0)

        try:
            health_value = int(health_value)
        except Exception:
            health_value = 0

        health_value = max(0, min(100, health_value))

        return {
            "component_id": health_data.get(
                "component_id",
                health_data.get(
                    "manager_id",
                    health_data.get("engine_id", component_id)
                )
            ),
            "component_type": component_type,
            "status": health_data.get("status", "UNKNOWN"),
            "health": health_value,
            "healthy": health_data.get("healthy", health_value > 0),
            "last_error": health_data.get("last_error"),
            "checked_at": datetime.now(UTC).isoformat()
        }

    def get_severity(self, health_value, status):
        if status in ["OFFLINE", "ERROR"]:
            return "OFFLINE"

        if health_value <= self.HEALTH_OFFLINE:
            return "OFFLINE"

        if health_value < self.HEALTH_CRITICAL:
            return "CRITICAL"

        if health_value < self.HEALTH_WARNING:
            return "WARNING"

        return "INFO"

    def handle_severity(
        self,
        component_id,
        severity,
        health_data
    ):
        with self.lock:
            if severity == "WARNING":
                self.warnings_created += 1
                self.last_warning_at = datetime.now(UTC).isoformat()
            elif severity == "CRITICAL":
                self.criticals_created += 1
                self.last_critical_at = datetime.now(UTC).isoformat()
            elif severity == "OFFLINE":
                self.offline_detected += 1

        if severity in ["WARNING", "CRITICAL", "OFFLINE"]:
            self.add_timeline_event(
                event_type=f"HEALTH_{severity}",
                payload={
                    "component_id": component_id,
                    "health": health_data
                }
            )

            self._emit_event(
                event_type=f"HEALTH_{severity}",
                payload={
                    "component_id": component_id,
                    "health": health_data
                },
                severity=severity
            )

        return True

    def build_summary(self, results):
        total = len(results)

        if total == 0:
            return {
                "total_components": 0,
                "online_count": 0,
                "warning_count": 0,
                "critical_count": 0,
                "offline_count": 0,
                "average_health": 100
            }

        online_count = 0
        warning_count = 0
        critical_count = 0
        offline_count = 0
        health_sum = 0

        for health_data in results.values():
            severity = health_data.get("severity", "INFO")
            health_sum += health_data.get("health", 0)

            if severity == "INFO":
                online_count += 1
            elif severity == "WARNING":
                warning_count += 1
            elif severity == "CRITICAL":
                critical_count += 1
            elif severity == "OFFLINE":
                offline_count += 1

        return {
            "total_components": total,
            "online_count": online_count,
            "warning_count": warning_count,
            "critical_count": critical_count,
            "offline_count": offline_count,
            "average_health": round(health_sum / total, 2)
        }

    def get_latest_report(self):
        with self.lock:
            if not self.history:
                return None

            return deepcopy(self.history[-1])

    def get_history(self, limit=None):
        with self.lock:
            if limit is None:
                return deepcopy(self.history)

            return deepcopy(self.history[-limit:])

    def clear_history(self):
        with self.lock:
            self.history = []

        return True

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
                    "payload": payload,
                    "timestamp": datetime.now(UTC).isoformat()
                }
            )

        return True

    def get_manifest(self):
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "mission": self.mission,
            "capabilities": self.capabilities
        }

    def get_statistics(self):
        with self.lock:
            return {
                "registered_components": len(self.components),
                "history_count": len(self.history),
                "timeline_count": len(self.timeline),
                "check_count": self.check_count,
                "components_checked": self.components_checked,
                "warnings_created": self.warnings_created,
                "criticals_created": self.criticals_created,
                "offline_detected": self.offline_detected,
                "errors_detected": self.errors_detected,
                "last_check_at": self.last_check_at,
                "last_warning_at": self.last_warning_at,
                "last_critical_at": self.last_critical_at
            }

    def get_status(self):
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health,
            "lifecycle": deepcopy(self.lifecycle),
            "statistics": self.get_statistics(),
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

    def _get_component_id(self, component):
        if hasattr(component, "component_id"):
            return component.component_id

        if hasattr(component, "manager_id"):
            return component.manager_id

        if hasattr(component, "engine_id"):
            return component.engine_id

        return None

    def _emit_event(
        self,
        event_type,
        payload,
        severity="INFO"
    ):
        if self.event_bus is not None:
            self.event_bus.publish(
                event_type=event_type,
                payload=payload,
                source=self.component_id,
                severity=severity
            )

        if self.logger is not None:
            self.logger.info(
                message=event_type,
                source=self.component_id,
                payload=payload
            )

        return True


if __name__ == "__main__":
    from core.base_manager import BaseManager
    from core.base_engine import BaseEngine

    health_monitor = HealthMonitor()
    manager = BaseManager()
    engine = BaseEngine()

    health_monitor.initialize()
    health_monitor.start()

    manager.initialize()
    manager.register_engine(engine)
    manager.start()

    health_monitor.register_manager(manager)
    health_monitor.register_engine(engine)

    report = health_monitor.health_check()

    print("=== HEALTH MONITOR TEST ===")
    print()
    print("Report:")
    print(report)

    print()
    print("Status:")
    print(
        health_monitor.get_status()
    )