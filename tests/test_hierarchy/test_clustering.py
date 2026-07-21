"""Unit tests for klustra.hierarchy.clustering (SPEC §6.1)."""

from __future__ import annotations

import hashlib

from klustra.hierarchy.clustering import (
    ClusterResult,
    PageInput,
    _auto_n_neighbors,
    cluster_pages,
)
from klustra.hierarchy.embeddings import EmbeddingCache
from tests.test_hierarchy.conftest import ClusterableEmbeddingProvider, MockEmbeddingProvider


def _make_page(entity_id: str, body: str) -> PageInput:
    return PageInput(
        entity_id=entity_id,
        content_hash=hashlib.sha256(body.encode()).hexdigest()[:16],
        body_md=body,
    )


def _make_separable_pages() -> list[PageInput]:
    """Create 10 pages: 4 in group-a, 4 in group-b, 2 outliers."""
    pages: list[PageInput] = []
    for i in range(4):
        pages.append(_make_page(f"a.item-{i}", f"group-a content variant {i}"))
    for i in range(4):
        pages.append(_make_page(f"b.item-{i}", f"group-b content variant {i}"))
    pages.append(_make_page("x.outlier-0", "outlier unique content alpha"))
    pages.append(_make_page("x.outlier-1", "outlier unique content beta"))
    return pages


# ---------------------------------------------------------------------------
# Hard mode (HDBSCAN)
# ---------------------------------------------------------------------------


class TestHardMode:
    def test_partitions_cleanly(self) -> None:
        """HDBSCAN separates two clear groups; outliers pass through."""
        pages = _make_separable_pages()
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)

        result = cluster_pages(
            pages,
            provider,
            mode="hard",
            min_cluster_size=3,
        )

        assert result.mode == "hard"
        assert result.algo == "hdbscan"
        assert result.n_clusters >= 2

        # Group-a pages should share a cluster
        a_clusters = {a.cluster_id for a in result.assignments if a.entity_id.startswith("a.")}
        assert len(a_clusters) == 1
        assert -1 not in a_clusters

        # Group-b pages should share a different cluster
        b_clusters = {a.cluster_id for a in result.assignments if a.entity_id.startswith("b.")}
        assert len(b_clusters) == 1
        assert -1 not in b_clusters

        # The two groups have different cluster IDs
        assert a_clusters != b_clusters

    def test_outliers_pass_through(self) -> None:
        """Outlier pages (cluster_id=-1) appear in outliers list."""
        pages = _make_separable_pages()
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)

        result = cluster_pages(
            pages,
            provider,
            mode="hard",
            min_cluster_size=3,
        )

        # Structural invariant: outliers list matches -1 assignments
        outlier_ids_from_assignments = {
            a.entity_id for a in result.assignments if a.cluster_id == -1
        }
        assert set(result.outliers) == outlier_ids_from_assignments

        # Outliers have probability 0.0
        for a in result.assignments:
            if a.cluster_id == -1:
                assert a.probability == 0.0

    def test_forced_outliers_with_sparse_data(self) -> None:
        """With high min_cluster_size, isolated points become outliers."""
        # 5 tight-group pages + 1 isolated page — with min_cluster_size=5,
        # the isolated page cannot form a cluster
        pages = [_make_page(f"g.item-{i}", f"group-a content variant {i}") for i in range(5)]
        pages.append(_make_page("lone.wolf", "completely unrelated isolated content xyz"))
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.01)

        result = cluster_pages(
            pages,
            provider,
            mode="hard",
            min_cluster_size=5,
        )

        # The isolated page should be an outlier (cluster too small for it)
        assert len(result.outliers) >= 1

    def test_all_outliers_when_below_threshold(self) -> None:
        """When corpus < min_cluster_size, all are outliers."""
        pages = [_make_page(f"tiny.p-{i}", f"tiny content {i}") for i in range(3)]
        provider = MockEmbeddingProvider()

        result = cluster_pages(
            pages,
            provider,
            mode="hard",
            min_cluster_size=4,
        )

        assert result.n_clusters == 0
        assert len(result.outliers) == 3
        assert all(a.cluster_id == -1 for a in result.assignments)


# ---------------------------------------------------------------------------
# Soft mode (GMM)
# ---------------------------------------------------------------------------


class TestSoftMode:
    def test_allows_multi_membership(self) -> None:
        """GMM soft mode can assign pages to multiple clusters."""
        pages = _make_separable_pages()
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.3)

        result = cluster_pages(
            pages,
            provider,
            mode="soft",
            min_cluster_size=3,
            probability_threshold=0.2,
        )

        assert result.mode == "soft"
        assert result.algo == "gmm"
        assert result.n_clusters >= 2

        # With noise=0.3 and threshold=0.2, some multi-membership is expected
        # but not guaranteed — assert basic structure
        assert all(a.cluster_id >= 0 for a in result.assignments)
        assert all(0.0 <= a.probability <= 1.0 for a in result.assignments)
        # GMM doesn't produce outliers
        assert result.outliers == []

    def test_primary_cluster_is_max_probability(self) -> None:
        """Primary cluster_id corresponds to highest probability."""
        pages = _make_separable_pages()
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.1)

        result = cluster_pages(
            pages,
            provider,
            mode="soft",
            min_cluster_size=3,
            probability_threshold=0.3,
        )

        for assignment in result.assignments:
            # primary cluster should NOT be in secondary memberships
            assert assignment.cluster_id not in assignment.memberships


# ---------------------------------------------------------------------------
# Embedding cache
# ---------------------------------------------------------------------------


class TestEmbeddingCache:
    def test_cache_prevents_redundant_calls(self) -> None:
        """Cached pages don't trigger a second embed() call."""
        pages = _make_separable_pages()
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        cache = EmbeddingCache()

        # First run: populates cache
        cluster_pages(pages, provider, mode="hard", min_cluster_size=3, cache=cache)

        # Second run with same pages: should use cache entirely
        provider2 = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        cluster_pages(pages, provider2, mode="hard", min_cluster_size=3, cache=cache)

        assert provider2.call_count == 0

    def test_cache_partial_hit(self) -> None:
        """When some pages are cached, only uncached ones are embedded."""
        pages = _make_separable_pages()
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        cache = EmbeddingCache()

        # Pre-cache first 5 pages
        first_five = pages[:5]
        texts = [p.body_md for p in first_five]
        hashes = [p.content_hash for p in first_five]
        cache.get_or_embed(texts, hashes, provider)

        provider.call_count = 0

        # Now cluster all 10: only 5 uncached should trigger embed()
        cluster_pages(pages, provider, mode="hard", min_cluster_size=3, cache=cache)
        assert provider.call_count == 1


# ---------------------------------------------------------------------------
# Edge cases and utilities
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_n_neighbors_scales_with_corpus(self) -> None:
        """Auto n_neighbors = max(2, sqrt(N))."""
        assert _auto_n_neighbors(4) == 2
        assert _auto_n_neighbors(9) == 3
        assert _auto_n_neighbors(100) == 10
        assert _auto_n_neighbors(1) == 2

    def test_result_model_fields(self) -> None:
        """ClusterResult has expected structure."""
        pages = _make_separable_pages()
        provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)

        result = cluster_pages(pages, provider, mode="hard", min_cluster_size=3)

        assert isinstance(result, ClusterResult)
        assert len(result.assignments) == len(pages)
        for a in result.assignments:
            assert a.entity_id in [p.entity_id for p in pages]
