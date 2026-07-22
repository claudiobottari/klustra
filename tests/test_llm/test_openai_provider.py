from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from klustra.core.errors import LLMCallError, LLMEmptyCompletionError, LLMValidationError
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
