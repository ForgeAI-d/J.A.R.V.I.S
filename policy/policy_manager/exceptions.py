class PolicyError(Exception):
    """Base exception for the policy subsystem."""


class InvalidPolicyRequest(PolicyError):
    """Raised when a request cannot be normalized or validated."""


class PolicyRuleConflict(PolicyError):
    """Raised when a policy rule conflicts with an existing rule."""
