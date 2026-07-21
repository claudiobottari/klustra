from __future__ import annotations

import json

from klustra.llm import MockProvider
from klustra.llm.provider import LLMMessage, LLMRequest, LLMResponse


def test_mock_provider_default_response(mock_provider: MockProvider) -> None:
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="hello")],
        model="test-model",
    )
    response = mock_provider.call(request)
    assert isinstance(response, LLMResponse)
    assert json.loads(response.content) == {"result": "mock"}
    assert response.model == "test-model"


def test_mock_provider_schema_fallback(mock_provider: MockProvider) -> None:
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "count": {"type": "integer"},
        },
        "required": ["title", "count"],
    }
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="generate")],
        model="test-model",
        response_schema=schema,
    )
    response = mock_provider.call(request)
    assert response.parsed is not None
    assert response.parsed["title"] == "mock_value"
    assert response.parsed["count"] == 0


def test_mock_provider_canned_response() -> None:
    import hashlib

    content = "What is 2+2?"
    key = hashlib.sha256(content.encode()).hexdigest()[:16]
    provider = MockProvider(canned={key: '{"answer": 4}'})

    request = LLMRequest(
        messages=[LLMMessage(role="user", content="What is 2+2?")],
        model="math-model",
    )
    response = provider.call(request)
    assert json.loads(response.content) == {"answer": 4}


def test_mock_provider_tokens_nonzero(mock_provider: MockProvider) -> None:
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="a" * 100)],
        model="test-model",
    )
    response = mock_provider.call(request)
    assert response.tokens_in >= 1
    assert response.tokens_out >= 1


def test_mock_provider_nested_schema() -> None:
    schema = {
        "type": "object",
        "properties": {
            "items": {"type": "array"},
            "meta": {
                "type": "object",
                "properties": {"version": {"type": "string"}},
                "required": ["version"],
            },
        },
        "required": ["items", "meta"],
    }
    provider = MockProvider()
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="nested")],
        model="test-model",
        response_schema=schema,
    )
    response = provider.call(request)
    assert response.parsed is not None
    assert response.parsed["items"] == []
    assert response.parsed["meta"]["version"] == "mock_value"
