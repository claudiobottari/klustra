from klustra.llm.accounting import AccountingSink, ListSink, NullSink, TokenRecord
from klustra.llm.anthropic_provider import AnthropicProvider
from klustra.llm.mock_provider import MockProvider
from klustra.llm.openai_provider import OpenAICompatibleProvider
from klustra.llm.prompts import PromptRegistry
from klustra.llm.provider import (
    DEFAULT_TIMEOUT_SECONDS,
    OPENAI_COMPATIBLE_PROVIDERS,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    resolve_base_url,
    supported_providers_hint,
)
from klustra.llm.retry import DEFAULT_MAX_ATTEMPTS, llm_retry

__all__ = [
    "AccountingSink",
    "AnthropicProvider",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_TIMEOUT_SECONDS",
    "OPENAI_COMPATIBLE_PROVIDERS",
    "LLMMessage",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "ListSink",
    "MockProvider",
    "NullSink",
    "OpenAICompatibleProvider",
    "PromptRegistry",
    "TokenRecord",
    "llm_retry",
    "resolve_base_url",
    "resolve_provider",
    "supported_providers_hint",
]


def resolve_provider(
    provider_name: str,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> LLMProvider:
    """Instantiate a provider by name. Falls back to env for API key."""
    from klustra.core.config import resolve_api_key
    from klustra.core.errors import LLMKeyMissingError

    if provider_name == "mock":
        return MockProvider()

    key = api_key or resolve_api_key(provider_name)
    if not key:
        raise LLMKeyMissingError(
            f"No API key for provider '{provider_name}'. "
            f"Set {provider_name.upper()}_API_KEY environment variable."
        )

    if provider_name == "anthropic":
        return AnthropicProvider(api_key=key, timeout_seconds=timeout_seconds)

    # Everything else speaks the OpenAI wire format. An unknown name is allowed
    # through as the escape hatch for a self-hosted endpoint via base_url.
    return OpenAICompatibleProvider(
        api_key=key,
        base_url=resolve_base_url(provider_name, base_url),
        timeout_seconds=timeout_seconds,
    )
