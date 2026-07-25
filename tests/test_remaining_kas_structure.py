from importlib import import_module
from pathlib import Path

COMPONENTS = {
    "assistant.command_manager": "CommandManager",
    "database.database_manager": "DatabaseManager",
    "devices.device_manager": "DeviceManager",
    "events.event_manager": "EventManager",
    "identity.identity_manager": "IdentityManager",
    "memory.memory_manager": "MemoryManager",
    "permissions.permission_manager": "PermissionManager",
    "vision.camera_manager": "CameraManager",
    "vision.face_manager": "FaceManager",
    "vision.vision_manager": "VisionManager",
    "core.jarvis_core": "JarvisCore",
}

REQUIRED_FILES = {
    "__init__.py", "component.py", "manifest.py", "validator.py",
    "report.py", "statistics.py", "observer.py", "transaction.py", "events.py"
}


def test_remaining_components_use_kas_packages():
    root = Path(__file__).resolve().parents[1]
    for module_name, class_name in COMPONENTS.items():
        package_path = root.joinpath(*module_name.split("."))
        assert package_path.is_dir(), module_name
        assert REQUIRED_FILES <= {p.name for p in package_path.iterdir()}, module_name
        if module_name.startswith("vision."):
            source = (package_path / "component.py").read_text(encoding="utf-8")
            assert f"class {class_name}" in source
            continue
        module = import_module(module_name)
        component_class = getattr(module, class_name)
        for name in ("get_manifest", "get_health", "get_status", "get_statistics", "report", "validate"):
            assert callable(getattr(component_class, name, None)), f"{module_name}.{name}"
