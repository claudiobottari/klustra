"""Embedding provider abstraction and caching (SPEC §6.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod

import openai

from klustra.core.config import LLMRoleConfig
from klustra.core.errors import ConfigError, LLMKeyMissingError, LLMTimeoutError
from klustra.llm.provider import (
    DEFAULT_TIMEOUT_SECONDS,
    OPENAI_COMPATIBLE_PROVIDERS,
    resolve_base_url,
    supported_providers_hint,
)


class EmbeddingProvider(ABC):
    """ABC for text embedding providers (SPEC §6.1).

    Implementations: OpenAI text-embedding-3-small, local sentence-transformers, mock.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """EmbeddingProvider for any OpenAI-compatible /embeddings endpoint (SPEC §8, §12).

    OpenAI, OpenRouter and self-hosted gateways share the same request/response
    shape, so the only thing that varies is `base_url` — the same routing the
    chat roles get from `resolve_base_url`. Embeddings are never streamed:
    `embeddings.create` returns the complete `data` list in one response.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        base_url: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.model = model
        self._timeout_seconds = timeout_seconds
        # max_retries=0 + explicit timeout: an embeddings batch is one blocking
        # call over potentially hundreds of texts and must never hang silently.
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embeddings.create(model=self.model, input=texts)
        except openai.APITimeoutError as exc:
            raise LLMTimeoutError(
                f"Embeddings request to {self.model!r} timed out after "
                f"{self._timeout_seconds}s ({len(texts)} text(s))"
            ) from exc
        return [item.embedding for item in response.data]


def resolve_embedding_provider(cfg: LLMRoleConfig) -> EmbeddingProvider:
    """Build a concrete EmbeddingProvider from an [llm.embeddings] config section.

    Any OpenAI-compatible provider works (SPEC §8) — resolution goes through the
    same OPENAI_COMPATIBLE_PROVIDERS table the chat roles use, so `openrouter`
    and friends need no branch here. An unlisted provider is still accepted when
    an explicit base_url is given, which is the escape hatch for self-hosted
    endpoints.

    Secrets stay in env only (SPEC §12) — resolved via resolve_api_key, never read
    from klustra.toml. Raises LLMKeyMissingError (not a silent None) if the env var
    for the configured provider is unset.
    """
    from klustra.core.config import resolve_api_key

    base_url = resolve_base_url(cfg.provider, cfg.base_url)
    if base_url is None and cfg.provider not in OPENAI_COMPATIBLE_PROVIDERS:
        raise ConfigError(
            f"Unsupported embeddings provider {cfg.provider!r}. "
            f"Supported: {supported_providers_hint()}. "
            f"Any other OpenAI-compatible endpoint works too — set "
            f"[llm.embeddings] base_url explicitly."
        )

    key = resolve_api_key(cfg.provider)
    if not key:
        raise LLMKeyMissingError(
            f"No API key for embeddings provider {cfg.provider!r}. "
            f"Set {cfg.provider.upper()}_API_KEY environment variable."
        )
    return OpenAICompatibleEmbeddingProvider(
        api_key=key,
        model=cfg.model,
        base_url=base_url,
        timeout_seconds=cfg.timeout_seconds,
    )


class EmbeddingCache:
    """In-memory cache: content_hash → embedding vector.

    Prevents redundant embedding API calls for unchanged pages.
    """

    def __init__(self) -> None:
        self._store: dict[str, list[float]] = {}

    def get(self, content_hash: str) -> list[float] | None:
        return self._store.get(content_hash)

    def put(self, content_hash: str, embedding: list[float]) -> None:
        self._store[content_hash] = embedding

    def get_or_embed(
        self,
        texts: list[str],
        hashes: list[str],
        provider: EmbeddingProvider,
    ) -> list[list[float]]:
        """Return embeddings for all texts, using cache where possible."""
        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, h in enumerate(hashes):
            cached = self.get(h)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(texts[i])

        if uncached_texts:
            new_embeddings = provider.embed(uncached_texts)
            for idx, emb in zip(uncached_indices, new_embeddings, strict=True):
                self.put(hashes[idx], emb)
                results[idx] = emb

        return [r for r in results if r is not None]
