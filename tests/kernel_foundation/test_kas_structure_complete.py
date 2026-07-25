from pathlib import Path

REQUIRED={"__init__.py","component.py","manifest.py","validator.py","report.py","statistics.py","observer.py","transaction.py","events.py","exceptions.py","lifecycle.py"}

def test_all_kas_component_packages_have_standard_structure():
    root=Path(__file__).resolve().parents[2]
    packages=sorted(path.parent for path in root.rglob("component.py") if "__pycache__" not in path.parts)
    assert packages
    failures={}
    for package in packages:
        present={p.name for p in package.iterdir() if p.is_file()}
        missing=sorted(REQUIRED-present)
        if missing: failures[str(package.relative_to(root))]=missing
    assert not failures, failures
