from __future__ import annotations

import json
from typing import Any

import anthropic

from klustra.core.errors import LLMCallError, LLMValidationError
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse
from klustra.llm.retry import call_with_corrective_retry, llm_retry


class AnthropicProvider(LLMProvider):
    """Anthropic provider: structured output via forced tool_use."""

    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def call(self, request: LLMRequest) -> LLMResponse:
        return call_with_corrective_retry(self._call_with_retry, request)

    @llm_retry()
    def _call_with_retry(self, request: LLMRequest) -> LLMResponse:
        system_parts: list[str] = []
        messages: list[dict[str, str]] = []
        for m in request.messages:
            if m.role == "system":
                system_parts.append(m.content)
            else:
                messages.append({"role": m.role, "content": m.content})

        if not messages:
            messages = [{"role": "user", "content": "Respond."}]

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        if request.response_schema is not None:
            kwargs["tools"] = [
                {
                    "name": "respond",
                    "description": "Structured response",
                    "input_schema": request.response_schema,
                }
            ]
            kwargs["tool_choice"] = {"type": "tool", "name": "respond"}

        try:
            response = self._client.messages.create(**kwargs)
        except anthropic.APIStatusError as exc:
            raise LLMCallError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMCallError(f"Anthropic connection error: {exc}") from exc

        content = ""
        parsed = None

        if request.response_schema is not None:
            for block in response.content:
                if block.type == "tool_use":
                    parsed = block.input
                    content = json.dumps(parsed)
                    break
            if parsed is None:
                raise LLMValidationError("Anthropic response did not contain a tool_use block")
        else:
            for block in response.content:
                if block.type == "text":
                    content = block.text
                    break

        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        return LLMResponse(
            content=content,
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=request.model,
        )
