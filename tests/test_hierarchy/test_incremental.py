"""Unit tests for klustra.hierarchy.incremental (SPEC §6.2)."""

from __future__ import annotations

import json
import math

from klustra.hierarchy.incremental import (
    IncrementalConfig,
    JudgeVerdict,
    check_materiality,
    cosine_distance,
    judge_cluster,
    run_incremental,
    should_full_rebuild,
)
from klustra.llm import ListSink, LLMRequest, LLMResponse, MockProvider, NullSink


class JudgeMockProvider(MockProvider):
    """MockProvider that returns a configurable judge verdict."""

    def __init__(self, verdict: JudgeVerdict = "fits", reason: str = "test") -> None:
        super().__init__()
        self._verdict = verdict
        self._reason = reason
        self.call_count = 0

    def call(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        content = json.dumps({"verdict": self._verdict, "reason": self._reason})
        msg_chars = sum(len(m.content) for m in request.messages)
        return LLMResponse(
            content=content,
            parsed=json.loads(content),
            tokens_in=max(1, msg_chars // 4),
            tokens_out=max(1, len(content) // 4),
            model=request.model,
        )


# ---------------------------------------------------------------------------
# Cosine distance
# ---------------------------------------------------------------------------


class TestCosineDistance:
    def test_identical_vectors(self) -> None:
        """Same vector → distance 0.0."""
        v = [1.0, 2.0, 3.0, 4.0]
        assert cosine_distance(v, v) == 0.0

    def test_orthogonal_vectors(self) -> None:
        """Orthogonal vectors → distance 1.0."""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert math.isclose(cosine_distance(a, b), 1.0, abs_tol=1e-10)

    def test_opposite_vectors(self) -> None:
        """Opposite vectors → distance 2.0."""
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert math.isclose(cosine_distance(a, b), 2.0, abs_tol=1e-10)

    def test_similar_vectors_small_distance(self) -> None:
        """Slightly different vectors → small distance."""
        a = [1.0, 0.0, 0.0]
        b = [0.99, 0.01, 0.0]
        dist = cosine_distance(a, b)
        assert 0.0 < dist < 0.01

    def test_zero_vector(self) -> None:
        """Zero vector → distance 1.0 (undefined, fallback)."""
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert cosine_distance(a, b) == 1.0


# ---------------------------------------------------------------------------
# Materiality pre-filter
# ---------------------------------------------------------------------------


class TestMateriality:
    def test_sub_threshold_not_material(self) -> None:
        """Small change below threshold → not material."""
        a = [1.0, 0.0, 0.0, 0.0]
        b = [0.999, 0.001, 0.0, 0.0]
        result = check_materiality("test.page", a, b, threshold=0.10)
        assert not result.is_material
        assert result.cosine_distance < 0.10

    def test_above_threshold_is_material(self) -> None:
        """Large change above threshold → material."""
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        result = check_materiality("test.page", a, b, threshold=0.10)
        assert result.is_material
        assert result.cosine_distance >= 0.10

    def test_exact_threshold_is_material(self) -> None:
        """Distance exactly at threshold → material (>= comparison)."""
        a = [1.0, 0.0]
        b = [1.0, 0.0]
        # Identical → distance 0.0, threshold 0.0 → is_material
        result = check_materiality("p", a, b, threshold=0.0)
        assert result.is_material


# ---------------------------------------------------------------------------
# LLM judge
# ---------------------------------------------------------------------------


class TestJudgeCluster:
    def test_fits_verdict(self) -> None:
        """Judge returns 'fits' → no propagation needed."""
        provider = JudgeMockProvider(verdict="fits", reason="Minor wording change")
        sink = NullSink()

        result = judge_cluster(
            cluster_entity_id="dom.cluster.l1.cables",
            cluster_summary="High-voltage cable engineering topics.",
            member_titles=["Cable A", "Cable B", "Cable C"],
            delta_description="Modified: dom.cable-a",
            provider=provider,
            sink=sink,
            model="test-model",
        )

        assert result.verdict == "fits"
        assert result.cluster_entity_id == "dom.cluster.l1.cables"
        assert len(result.reason) > 0

    def test_regenerate_verdict(self) -> None:
        """Judge returns 'regenerate_page' → cluster needs re-synthesis."""
        provider = JudgeMockProvider(verdict="regenerate_page", reason="New major topic added")
        sink = NullSink()

        result = judge_cluster(
            cluster_entity_id="dom.cluster.l1.thermal",
            cluster_summary="Thermal management.",
            member_titles=["Heat sink", "Cooling"],
            delta_description="Added: dom.cryogenics",
            provider=provider,
            sink=sink,
            model="m",
        )

        assert result.verdict == "regenerate_page"

    def test_recluster_verdict(self) -> None:
        """Judge returns 'recluster_subtree' → structural change."""
        provider = JudgeMockProvider(
            verdict="recluster_subtree", reason="Members no longer cohesive"
        )
        sink = NullSink()

        result = judge_cluster(
            cluster_entity_id="dom.cluster.l1.mixed",
            cluster_summary="Mixed topics.",
            member_titles=["Topic A", "Topic B"],
            delta_description="Removed: dom.topic-a\nAdded: dom.unrelated",
            provider=provider,
            sink=sink,
            model="m",
        )

        assert result.verdict == "recluster_subtree"

    def test_token_accounting_judge_role(self) -> None:
        """Judge records TokenRecord with role='judge'."""
        provider = JudgeMockProvider(verdict="fits")
        sink = ListSink()

        judge_cluster(
            cluster_entity_id="c.test",
            cluster_summary="Test cluster.",
            member_titles=["A"],
            delta_description="Modified: c.a",
            provider=provider,
            sink=sink,
            model="judge-model",
        )

        assert len(sink.entries) == 1
        assert sink.entries[0].role == "judge"
        assert sink.entries[0].model == "judge-model"
        assert sink.total_tokens_in > 0
        assert sink.total_tokens_out > 0


# ---------------------------------------------------------------------------
# Drift threshold / full rebuild
# ---------------------------------------------------------------------------


class TestShouldFullRebuild:
    def test_drift_above_threshold(self) -> None:
        """40% changed with 30% threshold → True."""
        assert should_full_rebuild(40, 100, 0.30) is True

    def test_drift_below_threshold(self) -> None:
        """10% changed with 30% threshold → False."""
        assert should_full_rebuild(10, 100, 0.30) is False

    def test_drift_at_threshold(self) -> None:
        """Exactly at threshold → True (>= comparison)."""
        assert should_full_rebuild(30, 100, 0.30) is True

    def test_force_full_always_true(self) -> None:
        """force_full=True → True regardless of drift."""
        assert should_full_rebuild(0, 100, 0.30, force_full=True) is True

    def test_zero_total_triggers_rebuild(self) -> None:
        """Empty corpus → full rebuild."""
        assert should_full_rebuild(0, 0, 0.30) is True


# ---------------------------------------------------------------------------
# run_incremental — integration
# ---------------------------------------------------------------------------


class TestRunIncremental:
    def test_sub_threshold_skips_judge(self) -> None:
        """Changes below materiality threshold skip the judge entirely."""
        # Nearly identical embeddings → cosine distance ≈ 0
        old_emb = {"p.changed": [1.0, 0.0, 0.0, 0.0]}
        new_emb = {"p.changed": [0.9999, 0.0001, 0.0, 0.0]}

        provider = JudgeMockProvider(verdict="fits")
        sink = NullSink()
        config = IncrementalConfig(materiality_threshold=0.10)

        result = run_incremental(
            changed_ids=["p.changed"],
            removed_ids=[],
            added_ids=[],
            cluster_membership={"p.changed": "cluster.a"},
            cluster_summaries={"cluster.a": "Cluster A summary."},
            old_embeddings=old_emb,
            new_embeddings=new_emb,
            config=config,
            provider=provider,
            sink=sink,
        )

        assert "p.changed" in result.skipped
        assert len(result.judged) == 0
        assert provider.call_count == 0

    def test_above_threshold_triggers_judge(self) -> None:
        """Material change above threshold triggers the judge."""
        # Orthogonal embeddings → distance = 1.0
        old_emb = {"p.changed": [1.0, 0.0, 0.0]}
        new_emb = {"p.changed": [0.0, 1.0, 0.0]}

        provider = JudgeMockProvider(verdict="regenerate_page", reason="Big change")
        sink = NullSink()
        config = IncrementalConfig(materiality_threshold=0.10)

        result = run_incremental(
            changed_ids=["p.changed"],
            removed_ids=[],
            added_ids=[],
            cluster_membership={"p.changed": "cluster.a"},
            cluster_summaries={"cluster.a": "Cluster A."},
            old_embeddings=old_emb,
            new_embeddings=new_emb,
            config=config,
            provider=provider,
            sink=sink,
        )

        assert "p.changed" not in result.skipped
        assert len(result.judged) == 1
        assert result.judged[0].verdict == "regenerate_page"
        assert "cluster.a" in result.regenerated
        assert provider.call_count == 1

    def test_added_concepts_trigger_judge(self) -> None:
        """New concepts always trigger judge on their cluster."""
        provider = JudgeMockProvider(verdict="fits")
        sink = NullSink()
        config = IncrementalConfig()

        result = run_incremental(
            changed_ids=[],
            removed_ids=[],
            added_ids=["p.new"],
            cluster_membership={"p.new": "cluster.b"},
            cluster_summaries={"cluster.b": "B summary."},
            old_embeddings={},
            new_embeddings={},
            config=config,
            provider=provider,
            sink=sink,
        )

        assert len(result.judged) == 1
        assert result.judged[0].cluster_entity_id == "cluster.b"
        assert provider.call_count == 1

    def test_removed_concepts_trigger_judge(self) -> None:
        """Removed concepts trigger judge on their cluster."""
        provider = JudgeMockProvider(verdict="recluster_subtree", reason="Lost member")
        sink = NullSink()
        config = IncrementalConfig()

        result = run_incremental(
            changed_ids=[],
            removed_ids=["p.gone"],
            added_ids=[],
            cluster_membership={"p.gone": "cluster.c"},
            cluster_summaries={"cluster.c": "C summary."},
            old_embeddings={},
            new_embeddings={},
            config=config,
            provider=provider,
            sink=sink,
        )

        assert len(result.judged) == 1
        assert result.judged[0].verdict == "recluster_subtree"
        assert "cluster.c" in result.reclustered

    def test_missing_embedding_treated_as_material(self) -> None:
        """If old or new embedding is missing, treat as material."""
        provider = JudgeMockProvider(verdict="fits")
        sink = NullSink()
        config = IncrementalConfig(materiality_threshold=0.10)

        result = run_incremental(
            changed_ids=["p.noold"],
            removed_ids=[],
            added_ids=[],
            cluster_membership={"p.noold": "cluster.x"},
            cluster_summaries={"cluster.x": "X."},
            old_embeddings={},
            new_embeddings={"p.noold": [1.0, 0.0]},
            config=config,
            provider=provider,
            sink=sink,
        )

        assert "p.noold" not in result.skipped
        assert provider.call_count == 1
