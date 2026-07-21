from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from klustra.core.errors import LLMCallError, LLMValidationError
from klustra.llm.anthropic_provider import AnthropicProvider
from klustra.llm.provider import LLMMessage, LLMRequest


@pytest.fixture
def provider() -> AnthropicProvider:
    return AnthropicProvider(api_key="test-key")


def _mock_text_response(text: str, input_tokens: int = 10, output_tokens: int = 5) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response = MagicMock()
    response.content = [block]
    response.usage = usage
    return response


def _mock_tool_response(
    data: dict,
    input_tokens: int = 10,
    output_tokens: int = 5,  # noqa: B006
) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.input = data
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    response = MagicMock()
    response.content = [block]
    response.usage = usage
    return response


def test_call_plain_text(provider: AnthropicProvider) -> None:
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hi")],
        model="claude-sonnet-4-6",
    )
    mock_resp = _mock_text_response("Hello!")
    with patch.object(provider._client.messages, "create", return_value=mock_resp):
        response = provider.call(request)
    assert response.content == "Hello!"
    assert response.tokens_in == 10
    assert response.tokens_out == 5


def test_call_structured_output(provider: AnthropicProvider) -> None:
    schema = {"type": "object", "properties": {"y": {"type": "string"}}, "required": ["y"]}
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="give y")],
        model="claude-sonnet-4-6",
        response_schema=schema,
    )
    mock_resp = _mock_tool_response({"y": "value"})
    with patch.object(provider._client.messages, "create", return_value=mock_resp):
        response = provider.call(request)
    assert response.parsed == {"y": "value"}


def test_call_missing_tool_use_raises(provider: AnthropicProvider) -> None:
    schema = {"type": "object", "properties": {"z": {"type": "integer"}}}
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="bad")],
        model="claude-sonnet-4-6",
        response_schema=schema,
    )
    mock_resp = _mock_text_response("oops")
    with patch.object(provider._client.messages, "create", return_value=mock_resp):
        with pytest.raises(LLMValidationError, match="tool_use"):
            provider.call(request)


def test_system_message_extracted(provider: AnthropicProvider) -> None:
    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content="Be brief."),
            LLMMessage(role="user", content="hi"),
        ],
        model="claude-sonnet-4-6",
    )
    mock_resp = _mock_text_response("Hi!")
    with patch.object(provider._client.messages, "create", return_value=mock_resp) as mock_create:
        provider.call(request)
    kwargs = mock_create.call_args[1]
    assert kwargs["system"] == "Be brief."
    assert all(m["role"] != "system" for m in kwargs["messages"])


def test_call_api_error_raises_llm_call_error(provider: AnthropicProvider) -> None:
    import anthropic

    request = LLMRequest(
        messages=[LLMMessage(role="user", content="fail")],
        model="claude-sonnet-4-6",
    )
    exc = anthropic.APIStatusError(
        message="overloaded",
        response=MagicMock(status_code=529, headers={}),
        body=None,
    )
    with patch.object(provider._client.messages, "create", side_effect=exc):
        with pytest.raises(LLMCallError, match="529"):
            provider.call(request)
