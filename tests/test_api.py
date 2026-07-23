from __future__ import annotations

from pathlib import Path

import pytest

from klustra.api import Klustra
from klustra.core.errors import ConfigError, LLMKeyMissingError
from klustra.hierarchy.embeddings import EmbeddingProvider, OpenAICompatibleEmbeddingProvider


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

        assert isinstance(first, OpenAICompatibleEmbeddingProvider)
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


class TestRoleModelResolution:
    """Regression: a missing [llm.hierarchy] section used to leave the literal
    placeholder "default" as the model, which reached the provider as a model id
    and came back as `400 - 'default is not a valid model ID'`."""

    def _project(self, root: Path, extra: str = "") -> Klustra:
        root.mkdir(parents=True, exist_ok=True)
        (root / "klustra.toml").write_text(
            '[llm.extraction]\nprovider = "openrouter"\nmodel = "deepseek/deepseek-v4-flash"\n\n'
            '[llm.librarian]\nprovider = "openrouter"\nmodel = "deepseek/deepseek-v4-pro"\n'
            + extra,
            encoding="utf-8",
        )
        return Klustra(root=root, embedding_provider=_FakeEmbedder())

    def test_missing_hierarchy_section_never_yields_the_placeholder(self, tmp_path: Path) -> None:
        nx = self._project(tmp_path / "p")

        config = nx._build_hierarchy_config()

        assert config.model != "default", "placeholder must never reach the provider"
        assert config.model == "deepseek/deepseek-v4-flash", "falls back to [llm.extraction]"

    def test_missing_judge_section_never_yields_the_placeholder(self, tmp_path: Path) -> None:
        nx = self._project(tmp_path / "p")

        config = nx._build_incremental_config()

        assert config.judge_model != "default"
        assert config.judge_model == "deepseek/deepseek-v4-flash"

    def test_explicit_role_sections_win_over_the_fallback(self, tmp_path: Path) -> None:
        nx = self._project(
            tmp_path / "p",
            extra=(
                '\n[llm.hierarchy]\nprovider = "openrouter"\n'
                'model = "anthropic/claude-sonnet-4-6"\n'
                '\n[llm.judge]\nprovider = "openrouter"\nmodel = "qwen/qwen3-8b"\n'
            ),
        )

        assert nx._build_hierarchy_config().model == "anthropic/claude-sonnet-4-6"
        assert nx._build_incremental_config().judge_model == "qwen/qwen3-8b"

    def test_role_retry_attempts_follow_the_resolved_section(self, tmp_path: Path) -> None:
        nx = self._project(
            tmp_path / "p",
            extra=('\n[llm.hierarchy]\nprovider = "openrouter"\nmodel = "m"\nretry_attempts = 7\n'),
        )

        assert nx._build_hierarchy_config().retry_attempts == 7
        # judge has no section — inherits extraction's budget, not a placeholder
        assert nx._build_incremental_config().judge_retry_attempts == 3

    def test_no_llm_config_at_all_raises_a_clear_config_error(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        (root / "klustra.toml").write_text("[hierarchy]\nmin_cluster_size = 4\n", encoding="utf-8")
        nx = Klustra(root=root, embedding_provider=_FakeEmbedder())

        with pytest.raises(ConfigError) as exc:
            nx._build_hierarchy_config()

        message = str(exc.value)
        assert "[llm.hierarchy]" in message
        assert "[llm.extraction]" in message


def test_build_hierarchy_fails_fast_before_embedding_when_llm_config_is_missing(
    tmp_path: Path,
) -> None:
    """The config error must not surface only after embedding + clustering has
    already been paid for."""
    root = tmp_path / "p"
    root.mkdir()
    (root / "klustra.toml").write_text("[hierarchy]\nmin_cluster_size = 4\n", encoding="utf-8")

    class _ExplodingEmbedder(EmbeddingProvider):
        def embed(self, texts: list[str]) -> list[list[float]]:
            raise AssertionError("embedding must not run before config validation")

    nx = Klustra(root=root, embedding_provider=_ExplodingEmbedder())
    from klustra.core.state_store import PageRecord

    for i in range(6):
        nx.state.put_page(
            PageRecord(entity_id=f"c.{i}", level=0, content_hash=f"h{i}", title=f"T{i}"),
            run_id="r",
        )

    with pytest.raises(ConfigError, match=r"\[llm\.hierarchy\]"):
        nx.build_hierarchy(full=True)
