from __future__ import annotations

import json
from typing import Any

import openai

from klustra.core.errors import LLMCallError, LLMEmptyCompletionError, LLMValidationError
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse
from klustra.llm.retry import call_with_corrective_retry, llm_retry

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
        return call_with_corrective_retry(self._call_with_retry, request)

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
        except openai.APIError as exc:
            # Catch-all for the rest of the openai.APIError hierarchy (e.g.
            # APIResponseValidationError) that isn't a APIStatusError/APIConnectionError
            # subclass — without this, such an exception would bypass the retry
            # taxonomy entirely instead of becoming a retryable LLMCallError.
            raise LLMCallError(f"OpenAI API error: {exc}") from exc

        if not completion.choices:
            raise LLMEmptyCompletionError(
                f"Model {request.model} returned no choices "
                f"(id={completion.id!r}, model={completion.model!r}, "
                f"extra={completion.model_extra!r})"
            )
        choice = completion.choices[0]
        message = choice.message
        raw = message.content if message is not None else None
        if raw is None or not isinstance(raw, str) or not raw.strip():
            raise LLMEmptyCompletionError(
                f"Model {request.model} returned empty or malformed completion "
                f"(message={message!r}, content={raw!r})"
            )
        content = raw
        usage = completion.usage
        tokens_in = (usage.prompt_tokens or 0) if usage else 0
        tokens_out = (usage.completion_tokens or 0) if usage else 0

        parsed = None
        if request.response_schema is not None:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                # finish_reason == "length" is the definitive max_tokens-truncation
                # signal; report it alongside sizes so recurrences are diagnosable.
                max_tok = "not set" if request.max_tokens is None else request.max_tokens
                raise LLMValidationError(
                    f"Response is not valid JSON: {exc} "
                    f"(response_chars={len(content)}, tokens_out={tokens_out}, "
                    f"finish_reason={choice.finish_reason!r}, max_tokens={max_tok})",
                    raw_content=content,
                ) from exc

        return LLMResponse(
            content=content,
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=request.model,
        )
