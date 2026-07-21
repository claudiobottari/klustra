from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from klustra.core.errors import LLMCallError, LLMValidationError
from klustra.llm.openai_provider import OpenAICompatibleProvider
from klustra.llm.provider import LLMMessage, LLMRequest


@pytest.fixture
def provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(api_key="test-key", base_url="http://fake")


def _mock_completion(
    content: str, prompt_tokens: int = 10, completion_tokens: int = 5
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
