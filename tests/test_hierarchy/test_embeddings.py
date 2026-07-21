from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from klustra.core.config import LLMRoleConfig
from klustra.core.errors import ConfigError, LLMKeyMissingError
from klustra.hierarchy.embeddings import OpenAIEmbeddingProvider, resolve_embedding_provider


def _mock_embedding_response(vectors: list[list[float]]) -> MagicMock:
    data = []
    for v in vectors:
        item = MagicMock()
        item.embedding = v
        data.append(item)
    response = MagicMock()
    response.data = data
    return response


class TestOpenAIEmbeddingProvider:
    def test_embed_returns_one_vector_per_text(self) -> None:
        provider = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-small")
        mock_response = _mock_embedding_response([[0.1, 0.2], [0.3, 0.4]])
        with patch.object(
            provider._client.embeddings, "create", return_value=mock_response
        ) as mock_create:
            result = provider.embed(["hello", "world"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_create.assert_called_once_with(
            model="text-embedding-3-small", input=["hello", "world"]
        )

    def test_uses_configured_model(self) -> None:
        provider = OpenAIEmbeddingProvider(api_key="test-key", model="text-embedding-3-large")
        mock_response = _mock_embedding_response([[1.0]])
        with patch.object(provider._client.embeddings, "create", return_value=mock_response):
            provider.embed(["x"])
        assert provider.model == "text-embedding-3-large"


class TestResolveEmbeddingProvider:
    def test_builds_from_config_when_key_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        cfg = LLMRoleConfig(provider="openai", model="text-embedding-3-small")
        provider = resolve_embedding_provider(cfg)
        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.model == "text-embedding-3-small"

    def test_raises_key_missing_error_when_env_var_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cfg = LLMRoleConfig(provider="openai", model="text-embedding-3-small")
        with pytest.raises(LLMKeyMissingError, match="OPENAI_API_KEY"):
            resolve_embedding_provider(cfg)

    def test_raises_config_error_for_unsupported_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        cfg = LLMRoleConfig(provider="cohere", model="some-embedding-model")
        with pytest.raises(ConfigError, match="Unsupported embeddings provider"):
            resolve_embedding_provider(cfg)
