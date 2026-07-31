from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(StrEnum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALL = "tool_call"
    CONTENT_FILTER = "content_filter"
    CANCELLED = "cancelled"
    ERROR = "error"


class ProviderState(StrEnum):
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class ModelCapability(StrEnum):
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    STREAMING = "streaming"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"


@dataclass(slots=True, frozen=True)
class AIMessage:
    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if self.role is MessageRole.TOOL and not self.tool_call_id:
            raise ValueError("tool messages require tool_call_id")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["role"] = self.role.value
        return data


@dataclass(slots=True, frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    strict: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tool name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.call_id.strip():
            raise ValueError("call_id must not be empty")
        if not self.name.strip():
            raise ValueError("tool call name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class GenerationRequest:
    messages: tuple[AIMessage, ...]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: tuple[ToolDefinition, ...] = ()
    response_format: dict[str, Any] | None = None
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("messages must not be empty")
        if not 0.0 <= float(self.temperature) <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "messages": [message.to_dict() for message in self.messages],
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": [tool.to_dict() for tool in self.tools],
            "response_format": self.response_format,
            "timeout_seconds": self.timeout_seconds,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True, frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if min(self.prompt_tokens, self.completion_tokens, self.total_tokens) < 0:
            raise ValueError("token counts must be >= 0")

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class GenerationResponse:
    message: AIMessage
    provider_id: str
    model_id: str
    finish_reason: FinishReason = FinishReason.STOP
    tool_calls: tuple[ToolCall, ...] = ()
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float | None = None
    response_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")
        if not self.model_id.strip():
            raise ValueError("model_id must not be empty")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message.to_dict(),
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "finish_reason": self.finish_reason.value,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "usage": self.usage.to_dict(),
            "latency_ms": self.latency_ms,
            "response_id": self.response_id,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass(slots=True, frozen=True)
class StreamChunk:
    provider_id: str
    model_id: str
    delta: str = ""
    finish_reason: FinishReason | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: TokenUsage | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "delta": self.delta,
            "finish_reason": self.finish_reason.value if self.finish_reason else None,
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "usage": self.usage.to_dict() if self.usage else None,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True, frozen=True)
class EmbeddingRequest:
    inputs: tuple[str, ...]
    model: str | None = None
    dimensions: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.inputs:
            raise ValueError("inputs must not be empty")
        if any(not isinstance(item, str) for item in self.inputs):
            raise TypeError("all embedding inputs must be strings")
        if self.dimensions is not None and self.dimensions <= 0:
            raise ValueError("dimensions must be > 0")


@dataclass(slots=True, frozen=True)
class EmbeddingResponse:
    embeddings: tuple[tuple[float, ...], ...]
    provider_id: str
    model_id: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.embeddings:
            raise ValueError("embeddings must not be empty")


@dataclass(slots=True, frozen=True)
class VisionRequest:
    prompt: str
    images: tuple[bytes | str, ...]
    model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.images:
            raise ValueError("images must not be empty")


@dataclass(slots=True, frozen=True)
class SpeechRequest:
    audio: bytes | str
    model: str | None = None
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SpeechResponse:
    text: str
    provider_id: str
    model_id: str
    language: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(slots=True, frozen=True)
class ModelDescriptor:
    model_id: str
    provider_id: str
    display_name: str
    capabilities: tuple[ModelCapability, ...]
    context_window: int | None = None
    max_output_tokens: int | None = None
    local: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.provider_id.strip():
            raise ValueError("model_id and provider_id must not be empty")
        if self.context_window is not None and self.context_window <= 0:
            raise ValueError("context_window must be > 0")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be > 0")


@dataclass(slots=True, frozen=True)
class ProviderHealth:
    provider_id: str
    state: ProviderState
    healthy: bool
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")
