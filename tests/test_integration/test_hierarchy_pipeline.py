"""Integration test: hierarchy pipeline end-to-end (SPEC §6).

Full build path + incremental path (materiality + judge) + stability inheritance
across consecutive runs, plus CLI --full flag.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from klustra.api import Klustra
from klustra.core.state_store import PageRecord
from klustra.hierarchy.embeddings import EmbeddingProvider
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse

# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------


_TOKEN_RE = re.compile(r"TOKEN_([a-z0-9_]+)")
_ENTITY_RE = re.compile(r"## Entity: (\S+)")


class _HierarchyMockProvider(LLMProvider):
    """Routes calls by system prompt role.

    - extraction: reads TOKEN_<slug> from the unit content, emits entity_id_proposal.
    - librarian: reads `## Entity: <id>` from user content, emits a body with a citation
      and a group keyword ("cable-group" / "material-group") for the embedder.
    - hierarchy (cluster + home): emits valid CLUSTER_PAGE_SCHEMA JSON with a unique slug.
    - judge: returns "fits" by default.
    """

    name = "hierarchy_mock"

    def __init__(self) -> None:
        self._cluster_counter = 0
        self.judge_calls = 0

    def call(self, request: LLMRequest) -> LLMResponse:
        system = request.messages[0].content if request.messages else ""
        user = request.messages[1].content if len(request.messages) > 1 else ""
        sys_lower = system.lower()

        if "extraction engine" in sys_lower:
            data = self._extract(user)
        elif "librarian" in sys_lower:
            data = self._librarian(user)
        elif "hierarchy judge" in sys_lower:
            self.judge_calls += 1
            data = {"verdict": "fits", "reason": "no material drift"}
        elif "knowledge architect" in sys_lower:
            if "home page" in sys_lower:
                data = self._home(user)
            else:
                data = self._cluster(user)
        else:
            data = {}

        content = json.dumps(data)
        return LLMResponse(
            content=content,
            parsed=data,
            tokens_in=max(1, len(user) // 4),
            tokens_out=max(1, len(content) // 4),
            model=request.model,
        )

    def _extract(self, user: str) -> dict:
        m = _TOKEN_RE.search(user)
        if not m:
            return {"candidates": []}
        slug = m.group(1)
        family = "cable" if slug.startswith("cable") else "material"
        return {
            "candidates": [
                {
                    "name": slug.replace("_", " ").title(),
                    "entity_id_proposal": f"item.{family}.{slug}",
                    "summary": f"A {family} concept.",
                    "is_new": True,
                    "related_existing": [],
                }
            ]
        }

    def _librarian(self, user: str) -> dict:
        m = _ENTITY_RE.search(user)
        entity_id = m.group(1) if m else "item.unknown"
        family = "cable-group" if ".cable." in entity_id else "material-group"
        # Body includes group keyword so the embedder clusters cleanly.
        body = (
            f"{entity_id} is part of {family}. "
            f"^[src:doc:1]\n\n"
            f"See related content in the {family} family."
        )
        return {
            "title": entity_id.split(".")[-1].replace("_", " ").title(),
            "description": f"Concept about {family}.",
            "body_md": body,
            "tags": [family],
            "aliases": [],
            "confidence": 0.9,
        }

    def _cluster(self, user: str) -> dict:
        self._cluster_counter += 1
        idx = self._cluster_counter
        family = "cable" if "cable-group" in user or ".cable." in user else "material"
        return {
            "title": f"{family.title()} Cluster {idx}",
            "description": f"Cluster of {family} concepts.",
            "body_md": f"This cluster covers {family} topics.",
            "tags": [family],
            "entity_id_slug": f"{family}-cluster-{idx}",
        }

    def _home(self, user: str) -> dict:
        return {
            "title": "Test Domain Home",
            "description": "Top-level entry point for the test corpus.",
            "body_md": "This domain contains cable and material concepts.",
            "tags": ["home", "test"],
            "entity_id_slug": "home",
        }


class _GroupEmbedder(EmbeddingProvider):
    """Deterministic keyword-based embedder — 'cable-group' and 'material-group' cluster cleanly."""

    def __init__(self, dim: int = 32, noise: float = 0.03) -> None:
        self.dim = dim
        self.noise = noise
        self._dir_cable = self._fixed_dir(0)
        self._dir_material = self._fixed_dir(1)

    def _fixed_dir(self, seed: int) -> np.ndarray:
        rng = np.random.default_rng(seed * 999 + 7)
        v = rng.standard_normal(self.dim)
        return v / np.linalg.norm(v)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec_for(t) for t in texts]

    def _vec_for(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        rng = np.random.default_rng(int.from_bytes(h[:8], "big"))
        if "cable-group" in text or ".cable." in text:
            direction = self._dir_cable
        elif "material-group" in text or ".material." in text:
            direction = self._dir_material
        else:
            direction = rng.standard_normal(self.dim)
            direction = direction / np.linalg.norm(direction)
        noise = rng.standard_normal(self.dim) * self.noise
        vec = direction + noise
        return (vec / np.linalg.norm(vec)).tolist()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_mini_corpus(corpus_dir: Path) -> None:
    """Write 12 markdown files — 6 cable, 6 material — with unique TOKEN_ markers."""
    for i in range(1, 7):
        (corpus_dir / f"cable_{i}.md").write_text(
            f"# Cable Concept {i}\n\nThis document describes cable topic {i}. TOKEN_cable_{i}\n",
            encoding="utf-8",
        )
        (corpus_dir / f"material_{i}.md").write_text(
            f"# Material Concept {i}\n\n"
            f"This document describes material topic {i}. TOKEN_material_{i}\n",
            encoding="utf-8",
        )


@pytest.fixture
def hierarchy_project(tmp_path: Path) -> Path:
    """Klustra project with 12-file mini corpus (2 clean topic groups)."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "klustra.toml").write_text(
        "[llm.extraction]\n"
        'provider = "mock"\nmodel = "test-model"\n\n'
        "[llm.librarian]\n"
        'provider = "mock"\nmodel = "test-model"\n\n'
        "[llm.hierarchy]\n"
        'provider = "mock"\nmodel = "test-model"\n\n'
        "[llm.judge]\n"
        'provider = "mock"\nmodel = "test-model"\n\n'
        "[hierarchy]\n"
        "min_cluster_size = 3\n"
        "home_threshold = 3\n"
        "materiality_threshold = 0.0\n",
        encoding="utf-8",
    )
    for subdir in [".klustra", ".klustra/vault", ".klustra/domains", ".klustra/instructions"]:
        (root / subdir).mkdir(parents=True, exist_ok=True)
    corpus = root / "corpus"
    corpus.mkdir()
    _write_mini_corpus(corpus)
    return root


