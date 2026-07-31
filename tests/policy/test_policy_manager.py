from __future__ import annotations

from policy.policy_manager import (
    PolicyDecisionStatus,
    PolicyManager,
    PolicyRequest,
    PolicyRule,
    PolicySensitivity,
)


def running_manager() -> PolicyManager:
    manager = PolicyManager()
    assert manager.initialize()
    assert manager.start()
    return manager


def test_web_search_is_allowed() -> None:
    manager = running_manager()
    decision = manager.evaluate(action="search", resource="web.google")
    assert decision.status == PolicyDecisionStatus.ALLOW
    assert decision.allowed is True
    assert decision.policy_id == "policy.web.search.allow"


def test_system_critical_is_denied() -> None:
    manager = running_manager()
    decision = manager.evaluate(action="delete", resource="system.critical.kernel")
    assert decision.status == PolicyDecisionStatus.DENY
    assert decision.allowed is False


def test_file_delete_requires_approval() -> None:
    manager = running_manager()
    decision = manager.evaluate(action="delete", resource="file.user_document")
    assert decision.status == PolicyDecisionStatus.REQUIRE_APPROVAL
    assert decision.required_approval == "user"


def test_code_execution_requires_sandbox() -> None:
    manager = running_manager()
    decision = manager.evaluate(action="execute", resource="code.generated")
    assert decision.status == PolicyDecisionStatus.SANDBOX
    assert decision.sandbox_required is True
    assert decision.constraints["filesystem"] == "isolated"


def test_sensitive_request_requires_approval() -> None:
    manager = running_manager()
    request = PolicyRequest(
        action="read",
        resource="profile.health",
        sensitivity=PolicySensitivity.SENSITIVE,
    )
    decision = manager.evaluate(request)
    assert decision.status == PolicyDecisionStatus.REQUIRE_APPROVAL


def test_unknown_action_uses_secure_default_deny() -> None:
    manager = running_manager()
    decision = manager.evaluate(action="teleport", resource="unknown.resource")
    assert decision.status == PolicyDecisionStatus.DENY
    assert decision.policy_id is None


def test_invalid_request_returns_error_decision() -> None:
    manager = running_manager()
    decision = manager.evaluate(action="", resource="web")
    assert decision.status == PolicyDecisionStatus.ERROR
    assert decision.confidence == 0.0


def test_custom_high_priority_rule_overrides_default() -> None:
    manager = running_manager()
    assert manager.register_rule(
        PolicyRule(
            policy_id="test.web.deny",
            action_pattern="search",
            resource_pattern="web.private*",
            decision=PolicyDecisionStatus.DENY,
            reason="Private endpoint blocked in test.",
            priority=999,
        )
    )
    decision = manager.evaluate(action="search", resource="web.private.internal")
    assert decision.status == PolicyDecisionStatus.DENY
    assert decision.policy_id == "test.web.deny"


def test_events_statistics_report_and_health() -> None:
    manager = running_manager()
    manager.evaluate(action="search", resource="web")
    manager.evaluate(action="execute", resource="code.generated")
    statistics = manager.get_statistics()
    assert statistics["evaluation_count"] == 2
    assert statistics["decision_counts"]["ALLOW"] == 1
    assert statistics["decision_counts"]["SANDBOX"] == 1
    assert manager.health_check()["healthy"] is True
    report = manager.report()
    assert report["manifest"]["component_id"] == "policy.policy_manager"
    assert len(report["recent_decisions"]) == 2
    event_types = {event["event_type"] for event in manager.timeline}
    assert "POLICY_ALLOWED" in event_types
    assert "POLICY_SANDBOX_REQUIRED" in event_types


def test_stop_is_clean() -> None:
    manager = running_manager()
    assert manager.stop()
    assert manager.status == "OFFLINE"
