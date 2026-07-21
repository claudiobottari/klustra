"""Unit tests for klustra.hierarchy.pages (SPEC §6.1)."""

from __future__ import annotations

import hashlib
import json

from klustra.hierarchy.pages import (
    HierarchyConfig,
    HierarchyNode,
    build_hierarchy,
    synthesize_cluster_page,
    synthesize_home_page,
)
from klustra.llm import ListSink, LLMRequest, LLMResponse, MockProvider, NullSink
from tests.test_hierarchy.conftest import ClusterableEmbeddingProvider


class DeterministicMockProvider(MockProvider):
    """MockProvider that returns themed responses based on input content."""

    def __init__(self) -> None:
        super().__init__()
        self._counter = 0

    def call(self, request: LLMRequest) -> LLMResponse:
        self._counter += 1
        slug = f"cluster-{self._counter}"

        content = json.dumps(
            {
                "title": f"Cluster {self._counter}",
                "description": f"A synthesized cluster page ({self._counter})",
                "body_md": f"Cluster body for {slug}.",
                "tags": ["synthesized", f"group-{self._counter}"],
                "entity_id_slug": slug,
            }
        )
        msg_chars = sum(len(m.content) for m in request.messages)
        return LLMResponse(
            content=content,
            parsed=json.loads(content),
            tokens_in=max(1, msg_chars // 4),
            tokens_out=max(1, len(content) // 4),
            model=request.model,
        )


def _make_node(entity_id: str, title: str, group: str, level: int = 0) -> HierarchyNode:
    body = f"{group} content for {title}"
    return HierarchyNode(
        entity_id=entity_id,
        content_hash=hashlib.sha256(body.encode()).hexdigest()[:16],
        body_md=body,
        title=title,
        description=f"Description of {title}",
        tags=[group, "test"],
        level=level,
    )


def _make_12_concept_nodes() -> list[HierarchyNode]:
    """12 nodes: 4 in group-a, 4 in group-b, 4 in group-c."""
    nodes: list[HierarchyNode] = []
    for i in range(4):
        nodes.append(_make_node(f"a.item-{i}", f"A Item {i}", "group-a"))
    for i in range(4):
        nodes.append(_make_node(f"b.item-{i}", f"B Item {i}", "group-b"))
    for i in range(4):
        nodes.append(_make_node(f"c.item-{i}", f"C Item {i}", "group-c"))
    return nodes


# ---------------------------------------------------------------------------
# Synthesize cluster page
# ---------------------------------------------------------------------------


class TestSynthesizeClusterPage:
    def test_produces_cluster_page(self) -> None:
        """synthesize_cluster_page returns a Page with type=cluster."""
        members = [_make_node(f"x.item-{i}", f"Item {i}", "group-a") for i in range(4)]
        config = HierarchyConfig(domain="test-domain")
        provider = DeterministicMockProvider()
        sink = NullSink()

        page, body = synthesize_cluster_page(
            cluster_id=0,
            members=members,
            level=1,
            config=config,
            provider=provider,
            sink=sink,
            run_id="run-1",
        )

        assert page.type == "cluster"
        assert page.level == 1
        assert page.domain == "test-domain"
        assert page.cluster_meta is not None
        assert page.cluster_meta.run_id == "run-1"
        assert len(body) > 0

    def test_children_are_member_ids(self) -> None:
        """Cluster page children list matches member entity_ids."""
        members = [_make_node(f"x.item-{i}", f"Item {i}", "group-a") for i in range(3)]
        config = HierarchyConfig(domain="mydom")
        provider = DeterministicMockProvider()
        sink = NullSink()

        page, _ = synthesize_cluster_page(
            cluster_id=1,
            members=members,
            level=2,
            config=config,
            provider=provider,
            sink=sink,
            run_id="r2",
        )

        assert page.children == ["x.item-0", "x.item-1", "x.item-2"]

    def test_entity_id_format(self) -> None:
        """Cluster page entity_id follows domain.cluster.l{level}.{slug} pattern."""
        members = [_make_node("a.test", "Test", "group-a")]
        config = HierarchyConfig(domain="eng")
        provider = DeterministicMockProvider()
        sink = NullSink()

        page, _ = synthesize_cluster_page(
            cluster_id=0,
            members=members,
            level=3,
            config=config,
            provider=provider,
            sink=sink,
            run_id="r",
        )

        assert page.entity_id.startswith("eng.cluster.l3.")


# ---------------------------------------------------------------------------
# Synthesize home page
# ---------------------------------------------------------------------------


class TestSynthesizeHomePage:
    def test_produces_home_page(self) -> None:
        """synthesize_home_page returns a Page with type=home."""
        top_nodes = [_make_node(f"c.item-{i}", f"Cluster {i}", "group", level=1) for i in range(3)]
        config = HierarchyConfig(domain="cables")
        provider = DeterministicMockProvider()
        sink = NullSink()

        page, body = synthesize_home_page(
            top_nodes=top_nodes,
            level=2,
            config=config,
            provider=provider,
            sink=sink,
            run_id="run-h",
        )

        assert page.type == "home"
        assert page.level == 2
        assert page.entity_id == "cables.home"
        assert page.cluster_meta is not None
        assert len(body) > 0

    def test_home_children_are_top_nodes(self) -> None:
        """Home page children match the top-level node entity_ids."""
        top_nodes = [_make_node(f"c.area-{i}", f"Area {i}", "group", level=1) for i in range(4)]
        config = HierarchyConfig(domain="dom")
        provider = DeterministicMockProvider()
        sink = NullSink()

        page, _ = synthesize_home_page(
            top_nodes=top_nodes,
            level=2,
            config=config,
            provider=provider,
            sink=sink,
            run_id="rh",
        )

        assert page.children == ["c.area-0", "c.area-1", "c.area-2", "c.area-3"]


# ---------------------------------------------------------------------------
# build_hierarchy — recursive driver
# ---------------------------------------------------------------------------


class TestBuildHierarchy:
    def test_produces_home(self) -> None:
        """12 nodes → clustering → home page is generated."""
        nodes = _make_12_concept_nodes()
        embedding_provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        llm_provider = DeterministicMockProvider()
        config = HierarchyConfig(domain="test", min_cluster_size=3, home_threshold=5)
        sink = NullSink()

        result = build_hierarchy(nodes, embedding_provider, llm_provider, config, sink, run_id="r1")

        home_pages = [p for p in result.pages if p.type == "home"]
        assert len(home_pages) == 1
        assert home_pages[0].entity_id == "test.home"

    def test_cluster_pages_have_correct_level(self) -> None:
        """Cluster pages are at level 1, home at max_level."""
        nodes = _make_12_concept_nodes()
        embedding_provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        llm_provider = DeterministicMockProvider()
        config = HierarchyConfig(domain="test", min_cluster_size=3, home_threshold=5)
        sink = NullSink()

        result = build_hierarchy(nodes, embedding_provider, llm_provider, config, sink, run_id="r2")

        cluster_pages = [p for p in result.pages if p.type == "cluster"]
        for cp in cluster_pages:
            assert cp.level >= 1

        home = next(p for p in result.pages if p.type == "home")
        assert home.level == result.max_level

    def test_children_correctness(self) -> None:
        """Each cluster page's children are entity_ids that exist in input."""
        nodes = _make_12_concept_nodes()
        all_ids = {n.entity_id for n in nodes}
        embedding_provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        llm_provider = DeterministicMockProvider()
        config = HierarchyConfig(domain="test", min_cluster_size=3, home_threshold=5)
        sink = NullSink()

        result = build_hierarchy(nodes, embedding_provider, llm_provider, config, sink, run_id="r3")

        # Level-1 cluster pages should have children from the original nodes
        level1_clusters = [p for p in result.pages if p.type == "cluster" and p.level == 1]
        for cp in level1_clusters:
            for child_id in cp.children:
                assert child_id in all_ids

    def test_home_generated_when_below_threshold(self) -> None:
        """If input ≤ home_threshold, immediately generates home."""
        nodes = [_make_node(f"x.item-{i}", f"Item {i}", "group-a") for i in range(3)]
        embedding_provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        llm_provider = DeterministicMockProvider()
        config = HierarchyConfig(domain="small", home_threshold=5)
        sink = NullSink()

        result = build_hierarchy(nodes, embedding_provider, llm_provider, config, sink, run_id="r4")

        assert len(result.pages) == 1
        assert result.pages[0].type == "home"
        assert result.pages[0].children == ["x.item-0", "x.item-1", "x.item-2"]

    def test_token_accounting_recorded(self) -> None:
        """ListSink records hierarchy role entries."""
        nodes = [_make_node(f"x.item-{i}", f"Item {i}", "group-a") for i in range(3)]
        embedding_provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        llm_provider = DeterministicMockProvider()
        config = HierarchyConfig(domain="acct", home_threshold=5)
        sink = ListSink()

        build_hierarchy(nodes, embedding_provider, llm_provider, config, sink, run_id="r5")

        assert sink.total_tokens_in > 0
        assert sink.total_tokens_out > 0
        assert all(r.role == "hierarchy" for r in sink.entries)

    def test_single_cluster_triggers_home(self) -> None:
        """If clustering yields 1 cluster, home is generated immediately."""
        # All nodes very similar → single cluster likely
        nodes = [_make_node(f"s.item-{i}", f"Same Item {i}", "group-a") for i in range(6)]
        embedding_provider = ClusterableEmbeddingProvider(dim=64, noise=0.01)
        llm_provider = DeterministicMockProvider()
        # min_cluster_size=6 means all 6 fit in one cluster
        config = HierarchyConfig(domain="single", min_cluster_size=3, home_threshold=3)
        sink = NullSink()

        result = build_hierarchy(nodes, embedding_provider, llm_provider, config, sink, run_id="r6")

        home_pages = [p for p in result.pages if p.type == "home"]
        assert len(home_pages) == 1

    def test_bodies_populated(self) -> None:
        """HierarchyResult.bodies has entries for all generated pages."""
        nodes = [_make_node(f"x.item-{i}", f"Item {i}", "group-a") for i in range(3)]
        embedding_provider = ClusterableEmbeddingProvider(dim=64, noise=0.02)
        llm_provider = DeterministicMockProvider()
        config = HierarchyConfig(domain="bod", home_threshold=5)
        sink = NullSink()

        result = build_hierarchy(nodes, embedding_provider, llm_provider, config, sink, run_id="r7")

        for page in result.pages:
            assert page.entity_id in result.bodies
            assert len(result.bodies[page.entity_id]) > 0