def _make_klustra(root: Path) -> tuple[Klustra, _HierarchyMockProvider]:
    provider = _HierarchyMockProvider()
    nx = Klustra(root=root, provider=provider, embedding_provider=_GroupEmbedder())
    return nx, provider


def _ingest_and_compile(nx: Klustra, corpus: Path) -> None:
    nx.ingest_folder(corpus)
    results = nx.compile()
    assert len(results) == 12, f"expected 12 concept pages, got {len(results)}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHierarchyPipeline:
    def test_full_build_produces_home_and_clusters(self, hierarchy_project: Path) -> None:
        nx, _ = _make_klustra(hierarchy_project)
        _ingest_and_compile(nx, hierarchy_project / "corpus")

        result = nx.build_hierarchy(full=True)

        types = {p.type for p in result.pages}
        assert "home" in types, f"expected a home page, got types={types}"
        assert "cluster" in types, f"expected cluster page(s), got types={types}"
        assert result.max_level >= 1

        hstate = nx.state.get_hierarchy_state()
        assert hstate is not None
        assert len(hstate.page_embeddings) == 12
        assert len(hstate.page_content_hashes) == 12
        assert hstate.cluster_membership, "cluster_membership should be populated"

    def test_second_build_incremental_no_change(self, hierarchy_project: Path) -> None:
        """Second identical build takes the incremental path — no new hierarchy LLM calls."""
        nx, provider = _make_klustra(hierarchy_project)
        _ingest_and_compile(nx, hierarchy_project / "corpus")

        nx.build_hierarchy(full=True)
        hier_calls_after_first = sum(1 for e in nx._sink.entries if e.role == "hierarchy")
        prev_state = nx.state.get_hierarchy_state()
        assert prev_state is not None
        prev_cluster_ids = {p.entity_id for p in nx._load_pages() if p.type in ("cluster", "home")}

        # Rebuild with no changes — incremental path should short-circuit.
        nx.build_hierarchy(full=False)

        hier_calls_after_second = sum(1 for e in nx._sink.entries if e.role == "hierarchy")
        assert hier_calls_after_second == hier_calls_after_first, (
            "no-change rebuild must NOT trigger cluster/home LLM synthesis"
        )

        # Cluster IDs preserved verbatim.
        new_cluster_ids = {p.entity_id for p in nx._load_pages() if p.type in ("cluster", "home")}
        assert new_cluster_ids == prev_cluster_ids

    def test_second_build_small_change_preserves_ids(self, hierarchy_project: Path) -> None:
        """Small edit below drift threshold → judge fires → cluster IDs stable."""
        nx, provider = _make_klustra(hierarchy_project)
        _ingest_and_compile(nx, hierarchy_project / "corpus")

        nx.build_hierarchy(full=True)
        prev_cluster_ids = {p.entity_id for p in nx._load_pages() if p.type in ("cluster", "home")}
        assert prev_cluster_ids

        # Nudge exactly one concept — 1/12 = 8.3% < 30% drift threshold — so incremental
        # runs (not full rebuild). Change both body_md AND content_hash so the embedder
        # produces a different vector, tripping materiality > 0.
        target = next(p for p in nx.state.list_pages() if p.level == 0)
        new_body = f"{target.entity_id} nudged content — cable-group ^[src:doc:1]"
        new_hash = hashlib.sha256(new_body.encode()).hexdigest()[:16]
        nx._write_body(target.entity_id, new_body)
        nudged = PageRecord(
            entity_id=target.entity_id,
            source_ids=target.source_ids,
            level=target.level,
            content_hash=new_hash,
            title=target.title,
            description=target.description,
            tags=list(target.tags),
        )
        nx.state.put_page(nudged, run_id="test-nudge")

        judge_before = provider.judge_calls
        nx.build_hierarchy(full=False)

        assert provider.judge_calls > judge_before, "judge must be called for material change"

        new_cluster_ids = {p.entity_id for p in nx._load_pages() if p.type in ("cluster", "home")}
        assert new_cluster_ids == prev_cluster_ids, (
            "cluster IDs must survive an incremental rebuild"
        )


