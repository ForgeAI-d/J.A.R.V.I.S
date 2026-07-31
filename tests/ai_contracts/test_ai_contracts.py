from __future__ import annotations

from core.ai_contracts import (
    AIMessage,
    AIProvider,
    ChatProvider,
    FinishReason,
    GenerationRequest,
    GenerationResponse,
    MessageRole,
    ModelCapability,
    ModelDescriptor,
    ProviderHealth,
    ProviderState,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)


class FakeChatProvider:
    provider_id = "fake"
    name = "Fake Provider"
    version = "1.0.0"

    async def initialize(self) -> bool:
        return True

    async def close(self) -> None:
        return None

    async def health(self) -> ProviderHealth:
        return ProviderHealth("fake", ProviderState.AVAILABLE, True)

    async def list_models(self) -> tuple[ModelDescriptor, ...]:
        return (
            ModelDescriptor(
                model_id="fake-chat",
                provider_id="fake",
                display_name="Fake Chat",
                capabilities=(ModelCapability.CHAT,),
            ),
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        return GenerationResponse(
            message=AIMessage(MessageRole.ASSISTANT, "ok"),
            provider_id=self.provider_id,
            model_id=request.model or "fake-chat",
        )


def test_runtime_protocols_accept_valid_provider() -> None:
    provider = FakeChatProvider()
    assert isinstance(provider, AIProvider)
    assert isinstance(provider, ChatProvider)


def test_generation_request_and_response_are_serializable() -> None:
    request = GenerationRequest(
        messages=(AIMessage(MessageRole.USER, "Hallo"),),
        model="fake-chat",
        tools=(ToolDefinition("search", "Search the web", {"type": "object"}),),
    )
    response = GenerationResponse(
        message=AIMessage(MessageRole.ASSISTANT, "Hallo"),
        provider_id="fake",
        model_id="fake-chat",
        finish_reason=FinishReason.TOOL_CALL,
        tool_calls=(ToolCall("call-1", "search", {"query": "Jarvis"}),),
        usage=TokenUsage(3, 2, 5),
    )

    assert request.to_dict()["messages"][0]["role"] == "user"
    assert response.to_dict()["finish_reason"] == "tool_call"
    assert response.to_dict()["usage"]["total_tokens"] == 5


def test_contract_validation_rejects_invalid_values() -> None:
    try:
        GenerationRequest(
            messages=(AIMessage(MessageRole.USER, "test"),),
            temperature=3.0,
        )
    except ValueError as exc:
        assert "temperature" in str(exc)
    else:
        raise AssertionError("invalid temperature must be rejected")

    try:
        AIMessage(MessageRole.TOOL, "result")
    except ValueError as exc:
        assert "tool_call_id" in str(exc)
    else:
        raise AssertionError("tool message without tool_call_id must be rejected")


def test_model_descriptor_exposes_capabilities() -> None:
    descriptor = ModelDescriptor(
        model_id="local-model",
        provider_id="ollama",
        display_name="Local Model",
        capabilities=(ModelCapability.CHAT, ModelCapability.STREAMING),
        context_window=8192,
        local=True,
    )
    assert descriptor.local is True
    assert ModelCapability.STREAMING in descriptor.capabilities
