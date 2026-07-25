from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE = PROJECT_ROOT / "core"


def test_core_has_no_loose_config_compatibility_modules():
    loose = sorted(path.name for path in CORE.glob("config_*.py"))
    assert loose == []


def test_project_has_no_legacy_python_modules():
    legacy = sorted(
        str(path.relative_to(PROJECT_ROOT))
        for path in PROJECT_ROOT.rglob("*.py")
        if path.name == "legacy.py" or path.stem.endswith("_legacy")
    )
    assert legacy == []


def test_config_manager_uses_kas_layout_and_private_internals():
    package = CORE / "config_manager"
    expected = {
        "__init__.py",
        "component.py",
        "events.py",
        "exceptions.py",
        "lifecycle.py",
        "manifest.py",
        "observer.py",
        "report.py",
        "statistics.py",
        "transaction.py",
        "validator.py",
        "internals",
    }
    assert expected.issubset({path.name for path in package.iterdir()})
    assert (package / "internals" / "__init__.py").is_file()
