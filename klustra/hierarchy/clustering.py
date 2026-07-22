"""Clustering module — UMAP + HDBSCAN/GMM (SPEC §6.1)."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from klustra.hierarchy.embeddings import EmbeddingCache, EmbeddingProvider
from klustra.logging_setup import log_op

try:
    import numpy as np
    from numpy.typing import NDArray
except ImportError as _e:
    raise ImportError("klustra[hierarchy] extra required: uv sync --extra hierarchy") from _e


class PageInput(BaseModel):
    """Input to cluster_pages(): a page's identity, content hash, and body text."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    content_hash: str
    body_md: str


class ClusterAssignment(BaseModel):
    """One page's cluster assignment."""

    model_config = ConfigDict(frozen=True)

    entity_id: str
    cluster_id: int = Field(description="-1 = outlier in hard mode")
    probability: float = Field(ge=0.0, le=1.0)
    memberships: list[int] = Field(
        default_factory=list, description="Secondary clusters (soft mode)"
    )


class ClusterResult(BaseModel):
    """Output of cluster_pages()."""

    model_config = ConfigDict(frozen=True)

    assignments: list[ClusterAssignment]
    outliers: list[str] = Field(description="entity_ids of unassigned pages")
    n_clusters: int
    mode: Literal["hard", "soft"]
    algo: Literal["hdbscan", "gmm"]


def _auto_n_neighbors(n_pages: int) -> int:
    """Scale n_neighbors with corpus size: max(2, sqrt(N))."""
    return max(2, int(math.sqrt(n_pages)))


def _reduce_umap(
    embeddings: NDArray[np.float64],
    n_neighbors: int,
) -> NDArray[np.float64]:
    """UMAP dimensionality reduction."""
    import umap

    n_samples, n_features = embeddings.shape
    n_components = min(50, n_features - 1, n_samples - 2)
    if n_components < 2:
        n_components = 2

    reducer = umap.UMAP(
        n_neighbors=min(n_neighbors, n_samples - 1),
        n_components=n_components,
        metric="cosine",
        random_state=42,
    )
    return reducer.fit_transform(embeddings)  # type: ignore[no-any-return]


def _cluster_hard(
    reduced: NDArray[np.float64],
    min_cluster_size: int,
) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
    """HDBSCAN hard clustering. Returns (labels, probabilities)."""
    import hdbscan

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        metric="euclidean",
    )
    clusterer.fit(reduced)
    return clusterer.labels_, clusterer.probabilities_


def _cluster_soft(
    reduced: NDArray[np.float64],
    min_cluster_size: int,
    probability_threshold: float,
) -> tuple[NDArray[np.int64], NDArray[np.float64], list[list[int]]]:
    """GMM soft clustering. Returns (primary_labels, max_probs, all_memberships)."""
    from sklearn.mixture import GaussianMixture

    n_samples = reduced.shape[0]
    max_components = max(2, n_samples // min_cluster_size)
    best_k = _select_n_components(reduced, max_components)

    gmm = GaussianMixture(
        n_components=best_k,
        covariance_type="full",
        random_state=42,
    )
    gmm.fit(reduced)
    proba = gmm.predict_proba(reduced)

    primary_labels = np.argmax(proba, axis=1)
    max_probs = np.max(proba, axis=1)

    memberships: list[list[int]] = []
    for row in proba:
        members = [int(k) for k in range(best_k) if row[k] >= probability_threshold]
        memberships.append(members)

    return primary_labels, max_probs, memberships


def _select_n_components(
    data: NDArray[np.float64],
    max_k: int,
) -> int:
    """Select GMM n_components via BIC (lower is better)."""
    from sklearn.mixture import GaussianMixture

    best_bic = float("inf")
    best_k = 2
    for k in range(2, max_k + 1):
        gmm = GaussianMixture(
            n_components=k,
            covariance_type="full",
            random_state=42,
        )
        gmm.fit(data)
        bic = gmm.bic(data)
        if bic < best_bic:
            best_bic = bic
            best_k = k
    return best_k


def cluster_pages(
    pages: list[PageInput],
    provider: EmbeddingProvider,
    *,
    mode: Literal["hard", "soft"] = "hard",
    min_cluster_size: int = 4,
    n_neighbors: int | None = None,
    probability_threshold: float = 0.5,
    cache: EmbeddingCache | None = None,
) -> ClusterResult:
    """Embed pages, reduce with UMAP, cluster with HDBSCAN or GMM (SPEC §6.1)."""
    n = len(pages)

    if n < min_cluster_size:
        return ClusterResult(
            assignments=[
                ClusterAssignment(entity_id=p.entity_id, cluster_id=-1, probability=0.0)
                for p in pages
            ],
            outliers=[p.entity_id for p in pages],
            n_clusters=0,
            mode=mode,
            algo="hdbscan" if mode == "hard" else "gmm",
        )

    # Embed
    texts = [p.body_md for p in pages]
    hashes = [p.content_hash for p in pages]

    with log_op("hierarchy", "embed", pages=n, cached=cache is not None, heartbeat=True):
        if cache is not None:
            embeddings_list = cache.get_or_embed(texts, hashes, provider)
        else:
            embeddings_list = provider.embed(texts)

    embeddings = np.array(embeddings_list, dtype=np.float64)

    # UMAP reduction
    if n_neighbors is None:
        n_neighbors = _auto_n_neighbors(n)

    # UMAP + HDBSCAN are pure CPU and can run for minutes on a large corpus;
    # they release the GIL, so the heartbeat thread keeps reporting.
    with log_op("hierarchy", "umap_reduce", pages=n, n_neighbors=n_neighbors, heartbeat=True):
        reduced = _reduce_umap(embeddings, n_neighbors)

    # Cluster
    if mode == "hard":
        with log_op("hierarchy", "cluster", algo="hdbscan", pages=n, heartbeat=True):
            labels, probs = _cluster_hard(reduced, min_cluster_size)
        assignments: list[ClusterAssignment] = []
        outliers: list[str] = []

        for i, page in enumerate(pages):
            label = int(labels[i])
            prob = float(probs[i])
            assignments.append(
                ClusterAssignment(
                    entity_id=page.entity_id,
                    cluster_id=label,
                    probability=prob if label >= 0 else 0.0,
                )
            )
            if label == -1:
                outliers.append(page.entity_id)

        n_clusters = int(labels.max() + 1) if labels.max() >= 0 else 0
        return ClusterResult(
            assignments=assignments,
            outliers=outliers,
            n_clusters=n_clusters,
            mode="hard",
            algo="hdbscan",
        )

    else:
        with log_op("hierarchy", "cluster", algo="gmm", pages=n, heartbeat=True):
            primary_labels, max_probs, memberships = _cluster_soft(
                reduced, min_cluster_size, probability_threshold
            )
        assignments = []
        outliers = []

        for i, page in enumerate(pages):
            label = int(primary_labels[i])
            prob = float(max_probs[i])
            members = memberships[i]
            secondary = [m for m in members if m != label]
            assignments.append(
                ClusterAssignment(
                    entity_id=page.entity_id,
                    cluster_id=label,
                    probability=prob,
                    memberships=secondary,
                )
            )

        n_clusters = int(primary_labels.max() + 1)
        return ClusterResult(
            assignments=assignments,
            outliers=outliers,
            n_clusters=n_clusters,
            mode="soft",
            algo="gmm",
        )
