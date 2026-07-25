from importlib import import_module
from pathlib import Path

COMPONENTS = {
    "config_manager": "ConfigManager",
    "task_manager": "TaskManager",
    "health_monitor": "HealthMonitor",
    "module_manager": "ModuleManager",
    "registry_manager": "RegistryManager",
    "state_manager": "StateManager",
    "event_bus": "EventBus",
    "logger": "JarvisLogger",
}

REQUIRED_FILES = {
    "__init__.py",
    "component.py",
    "manifest.py",
    "validator.py",
    "report.py",
    "statistics.py",
    "observer.py",
    "transaction.py",
    "events.py",
}


def test_all_kernel_components_use_the_same_package_layout():
    core = Path(__file__).parents[1] / "core"
    for package in COMPONENTS:
        files = {item.name for item in (core / package).iterdir() if item.is_file()}
        assert REQUIRED_FILES <= files


def test_legacy_public_imports_remain_compatible():
    for package, class_name in COMPONENTS.items():
        module = import_module(f"core.{package}")
        component_class = getattr(module, class_name)
        assert component_class.__name__ == class_name


def test_components_expose_kas_identity_and_lifecycle():
    constructors = {
        "config_manager": {"watcher_enabled": False},
        "logger": {"log_path": "/tmp/jarvis-kas-test-logs"},
    }
    for package, class_name in COMPONENTS.items():
        component_class = getattr(import_module(f"core.{package}"), class_name)
        instance = component_class(**constructors.get(package, {}))
        assert instance.component_id.startswith("core.")
        assert callable(instance.initialize)
        assert callable(instance.start)
        assert callable(instance.stop)
        assert callable(instance.get_manifest)
        assert callable(instance.get_status)
        assert callable(instance.get_statistics)
        assert callable(instance.get_health)
        assert callable(instance.validate)
        assert callable(instance.report)
