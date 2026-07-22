from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from klustra.core.errors import (
    LLMCallError,
    LLMEmptyCompletionError,
    LLMRateLimitError,
    LLMValidationError,
)
from klustra.llm.openai_provider import OpenAICompatibleProvider
from klustra.llm.provider import LLMMessage, LLMRequest


@pytest.fixture
def provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(api_key="test-key", base_url="http://fake")


def _mock_completion(
    content: str | None, prompt_tokens: int = 10, completion_tokens: int = 5
) -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage = usage
    return completion


def test_call_plain_text(provider: OpenAICompatibleProvider) -> None:
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4",
    )
    mock_completion = _mock_completion("Hello!")
    with patch.object(provider._client.chat.completions, "create", return_value=mock_completion):
        response = provider.call(request)
    assert response.content == "Hello!"
    assert response.tokens_in == 10
    assert response.tokens_out == 5
    assert response.parsed is None


def test_call_structured_output(provider: OpenAICompatibleProvider) -> None:
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="give x")],
        model="gpt-4",
        response_schema=schema,
    )
    mock_completion = _mock_completion('{"x": 42}')
    with patch.object(provider._client.chat.completions, "create", return_value=mock_completion):
        response = provider.call(request)
    assert response.parsed == {"x": 42}


def test_call_invalid_json_raises_validation_error(
    provider: OpenAICompatibleProvider,
) -> None:
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="bad")],
        model="gpt-4",
        response_schema=schema,
    )
    mock_completion = _mock_completion("not json at all")
    with patch.object(provider._client.chat.completions, "create", return_value=mock_completion):
        with pytest.raises(LLMValidationError, match="not valid JSON"):
            provider.call(request)


def test_call_api_error_raises_llm_call_error(
    provider: OpenAICompatibleProvider,
) -> None:
    import openai

    request = LLMRequest(
        messages=[LLMMessage(role="user", content="fail")],
        model="gpt-4",
    )
    exc = openai.APIStatusError(
        message="rate limited",
        response=MagicMock(status_code=429, headers={}),
        body=None,
    )
    with patch.object(provider._client.chat.completions, "create", side_effect=exc):
        with pytest.raises(LLMCallError, match="429"):
            provider.call(request)


def test_empty_completion_retries_then_succeeds(
    provider: OpenAICompatibleProvider,
) -> None:
    """Empty completion is transient: retried via LLMCallError branch, succeeds on 3rd."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4",
    )
    empty = _mock_completion("")
    whitespace = _mock_completion("   \n")
    good = _mock_completion("Hello!", prompt_tokens=12, completion_tokens=7)
    with patch.object(
        provider._client.chat.completions,
        "create",
        side_effect=[empty, whitespace, good],
    ) as mock_create:
        response = provider.call(request)
    assert response.content == "Hello!"
    assert response.tokens_in == 12
    assert response.tokens_out == 7
    assert mock_create.call_count == 3


def test_none_choices_raises_empty_completion_error_not_typeerror(
    provider: OpenAICompatibleProvider,
) -> None:
    """completion.choices=None (lenient SDK parsing of a malformed OpenRouter response)
    must raise LLMEmptyCompletionError, not TypeError, and must be retried like the
    empty-content case."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4",
    )
    none_choices = MagicMock(
        id="cmpl-1",
        model="gpt-4",
        choices=None,
        model_extra={"error": {"message": "upstream failure", "code": 502}},
    )
    good = _mock_completion("Hello!", prompt_tokens=12, completion_tokens=7)
    with patch.object(
        provider._client.chat.completions,
        "create",
        side_effect=[none_choices, good],
    ) as mock_create:
        response = provider.call(request)
    assert response.content == "Hello!"
    assert mock_create.call_count == 2


