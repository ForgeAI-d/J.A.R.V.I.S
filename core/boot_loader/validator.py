from typing import Any

REQUIRED_MANIFEST_FIELDS = {"component_id", "name", "version"}


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    return {
        "valid": not missing,
        "missing": missing,
        "component_id": manifest.get("component_id"),
    }


def validate_component(component: Any) -> dict[str, Any]:
    manifest_getter = getattr(component, "get_manifest", None)
    if not callable(manifest_getter):
        return {"valid": False, "errors": ["get_manifest() fehlt"]}
    result = validate_manifest(manifest_getter())
    lifecycle = [name for name in ("initialize", "start", "stop") if not callable(getattr(component, name, None))]
    if lifecycle:
        result["valid"] = False
        result["missing_lifecycle_methods"] = lifecycle
    return result
