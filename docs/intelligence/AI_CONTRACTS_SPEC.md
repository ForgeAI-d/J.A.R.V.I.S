# J.A.R.V.I.S. AI Contracts 1.0

## Status

- Version: 1.0.0
- API status: stable
- Scope: provider-neutral contracts and immutable transfer objects
- Runtime logic: none

## Purpose

`core.ai_contracts` is the stable boundary between J.A.R.V.I.S. and concrete AI backends. No manager, skill, mission, memory component, or application module may depend directly on Ollama, OpenAI, llama.cpp, Gemini, Claude, or a future Velthor model.

Concrete adapters implement the contracts in this package. The future `ModelManager` registers and routes those adapters; the future `AIManager` exposes the public Intelligence Platform API.

## Stable contracts

- `AIProvider`: lifecycle, health, and model discovery
- `ChatProvider`: message-based generation
- `CompletionProvider`: text completion
- `StreamingProvider`: asynchronous response chunks
- `EmbeddingProvider`: vector generation
- `ToolCallingProvider`: structured tool calls
- `VisionProvider`: image analysis
- `SpeechToTextProvider`: transcription
- `TextToSpeechProvider`: speech synthesis
- `ModelProvider`: explicit model load/unload operations

## Stable data types

The package defines provider-neutral request and response objects:

- `AIMessage`
- `GenerationRequest`
- `GenerationResponse`
- `StreamChunk`
- `EmbeddingRequest`
- `EmbeddingResponse`
- `VisionRequest`
- `SpeechRequest`
- `SpeechResponse`
- `ToolDefinition`
- `ToolCall`
- `TokenUsage`
- `ModelDescriptor`
- `ProviderHealth`

All public transfer objects use typed dataclasses and validate their invariants at construction time. Provider-specific raw responses belong in `metadata` and may not leak into manager APIs.

## Async rule

Provider I/O is asynchronous. Network calls, local model inference, streaming, audio processing, and image analysis must not block the kernel runtime. `StreamingProvider.stream()` returns an `AsyncIterator[StreamChunk]`.

## Error rule

Provider adapters translate backend-specific failures into the shared exception hierarchy:

- `ProviderUnavailableError`
- `ModelUnavailableError`
- `CapabilityNotSupportedError`
- `InvalidAIRequestError`

Secrets, credentials, prompts containing sensitive data, and raw provider payloads must not be included in exception messages.

## Dependency rule

`core.ai_contracts` has no third-party runtime dependencies. Importing it must never load model SDKs, native libraries, network clients, GPU libraries, or optional vision/speech packages.

## Compatibility rule

Breaking changes require a new major contract version. New optional fields or new provider protocols may be introduced in compatible minor versions. Existing providers must remain usable without modification throughout the 1.x line.

## Acceptance criteria

AI Contracts 1.0 is accepted when:

1. all contracts are runtime-checkable protocols;
2. all transfer objects validate invalid values predictably;
3. serialization is provider-neutral;
4. no concrete provider package is imported;
5. unit tests pass;
6. the existing kernel boot remains unchanged.
