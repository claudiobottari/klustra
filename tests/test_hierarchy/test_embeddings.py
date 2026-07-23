from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from klustra.core.config import LLMRoleConfig
from klustra.core.errors import ConfigError, LLMKeyMissingError
from klustra.hierarchy.embeddings import (
    OpenAICompatibleEmbeddingProvider,
    resolve_embedding_provider,
)


def _mock_embedding_response(vectors: list[list[float]]) -> MagicMock:
    data = []
    for v in vectors:
        item = MagicMock()
        item.embedding = v
        data.append(item)
    response = MagicMock()
    response.data = data
    return response


class TestOpenAICompatibleEmbeddingProvider:
    def test_embed_returns_one_vector_per_text(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test-key", model="text-embedding-3-small"
        )
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
        provider = OpenAICompatibleEmbeddingProvider(
            api_key="test-key", model="text-embedding-3-large"
        )
        mock_response = _mock_embedding_response([[1.0]])
        with patch.object(provider._client.embeddings, "create", return_value=mock_response):
            provider.embed(["x"])
        assert provider.model == "text-embedding-3-large"


class TestResolveEmbeddingProvider:
    def test_builds_from_config_when_key_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        cfg = LLMRoleConfig(provider="openai", model="text-embedding-3-small")
        provider = resolve_embedding_provider(cfg)
        assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
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


class TestEmbeddingProviderRouting:
    """Gap #9 (embeddings instance): base_url must resolve from the same table
    the chat roles use, so any OpenAI-compatible provider works without a
    per-provider branch."""

    def test_openrouter_is_accepted_and_routed_to_its_endpoint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        cfg = LLMRoleConfig(provider="openrouter", model="openai/text-embedding-3-small")

        provider = resolve_embedding_provider(cfg)

        assert isinstance(provider, OpenAICompatibleEmbeddingProvider)
        assert str(provider._client.base_url).rstrip("/") == "https://openrouter.ai/api/v1"
        assert provider.model == "openai/text-embedding-3-small"

    def test_openai_default_endpoint_is_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        cfg = LLMRoleConfig(provider="openai", model="text-embedding-3-small")

        provider = resolve_embedding_provider(cfg)

        assert str(provider._client.base_url).rstrip("/") == "https://api.openai.com/v1"

    def test_explicit_base_url_wins_over_the_provider_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        cfg = LLMRoleConfig(
            provider="openrouter",
            model="qwen/qwen3-embedding-8b",
            base_url="https://gateway.internal/v1",
        )

        provider = resolve_embedding_provider(cfg)

        assert str(provider._client.base_url).rstrip("/") == "https://gateway.internal/v1"

    def test_unlisted_provider_works_when_base_url_is_given(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The escape hatch: a self-hosted endpoint needs no code change."""
        monkeypatch.setenv("VLLM_API_KEY", "sk-local")
        cfg = LLMRoleConfig(provider="vllm", model="bge-m3", base_url="http://localhost:8000/v1")

        provider = resolve_embedding_provider(cfg)

        assert str(provider._client.base_url).rstrip("/") == "http://localhost:8000/v1"

    def test_unsupported_provider_error_lists_the_valid_options(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENROUTR_API_KEY", "typo")
        cfg = LLMRoleConfig(provider="openroutr", model="whatever")

        with pytest.raises(ConfigError) as exc:
            resolve_embedding_provider(cfg)

        message = str(exc.value)
        assert "'openroutr'" in message, "must still name the invalid provider"
        assert "'openai'" in message and "'openrouter'" in message, "must list valid options"
        assert "base_url" in message, "must point at the escape hatch"

    def test_anthropic_is_rejected_since_it_has_no_embeddings_api(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
        cfg = LLMRoleConfig(provider="anthropic", model="whatever")

        with pytest.raises(ConfigError, match="Unsupported embeddings provider"):
            resolve_embedding_provider(cfg)

    def test_api_key_env_var_follows_the_provider_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        cfg = LLMRoleConfig(provider="openrouter", model="openai/text-embedding-3-small")

        with pytest.raises(LLMKeyMissingError, match="OPENROUTER_API_KEY"):
            resolve_embedding_provider(cfg)

    def test_embeddings_and_chat_resolve_identical_base_urls(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The regression that caused this bug: two resolution paths drifting."""
        from klustra.llm import resolve_provider

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        cfg = LLMRoleConfig(provider="openrouter", model="m")

        embeddings = resolve_embedding_provider(cfg)
        chat = resolve_provider(cfg.provider, base_url=cfg.base_url)

        assert str(embeddings._client.base_url) == str(chat._client.base_url)  # type: ignore[attr-defined]


def test_embeddings_response_is_not_streamed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Embeddings have no streaming mode — the client must not pass stream= and
    must read the complete `data` list from a single response."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    provider = resolve_embedding_provider(
        LLMRoleConfig(provider="openrouter", model="openai/text-embedding-3-small")
    )
    response = _mock_embedding_response([[0.1], [0.2], [0.3]])

    with patch.object(provider._client.embeddings, "create", return_value=response) as mock_create:
        vectors = provider.embed(["a", "b", "c"])

    assert vectors == [[0.1], [0.2], [0.3]]
    assert "stream" not in mock_create.call_args.kwargs
