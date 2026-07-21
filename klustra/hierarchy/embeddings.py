"""Embedding provider abstraction and caching (SPEC §6.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """ABC for text embedding providers (SPEC §6.1).

    Implementations: OpenAI text-embedding-3-small, local sentence-transformers, mock.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


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
