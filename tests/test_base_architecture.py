from core.base_engine import BaseEngine
from core.base_manager import BaseManager
from core.common import BaseComponent, BaseKernelComponent


def test_base_hierarchy_and_identifiers():
    engine = BaseEngine()
    manager = BaseManager()
    assert isinstance(engine, BaseKernelComponent)
    assert isinstance(manager, BaseKernelComponent)
    assert isinstance(engine, BaseComponent)
    assert engine.component_id == engine.engine_id
    assert manager.component_id == manager.manager_id


def test_engine_legacy_lifecycle_is_preserved():
    engine = BaseEngine()
    assert engine.initialize() is True
    assert engine.start() is True
    assert engine.status == "ONLINE"
    assert engine.lifecycle["started"] is True
    assert engine.pause() is True
    assert engine.resume() is True
    assert engine.restart() is True
    assert engine.stop() is True
    assert engine.status == "OFFLINE"
    assert engine.start_count == 2
    assert engine.restart_count == 1


def test_manager_controls_registered_engines():
    manager = BaseManager()
    engine = BaseEngine()
    assert manager.register_engine(engine) is True
    assert manager.register_engine(engine) is False
    assert manager.start() is True
    assert manager.status == "ONLINE"
    assert engine.status == "ONLINE"
    health = manager.health_check()
    assert health["healthy"] is True
    assert manager.stop() is True
    assert engine.status == "OFFLINE"


def test_kas_surface_is_available():
    engine = BaseEngine()
    for name in ("get_manifest", "get_health", "get_status", "get_statistics", "report", "validate"):
        assert callable(getattr(engine, name))
    manifest = engine.get_manifest()
    assert manifest["component_id"] == "base.engine"
    assert manifest["engine_id"] == "base.engine"
    assert manifest["kind"] == "engine"
