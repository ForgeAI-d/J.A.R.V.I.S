from __future__ import annotations

from collections import Counter, deque
from copy import deepcopy
from fnmatch import fnmatchcase
from threading import RLock
from typing import Any, Iterable, Mapping

from core.base_manager import BaseManager
from core.types import APIStatus, BuildStatus

from .defaults import default_policy_rules
from .models import (
    PolicyDecision,
    PolicyDecisionStatus,
    PolicyRequest,
    PolicyRule,
    PolicySensitivity,
)


class PolicyManager(BaseManager):
    """Deterministic policy decision point for Intelligence Platform 1.0."""

    COMPONENT_ID = "policy.policy_manager"
    MANAGER_ID = COMPONENT_ID
    NAME = "Policy Manager"
    VERSION = "1.0.0"
    AUTHOR = "Velthor Technologies"
    MISSION = "Evaluate every potentially consequential J.A.R.V.I.S. action before execution."
    PRIORITY = 15
    AUTO_START = True
    REQUIRES = ("core.config_manager", "core.event_bus")
    OPTIONAL = ("permissions.permission_manager", "identity.identity_manager")
    CAPABILITIES = (
        "policy_evaluation",
        "rule_management",
        "approval_routing",
        "sandbox_enforcement",
        "decision_audit",
        "policy_reporting",
    )
    BUILD_STATUS = BuildStatus.COMPLETE
    API_STATUS = APIStatus.FROZEN
    SCHEMA_VERSION = "1.0"

    DEFAULT_DECISION = PolicyDecisionStatus.DENY
    HISTORY_LIMIT = 10_000

    def __init__(
        self,
        context: Any | None = None,
        rules: Iterable[PolicyRule | Mapping[str, Any]] | None = None,
        history_limit: int = HISTORY_LIMIT,
    ) -> None:
        super().__init__(context=context)
        self._policy_lock = RLock()
        self._rules: dict[str, PolicyRule] = {}
        self._history: deque[dict[str, Any]] = deque(maxlen=max(1, int(history_limit)))
        self._decision_counts: Counter[str] = Counter()
        self._evaluation_count = 0
        self._rule_matches = 0
        self._default_decisions = 0
        self._load_rules(rules if rules is not None else default_policy_rules())

    def initialize(self) -> bool:
        if not super().initialize():
            return False
        validation = self.validate()
        if not validation["valid"]:
            return self.set_error("; ".join(validation["errors"]))
        self.add_timeline_event("POLICY_MANAGER_READY", {"rule_count": len(self._rules)})
        return True

    def evaluate(
        self,
        request: PolicyRequest | Mapping[str, Any] | None = None,
        **request_fields: Any,
    ) -> PolicyDecision:
        try:
            normalized = self._normalize_request(request, request_fields)
            with self._policy_lock:
                self._evaluation_count += 1
                matching_rule = next(
                    (rule for rule in self._ordered_rules() if self._matches(rule, normalized)),
                    None,
                )
                if matching_rule is None:
                    self._default_decisions += 1
                    decision = PolicyDecision(
                        status=self.DEFAULT_DECISION,
                        reason="No matching policy rule; secure default is DENY.",
                        request_id=normalized.request_id,
                        confidence=1.0,
                    )
                else:
                    self._rule_matches += 1
                    decision = self._decision_from_rule(matching_rule, normalized)
                self._record_decision(normalized, decision)
            self._emit_decision_event(normalized, decision)
            return decision
        except Exception as exc:
            request_id = getattr(request, "request_id", "invalid-request")
            decision = PolicyDecision(
                status=PolicyDecisionStatus.ERROR,
                reason=f"Policy evaluation failed: {exc}",
                request_id=request_id,
                confidence=0.0,
            )
            with self._policy_lock:
                self._decision_counts[decision.status.value] += 1
            self.add_timeline_event("POLICY_ERROR", decision.to_dict())
            return decision

    def allow(self, request: PolicyRequest | Mapping[str, Any], reason: str, policy_id: str | None = None) -> PolicyDecision:
        normalized = self._normalize_request(request, {})
        return PolicyDecision(PolicyDecisionStatus.ALLOW, reason, normalized.request_id, policy_id)

    def deny(self, request: PolicyRequest | Mapping[str, Any], reason: str, policy_id: str | None = None) -> PolicyDecision:
        normalized = self._normalize_request(request, {})
        return PolicyDecision(PolicyDecisionStatus.DENY, reason, normalized.request_id, policy_id)

    def require_approval(
        self,
        request: PolicyRequest | Mapping[str, Any],
        reason: str,
        approval_level: str = "user",
        policy_id: str | None = None,
    ) -> PolicyDecision:
        normalized = self._normalize_request(request, {})
        return PolicyDecision(
            PolicyDecisionStatus.REQUIRE_APPROVAL,
            reason,
            normalized.request_id,
            policy_id,
            required_approval=approval_level,
        )

    def sandbox(
        self,
        request: PolicyRequest | Mapping[str, Any],
        reason: str,
        constraints: Mapping[str, Any] | None = None,
        policy_id: str | None = None,
    ) -> PolicyDecision:
        normalized = self._normalize_request(request, {})
        return PolicyDecision(
            PolicyDecisionStatus.SANDBOX,
            reason,
            normalized.request_id,
            policy_id,
            sandbox_required=True,
            constraints=constraints or {},
        )

    def register_rule(self, rule: PolicyRule | Mapping[str, Any], replace: bool = False) -> bool:
        normalized = rule if isinstance(rule, PolicyRule) else PolicyRule.from_mapping(rule)
        with self._policy_lock:
            if normalized.policy_id in self._rules and not replace:
                return False
            self._rules[normalized.policy_id] = normalized
        self.add_timeline_event("POLICY_RULE_REGISTERED", {"policy_id": normalized.policy_id, "replaced": replace})
        return True

    def unregister_rule(self, policy_id: str) -> bool:
        with self._policy_lock:
            if policy_id not in self._rules:
                return False
            del self._rules[policy_id]
        self.add_timeline_event("POLICY_RULE_UNREGISTERED", {"policy_id": policy_id})
        return True

    def get_rule(self, policy_id: str) -> dict[str, Any] | None:
        with self._policy_lock:
            rule = self._rules.get(policy_id)
            return rule.to_dict() if rule else None

    def list_rules(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        with self._policy_lock:
            rules = self._ordered_rules()
            if enabled_only:
                rules = [rule for rule in rules if rule.enabled]
            return [rule.to_dict() for rule in rules]

    def get_decision_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._policy_lock:
            items = list(self._history)
        if limit is not None:
            items = items[-max(0, int(limit)):]
        return deepcopy(items)

    def clear_decision_history(self) -> int:
        with self._policy_lock:
            count = len(self._history)
            self._history.clear()
        return count

    def validate(self) -> dict[str, Any]:
        base = super().validate()
        errors = list(base.get("errors", []))
        with self._policy_lock:
            if not self._rules:
                errors.append("At least one policy rule is required")
            for policy_id, rule in self._rules.items():
                if policy_id != rule.policy_id:
                    errors.append(f"Rule key mismatch: {policy_id}")
        return {
            "valid": not errors,
            "errors": errors,
            "component_id": self.component_id,
            "rule_count": len(self._rules),
        }

    def health_check(self) -> dict[str, Any]:
        validation = self.validate()
        if self.status == "ERROR" or not validation["valid"]:
            self.set_health(0)
        elif self.lifecycle["started"]:
            self.set_health(100)
        else:
            self.set_health(50 if self.lifecycle["initialized"] else 0)
        health = self.get_health()
        health["rule_count"] = len(self._rules)
        health["validation"] = validation
        return health

    def get_statistics(self) -> dict[str, Any]:
        statistics = super().get_statistics()
        with self._policy_lock:
            statistics.update(
                {
                    "rule_count": len(self._rules),
                    "evaluation_count": self._evaluation_count,
                    "rule_matches": self._rule_matches,
                    "default_decisions": self._default_decisions,
                    "history_count": len(self._history),
                    "decision_counts": dict(self._decision_counts),
                }
            )
        return statistics

    def report(self) -> dict[str, Any]:
        return {
            "manifest": self.get_manifest(),
            "status": self.status,
            "health": self.health_check(),
            "statistics": self.get_statistics(),
            "rules": self.list_rules(),
            "recent_decisions": self.get_decision_history(limit=25),
            "last_error": self.last_error,
        }

    def _load_rules(self, rules: Iterable[PolicyRule | Mapping[str, Any]]) -> None:
        for rule in rules:
            self.register_rule(rule, replace=True)

    @staticmethod
    def _normalize_request(
        request: PolicyRequest | Mapping[str, Any] | None,
        request_fields: Mapping[str, Any],
    ) -> PolicyRequest:
        if isinstance(request, PolicyRequest):
            if request_fields:
                raise ValueError("Cannot combine a PolicyRequest with additional request fields")
            return request
        data: dict[str, Any] = {}
        if request is not None:
            if not isinstance(request, Mapping):
                raise TypeError("request must be PolicyRequest, mapping, or None")
            data.update(request)
        data.update(request_fields)
        return PolicyRequest.from_mapping(data)

    def _ordered_rules(self) -> list[PolicyRule]:
        return sorted(
            self._rules.values(),
            key=lambda rule: (-rule.priority, rule.policy_id),
        )

    @staticmethod
    def _matches(rule: PolicyRule, request: PolicyRequest) -> bool:
        if not rule.enabled:
            return False
        if not fnmatchcase(request.action, rule.action_pattern):
            return False
        if not fnmatchcase(request.resource, rule.resource_pattern):
            return False
        if rule.user_id is not None and rule.user_id != request.user_id:
            return False
        if rule.requester_id is not None and rule.requester_id != request.requester_id:
            return False
        if rule.minimum_sensitivity is not None:
            rank = list(PolicySensitivity)
            if rank.index(request.sensitivity) < rank.index(rule.minimum_sensitivity):
                return False
        combined = {**dict(request.context), **dict(request.metadata)}
        return all(combined.get(key) == value for key, value in rule.conditions.items())

    @staticmethod
    def _decision_from_rule(rule: PolicyRule, request: PolicyRequest) -> PolicyDecision:
        return PolicyDecision(
            status=rule.decision,
            reason=rule.reason,
            request_id=request.request_id,
            policy_id=rule.policy_id,
            confidence=rule.confidence,
            required_approval=rule.required_approval,
            sandbox_required=rule.decision == PolicyDecisionStatus.SANDBOX,
            constraints=rule.constraints,
        )

    def _record_decision(self, request: PolicyRequest, decision: PolicyDecision) -> None:
        self._decision_counts[decision.status.value] += 1
        self._history.append({"request": request.to_dict(), "decision": decision.to_dict()})

    def _emit_decision_event(self, request: PolicyRequest, decision: PolicyDecision) -> None:
        event_map = {
            PolicyDecisionStatus.ALLOW: "POLICY_ALLOWED",
            PolicyDecisionStatus.DENY: "POLICY_DENIED",
            PolicyDecisionStatus.REQUIRE_APPROVAL: "POLICY_APPROVAL_REQUIRED",
            PolicyDecisionStatus.SANDBOX: "POLICY_SANDBOX_REQUIRED",
            PolicyDecisionStatus.ERROR: "POLICY_ERROR",
        }
        self.add_timeline_event(
            event_map[decision.status],
            {
                "request_id": request.request_id,
                "decision_id": decision.decision_id,
                "action": request.action,
                "resource": request.resource,
                "policy_id": decision.policy_id,
                "reason": decision.reason,
            },
        )
