from core.contracts import ComponentContract, LifecycleContract
from core.testing import FakeComponent


def test_manifest_and_contracts():
    component = FakeComponent()
    assert isinstance(component, LifecycleContract)
    assert isinstance(component, ComponentContract)
    manifest = component.get_manifest()
    assert manifest["component_id"] == "testing.fake_component"
    assert manifest["api_status"] == "FROZEN"


def test_lifecycle_and_observer():
    component = FakeComponent()
    events = []
    assert component.subscribe(events.append)
    assert component.initialize()
    assert component.start()
    assert component.get_health()["healthy"] is True
    assert component.stop()
    assert events
    assert component.get_statistics()["events"] == len(events)


def test_validation_and_report():
    component = FakeComponent()
    assert component.validate()["valid"] is True
    report = component.report()
    assert report["manifest"]["version"] == "1.0.0"
    assert "statistics" in report
