"""Unit tests for klustra.hierarchy.stability (SPEC §6.3)."""

from __future__ import annotations

import math

from klustra.hierarchy.stability import (
    NewCluster,
    OldCluster,
    jaccard_similarity,
    match_clusters,
    resolve_superseded,
)

# ---------------------------------------------------------------------------
# Jaccard similarity
# ---------------------------------------------------------------------------


class TestJaccardSimilarity:
    def test_identical_sets(self) -> None:
        """Same members → 1.0."""
        assert jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"}) == 1.0

    def test_disjoint_sets(self) -> None:
        """No overlap → 0.0."""
        assert jaccard_similarity({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self) -> None:
        """Known overlap: {a,b,c} ∩ {b,c,d} = {b,c}, union = {a,b,c,d} → 2/4 = 0.5."""
        assert math.isclose(jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"}), 0.5)

    def test_empty_sets(self) -> None:
        """Both empty → 1.0 (convention)."""
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self) -> None:
        """One empty → 0.0."""
        assert jaccard_similarity({"a"}, set()) == 0.0

    def test_superset(self) -> None:
        """{a,b} ⊂ {a,b,c} → 2/3 ≈ 0.667."""
        j = jaccard_similarity({"a", "b"}, {"a", "b", "c"})
        assert math.isclose(j, 2 / 3, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# match_clusters
# ---------------------------------------------------------------------------


class TestMatchClusters:
    def test_inherits_above_threshold(self) -> None:
        """Jaccard ≥ 0.6 → new inherits old entity_id."""
        old = [OldCluster(entity_id="old.cluster-a", children=["p1", "p2", "p3", "p4", "p5"])]
        new = [NewCluster(entity_id="new.tentative", children=["p1", "p2", "p3", "p4", "p6"])]
        # Jaccard = 4/6 ≈ 0.667

        result = match_clusters(old, new, threshold=0.6)

        assert len(result.matches) == 1
        assert result.matches[0].inherited is True
        assert result.matches[0].new_entity_id == "old.cluster-a"
        assert result.matches[0].jaccard >= 0.6

    def test_new_id_below_threshold(self) -> None:
        """Jaccard < 0.6 → new keeps tentative id, old is superseded."""
        old = [OldCluster(entity_id="old.cluster-a", children=["p1", "p2", "p3"])]
        new = [NewCluster(entity_id="new.cluster-x", children=["p4", "p5", "p6"])]
        # Jaccard = 0/6 = 0.0

        result = match_clusters(old, new, threshold=0.6)

        assert len(result.matches) == 0
        assert "old.cluster-a" in result.superseded
        assert "new.cluster-x" in result.new_ids

    def test_greedy_one_to_one(self) -> None:
        """Each old matches at most one new (greedy best-first)."""
        old = [
            OldCluster(entity_id="old.a", children=["p1", "p2", "p3"]),
            OldCluster(entity_id="old.b", children=["p4", "p5", "p6"]),
        ]
        new = [
            NewCluster(entity_id="new.x", children=["p1", "p2", "p3"]),
            NewCluster(entity_id="new.y", children=["p4", "p5", "p6"]),
        ]

        result = match_clusters(old, new, threshold=0.6)

        assert len(result.matches) == 2
        matched_old_ids = {m.old_entity_id for m in result.matches}
        assert matched_old_ids == {"old.a", "old.b"}
        # Each inherited its exact old id
        for m in result.matches:
            assert m.inherited is True

    def test_multiple_old_one_new(self) -> None:
        """Two old clusters, one new — best match wins, other superseded."""
        old = [
            OldCluster(entity_id="old.a", children=["p1", "p2"]),
            OldCluster(entity_id="old.b", children=["p1", "p2", "p3"]),
        ]
        new = [NewCluster(entity_id="new.x", children=["p1", "p2", "p3"])]
        # old.b has higher Jaccard (3/3=1.0) vs old.a (2/3≈0.67)

        result = match_clusters(old, new, threshold=0.6)

        assert len(result.matches) == 1
        assert result.matches[0].old_entity_id == "old.b"
        assert result.matches[0].inherited is True
        assert "old.a" in result.superseded

    def test_no_old_clusters(self) -> None:
        """No old clusters → all new are truly new."""
        new = [NewCluster(entity_id="new.a", children=["p1", "p2"])]
        result = match_clusters([], new, threshold=0.6)

        assert len(result.matches) == 0
        assert result.new_ids == ["new.a"]

    def test_no_new_clusters(self) -> None:
        """No new clusters → all old superseded."""
        old = [OldCluster(entity_id="old.a", children=["p1"])]
        result = match_clusters(old, [], threshold=0.6)

        assert len(result.matches) == 0
        assert "old.a" in result.superseded


# ---------------------------------------------------------------------------
# resolve_superseded
# ---------------------------------------------------------------------------


class TestResolveSuperseded:
    def test_direct_redirect(self) -> None:
        """old → new resolves to new."""
        smap = {"old.a": "new.a"}
        assert resolve_superseded("old.a", smap) == "new.a"

    def test_chain_redirect(self) -> None:
        """old → mid → new resolves to new."""
        smap = {"old.a": "mid.a", "mid.a": "new.a"}
        assert resolve_superseded("old.a", smap) == "new.a"

    def test_no_redirect(self) -> None:
        """Active entity → returns itself."""
        smap = {"old.a": "new.a"}
        assert resolve_superseded("active.x", smap) == "active.x"

    def test_cycle_detection(self) -> None:
        """Circular redirect → stops and returns last seen."""
        smap = {"a": "b", "b": "a"}
        result = resolve_superseded("a", smap)
        assert result in ("a", "b")

    def test_empty_superseded_stops(self) -> None:
        """Empty string superseded_by → stops at current."""
        smap = {"old.a": ""}
        assert resolve_superseded("old.a", smap) == "old.a"
