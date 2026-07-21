"""Unit tests for klustra.hierarchy.context (SPEC §7)."""

from __future__ import annotations

import pytest

from klustra.hierarchy.context import (
    PageSummary,
    context,
    navigate,
    search,
)


def _build_hierarchy_pages() -> dict[str, PageSummary]:
    """Build a small test hierarchy:

    home (level=2)
    ├── cluster-a (level=1) → [concept-1, concept-2, concept-3]
    └── cluster-b (level=1) → [concept-4, concept-5]
    """
    return {
        "dom.home": PageSummary(
            entity_id="dom.home",
            title="Domain Home",
            description="The home page",
            level=2,
            type="home",
            children=["dom.cluster.l1.a", "dom.cluster.l1.b"],
        ),
        "dom.cluster.l1.a": PageSummary(
            entity_id="dom.cluster.l1.a",
            title="Cluster A",
            description="Group A topics",
            level=1,
            type="cluster",
            children=["dom.concept-1", "dom.concept-2", "dom.concept-3"],
        ),
        "dom.cluster.l1.b": PageSummary(
            entity_id="dom.cluster.l1.b",
            title="Cluster B",
            description="Group B topics",
            level=1,
            type="cluster",
            children=["dom.concept-4", "dom.concept-5"],
        ),
        "dom.concept-1": PageSummary(
            entity_id="dom.concept-1",
            title="Concept 1",
            description="First concept",
            level=0,
            type="concept",
        ),
        "dom.concept-2": PageSummary(
            entity_id="dom.concept-2",
            title="Concept 2",
            description="Second concept",
            level=0,
            type="concept",
        ),
        "dom.concept-3": PageSummary(
            entity_id="dom.concept-3",
            title="Concept 3",
            description="Third concept",
            level=0,
            type="concept",
        ),
        "dom.concept-4": PageSummary(
            entity_id="dom.concept-4",
            title="Concept 4",
            description="Fourth concept",
            level=0,
            type="concept",
        ),
        "dom.concept-5": PageSummary(
            entity_id="dom.concept-5",
            title="Concept 5",
            description="Fifth concept",
            level=0,
            type="concept",
        ),
    }


# ---------------------------------------------------------------------------
# context()
# ---------------------------------------------------------------------------


class TestContext:
    def test_returns_ancestor_chain(self) -> None:
        """Level-0 concept → ancestors up to home with depth=-1."""
        pages = _build_hierarchy_pages()

        result = context("dom.concept-1", pages, depth=-1, include=("ancestors",))

        assert result.page.entity_id == "dom.concept-1"
        assert len(result.ancestors) == 2
        assert result.ancestors[0].entity_id == "dom.cluster.l1.a"
        assert result.ancestors[1].entity_id == "dom.home"

    def test_ancestors_only_by_default(self) -> None:
        """Default include=("ancestors",) → siblings empty."""
        pages = _build_hierarchy_pages()

        result = context("dom.concept-1", pages)

        assert len(result.siblings) == 0
        assert len(result.ancestors) >= 1

    def test_depth_limits_ancestors(self) -> None:
        """depth=1 → only immediate parent."""
        pages = _build_hierarchy_pages()

        result = context("dom.concept-1", pages, depth=1)

        assert len(result.ancestors) == 1
        assert result.ancestors[0].entity_id == "dom.cluster.l1.a"

    def test_with_siblings(self) -> None:
        """include=("ancestors","siblings") → siblings populated."""
        pages = _build_hierarchy_pages()

        result = context("dom.concept-1", pages, include=("ancestors", "siblings"))

        sibling_ids = {s.entity_id for s in result.siblings}
        assert "dom.concept-2" in sibling_ids
        assert "dom.concept-3" in sibling_ids
        assert "dom.concept-1" not in sibling_ids

    def test_ancestors_are_title_description_only(self) -> None:
        """AncestorInfo carries only title + description (parsimonious)."""
        pages = _build_hierarchy_pages()

        result = context("dom.concept-4", pages, depth=-1)

        for anc in result.ancestors:
            assert isinstance(anc.title, str)
            assert isinstance(anc.description, str)
            assert isinstance(anc.level, int)

    def test_missing_entity_raises(self) -> None:
        """Unknown entity_id → KeyError."""
        pages = _build_hierarchy_pages()

        with pytest.raises(KeyError, match="not found"):
            context("nonexistent", pages)

    def test_home_page_has_no_ancestors(self) -> None:
        """Home page is the root → no ancestors."""
        pages = _build_hierarchy_pages()

        result = context("dom.home", pages, depth=-1)

        assert result.page.entity_id == "dom.home"
        assert len(result.ancestors) == 0


