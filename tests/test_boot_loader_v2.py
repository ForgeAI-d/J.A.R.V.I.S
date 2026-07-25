from core.boot_loader import BootLoader
from core.common import BaseKernelComponent
from core.dependency_resolver import DependencyResolver


def test_dependency_resolver_is_kas_component():
    assert issubclass(DependencyResolver, BaseKernelComponent)
    resolver = DependencyResolver()
    manifest = resolver.get_manifest()
    assert manifest["component_id"] == "core.dependency_resolver"
    assert all(callable(getattr(resolver, name)) for name in ("initialize", "start", "stop", "validate", "get_statistics", "get_status"))


def test_boot_loader_package_and_manifest():
    loader = BootLoader(search_packages=(), include_core_components=False)
    assert loader.get_manifest()["component_id"] == "core.boot_loader"
    assert loader.boot_mode in loader.VALID_BOOT_MODES


def test_boot_loader_empty_boot_and_shutdown():
    loader = BootLoader(search_packages=(), include_core_components=False)
    result = loader.boot(print_report=False)
    assert result["success"] is True
    assert result["report"]["ready"] is True
    assert loader.shutdown()["success"] is True


def test_boot_loader_starts_unified_core():
    loader = BootLoader(search_packages=(), include_core_components=True)
    result = loader.boot(print_report=False)
    assert result["success"] is True
    assert "core.dependency_resolver" in result["report"]["boot_order"]
    assert "core.module_manager" in result["report"]["boot_order"]
    assert loader.shutdown()["success"] is True
