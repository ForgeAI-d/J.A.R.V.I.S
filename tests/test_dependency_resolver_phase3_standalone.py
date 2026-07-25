from dependency_resolver import DependencyResolver

def build():
    r = DependencyResolver()
    assert r.initialize()
    assert r.start()
    return r

def reg(r, cid, priority=100):
    assert r.register_component(component_id=cid, name=cid, priority=priority)

def test_phase2_linear():
    r = build()
    for x in ("config","logger","event_bus","modules"): reg(r,x)
    assert r.add_dependency("logger","config")
    assert r.add_dependency("event_bus","logger")
    assert r.add_dependency("modules","event_bus")
    out = r.resolve(force=True)
    assert out["details"]["boot_order"] == ["config","logger","event_bus","modules"]
    assert out["details"]["shutdown_order"] == ["modules","event_bus","logger","config"]

def test_phase2_priority_determinism():
    r = build()
    reg(r,"late",50); reg(r,"first",1); reg(r,"middle",20)
    assert r.get_boot_order(force=True) == ["first","middle","late"]
    assert r.get_boot_order(force=True) == ["first","middle","late"]

def test_phase2_cache_version():
    r = build(); reg(r,"a"); reg(r,"b"); assert r.add_dependency("b","a")
    assert r.resolve()["details"]["cached"] is False
    assert r.resolve()["details"]["cached"] is True
    v = r.graph.version; reg(r,"c"); assert r.graph.version == v + 1
    assert r.resolve()["details"]["cached"] is False

def test_phase2_policies():
    r = build(); reg(r,"a",100); reg(r,"b",1)
    assert r.add_dependency("b","a","optional")
    assert r.get_boot_order(force=True) == ["b","a"]
    assert r.get_boot_order(("required","optional"), force=True) == ["a","b"]

def test_phase3_no_cycle():
    r = build()
    for x in ("a","b","c"): reg(r,x)
    r.add_dependency("b","a"); r.add_dependency("c","b")
    report = r.get_cycle_report()
    assert report["has_cycles"] is False and report["cycle_count"] == 0

def test_phase3_simple_cycle():
    r = build(); reg(r,"a"); reg(r,"b")
    r.add_dependency("a","b"); r.add_dependency("b","a")
    report = r.get_cycle_report()
    assert report["cycles"] == [["a","b","a"]]
    assert r.validate_cycles()["valid"] is False

def test_phase3_multiple_cycles():
    r = build()
    for x in ("a","b","x","y","z"): reg(r,x)
    r.add_dependency("a","b"); r.add_dependency("b","a")
    r.add_dependency("x","y"); r.add_dependency("y","z"); r.add_dependency("z","x")
    report = r.get_cycle_report()
    assert report["cycle_count"] == 2
    assert ["a","b","a"] in report["cycles"]
    assert ["x","y","z","x"] in report["cycles"]

def test_phase3_analysis():
    r = build()
    for x in ("config","logger","event_bus","isolated"): reg(r,x)
    r.add_dependency("logger","config"); r.add_dependency("event_bus","logger")
    report = r.analyze_graph()
    assert report["isolated_nodes"] == ["isolated"]
    assert report["independent_graph_count"] == 2
    assert report["longest_chain"] == ["event_bus","logger","config"]
    assert report["maximum_depth"] == 2

def main():
    tests = [
        test_phase2_linear,
        test_phase2_priority_determinism,
        test_phase2_cache_version,
        test_phase2_policies,
        test_phase3_no_cycle,
        test_phase3_simple_cycle,
        test_phase3_multiple_cycles,
        test_phase3_analysis,
    ]
    print("=== DEPENDENCY RESOLVER PHASE 2 + 3 ===")
    for test in tests:
        test()
        print(f"{test.__name__}: PASS")
    print("RESULT: PASS")

if __name__ == "__main__":
    main()