class TestHierarchyCli:
    def test_cli_hierarchy_full_flag(
        self, hierarchy_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI `klustra hierarchy --full` succeeds after compile."""
        import klustra.cli as cli_mod
        from klustra.cli import app

        nx, _ = _make_klustra(hierarchy_project)
        _ingest_and_compile(nx, hierarchy_project / "corpus")

        # CLI creates its own Klustra() via _get_klustra — inject providers by monkeypatch.
        provider = _HierarchyMockProvider()
        embedder = _GroupEmbedder()

        def _fake_get_klustra(root: Path | None = None) -> Klustra:
            return Klustra(
                root=root or hierarchy_project,
                provider=provider,
                embedding_provider=embedder,
            )

        monkeypatch.setattr(cli_mod, "_get_klustra", _fake_get_klustra)

        runner = CliRunner()
        result = runner.invoke(app, ["hierarchy", "--full"])
        assert result.exit_code == 0, result.output
        assert "Built" in result.output and "page(s)" in result.output


class TestEmbeddingsProviderRouting:
    """Gap #9 (embeddings instance): the embed step must work end-to-end when
    [llm.embeddings] names a non-OpenAI provider, resolved from config rather
    than injected by the caller."""

    def test_hierarchy_builds_with_openrouter_embeddings_config(
        self, hierarchy_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unittest.mock import MagicMock, patch

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
        toml = hierarchy_project / "klustra.toml"
        toml.write_text(
            toml.read_text(encoding="utf-8")
            + '\n[llm.embeddings]\nprovider = "openrouter"\n'
            + 'model = "openai/text-embedding-3-small"\n',
            encoding="utf-8",
        )

        # No embedding_provider injected — it must come from config.
        provider = _HierarchyMockProvider()
        nx = Klustra(root=hierarchy_project, provider=provider)
        _ingest_and_compile(nx, hierarchy_project / "corpus")

        reference = _GroupEmbedder()

        def _fake_create(*, model: str, input: list[str]) -> MagicMock:  # noqa: A002
            assert model == "openai/text-embedding-3-small"
            response = MagicMock()
            response.data = []
            for vector in reference.embed(input):
                item = MagicMock()
                item.embedding = vector
                response.data.append(item)
            return response

        embedder = nx.embedding_provider
        assert str(embedder._client.base_url).rstrip("/") == "https://openrouter.ai/api/v1"  # type: ignore[attr-defined]

        with patch.object(embedder._client.embeddings, "create", side_effect=_fake_create):  # type: ignore[attr-defined]
            result = nx.build_hierarchy(full=True)

        assert any(p.type == "home" for p in result.pages)
        assert any(p.type == "cluster" for p in result.pages)
