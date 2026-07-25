from __future__ import annotations
from pathlib import Path
import json, sys, tempfile

HERE = Path(__file__).resolve()
for parent in HERE.parents:
    if (parent / "core" / "dependency_resolver" / "__init__.py").exists():
        PROJECT_ROOT = parent
        break
else:
    raise RuntimeError("Projektwurzel mit core/dependency_resolver wurde nicht gefunden.")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.dependency_resolver import DependencyResolver


def build() -> DependencyResolver:
    r = DependencyResolver()
    assert r.initialize() and r.start()
    for cid, priority in (("config", 1), ("logger", 2), ("event_bus", 3), ("modules", 4), ("isolated", 5)):
        assert r.register_component(component_id=cid, name=cid, priority=priority)
    assert r.add_dependency("logger", "config")
    assert r.add_dependency("event_bus", "logger")
    assert r.add_dependency("modules", "event_bus")
    return r


def main() -> int:
    tests = []
    r = build()
    tests.append(("Version", r.VERSION == "0.4.0" and r.BUILD_STATUS == "PHASE_4"))
    tests.append(("Phase 2 resolve", r.get_boot_order(force=True)[:4] == ["config", "logger", "event_bus", "modules"]))
    tests.append(("Phase 3 analysis", r.analyze_graph()["maximum_depth"] == 3))
    inspection = r.inspect("config")
    tests.append(("Inspector", inspection["transitive_dependents"] == ["event_bus", "logger", "modules"] and inspection["critical"]))
    matrix = r.get_dependency_matrix()
    tests.append(("Matrix", matrix["values"][matrix["nodes"].index("logger")][matrix["nodes"].index("config")] == 1))
    metrics = r.get_metrics()
    tests.append(("Metrics", metrics["node_count"] == 5 and metrics["maximum_depth"] == 3 and "config" in metrics["critical_components"]))
    tree = r.visualize_graph("tree")
    tests.append(("Tree", "config\n└── logger" in tree and "modules" in tree))
    tests.append(("Compact", "logger -> config [required]" in r.visualize_graph("compact")))
    tests.append(("JSON", json.loads(r.export_json())["dependency_types"] == ["required"]))
    tests.append(("DOT", '"logger" -> "config"' in r.export_dot()))
    report = r.analysis_report()
    tests.append(("Report", report["summary"]["components"] == 5 and report["health"] == "WARNING"))
    tests.append(("Text report", "Dependency Resolver Analysis" in r.analysis_report(text=True)))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "graph.dot"
        r.export_dot(path=str(path))
        tests.append(("File export", path.exists() and path.read_text(encoding="utf-8").startswith("digraph")))
    stats = r.get_statistics()
    tests.append(("Statistics", stats["component_inspections"] >= 1 and stats["exports_created"] >= 3))
    timeline_types = {event["event_type"] for event in r.get_timeline()}
    tests.append(("Timeline", {"INSPECTION_CREATED", "GRAPH_VISUALIZED", "REPORT_CREATED", "EXPORT_CREATED"} <= timeline_types))

    failed = 0
    print("=== DEPENDENCY RESOLVER PHASE 4 REGRESSION ===")
    for name, passed in tests:
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
        failed += not passed
    print(f"RESULT: {len(tests)-failed}/{len(tests)} PASS")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
