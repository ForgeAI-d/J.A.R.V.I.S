from __future__ import annotations

from io import StringIO

from core.developer_console import DeveloperConsole
from core.kernel_runtime import (
    KERNEL_API_STATUS,
    KERNEL_VERSION,
    KernelRuntime,
)


def create_minimal_runtime() -> KernelRuntime:
    return KernelRuntime(search_packages=(), include_core_components=False)


def test_kernel_version_is_frozen():
    assert KERNEL_VERSION == "1.0.0"
    assert KERNEL_API_STATUS == "FROZEN"


def test_runtime_end_to_end_boot_status_and_shutdown():
    runtime = create_minimal_runtime()
    boot = runtime.boot()
    assert boot["success"]
    assert runtime.get_status()["ready"]
    assert runtime.context.is_ready()

    shutdown = runtime.shutdown()
    assert shutdown["success"]
    assert runtime.status == "STOPPED"
    assert runtime.context.status == "OFFLINE"


def test_runtime_context_manager():
    runtime = create_minimal_runtime()
    with runtime as active:
        assert active.status == "RUNNING"
    assert runtime.status == "STOPPED"


def test_developer_console_is_read_only_and_renderable():
    runtime = create_minimal_runtime()
    assert runtime.boot()["success"]
    stream = StringIO()
    output = DeveloperConsole(runtime, stream=stream).print()
    assert "J.A.R.V.I.S. Developer Console" in output
    assert "Kernel : RUNNING" in output
    assert stream.getvalue().strip() == output
    runtime.shutdown()