def test_none_choices_message_includes_diagnostic_fields(
    provider: OpenAICompatibleProvider,
) -> None:
    """The raised error carries whatever OpenRouter put on the completion, not just 'empty'."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4",
    )
    none_choices = MagicMock(
        id="cmpl-err",
        model="gpt-4",
        choices=None,
        model_extra={"error": {"message": "upstream failure", "code": 502}},
    )
    with (
        patch.object(
            provider._client.chat.completions,
            "create",
            side_effect=[none_choices] * 3,
        ),
        pytest.raises(LLMCallError, match="cmpl-err"),
    ):
        provider.call(request)


def test_none_message_raises_empty_completion_error_not_attributeerror(
    provider: OpenAICompatibleProvider,
) -> None:
    """choice.message=None (same lenient-parsing mechanism as choices=None) must raise
    LLMEmptyCompletionError, not AttributeError."""
    request = LLMRequest(messages=[LLMMessage(role="user", content="hi")], model="gpt-4")
    choice = MagicMock(message=None)
    none_message = MagicMock(choices=[choice])
    good = _mock_completion("Hello!", prompt_tokens=12, completion_tokens=7)
    with patch.object(
        provider._client.chat.completions,
        "create",
        side_effect=[none_message, good],
    ) as mock_create:
        response = provider.call(request)
    assert response.content == "Hello!"
    assert mock_create.call_count == 2


def test_non_string_content_raises_empty_completion_error_not_attributeerror(
    provider: OpenAICompatibleProvider,
) -> None:
    """content that isn't a str (lenient SDK parsing leniency) must raise
    LLMEmptyCompletionError, not AttributeError from calling .strip() on it."""
    request = LLMRequest(messages=[LLMMessage(role="user", content="hi")], model="gpt-4")
    bad_content = _mock_completion(content=None)
    bad_content.choices[0].message.content = {"unexpected": "object"}
    good = _mock_completion("Hello!", prompt_tokens=12, completion_tokens=7)
    with patch.object(
        provider._client.chat.completions,
        "create",
        side_effect=[bad_content, good],
    ) as mock_create:
        response = provider.call(request)
    assert response.content == "Hello!"
    assert mock_create.call_count == 2


def _choices_none_completion() -> MagicMock:
    return MagicMock(id="c1", model="gpt-4", choices=None, model_extra={})


def _content_completion(content: str | None) -> MagicMock:
    return _mock_completion(content)


@pytest.mark.parametrize("schema", [None, {"type": "object"}], ids=["no_schema", "with_schema"])
@pytest.mark.parametrize(
    "make_completion",
    [
        _choices_none_completion,
        lambda: _content_completion(None),
        lambda: _content_completion(""),
        lambda: _content_completion("   \n"),
    ],
    ids=["choices_none", "content_none", "content_empty", "content_whitespace"],
)
def test_malformed_response_matrix_always_raises_empty_completion_error(
    provider: OpenAICompatibleProvider,
    make_completion,
    schema: dict[str, object] | None,
) -> None:
    """Every malformed-response shape, with and without response_schema, must raise
    LLMEmptyCompletionError — never an unhandled TypeError/AttributeError/JSONDecodeError."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4",
        response_schema=schema,
    )
    completion = make_completion()
    with (
        patch.object(
            provider._client.chat.completions,
            "create",
            return_value=completion,
        ),
        pytest.raises(LLMEmptyCompletionError),
    ):
        provider.call(request)


def test_invalid_json_corrective_retry_feeds_error_back(
    provider: OpenAICompatibleProvider,
) -> None:
    """Invalid JSON triggers a corrective retry whose API call carries the parse
    error and a snippet of the bad response, then succeeds."""
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="give x")],
        model="gpt-4",
        response_schema=schema,
    )
    bad = _mock_completion('```json\n{"x": 42}\n```')
    good = _mock_completion('{"x": 42}')
    with patch.object(
        provider._client.chat.completions,
        "create",
        side_effect=[bad, good],
    ) as mock_create:
        response = provider.call(request)
    assert response.parsed == {"x": 42}
    assert mock_create.call_count == 2

    retry_messages = mock_create.call_args_list[1].kwargs["messages"]
    assert retry_messages[0] == {"role": "user", "content": "give x"}
    assert retry_messages[1]["role"] == "assistant"
    assert "```json" in retry_messages[1]["content"], "snippet of the bad response fed back"
    assert retry_messages[2]["role"] == "user"
    assert "REJECTED" in retry_messages[2]["content"]
    assert "not valid JSON" in retry_messages[2]["content"]
    assert "no markdown fences" in retry_messages[2]["content"]


def test_invalid_json_exhausts_corrective_retries(
    provider: OpenAICompatibleProvider,
) -> None:
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="give x")],
        model="gpt-4",
        response_schema={"type": "object"},
    )
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=_mock_completion("not json"),
    ) as mock_create:
        with pytest.raises(LLMValidationError, match="not valid JSON"):
            provider.call(request)
    assert mock_create.call_count == 3


