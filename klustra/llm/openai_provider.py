from __future__ import annotations

import json
from typing import Any

import openai

from klustra.core.errors import LLMCallError, LLMEmptyCompletionError, LLMValidationError
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse
from klustra.llm.retry import llm_retry

_OPENAI_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible provider: works with OpenAI, OpenRouter, or any base_url."""

    name = "openai_compatible"

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        url = base_url or _OPENAI_BASE_URLS["openai"]
        self._client = openai.OpenAI(api_key=api_key, base_url=url)

    def call(self, request: LLMRequest) -> LLMResponse:
        result: LLMResponse = self._call_with_retry(request)
        return result

    @llm_retry()
    def _call_with_retry(self, request: LLMRequest) -> LLMResponse:
        messages: list[dict[str, str]] = [
            {"role": m.role, "content": m.content} for m in request.messages
        ]

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens

        if request.response_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "strict": True,
                    "schema": request.response_schema,
                },
            }

        try:
            completion = self._client.chat.completions.create(**kwargs)
        except openai.APIStatusError as exc:
            raise LLMCallError(f"OpenAI API error {exc.status_code}: {exc.message}") from exc
        except openai.APIConnectionError as exc:
            raise LLMCallError(f"OpenAI connection error: {exc}") from exc

        if not completion.choices:
            raise LLMEmptyCompletionError(
                f"Model {request.model} returned no choices "
                f"(id={completion.id!r}, model={completion.model!r}, "
                f"extra={completion.model_extra!r})"
            )
        choice = completion.choices[0]
        raw = choice.message.content
        if raw is None or not raw.strip():
            raise LLMEmptyCompletionError(f"Model {request.model} returned empty completion")
        content = raw
        usage = completion.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        parsed = None
        if request.response_schema is not None:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                raise LLMValidationError(f"Response is not valid JSON: {exc}") from exc

        return LLMResponse(
            content=content,
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=request.model,
        )
