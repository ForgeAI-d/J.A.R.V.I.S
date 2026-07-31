# J.A.R.V.I.S. Policy Manager 1.0 Specification

## Status

- Component ID: `policy.policy_manager`
- Version: `1.0.0`
- API status: `FROZEN`
- Build status: `COMPLETE`
- Schema version: `1.0`

## Mission

The Policy Manager is the mandatory decision point for consequential actions performed by the J.A.R.V.I.S. Intelligence Platform. It produces deterministic, auditable decisions without executing the requested action itself.

## Stable public API

```python
evaluate(request=None, **request_fields) -> PolicyDecision
allow(request, reason, policy_id=None) -> PolicyDecision
deny(request, reason, policy_id=None) -> PolicyDecision
require_approval(request, reason, approval_level="user", policy_id=None) -> PolicyDecision
sandbox(request, reason, constraints=None, policy_id=None) -> PolicyDecision
register_rule(rule, replace=False) -> bool
unregister_rule(policy_id) -> bool
get_rule(policy_id) -> dict | None
list_rules(enabled_only=False) -> list[dict]
get_decision_history(limit=None) -> list[dict]
clear_decision_history() -> int
```

## Decision states

- `ALLOW`: action may proceed.
- `DENY`: action must not proceed.
- `REQUIRE_APPROVAL`: action is blocked until the required approval is recorded.
- `SANDBOX`: action may proceed only under the returned sandbox constraints.
- `ERROR`: evaluation could not be completed; callers must fail closed.

## Secure defaults

If no rule matches, the decision is `DENY`. Critical system resources are denied. Permission, security, installation, deletion, and sensitive-data operations require approval. Generated code and shell execution require sandboxing. Read-only web research is allowed.

## Rule evaluation

Rules are evaluated deterministically by descending priority and then by policy ID. Matching supports action and resource wildcard patterns, optional user/requester scoping, minimum sensitivity, and exact context/metadata conditions.

## Auditability

Every evaluation records the normalized request, decision, matching policy ID, reason, confidence, constraints, and UTC timestamps in a bounded in-memory decision history. Events are emitted for every decision category.

## Safety invariants

1. An error never grants permission.
2. Absence of a matching rule results in `DENY`.
3. The manager does not execute actions.
4. Sandbox decisions contain explicit constraints.
5. Approval decisions identify the required approval level.
6. Policies cannot autonomously increase their own authority.

## Dependencies

Required:

- `core.config_manager`
- `core.event_bus`

Optional:

- `permissions.permission_manager`
- `identity.identity_manager`

## Acceptance criteria

- KAS lifecycle and boot integration pass.
- All five decision states are representable.
- Default rules are deterministic.
- Invalid requests fail closed with `ERROR`.
- Rule CRUD, statistics, health, events, reports, and shutdown work.
- The full kernel boot remains successful with zero critical errors.
