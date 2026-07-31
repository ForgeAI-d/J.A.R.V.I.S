from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


class PolicyDecisionStatus(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    SANDBOX = "SANDBOX"
    ERROR = "ERROR"


class PolicySensitivity(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    PERSONAL = "PERSONAL"
    SENSITIVE = "SENSITIVE"
    CRITICAL = "CRITICAL"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class PolicyRequest:
    action: str
    resource: str = "*"
    target: str | None = None
    user_id: str | None = None
    requester_id: str | None = None
    priority: int = 50
    sensitivity: PolicySensitivity = PolicySensitivity.INTERNAL
    context: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: f"policy-request-{uuid4().hex}")
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        action = str(self.action).strip().lower()
        resource = str(self.resource).strip().lower()
        if not action:
            raise ValueError("PolicyRequest.action must not be empty")
        if not resource:
            raise ValueError("PolicyRequest.resource must not be empty")
        if not 0 <= int(self.priority) <= 100:
            raise ValueError("PolicyRequest.priority must be between 0 and 100")
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "resource", resource)
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "sensitivity", PolicySensitivity(self.sensitivity))
        object.__setattr__(self, "context", _freeze_mapping(self.context))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PolicyRequest":
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "resource": self.resource,
            "target": self.target,
            "user_id": self.user_id,
            "requester_id": self.requester_id,
            "priority": self.priority,
            "sensitivity": self.sensitivity.value,
            "context": dict(self.context),
            "metadata": dict(self.metadata),
            "request_id": self.request_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    status: PolicyDecisionStatus
    reason: str
    request_id: str
    policy_id: str | None = None
    confidence: float = 1.0
    required_approval: str | None = None
    sandbox_required: bool = False
    constraints: Mapping[str, Any] = field(default_factory=dict)
    decision_id: str = field(default_factory=lambda: f"policy-decision-{uuid4().hex}")
    decided_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        confidence = float(self.confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("PolicyDecision.confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "status", PolicyDecisionStatus(self.status))
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "constraints", _freeze_mapping(self.constraints))

    @property
    def allowed(self) -> bool:
        return self.status in {PolicyDecisionStatus.ALLOW, PolicyDecisionStatus.SANDBOX}

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "request_id": self.request_id,
            "policy_id": self.policy_id,
            "confidence": self.confidence,
            "required_approval": self.required_approval,
            "sandbox_required": self.sandbox_required,
            "constraints": dict(self.constraints),
            "decision_id": self.decision_id,
            "decided_at": self.decided_at,
            "allowed": self.allowed,
        }


@dataclass(frozen=True, slots=True)
class PolicyRule:
    policy_id: str
    action_pattern: str
    resource_pattern: str
    decision: PolicyDecisionStatus
    reason: str
    priority: int = 100
    enabled: bool = True
    user_id: str | None = None
    requester_id: str | None = None
    minimum_sensitivity: PolicySensitivity | None = None
    conditions: Mapping[str, Any] = field(default_factory=dict)
    constraints: Mapping[str, Any] = field(default_factory=dict)
    required_approval: str | None = None
    confidence: float = 1.0
    created_at: str = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not str(self.policy_id).strip():
            raise ValueError("PolicyRule.policy_id must not be empty")
        if not str(self.action_pattern).strip() or not str(self.resource_pattern).strip():
            raise ValueError("PolicyRule patterns must not be empty")
        if not 0 <= int(self.priority) <= 1000:
            raise ValueError("PolicyRule.priority must be between 0 and 1000")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("PolicyRule.confidence must be between 0.0 and 1.0")
        object.__setattr__(self, "action_pattern", str(self.action_pattern).strip().lower())
        object.__setattr__(self, "resource_pattern", str(self.resource_pattern).strip().lower())
        object.__setattr__(self, "decision", PolicyDecisionStatus(self.decision))
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "confidence", float(self.confidence))
        if self.minimum_sensitivity is not None:
            object.__setattr__(self, "minimum_sensitivity", PolicySensitivity(self.minimum_sensitivity))
        object.__setattr__(self, "conditions", _freeze_mapping(self.conditions))
        object.__setattr__(self, "constraints", _freeze_mapping(self.constraints))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PolicyRule":
        return cls(**dict(data))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "action_pattern": self.action_pattern,
            "resource_pattern": self.resource_pattern,
            "decision": self.decision.value,
            "reason": self.reason,
            "priority": self.priority,
            "enabled": self.enabled,
            "user_id": self.user_id,
            "requester_id": self.requester_id,
            "minimum_sensitivity": self.minimum_sensitivity.value if self.minimum_sensitivity else None,
            "conditions": dict(self.conditions),
            "constraints": dict(self.constraints),
            "required_approval": self.required_approval,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }
