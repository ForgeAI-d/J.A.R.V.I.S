from __future__ import annotations

from core.kernel_runtime import KernelRuntime


def test_policy_manager_is_discovered_and_started() -> None:
    runtime = KernelRuntime(search_packages=("policy",), include_core_components=True)
    result = runtime.boot(print_report=False)
    try:
        assert result["success"] is True
        policy = runtime.boot_loader.get_component_by_id("policy.policy_manager")
        assert policy is not None
        assert policy.status == "ONLINE"
        assert policy.health_check()["healthy"] is True
    finally:
        runtime.shutdown()