# ---------------------------------------------------------------------------
# navigate()
# ---------------------------------------------------------------------------


class TestNavigate:
    def test_from_none_returns_home(self) -> None:
        """No entity_id → home page."""
        pages = _build_hierarchy_pages()

        result = navigate(pages)

        assert result.current.entity_id == "dom.home"
        assert result.current.type == "home"

    def test_home_children(self) -> None:
        """Navigate from home → cluster children."""
        pages = _build_hierarchy_pages()

        result = navigate(pages)

        child_ids = {c.entity_id for c in result.children}
        assert child_ids == {"dom.cluster.l1.a", "dom.cluster.l1.b"}

    def test_navigate_from_cluster(self) -> None:
        """Navigate from cluster → concept children."""
        pages = _build_hierarchy_pages()

        result = navigate(pages, from_entity_id="dom.cluster.l1.a")

        assert result.current.entity_id == "dom.cluster.l1.a"
        child_ids = {c.entity_id for c in result.children}
        assert child_ids == {"dom.concept-1", "dom.concept-2", "dom.concept-3"}

    def test_leaf_has_no_children(self) -> None:
        """Navigate from concept → empty children."""
        pages = _build_hierarchy_pages()

        result = navigate(pages, from_entity_id="dom.concept-1")

        assert result.current.entity_id == "dom.concept-1"
        assert len(result.children) == 0

    def test_missing_entity_raises(self) -> None:
        """Unknown entity_id → KeyError."""
        pages = _build_hierarchy_pages()

        with pytest.raises(KeyError, match="not found"):
            navigate(pages, from_entity_id="nonexistent")


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestSearch:
    def _build_embeddings(self) -> dict[str, list[float]]:
        """Simple 3D embeddings for search tests."""
        return {
            "dom.home": [0.5, 0.5, 0.0],
            "dom.cluster.l1.a": [1.0, 0.0, 0.0],
            "dom.cluster.l1.b": [0.0, 1.0, 0.0],
            "dom.concept-1": [0.9, 0.1, 0.0],
            "dom.concept-2": [0.8, 0.2, 0.0],
            "dom.concept-3": [0.7, 0.3, 0.0],
            "dom.concept-4": [0.1, 0.9, 0.0],
            "dom.concept-5": [0.2, 0.8, 0.0],
        }

    def test_collapsed_ranks_all_levels(self) -> None:
        """Collapsed search returns hits from multiple levels, ranked by score."""
        pages = _build_hierarchy_pages()
        embeddings = self._build_embeddings()
        query = [1.0, 0.0, 0.0]

        results = search(query, embeddings, pages, mode="collapsed")

        assert len(results) > 0
        # Best match should be cluster-a or concept-1 (both near [1,0,0])
        assert results[0].entity_id in ("dom.cluster.l1.a", "dom.concept-1")
        # Results should span multiple levels
        levels = {r.level for r in results}
        assert len(levels) >= 2

    def test_level_filter(self) -> None:
        """level=1 → only level-1 results."""
        pages = _build_hierarchy_pages()
        embeddings = self._build_embeddings()
        query = [1.0, 0.0, 0.0]

        results = search(query, embeddings, pages, level=1, mode="collapsed")

        for hit in results:
            assert hit.level == 1

    def test_top_k_limits_results(self) -> None:
        """top_k=3 → at most 3 results."""
        pages = _build_hierarchy_pages()
        embeddings = self._build_embeddings()
        query = [1.0, 0.0, 0.0]

        results = search(query, embeddings, pages, top_k=3, mode="collapsed")

        assert len(results) <= 3

    def test_tree_mode(self) -> None:
        """Tree mode starts from home, descends."""
        pages = _build_hierarchy_pages()
        embeddings = self._build_embeddings()
        query = [1.0, 0.0, 0.0]

        results = search(query, embeddings, pages, mode="tree")

        assert len(results) > 0
        # First result is from the home level
        assert results[0].entity_id == "dom.home"

    def test_scores_are_bounded(self) -> None:
        """All scores between 0.0 and 1.0."""
        pages = _build_hierarchy_pages()
        embeddings = self._build_embeddings()
        query = [0.5, 0.5, 0.0]

        results = search(query, embeddings, pages, mode="collapsed")

        for hit in results:
            assert 0.0 <= hit.score <= 1.0
