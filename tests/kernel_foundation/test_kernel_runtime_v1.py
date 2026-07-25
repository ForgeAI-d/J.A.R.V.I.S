from core.base_manager import BaseManager
from core.base_engine import BaseEngine
from core.kernel_context import KernelContext
from core.component_registry import ComponentRegistry
from core.discovery_engine import DiscoveryEngine
from core.kernel_runtime import KernelRuntime

class DemoManager(BaseManager):
    COMPONENT_ID=MANAGER_ID="test.demo_manager"; NAME="Demo Manager"

def test_base_packages_and_context_contract():
    assert BaseManager.__module__.startswith("core.base_manager")
    assert BaseEngine.__module__.startswith("core.base_engine")
    assert KernelContext().validate_api_contract()["valid"]

def test_component_registry():
    registry=ComponentRegistry(); component=DemoManager()
    assert registry.register_component(component)
    assert registry.get(component.component_id) is component
    assert component.component_id in registry.list_managers()

def test_discovery_engine_finds_core_package_components():
    result=DiscoveryEngine().discover(["core.config_manager"])
    ids={getattr(cls,"COMPONENT_ID",None) for cls,_ in result["components"]}
    assert "core.config_manager" in ids

def test_kernel_runtime_surface():
    runtime=KernelRuntime(search_packages=(), include_core_components=False)
    assert callable(runtime.boot) and callable(runtime.shutdown) and callable(runtime.restart)