def test_invalid_json_error_carries_truncation_diagnostics(
    provider: OpenAICompatibleProvider,
) -> None:
    """The validation error reports response length, finish_reason, and max_tokens
    so a max_tokens truncation ('length') is diagnosable from the message alone."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="give x")],
        model="gpt-4",
        response_schema={"type": "object"},
        max_tokens=64,
    )
    truncated = _mock_completion('{"x": "cut off mid stri')
    truncated.choices[0].finish_reason = "length"
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=truncated,
    ):
        with pytest.raises(LLMValidationError) as exc_info:
            provider.call(request)
    msg = str(exc_info.value)
    assert "response_chars=23" in msg
    assert "finish_reason='length'" in msg
    assert "max_tokens=64" in msg
    assert exc_info.value.raw_content == '{"x": "cut off mid stri'


# --- 429 / rate-limit backoff (separate from the corrective-JSON loop above) ---


def _status_error(status_code: int, body: object = None, message: str = "err") -> Any:
    import openai

    return openai.APIStatusError(
        message=message,
        response=MagicMock(status_code=status_code, headers={}),
        body=body,
    )


def test_429_retried_with_configured_attempts_and_longer_backoff_succeeds_later(
    provider: OpenAICompatibleProvider,
) -> None:
    """A 429 is classified as LLMRateLimitError and retried up to the request's
    configured retry_attempts (LLMRoleConfig.retry_attempts), with the rate-limit
    backoff (not the default one) — separate attempt budget from the corrective
    JSON-retry loop tested above."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="deepseek/deepseek-v4-flash",
        retry_attempts=4,
    )
    rate_limited = _status_error(429, body={"error": {"message": "rate limited"}})
    good = _mock_completion("Hello!", prompt_tokens=12, completion_tokens=7)
    with (
        patch("tenacity.nap.time.sleep"),
        patch.object(
            provider._client.chat.completions,
            "create",
            side_effect=[rate_limited, rate_limited, rate_limited, good],
        ) as mock_create,
    ):
        response = provider.call(request)
    assert response.content == "Hello!"
    assert mock_create.call_count == 4


def test_429_exhausts_configured_attempts_raises_rate_limit_error(
    provider: OpenAICompatibleProvider,
) -> None:
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4",
        retry_attempts=2,
    )
    rate_limited = _status_error(429)
    with (
        patch("tenacity.nap.time.sleep"),
        patch.object(
            provider._client.chat.completions,
            "create",
            side_effect=[rate_limited, rate_limited],
        ) as mock_create,
        pytest.raises(LLMRateLimitError),
    ):
        provider.call(request)
    assert mock_create.call_count == 2


def test_openrouter_engine_overloaded_classified_as_rate_limit_even_without_429(
    provider: OpenAICompatibleProvider,
) -> None:
    """OpenRouter can signal overload via provider_error_code without a 429 status."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4",
        retry_attempts=2,
    )
    overloaded = _status_error(
        503,
        body={"error": {"metadata": {"provider_error_code": "engine_overloaded"}}},
    )
    good = _mock_completion("Hello!", prompt_tokens=12, completion_tokens=7)
    with (
        patch("tenacity.nap.time.sleep"),
        patch.object(
            provider._client.chat.completions,
            "create",
            side_effect=[overloaded, good],
        ) as mock_create,
    ):
        response = provider.call(request)
    assert response.content == "Hello!"
    assert mock_create.call_count == 2


def test_429_logs_requested_model_and_body_model_ref(
    provider: OpenAICompatibleProvider,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When a 429 fires, the log must carry the exact model string we requested
    plus whatever model reference the error body carries — so a routing-name
    mismatch (vs. a real one) is diagnosable without guessing."""
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="deepseek/deepseek-v4-flash",
        retry_attempts=2,
    )
    rate_limited = _status_error(
        429,
        body={"error": {"message": "rate limited", "model": "deepseek/deepseek-chat"}},
    )
    good = _mock_completion("Hello!", prompt_tokens=12, completion_tokens=7)
    with (
        patch("tenacity.nap.time.sleep"),
        patch.object(
            provider._client.chat.completions,
            "create",
            side_effect=[rate_limited, good],
        ),
        caplog.at_level("WARNING"),
    ):
        provider.call(request)
    warning_text = "\n".join(r.message for r in caplog.records)
    assert "deepseek/deepseek-v4-flash" in warning_text
    assert "deepseek/deepseek-chat" in warning_text
