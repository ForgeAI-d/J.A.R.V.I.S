from core.kernel_context import (
    ContextScope,
    DiagnosticResult,
    DiagnosticsManager,
    KernelContext,
    ResourceManager,
)


def test_public_import_surface_is_preserved():
    assert KernelContext.VERSION == "1.0.0"
    assert ContextScope.VERSION == "1.0.0"
    assert ResourceManager.VERSION == "1.0.0"
    assert DiagnosticsManager.VERSION == "1.0.0"
    assert DiagnosticResult("x", True).to_dict()["passed"] is True


def test_frozen_public_api_is_available():
    context = KernelContext()
    missing = [name for name in context.PUBLIC_API if not hasattr(context, name)]
    assert missing == []


def test_context_core_behaviour_survives_package_migration():
    context = KernelContext()
    assert context.initialize() is True
    assert context.register_service("example", object()) is True
    assert context.has_service("example") is True
    assert context.set_flag("ready", True) is True
    assert context.get_flag("ready") is True
    assert context.set_runtime("answer", 42) is True
    assert context.get_runtime("answer") == 42
    report = context.report()
    assert report["manifest"]["component_id"] == "core.kernel_context"
