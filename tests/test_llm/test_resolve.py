from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from klustra.core.errors import LLMKeyMissingError
from klustra.llm import (
    AnthropicProvider,
    MockProvider,
    OpenAICompatibleProvider,
    resolve_provider,
)


def test_resolve_mock_provider() -> None:
    provider = resolve_provider("mock")
    assert isinstance(provider, MockProvider)


def test_resolve_openai_with_key() -> None:
    provider = resolve_provider("openai", api_key="sk-test")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_resolve_openrouter_with_key() -> None:
    provider = resolve_provider("openrouter", api_key="or-test")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_resolve_anthropic_with_key() -> None:
    provider = resolve_provider("anthropic", api_key="ant-test")
    assert isinstance(provider, AnthropicProvider)


def test_resolve_from_env() -> None:
    with patch.dict(os.environ, {"OPENAI_API_KEY": "from-env"}):
        provider = resolve_provider("openai")
    assert isinstance(provider, OpenAICompatibleProvider)


def test_resolve_missing_key_raises() -> None:
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(LLMKeyMissingError, match="ANTHROPIC_API_KEY"):
            resolve_provider("anthropic")


def test_resolve_custom_base_url() -> None:
    provider = resolve_provider("openai", api_key="k", base_url="http://local:8080")
    assert isinstance(provider, OpenAICompatibleProvider)
