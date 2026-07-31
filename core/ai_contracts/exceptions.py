class AIContractError(Exception):
    """Base exception for Intelligence Platform contract violations."""


class ProviderUnavailableError(AIContractError):
    """Raised when a requested provider is unavailable."""


class ModelUnavailableError(AIContractError):
    """Raised when a requested model cannot be used."""


class CapabilityNotSupportedError(AIContractError):
    """Raised when a provider lacks a required capability."""


class InvalidAIRequestError(AIContractError):
    """Raised when a request violates the stable AI contract."""
