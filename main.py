from __future__ import annotations

import argparse
import json
import signal
from typing import Any

from core.developer_console import DeveloperConsole
from core.kernel_runtime import KernelRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Kernel Runtime")
    parser.add_argument("--report", action="store_true", help="Print the boot report")
    parser.add_argument("--status", action="store_true", help="Print developer status and exit")
    parser.add_argument("--json", action="store_true", help="Use JSON for --status output")
    parser.add_argument("--no-app-components", action="store_true", help="Boot core components only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = KernelRuntime(
        search_packages=() if args.no_app_components else None,
        include_core_components=True,
    )

    def request_shutdown(signum: int, frame: Any) -> None:
        del signum, frame
        runtime.shutdown()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    result = runtime.boot(print_report=args.report)
    if not result.get("success"):
        return 1

    if args.status:
        console = DeveloperConsole(runtime)
        if args.json:
            print(json.dumps(console.snapshot(), indent=2, ensure_ascii=False))
        else:
            console.print()
        runtime.shutdown()
        return 0

    try:
        runtime.run()
    finally:
        if runtime.status != "STOPPED":
            runtime.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
