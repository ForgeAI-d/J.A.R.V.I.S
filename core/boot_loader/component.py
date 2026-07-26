
from __future__ import annotations

import importlib
import inspect
import json
import os
import pkgutil
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

from core.base_engine import BaseEngine
from core.base_manager import BaseManager
from core.common import BaseKernelComponent
from core.dependency_resolver import DependencyResolver
from core.kernel_context import KernelContext
from core.component_registry import ComponentRegistry
from core.discovery_engine import DiscoveryEngine
from core.lifecycle_manager import LifecycleManager
from core.recovery_manager import RecoveryManager

from .transaction import BootTransaction
from .validator import validate_component


class BootLoader(BaseKernelComponent):
    """KAS v1 kernel runtime coordinator.

    Discovery, validation, dependency resolution, lifecycle startup and
    reverse-order shutdown are deliberately separated into explicit stages.
    Existing imports (``from core.boot_loader import BootLoader``) remain valid.
    """

    COMPONENT_ID = "core.boot_loader"
    NAME = "BootLoader"
    VERSION = "1.0.0"
    MISSION = "Discover, validate and start the J.A.R.V.I.S. kernel deterministically."
    PRIORITY = 0
    AUTO_START = False
    REQUIRES: tuple[str, ...] = ()
    OPTIONAL = ("core.event_bus", "core.logger")
    CAPABILITIES = (
        "component_discovery", "manifest_validation", "dependency_resolution",
        "context_injection", "ordered_startup", "reverse_shutdown", "boot_reporting",
    )
    VALID_BOOT_MODES = ("development", "testing", "production")
    CORE_COMPONENTS = ()
    CORE_SEARCH_PACKAGES = (
        "core.config_manager", "core.logger", "core.event_bus", "core.state_manager",
        "core.task_manager", "core.health_monitor", "core.module_manager",
    )
    DEFAULT_SEARCH_PACKAGES = (
        # Infrastructure services must be discovered before application managers
        # so constructor injection can resolve dependencies deterministically.
        "database",
        "vision", "voice", "security", "automation", "learning", "plugins",
        "identity", "memory", "communication", "devices", "events", "permissions",
    )

    def __init__(
        self,
        context: KernelContext | None = None,
        registry: ComponentRegistry | None = None,
        dependency_resolver: DependencyResolver | None = None,
        search_packages: Iterable[str] | None = None,
        include_core_components: bool = True,
    ) -> None:
        super().__init__(context=context or KernelContext())
        self.boot_mode = self.load_boot_mode()
        self.development_mode = self.boot_mode == "development"
        self.testing_mode = self.boot_mode == "testing"
        self.production_mode = self.boot_mode == "production"
        self.registry = registry or ComponentRegistry(context=self.context)
        self.discovery_engine = DiscoveryEngine(context=self.context)
        self.lifecycle_manager = LifecycleManager(context=self.context)
        self.recovery_manager = RecoveryManager(context=self.context)
        self.dependency_resolver = dependency_resolver or DependencyResolver(context=self.context)
        self.search_packages = tuple(self.DEFAULT_SEARCH_PACKAGES if search_packages is None else search_packages)
        self.include_core_components = include_core_components
        self.components: dict[str, Any] = {}
        self.managers: dict[str, Any] = {}
        self.engines: dict[str, Any] = {}
        self.boot_order: list[str] = []
        self.shutdown_order: list[str] = []
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.discovery_log: list[dict[str, Any]] = []
        self.transaction = BootTransaction()
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.ready = False
        self._boot_statistics = {
            "discovered": 0, "validated": 0, "initialized": 0, "started": 0,
            "stopped": 0, "failed": 0, "boot_time_seconds": 0.0,
        }
        self._bind_kernel_services()

    def _bind_kernel_services(self) -> None:
        self.set_context(self.context)
        self._context_register("boot_loader", self)
        self._context_register("registry", self.registry)
        self._context_register("registry_manager", self.registry)
        self._context_register("dependency_resolver", self.dependency_resolver)
        self.attach_context(self.registry)
        self.attach_context(self.dependency_resolver)

    def _context_register(self, name: str, value: Any) -> bool:
        for method_name in ("register", "register_service"):
            method = getattr(self.context, method_name, None)
            if not callable(method):
                continue
            try:
                result = method(name, value)
                return bool(result is not False)
            except TypeError:
                try:
                    result = method(name, value, replace=True)
                    return bool(result is not False)
                except Exception:
                    continue
            except Exception:
                continue
        try:
            setattr(self.context, name, value)
            return True
        except Exception:
            return False

    def load_boot_mode(self) -> str:
        env_mode = os.getenv("JARVIS_BOOT_MODE", "").strip().lower()
        if env_mode in self.VALID_BOOT_MODES:
            return env_mode
        candidates = (Path("config/boot.json"), Path(__file__).resolve().parents[2] / "config/boot.json")
        for path in candidates:
            if not path.exists():
                continue
            try:
                value = str(json.loads(path.read_text(encoding="utf-8")).get("boot_mode", "development")).lower()
                if value in self.VALID_BOOT_MODES:
                    return value
            except (OSError, ValueError, TypeError):
                pass
        return "development"

    def _record_error(self, stage: str, target: str, error: BaseException | str, critical: bool = False) -> None:
        item = {"stage": stage, "target": target, "error": str(error), "critical": critical}
        self.errors.append(item)
        self._boot_statistics["failed"] += 1
        self.add_timeline_event("BOOT_STAGE_ERROR", item)

    @staticmethod
    def _load_symbol(spec: str) -> type:
        module_name, symbol = spec.split(":", 1)
        return getattr(importlib.import_module(module_name), symbol)

    def discover_modules(self) -> list[str]:
        self.add_timeline_event("DISCOVERY_STARTED")
        packages = list(self.search_packages)
        if self.include_core_components:
            packages = list(self.CORE_SEARCH_PACKAGES) + packages
        result = self.discovery_engine.discover(packages)
        for error in result["errors"]:
            self._record_error("module_import", error["module"], error["error"])
        for component_class, source in result["components"]:
            self.create_component(component_class, source=source)
        self._boot_statistics["discovered"] = len(self.components)
        self.add_timeline_event("DISCOVERY_FINISHED", {"component_count": len(self.components)})
        return list(self.components)

    def inspect_module(self, module: Any) -> None:
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls in {BaseManager, BaseEngine, BaseKernelComponent, BootLoader}:
                continue
            if cls.__module__ != module.__name__:
                continue
            try:
                if issubclass(cls, (BaseManager, BaseEngine)):
                    self.create_component(cls, source=module.__name__)
            except TypeError:
                continue

    def create_component(self, component_class: type, source: str | None = None) -> Any | None:
        component_id = getattr(component_class, "COMPONENT_ID", None) or getattr(component_class, "MANAGER_ID", None) or getattr(component_class, "ENGINE_ID", None)
        if component_id in self.components:
            return self.components[component_id]
        try:
            instance = component_class(**self.build_constructor_kwargs(component_class))
            self.attach_context(instance)
            return self.register_component(instance, source=source)
        except Exception as exc:
            self._record_error("instantiation", component_class.__name__, exc)
            return None

    def register_component(self, component: Any, source: str | None = None) -> Any:
        component_id = getattr(component, "component_id", None) or getattr(component, "manager_id", None) or getattr(component, "engine_id", None)
        if not component_id:
            raise ValueError("Component has no canonical identifier")
        if component_id in {self.component_id, self.dependency_resolver.component_id}:
            return component
        validation = validate_component(component)
        if not validation["valid"]:
            raise ValueError(f"Invalid component {component_id}: {validation}")
        self._boot_statistics["validated"] += 1
        self.components[component_id] = component
        self.registry.register_component(component, replace=True, source=source)
        if isinstance(component, BaseManager):
            self.managers[component_id] = component
        elif isinstance(component, BaseEngine):
            self.engines[component_id] = component
        self.discovery_log.append({"component_id": component_id, "source": source, "class": component.__class__.__name__})
        self.add_timeline_event("COMPONENT_DISCOVERED", {"component_id": component_id})
        return component

    def attach_context(self, component: Any) -> bool:
        try:
            setter = getattr(component, "set_context", None) or getattr(component, "bind_context", None)
            if callable(setter):
                return bool(setter(self.context))
            component.context = self.context
            return True
        except Exception as exc:
            self._record_error("context_injection", component.__class__.__name__, exc)
            return False

    def build_constructor_kwargs(self, target_class: type) -> dict[str, Any]:
        available = {
            "context": self.context, "registry": self.registry, "registry_manager": self.registry,
            "dependency_resolver": self.dependency_resolver,
        }
        for component in self.components.values():
            name = component.__class__.__name__
            snake = "".join(("_" + c.lower()) if c.isupper() else c for c in name).lstrip("_")
            available[snake] = component
            if snake.endswith("_manager"):
                available[snake] = component
            if name == "JarvisLogger": available["logger"] = component
            if name == "ConfigManager": available["config"] = component
        kwargs = {}
        signature = inspect.signature(target_class.__init__)
        for name, parameter in signature.parameters.items():
            if name == "self" or parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                continue
            if name in available:
                kwargs[name] = available[name]
        return kwargs

    def register_engines(self) -> None:
        for engine in self.engines.values():
            manager = self.find_manager_for_engine(engine)
            if manager is None:
                self.warnings.append({"engine": engine.component_id, "warning": "No matching manager"})
                continue
            if manager.register_engine(engine):
                self.registry.register_component(engine, replace=True)

    def find_manager_for_engine(self, engine: Any) -> Any | None:
        requested = str(getattr(engine, "manager", "") or getattr(engine, "MANAGER", "")).lower().replace(" ", "")
        for manager in self.managers.values():
            options = {manager.name.lower().replace(" ", ""), manager.manager_id.lower().replace(".", ""), manager.__class__.__name__.lower()}
            if requested in options or any(option in requested for option in options if option):
                return manager
        return None

    def prepare_dependency_resolver(self) -> list[str]:
        self.dependency_resolver.initialize(); self.dependency_resolver.start()
        runtime_components = [self.dependency_resolver, self.registry, *self.components.values()]
        for component in runtime_components:
            self.dependency_resolver.register_component(component, priority=int(getattr(component, "priority", 100)), replace=True)
        registered = {item["component_id"] for item in self.dependency_resolver.list_components()}
        for component in runtime_components:
            cid = component.component_id
            manifest = component.get_manifest()
            required = list(manifest.get("requires", []) or getattr(component, "REQUIRES", ()))
            optional = list(manifest.get("optional", []) or getattr(component, "OPTIONAL", ()))
            if isinstance(component, BaseEngine):
                manager = self.find_manager_for_engine(component)
                if manager is not None and manager.component_id not in required:
                    required.append(manager.component_id)
            for dependency in required:
                if dependency == "core.kernel_context":
                    # KernelContext is an intrinsic runtime container, not a bootable graph node.
                    continue
                if dependency in registered and dependency != cid:
                    self.dependency_resolver.add_dependency(cid, dependency, "required", replace=True)
                else:
                    self._record_error("dependency", cid, f"Missing required dependency: {dependency}", critical=True)
            for dependency in optional:
                if dependency in registered and dependency != cid:
                    self.dependency_resolver.add_dependency(cid, dependency, "optional", replace=True)
        report = self.dependency_resolver.resolve(force=True)
        if not report.get("valid"):
            raise RuntimeError(report.get("summary", "Dependency resolution failed"))
        details = report.get("details", {})
        self.boot_order = list(details.get("boot_order", []))
        self.shutdown_order = list(details.get("shutdown_order", reversed(self.boot_order)))
        self.add_timeline_event("DEPENDENCIES_RESOLVED", {"boot_order": self.boot_order})
        return self.boot_order

    def get_component_by_id(self, component_id: str) -> Any | None:
        if component_id == self.registry.component_id: return self.registry
        if component_id == self.dependency_resolver.component_id: return self.dependency_resolver
        return self.components.get(component_id)

    def initialize_by_dependency_order(self) -> bool:
        ok = True
        for cid in self.boot_order:
            component = self.get_component_by_id(cid)
            if component is None: continue
            try:
                result = component.initialize()
                if result is False: raise RuntimeError("initialize() returned False")
                self.transaction.initialized.append(cid); self._boot_statistics["initialized"] += 1
            except Exception as exc:
                ok = False; self._record_error("initialize", cid, exc, critical=True)
                if self.production_mode: break
        return ok

    def start_by_dependency_order(self) -> bool:
        ok = True
        for cid in self.boot_order:
            component = self.get_component_by_id(cid)
            if component is None or not getattr(component, "auto_start", True): continue
            try:
                result = component.start()
                if result is False: raise RuntimeError("start() returned False")
                self.transaction.started.append(cid); self._boot_statistics["started"] += 1
            except Exception as exc:
                ok = False; self._record_error("start", cid, exc, critical=True)
                if self.production_mode: break
        return ok

    def shutdown(self) -> dict[str, Any]:
        failures = []
        order = self.shutdown_order or list(reversed(self.transaction.started))
        for cid in order:
            component = self.get_component_by_id(cid)
            if component is None or cid == self.dependency_resolver.component_id: continue
            try:
                if component.stop() is False: raise RuntimeError("stop() returned False")
                self._boot_statistics["stopped"] += 1
            except Exception as exc:
                failures.append(cid); self._record_error("shutdown", cid, exc)
        self.dependency_resolver.stop()
        self.ready = False
        return {"success": not failures, "stopped": self._boot_statistics["stopped"], "failures": failures}

    def health_check(self) -> dict[str, Any]:
        entries = {}
        for cid in self.boot_order:
            component = self.get_component_by_id(cid)
            if component is None: continue
            getter = getattr(component, "get_health", None) or getattr(component, "health_check", None)
            try: entries[cid] = getter() if callable(getter) else {"health": getattr(component, "health", 0)}
            except Exception as exc: entries[cid] = {"healthy": False, "error": str(exc)}
        healthy = sum(1 for item in entries.values() if item.get("healthy", item.get("health", 0) > 0))
        return {"healthy": healthy == len(entries), "healthy_components": healthy, "component_count": len(entries), "components": entries}

    def _build_boot_report(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id, "version": self.version, "boot_mode": self.boot_mode,
            "started_at": self.started_at, "finished_at": self.finished_at, "ready": self.ready,
            "boot_order": list(self.boot_order), "shutdown_order": list(self.shutdown_order),
            "statistics": deepcopy(self._boot_statistics), "discovery": deepcopy(self.discovery_log),
            "errors": deepcopy(self.errors), "warnings": deepcopy(self.warnings), "health": self.health_check(),
            "dependency_resolver": self.dependency_resolver.get_status(),
        }

    def get_boot_report(self) -> dict[str, Any]:
        return self._build_boot_report()

    def print_boot_report(self) -> None:
        report = self._build_boot_report(); stats = report["statistics"]
        print("\n==========================================")
        print("        J.A.R.V.I.S. BOOT REPORT")
        print("==========================================")
        print(f"Mode: {report['boot_mode']} | Ready: {report['ready']}")
        print(f"Components: {stats['discovered']} | Started: {stats['started']} | Errors: {len(report['errors'])}")
        print(f"Boot time: {stats['boot_time_seconds']:.3f}s")
        for index, cid in enumerate(report["boot_order"], 1): print(f"  {index:02d}. {cid}")
        print("==========================================\n")

    def boot(self, print_report: bool = True) -> dict[str, Any]:
        self.started_at = datetime.now(UTC).isoformat(); started = perf_counter()
        self.errors.clear(); self.warnings.clear(); self.ready = False
        self.add_timeline_event("BOOT_STARTED", {"mode": self.boot_mode})
        try:
            self.discover_modules(); self.register_engines(); self.prepare_dependency_resolver()
            initialized = self.initialize_by_dependency_order()
            started_ok = initialized and self.start_by_dependency_order()
            self.ready = initialized and started_ok and not any(item.get("critical") for item in self.errors)
        except Exception as exc:
            self._record_error("boot", self.component_id, exc, critical=True)
            self.ready = False
            if self.production_mode: self.shutdown()
        self.finished_at = datetime.now(UTC).isoformat()
        self._boot_statistics["boot_time_seconds"] = perf_counter() - started
        self.status = "RUNNING" if self.ready else "ERROR"
        self.health = 100 if self.ready else 0
        if print_report: self.print_boot_report()
        return {"success": self.ready, "boot_time_seconds": self._boot_statistics["boot_time_seconds"], "report": self._build_boot_report()}
