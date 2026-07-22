from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from klustra.core.errors import LLMCallError, LLMRateLimitError, LLMValidationError
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse
from klustra.llm.retry import (
    call_with_corrective_retry,
    find_body_model_ref,
    is_rate_limit_error,
    llm_retry,
)

logger = logging.getLogger(__name__)

_DEBUG_SNIPPET_MAX_CHARS = 200


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

        logger.debug(
            "[llm] request model=%r messages=%d max_tokens=%r schema=%s temperature=%s",
            request.model,
            len(messages),
            kwargs["max_tokens"],
            request.response_schema is not None,
            request.temperature,
        )

        try:
            response = self._client.messages.create(**kwargs)
        except anthropic.APIStatusError as exc:
            if is_rate_limit_error(exc.status_code, exc.body):
                body_model = find_body_model_ref(exc.body)
                logger.warning(
                    "[llm] rate-limited/overloaded calling model=%r "
                    "(status=%d, body_model_ref=%r%s)",
                    request.model,
                    exc.status_code,
                    body_model,
                    ""
                    if body_model in (None, request.model)
                    else " -- MISMATCH vs requested model",
                )
                raise LLMRateLimitError(
                    f"Anthropic API rate limit/overload {exc.status_code}: {exc.message} "
                    f"(requested_model={request.model!r}, body_model_ref={body_model!r})"
                ) from exc
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

        logger.debug(
            "[llm] response model=%r tokens_in=%d tokens_out=%d content_snippet=%r",
            request.model,
            tokens_in,
            tokens_out,
            content[:_DEBUG_SNIPPET_MAX_CHARS],
        )

        return LLMResponse(
            content=content,
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=request.model,
        )
