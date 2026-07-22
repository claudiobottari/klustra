from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


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
