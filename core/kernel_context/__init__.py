"""KernelContext package public API.

The package preserves the frozen v1 import surface while separating the
implementation into focused components.
"""

from .context_scope import ContextScope
from .diagnostic_result import DiagnosticResult
from .diagnostics_manager import DiagnosticsManager
from .kernel_context import KernelContext
from .resource_manager import ResourceManager

__all__ = [
    "ContextScope",
    "DiagnosticResult",
    "DiagnosticsManager",
    "KernelContext",
    "ResourceManager",
]

from .service_registry import KernelServiceRegistry
from .data_store import KernelDataStore
