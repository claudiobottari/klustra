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
