"""Static KAS manifest metadata for Policy Manager 1.0."""

MANIFEST = {
    "component_id": "policy.policy_manager",
    "name": "Policy Manager",
    "version": "1.0.0",
    "kind": "manager",
    "priority": 15,
    "auto_start": True,
    "requires": ["core.config_manager", "core.event_bus"],
    "optional": ["permissions.permission_manager", "identity.identity_manager"],
    "capabilities": [
        "policy_evaluation",
        "rule_management",
        "approval_routing",
        "sandbox_enforcement",
        "decision_audit",
    ],
    "schema_version": "1.0",
    "api_status": "FROZEN",
    "build_status": "COMPLETE",
}
