"""Shared fixtures for test_hierarchy."""

from __future__ import annotations

import hashlib

import numpy as np

from klustra.hierarchy.clustering import PageInput
from klustra.hierarchy.embeddings import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider for tests.

    Returns vectors constructed so that pages in the same group
    have high cosine similarity and pages in different groups are orthogonal.
    """

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self.call_count = 0
        self.last_texts: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        self.last_texts = texts
        return [self._vector_for(t) for t in texts]

    def _vector_for(self, text: str) -> list[float]:
        """Generate a deterministic vector from text content."""
        h = hashlib.sha256(text.encode()).digest()
        rng = np.random.default_rng(int.from_bytes(h[:8], "big"))
        vec = rng.standard_normal(self.dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()


def make_cluster_pages(
    prefix: str,
    count: int,
    base_text: str,
) -> list[PageInput]:
    """Create pages that will embed to similar vectors (same base_text with index suffix)."""
    pages: list[PageInput] = []
    for i in range(count):
        body = f"{base_text} — variant {i}"
        content_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
        pages.append(
            PageInput(
                entity_id=f"{prefix}.item-{i}",
                content_hash=content_hash,
                body_md=body,
            )
        )
    return pages


class ClusterableEmbeddingProvider(EmbeddingProvider):
    """Provider that returns vectors designed to form clear clusters.

    Assigns pages to cluster groups by entity_id prefix. Pages in the same
    group get vectors pointing in the same direction (with small noise).
    """

    def __init__(self, dim: int = 64, noise: float = 0.05) -> None:
        self.dim = dim
        self.noise = noise
        self.call_count = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        return [self._vector_for(t) for t in texts]

    def _vector_for(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:8], "big")
        rng = np.random.default_rng(seed)

        # Determine cluster direction from the text prefix
        if "group-a" in text:
            direction = self._fixed_direction(0)
        elif "group-b" in text:
            direction = self._fixed_direction(1)
        elif "outlier" in text:
            direction = rng.standard_normal(self.dim)
        else:
            direction = rng.standard_normal(self.dim)

        noise = rng.standard_normal(self.dim) * self.noise
        vec = direction + noise
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def _fixed_direction(self, cluster_idx: int) -> np.ndarray:
        """Return a fixed unit vector for a given cluster index."""
        rng = np.random.default_rng(cluster_idx * 12345)
        vec = rng.standard_normal(self.dim)
        return vec / np.linalg.norm(vec)
