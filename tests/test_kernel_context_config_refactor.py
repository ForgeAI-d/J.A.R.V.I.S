import os
from core.kernel_context import KernelContext, KernelServiceRegistry, KernelDataStore
from core.config_manager import ConfigManager, BootConfig

def test_kernel_context_delegates_mutable_ownership():
    context = KernelContext()
    assert isinstance(context.service_registry, KernelServiceRegistry)
    assert isinstance(context.data_store, KernelDataStore)
    service = object()
    assert context.register_service("example", service)
    assert context.service_registry.services["example"] is service
    assert context.set_flag("x", True)
    assert context.data_store.flags["x"] is True

def test_config_resolver_precedence_and_typed_model(tmp_path, monkeypatch):
    manager = ConfigManager(config_path=str(tmp_path / "config"), backup_path=str(tmp_path / "backup"), watcher_enabled=False)
    assert manager.initialize()
    monkeypatch.setenv("JARVIS_BOOT_SAFE_MODE", "true")
    assert manager.get_resolved("boot", "safe_mode") is True
    assert manager.set_runtime_override("boot", "safe_mode", False)
    assert manager.get_resolved("boot", "safe_mode") is False
    typed = manager.get_typed("boot")
    assert isinstance(typed, BootConfig)
    assert typed.safe_mode is False
    assert manager.get("boot", "safe_mode") is False  # persisted value is unchanged
