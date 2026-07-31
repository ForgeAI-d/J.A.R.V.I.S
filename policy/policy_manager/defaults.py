from __future__ import annotations

from .models import PolicyDecisionStatus, PolicyRule, PolicySensitivity


def default_policy_rules() -> tuple[PolicyRule, ...]:
    """Safe deterministic defaults for Intelligence Platform 1.0."""
    return (
        PolicyRule(
            policy_id="policy.system.critical.deny",
            action_pattern="*",
            resource_pattern="system.critical*",
            decision=PolicyDecisionStatus.DENY,
            reason="Critical system resources cannot be modified autonomously.",
            priority=1000,
        ),
        PolicyRule(
            policy_id="policy.permissions.elevated.approval",
            action_pattern="*",
            resource_pattern="permissions*",
            decision=PolicyDecisionStatus.REQUIRE_APPROVAL,
            reason="Permission changes require elevated user approval.",
            priority=950,
            required_approval="elevated",
        ),
        PolicyRule(
            policy_id="policy.security.approval",
            action_pattern="modify",
            resource_pattern="security*",
            decision=PolicyDecisionStatus.REQUIRE_APPROVAL,
            reason="Security configuration changes require elevated approval.",
            priority=950,
            required_approval="elevated",
        ),
        PolicyRule(
            policy_id="policy.files.delete.approval",
            action_pattern="delete",
            resource_pattern="file*",
            decision=PolicyDecisionStatus.REQUIRE_APPROVAL,
            reason="Deleting files requires explicit user approval.",
            priority=900,
            required_approval="user",
        ),
        PolicyRule(
            policy_id="policy.software.install.approval",
            action_pattern="install",
            resource_pattern="software*",
            decision=PolicyDecisionStatus.REQUIRE_APPROVAL,
            reason="Software installation changes the host and requires approval.",
            priority=900,
            required_approval="elevated",
        ),
        PolicyRule(
            policy_id="policy.code.execute.sandbox",
            action_pattern="execute",
            resource_pattern="code*",
            decision=PolicyDecisionStatus.SANDBOX,
            reason="Generated or untrusted code must run inside a sandbox.",
            priority=850,
            constraints={"network": False, "filesystem": "isolated"},
        ),
        PolicyRule(
            policy_id="policy.shell.execute.sandbox",
            action_pattern="execute",
            resource_pattern="shell*",
            decision=PolicyDecisionStatus.SANDBOX,
            reason="Shell commands require sandboxed execution by default.",
            priority=850,
            constraints={"network": False, "filesystem": "restricted"},
        ),
        PolicyRule(
            policy_id="policy.web.search.allow",
            action_pattern="search",
            resource_pattern="web*",
            decision=PolicyDecisionStatus.ALLOW,
            reason="Read-only web research is allowed by default.",
            priority=500,
        ),
        PolicyRule(
            policy_id="policy.knowledge.read.allow",
            action_pattern="read",
            resource_pattern="knowledge*",
            decision=PolicyDecisionStatus.ALLOW,
            reason="Reading the knowledge base is allowed.",
            priority=500,
        ),
        PolicyRule(
            policy_id="policy.sensitive.approval",
            action_pattern="*",
            resource_pattern="*",
            decision=PolicyDecisionStatus.REQUIRE_APPROVAL,
            reason="Sensitive and critical requests require user approval.",
            priority=400,
            minimum_sensitivity=PolicySensitivity.SENSITIVE,
            required_approval="user",
        ),
    )
