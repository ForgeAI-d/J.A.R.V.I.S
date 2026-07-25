from __future__ import annotations

import json
from typing import Any, TextIO
import sys

from core.kernel_runtime import KernelRuntime


class DeveloperConsole:
    """Read-only text diagnostics for development and operations."""

    def __init__(self, runtime: KernelRuntime, stream: TextIO | None = None) -> None:
        self.runtime = runtime
        self.stream = stream or sys.stdout

    @staticmethod
    def _component_health(component: Any) -> tuple[str, int]:
        status = str(getattr(component, "status", "UNKNOWN"))
        health = int(getattr(component, "health", 0) or 0)
        return status, health

    def snapshot(self) -> dict[str, Any]:
        registry = self.runtime.boot_loader.registry
        components = []
        for component_id in sorted(registry.list_components()):
            component = registry.get(component_id)
            status, health = self._component_health(component)
            components.append(
                {
                    "component_id": component_id,
                    "name": getattr(component, "name", component_id),
                    "status": status,
                    "health": health,
                }
            )
        return {
            "kernel": self.runtime.get_status(),
            "components": components,
            "boot_order": list(self.runtime.boot_loader.boot_order),
            "errors": list(self.runtime.boot_loader.errors),
            "warnings": list(self.runtime.boot_loader.warnings),
        }

    def render(self) -> str:
        data = self.snapshot()
        kernel = data["kernel"]
        lines = [
            "J.A.R.V.I.S. Developer Console",
            "=" * 34,
            f"Kernel : {kernel['status']}",
            f"Health : {kernel['health']}%",
            f"Uptime : {kernel['uptime_seconds']:.2f}s",
            "",
            "Components",
            "----------",
        ]
        if not data["components"]:
            lines.append("(none)")
        for item in data["components"]:
            lines.append(
                f"{item['component_id']:<34} {item['status']:<12} {item['health']:>3}%"
            )
        if data["errors"]:
            lines.extend(("", "Errors", "------"))
            lines.extend(json.dumps(item, ensure_ascii=False) for item in data["errors"])
        return "\n".join(lines)

    def print(self) -> str:
        output = self.render()
        print(output, file=self.stream)
        return output
