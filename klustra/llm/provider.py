from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

OPENAI_COMPATIBLE_PROVIDERS: dict[str, str | None] = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "databricks": None,  # workspace-specific — base_url must be configured
}
"""Provider name → default base_url for the OpenAI-compatible wire format.

Single source of truth for *every* role: chat completions and embeddings both
resolve through `resolve_base_url`, so a provider added here works for both.
Adding one is a dict entry, never a new branch.
"""


def resolve_base_url(provider: str, base_url: str | None = None) -> str | None:
    """Explicit config wins; otherwise the provider's known default (may be None)."""
    return base_url or OPENAI_COMPATIBLE_PROVIDERS.get(provider)


def supported_providers_hint() -> str:
    """Comma-separated provider names, for error messages."""
    return ", ".join(repr(name) for name in sorted(OPENAI_COMPATIBLE_PROVIDERS))


DEFAULT_TIMEOUT_SECONDS = 120.0
"""Client-side per-request timeout (SPEC §8). The SDK default is 600s with 2
silent internal retries; that is 30 minutes of no output per attempt."""


class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: list[LLMMessage]
    model: str
    max_tokens: int | None = None
    response_schema: dict[str, Any] | None = None
    temperature: float = 0.0
    retry_attempts: int | None = None
    """Per-role transient-failure retry budget (LLMRoleConfig.retry_attempts). None = default."""
    label: str | None = None
    """Human-readable call context for progress/retry logging, e.g. "librarian:iec_62067"."""


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    parsed: dict[str, Any] | None = None
    tokens_in: int
    tokens_out: int
    model: str


class LLMProvider(ABC):
    """Provider abstraction (SPEC §8). Implementations: OpenAI-compatible, Anthropic, Mock."""

    name: str

    @abstractmethod
    def call(self, request: LLMRequest) -> LLMResponse: ...
