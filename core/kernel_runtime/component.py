from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import Event, RLock
from time import monotonic
from typing import Any

from core.boot_loader import BootLoader
from core.common import BaseKernelComponent
from core.kernel_context import KernelContext


class KernelRuntime(BaseKernelComponent):
    """Single public entry point for the J.A.R.V.I.S. kernel.

    Applications interact with this class instead of coordinating BootLoader,
    KernelContext and individual components directly.
    """

    COMPONENT_ID = "core.kernel_runtime"
    NAME = "Kernel Runtime"
    VERSION = "1.0.0"
    PRIORITY = 0
    AUTO_START = False
    CAPABILITIES = (
        "kernel_boot",
        "kernel_shutdown",
        "kernel_restart",
        "kernel_pause",
        "kernel_resume",
        "kernel_run_loop",
        "runtime_report",
    )

    TERMINAL_STATES = frozenset({"STOPPED", "ERROR"})

    def __init__(
        self,
        context: KernelContext | None = None,
        boot_loader: BootLoader | None = None,
        **boot_loader_kwargs: Any,
    ) -> None:
        super().__init__(context=context or KernelContext(kernel_version=self.VERSION))
        self.boot_loader = boot_loader or BootLoader(
            context=self.context,
            **boot_loader_kwargs,
        )
        self._runtime_lock = RLock()
        self._stop_event = Event()
        self.boot_result: dict[str, Any] | None = None
        self.booted_at: str | None = None
        self.shutdown_at: str | None = None
        self.paused_at: str | None = None
        self.resumed_at: str | None = None
        self._started_monotonic: float | None = None
        self.status = "CREATED"
        self.health = 0
        self.context.set_shared("kernel_runtime", self)

    def boot(self, print_report: bool = False) -> dict[str, Any]:
        with self._runtime_lock:
            if self.status in {"RUNNING", "PAUSED"} and self.boot_result:
                return deepcopy(self.boot_result)

            self._stop_event.clear()
            self.status = "BOOTING"
            self.context.begin_boot()
            self.boot_result = self.boot_loader.boot(print_report=print_report)
            success = bool(self.boot_result.get("success"))

            if success:
                self.status = "RUNNING"
                self.health = 100
                self.booted_at = datetime.now(UTC).isoformat()
                self._started_monotonic = monotonic()
                self.context.complete_boot()
                self.context.mark_ready()
            else:
                self.status = "ERROR"
                self.health = 0
                self.context.set_error("Kernel boot failed")

            return deepcopy(self.boot_result)

    def shutdown(self) -> dict[str, Any]:
        with self._runtime_lock:
            if self.status == "STOPPED":
                return {"success": True, "stopped": 0, "failures": [], "already_stopped": True}

            self.status = "SHUTTING_DOWN"
            self.context.begin_shutdown()
            result = self.boot_loader.shutdown()
            success = bool(result.get("success"))
            self.status = "STOPPED" if success else "ERROR"
            self.health = 0
            self.shutdown_at = datetime.now(UTC).isoformat()
            self._stop_event.set()
            self.context.complete_shutdown()
            return deepcopy(result)

    def restart(self, print_report: bool = False) -> dict[str, Any]:
        shutdown_result = self.shutdown()
        if not shutdown_result.get("success"):
            return {"success": False, "shutdown": shutdown_result, "boot": None}
        boot_result = self.boot(print_report=print_report)
        return {
            "success": bool(boot_result.get("success")),
            "shutdown": shutdown_result,
            "boot": boot_result,
        }

    def pause(self) -> bool:
        with self._runtime_lock:
            if self.status != "RUNNING":
                return False
            failures: list[str] = []
            for component_id in reversed(self.boot_loader.boot_order):
                component = self.boot_loader.get_component_by_id(component_id)
                pause = getattr(component, "pause", None)
                if callable(pause) and pause() is False:
                    failures.append(component_id)
            if failures:
                self.status = "DEGRADED"
                self.health = 50
                return False
            self.status = "PAUSED"
            self.paused_at = datetime.now(UTC).isoformat()
            self.context.set_state("DEGRADED", reason="runtime_paused")
            return True

    def resume(self) -> bool:
        with self._runtime_lock:
            if self.status != "PAUSED":
                return False
            failures: list[str] = []
            for component_id in self.boot_loader.boot_order:
                component = self.boot_loader.get_component_by_id(component_id)
                resume = getattr(component, "resume", None)
                if callable(resume) and resume() is False:
                    failures.append(component_id)
            if failures:
                self.status = "DEGRADED"
                self.health = 50
                return False
            self.status = "RUNNING"
            self.health = 100
            self.resumed_at = datetime.now(UTC).isoformat()
            self.context.set_state("READY")
            return True

    def run(self, poll_interval: float = 0.25) -> None:
        """Block until :meth:`shutdown` is called.

        This deliberately contains no application logic. It is only the stable
        process-lifetime loop used by command-line entry points and services.
        """
        if self.status not in {"RUNNING", "PAUSED"}:
            result = self.boot(print_report=False)
            if not result.get("success"):
                raise RuntimeError("Kernel could not enter the run loop because boot failed")
        while not self._stop_event.wait(max(0.01, float(poll_interval))):
            continue

    def get_uptime(self) -> float:
        if self._started_monotonic is None or self.status in self.TERMINAL_STATES:
            return 0.0
        return max(0.0, monotonic() - self._started_monotonic)

    def get_status(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "version": self.version,
            "status": self.status,
            "health": self.health,
            "ready": self.status in {"RUNNING", "PAUSED"},
            "paused": self.status == "PAUSED",
            "uptime_seconds": self.get_uptime(),
        }

    def get_runtime_report(self) -> dict[str, Any]:
        return {
            **self.get_status(),
            "booted_at": self.booted_at,
            "shutdown_at": self.shutdown_at,
            "paused_at": self.paused_at,
            "resumed_at": self.resumed_at,
            "context": self.context.report(),
            "boot": self.boot_loader.get_boot_report(),
        }

    def report(self) -> dict[str, Any]:
        return self.get_runtime_report()

    def __enter__(self) -> "KernelRuntime":
        result = self.boot(print_report=False)
        if not result.get("success"):
            raise RuntimeError("Kernel boot failed")
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.shutdown()
