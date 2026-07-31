from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from typing import Any, Protocol, runtime_checkable

from .models import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    ModelDescriptor,
    ProviderHealth,
    SpeechRequest,
    SpeechResponse,
    StreamChunk,
    VisionRequest,
)


@runtime_checkable
class AIProvider(Protocol):
    provider_id: str
    name: str
    version: str

    async def initialize(self) -> bool: ...
    async def close(self) -> None: ...
    async def health(self) -> ProviderHealth: ...
    async def list_models(self) -> tuple[ModelDescriptor, ...]: ...


@runtime_checkable
class ChatProvider(AIProvider, Protocol):
    async def generate(self, request: GenerationRequest) -> GenerationResponse: ...


@runtime_checkable
class CompletionProvider(AIProvider, Protocol):
    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> GenerationResponse: ...


@runtime_checkable
class StreamingProvider(AIProvider, Protocol):
    def stream(self, request: GenerationRequest) -> AsyncIterator[StreamChunk]: ...


@runtime_checkable
class EmbeddingProvider(AIProvider, Protocol):
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...


@runtime_checkable
class ToolCallingProvider(ChatProvider, Protocol):
    @property
    def supports_parallel_tool_calls(self) -> bool: ...


@runtime_checkable
class VisionProvider(AIProvider, Protocol):
    async def analyze_image(self, request: VisionRequest) -> GenerationResponse: ...


@runtime_checkable
class SpeechToTextProvider(AIProvider, Protocol):
    async def transcribe(self, request: SpeechRequest) -> SpeechResponse: ...


@runtime_checkable
class TextToSpeechProvider(AIProvider, Protocol):
    async def synthesize(
        self,
        text: str,
        *,
        model: str | None = None,
        voice: str | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> bytes: ...


@runtime_checkable
class ModelProvider(AIProvider, Protocol):
    async def load_model(self, model_id: str) -> bool: ...
    async def unload_model(self, model_id: str) -> bool: ...
    async def is_model_loaded(self, model_id: str) -> bool: ...
