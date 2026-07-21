from __future__ import annotations

from pathlib import Path

import pytest

from klustra.api import Klustra
from klustra.core.errors import ConfigError, LLMKeyMissingError
from klustra.hierarchy.embeddings import EmbeddingProvider, OpenAIEmbeddingProvider


class _FakeEmbedder(EmbeddingProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


def _write_klustra_toml(root: Path, *, with_embeddings: bool) -> None:
    root.mkdir(parents=True, exist_ok=True)
    body = ""
    if with_embeddings:
        body = '[llm.embeddings]\nprovider = "openai"\nmodel = "text-embedding-3-small"\n'
    (root / "klustra.toml").write_text(body, encoding="utf-8")


class TestEmbeddingProviderWiring:
    def test_injected_instance_is_used_as_is(self, tmp_path: Path) -> None:
        """Explicit embedding_provider passed to the constructor wins over config."""
        _write_klustra_toml(tmp_path, with_embeddings=False)
        fake = _FakeEmbedder()
        nx = Klustra(root=tmp_path, embedding_provider=fake)
        assert nx.embedding_provider is fake

    def test_builds_and_caches_from_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        _write_klustra_toml(tmp_path, with_embeddings=True)
        nx = Klustra(root=tmp_path)

        first = nx.embedding_provider
        second = nx.embedding_provider

        assert isinstance(first, OpenAIEmbeddingProvider)
        assert first.model == "text-embedding-3-small"
        assert first is second  # constructed once, cached thereafter

    def test_raises_config_error_when_section_missing(self, tmp_path: Path) -> None:
        _write_klustra_toml(tmp_path, with_embeddings=False)
        nx = Klustra(root=tmp_path)
        with pytest.raises(ConfigError, match="llm.embeddings"):
            _ = nx.embedding_provider

    def test_raises_key_missing_when_env_var_absent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        _write_klustra_toml(tmp_path, with_embeddings=True)
        nx = Klustra(root=tmp_path)
        with pytest.raises(LLMKeyMissingError, match="OPENAI_API_KEY"):
            _ = nx.embedding_provider
