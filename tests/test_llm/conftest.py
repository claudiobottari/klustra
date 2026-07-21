from __future__ import annotations

from pathlib import Path

import pytest

from klustra.core.config import LLMRoleConfig
from klustra.llm import MockProvider
from klustra.llm.accounting import ListSink
from klustra.llm.provider import LLMMessage, LLMRequest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def list_sink() -> ListSink:
    return ListSink()


@pytest.fixture
def sample_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content="You are a helpful assistant."),
            LLMMessage(role="user", content="Hello"),
        ],
        model="test-model",
    )


@pytest.fixture
def sample_role_config() -> LLMRoleConfig:
    return LLMRoleConfig(provider="mock", model="test-model")
