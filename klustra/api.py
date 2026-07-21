"""Klustra facade — the ONLY public import surface (SPEC §4.3, §12)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from pathlib import Path
from typing import Literal

from klustra.core.changeset import ChangeSet
from klustra.core.config import KlustraConfig, load_config
from klustra.core.file_state_store import FileStateStore
from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.page import Page
from klustra.core.source_ref import SourceRef
from klustra.core.state_store import HierarchyStateRecord, PageRecord
from klustra.engine.extraction import extract_concepts
from klustra.engine.librarian import merge_and_generate, persist_librarian_result
from klustra.engine.lint import LintConfig, LintFinding, lint_pages
from klustra.engine.models import LibrarianResult, SourceContribution
from klustra.engine.validate import ValidationFinding, validate_all
from klustra.exporters import ExportContext, ExporterRegistry, ExportPage, build_default_registry
from klustra.hierarchy.context import (
    ConceptContext,
    NavigateResult,
    PageSummary,
    SearchHit,
)
from klustra.hierarchy.context import (
    context as context_fn,
)
from klustra.hierarchy.context import (
    navigate as navigate_fn,
)
from klustra.hierarchy.context import (
    search as search_fn,
)
from klustra.hierarchy.embeddings import (
    EmbeddingCache,
    EmbeddingProvider,
    resolve_embedding_provider,
)
from klustra.hierarchy.incremental import (
    IncrementalConfig,
    IncrementalResult,
    run_incremental,
    should_full_rebuild,
)
from klustra.hierarchy.pages import (
    HierarchyConfig,
    HierarchyNode,
    HierarchyResult,
)
from klustra.hierarchy.pages import (
    build_hierarchy as build_hierarchy_fn,
)
from klustra.hierarchy.stability import NewCluster, OldCluster, match_clusters
from klustra.ingestion.connectors import ConnectorRegistry, LocalFolderConnector
from klustra.ingestion.domain_registry import DomainConfig, get_domain, list_domains
from klustra.ingestion.source_manager import (
    ingest_file,
    ingest_folder,
    remove_source,
    sync_folder,
    update_source,
)
from klustra.ingestion.translator import TranslateContext, TranslationResult
from klustra.ingestion.translator_registry import TranslatorRegistry
from klustra.llm import AccountingSink, ListSink, LLMProvider, PromptRegistry, resolve_provider
from klustra.translators.registry import build_default_registry as build_translator_registry


class Klustra:
    """Public facade for all klustra operations (SPEC §4.3)."""

    def __init__(
        self,
        root: Path | str = Path("."),
        *,
        provider: LLMProvider | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.config: KlustraConfig = load_config(self.root / "klustra.toml")
        self.state = FileStateStore(self.root)
        self.translator_registry: TranslatorRegistry = build_translator_registry()
        self.exporter_registry: ExporterRegistry = build_default_registry()
        self._provider = provider
        self._embedding_provider = embedding_provider
        self._sink: ListSink = ListSink()

    @property
    def provider(self) -> LLMProvider:
        if self._provider is not None:
            return self._provider
        cfg = self.config.llm.extraction
        if cfg is None:
            from klustra.core.errors import ConfigError

            raise ConfigError("llm.extraction config is required for LLM operations")
        self._provider = resolve_provider(cfg.provider, base_url=cfg.base_url)
        return self._provider

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        if self._embedding_provider is not None:
            return self._embedding_provider
        cfg = self.config.llm.embeddings
        if cfg is None:
            from klustra.core.errors import ConfigError

            raise ConfigError(
                "llm.embeddings config is required for hierarchy operations — "
                "add an [llm.embeddings] section to klustra.toml or pass "
                "embedding_provider to Klustra(...)"
            )
        self._embedding_provider = resolve_embedding_provider(cfg)
        return self._embedding_provider

    # --- Ingestion ---

    def ingest_file(self, path: Path | str, *, domain: str | None = None) -> ChangeSet:
        return ingest_file(path, self.state, self.translator_registry)

    def ingest_folder(
        self,
        path: Path | str,
        *,
        recursive: bool = True,
        glob: list[str] | None = None,
    ) -> ChangeSet:
        return ingest_folder(
            path, self.state, self.translator_registry, recursive=recursive, glob=glob
        )

    def update_source(self, path: Path | str) -> ChangeSet:
        return update_source(path, self.state, self.translator_registry)

    def remove_source(self, path: Path | str) -> ChangeSet:
        return remove_source(path, self.state)

    def sync_folder(
        self,
        path: Path | str,
        *,
        recursive: bool = True,
        glob: list[str] | None = None,
    ) -> ChangeSet:
        return sync_folder(
            path, self.state, self.translator_registry, recursive=recursive, glob=glob
        )

    # --- Compilation ---

    def compile(self) -> list[LibrarianResult]:
        """Full compile pipeline: translate → extract → librarian merge (SPEC §5)."""
        from klustra.core.errors import ConfigError

        run_id = str(uuid.uuid4())
        sources = self.state.list_sources()
        if not sources:
            return []

        extraction_cfg = self.config.llm.extraction
        librarian_cfg = self.config.llm.librarian
        if extraction_cfg is None:
            raise ConfigError("llm.extraction config is required for compile")
        if librarian_cfg is None:
            raise ConfigError("llm.librarian config is required for compile")

        all_units: list[KnowledgeUnit] = []
        units_by_source: dict[str, list[KnowledgeUnit]] = defaultdict(list)
        source_paths: dict[str, str] = {}

        for source in sources:
            source_paths[source.source_id] = source.source_path
            translator = self.translator_registry.get_for_path(source.source_path)
            ctx = TranslateContext(run_id=run_id)
            ref = SourceRef(source_id=source.source_id, source_path=source.source_path)
            result: TranslationResult = translator.translate(ref, ctx)
            for unit in result.units:
                all_units.append(unit)
                units_by_source[source.source_id].append(unit)

        existing_index = [p.entity_id for p in self.state.list_pages()]

        entity_contributions: dict[str, list[SourceContribution]] = defaultdict(list)

        for source_id, units in units_by_source.items():
            extraction_results = extract_concepts(
                units=units,
                source_id=source_id,
                existing_index=existing_index,
                provider=self.provider,
                model=extraction_cfg.model,
                sink=self._sink,
                max_tokens=extraction_cfg.max_tokens,
            )
            for er in extraction_results:
                for candidate in er.candidates:
                    entity_id = candidate.entity_id_proposal
                    if entity_id not in existing_index:
                        existing_index.append(entity_id)
                    contrib = SourceContribution(
                        source_id=source_id,
                        source_path=source_paths[source_id],
                        units=units,
                    )
                    entity_contributions[entity_id].append(contrib)

        results: list[LibrarianResult] = []
        for entity_id, contributions in entity_contributions.items():
            result_lib = merge_and_generate(
                entity_id=entity_id,
                contributions=contributions,
                existing_index=existing_index,
                domain=extraction_cfg.provider,
                provider=self.provider,
                model=librarian_cfg.model,
                sink=self._sink,
                max_tokens=librarian_cfg.max_tokens,
                run_id=run_id,
            )
            persist_librarian_result(result_lib, self.state, run_id=run_id)
            self._write_body(result_lib.page.entity_id, result_lib.body_md)
            results.append(result_lib)

        return results

    # --- Validation & Lint ---

    def validate(self) -> list[ValidationFinding]:
        pages = self._load_pages()
        return validate_all(pages)

    def lint(self) -> list[LintFinding]:
        pages = self._load_pages()
        bodies = {p.entity_id: self._read_body(p.entity_id) for p in pages}
        lint_cfg = LintConfig(
            promote_to_error=self.config.lint.promote_to_error if self.config.lint else []
        )
        return lint_pages(pages, bodies=bodies, config=lint_cfg)

    # --- Export ---

    def export(self, target: str, output_dir: Path | str) -> None:
        exporter = self.exporter_registry.get(target)
        pages = self._load_pages()
        export_pages = [ExportPage(page=p, body_md=self._read_body(p.entity_id)) for p in pages]
        ctx = ExportContext(run_id=str(uuid.uuid4()))
        exporter.export(export_pages, Path(output_dir), ctx)

    # --- Domain ---

    def domain_list(self) -> list[DomainConfig]:
        return list_domains(self.root / ".klustra")

    def domain_show(self, label: str) -> DomainConfig | None:
        return get_domain(label, self.root / ".klustra")

    def sync_domain(self, label: str) -> ChangeSet:
        domain = get_domain(label, self.root / ".klustra")
        if domain is None:
            from klustra.core.errors import ConfigError

            raise ConfigError(f"Domain {label!r} not found")
        connector_registry = self._build_connector_registry()
        merged = ChangeSet()
        for source_cfg in domain.sources:
            connector = connector_registry.get(source_cfg.type)
            cs = connector.sync(source_cfg, self.state)
            merged = ChangeSet(
                sources=merged.sources.model_copy(
                    update={
                        "added": merged.sources.added + cs.sources.added,
                        "modified": merged.sources.modified + cs.sources.modified,
                        "removed": merged.sources.removed + cs.sources.removed,
                    }
                ),
                pages=merged.pages.model_copy(
                    update={
                        "removed": merged.pages.removed + cs.pages.removed,
                        "affected": merged.pages.affected + cs.pages.affected,
                    }
                ),
            )
        return merged

    def sync_all(self) -> ChangeSet:
        domains = self.domain_list()
        merged = ChangeSet()
        for domain in domains:
            cs = self.sync_domain(domain.label)
            merged = ChangeSet(
                sources=merged.sources.model_copy(
                    update={
                        "added": merged.sources.added + cs.sources.added,
                        "modified": merged.sources.modified + cs.sources.modified,
                        "removed": merged.sources.removed + cs.sources.removed,
                    }
                ),
                pages=merged.pages.model_copy(
                    update={
                        "removed": merged.pages.removed + cs.pages.removed,
                        "affected": merged.pages.affected + cs.pages.affected,
                    }
                ),
            )
        return merged

    # --- Hierarchy (SPEC §6) ---

    def build_hierarchy(self, *, full: bool = False) -> HierarchyResult:
        """Build RAPTOR-style cluster/home hierarchy (SPEC §6.1-§6.3).

        Incremental when a prior state exists and drift is below threshold;
        full rebuild otherwise or when ``full=True`` / verdict escalates.
        """
        from klustra.core.errors import ConfigError

        concept_records = [p for p in self.state.list_pages() if p.level == 0]
        if not concept_records:
            raise ConfigError("No concept pages — run compile first")

        nodes = [self._record_to_hierarchy_node(r) for r in concept_records]
        hcfg = self.config.hierarchy
        prev = self.state.get_hierarchy_state()
        cache = EmbeddingCache()
        prompts = PromptRegistry()
        run_id = str(uuid.uuid4())

        if not full and prev is not None:
            changed, added, removed = self._diff_ids(nodes, prev)
            drift_count = len(changed) + len(added) + len(removed)
            if not should_full_rebuild(
                changed_count=drift_count,
                total_count=len(nodes),
                drift_threshold_percent=hcfg.drift_threshold_percent,
            ):
                new_embeddings = self._embed_nodes(nodes, cache)
                inc_result = run_incremental(
                    changed_ids=changed,
                    removed_ids=removed,
                    added_ids=added,
                    cluster_membership=prev.cluster_membership,
                    cluster_summaries=prev.cluster_summaries,
                    old_embeddings=prev.page_embeddings,
                    new_embeddings=new_embeddings,
                    config=self._build_incremental_config(),
                    provider=self.provider,
                    sink=self._sink,
                    prompts=prompts,
                )
                if not inc_result.regenerated and not inc_result.reclustered:
                    return self._package_incremental_result(
                        prev, inc_result, new_embeddings, nodes, run_id
                    )

        result = build_hierarchy_fn(
            nodes=nodes,
            embedding_provider=self.embedding_provider,
            llm_provider=self.provider,
            config=self._build_hierarchy_config(),
            sink=self._sink,
            run_id=run_id,
            cache=cache,
            prompts=prompts,
        )

        final_result, superseded_map = self._apply_stability(result, prev, hcfg.stability_threshold)
        new_embeddings = self._embed_nodes(nodes, cache)
        self._persist_hierarchy(final_result, new_embeddings, nodes, superseded_map, run_id)
        return final_result

    # --- Context / Navigate / Search (SPEC §7) ---

    def context(
        self,
        entity_id: str,
        *,
        depth: int = 1,
        include: tuple[str, ...] = ("ancestors",),
    ) -> ConceptContext:
        """Parsimonious context: page + ancestor chain (SPEC §7.2)."""
        pages = self._build_page_summaries()
        return context_fn(entity_id, pages, depth=depth, include=include)

    def navigate(self, from_entity_id: str | None = None) -> NavigateResult:
        """Guided descent through the hierarchy (SPEC §7.1)."""
        pages = self._build_page_summaries()
        return navigate_fn(pages, from_entity_id=from_entity_id)

    def search(
        self,
        query_embedding: list[float],
        page_embeddings: dict[str, list[float]],
        *,
        level: int | None = None,
        mode: Literal["collapsed", "tree"] = "collapsed",
        top_k: int = 10,
    ) -> list[SearchHit]:
        """Ranked search across hierarchy levels (SPEC §7.3)."""
        pages = self._build_page_summaries()
        return search_fn(
            query_embedding,
            page_embeddings,
            pages,
            level=level,
            mode=mode,
            top_k=top_k,
        )

    # --- Accounting ---

    @property
    def accounting(self) -> AccountingSink:
        return self._sink

    # --- Private helpers ---

    def _build_page_summaries(self) -> dict[str, PageSummary]:
        """Build PageSummary dict from loaded pages."""
        result: dict[str, PageSummary] = {}
        for page in self._load_pages():
            result[page.entity_id] = PageSummary(
                entity_id=page.entity_id,
                title=page.title,
                description=page.description,
                level=page.level,
                type=page.type,
                children=page.children,
            )
        return result

    def _load_pages(self) -> list[Page]:
        pages: list[Page] = []
        for record in self.state.list_pages():
            page = self._record_to_page(record)
            if page:
                pages.append(page)
        return pages

    def _record_to_page(self, record: PageRecord) -> Page | None:
        """Reconstruct a Page from PageRecord. Inferred type: concept (L0) / home / cluster."""
        from datetime import UTC, datetime

        from klustra.core.page import ClusterMeta

        now = datetime.now(UTC)

        if record.level == 0:
            sources = []
            for sid in record.source_ids:
                sr = self.state.get_source(sid)
                if sr:
                    sources.append(SourceRef(source_id=sid, source_path=sr.source_path))
            return Page(
                type="concept",
                level=record.level,
                entity_id=record.entity_id,
                title=record.title or record.entity_id,
                description=record.description,
                tags=list(record.tags),
                domain="default",
                confidence=0.5,
                sources=sources,
                created_at=now,
                updated_at=now,
            )

        ptype: Literal["home", "cluster"] = (
            "home" if record.entity_id.endswith(".home") else "cluster"
        )
        hstate = self.state.get_hierarchy_state()
        children: list[str] = []
        if hstate is not None:
            children = [
                cid
                for cid, parent in hstate.cluster_membership.items()
                if parent == record.entity_id
            ]
        return Page(
            type=ptype,
            level=record.level,
            entity_id=record.entity_id,
            title=record.title or record.entity_id,
            description=record.description,
            tags=list(record.tags),
            domain="default",
            confidence=0.8 if ptype == "cluster" else 1.0,
            children=children,
            cluster_meta=ClusterMeta(
                algo="hdbscan",
                run_id=record.entity_id,
                cohesion=0.7 if ptype == "cluster" else 1.0,
            ),
            created_at=now,
            updated_at=now,
        )

    def _read_body(self, entity_id: str) -> str:
        """Read body markdown from vault. Returns empty string if not found."""
        vault_path = self.root / ".klustra" / "vault" / f"{entity_id}.md"
        if vault_path.exists():
            return vault_path.read_text(encoding="utf-8")
        return ""

    def _write_body(self, entity_id: str, body_md: str) -> None:
        """Write body markdown to vault."""
        vault_dir = self.root / ".klustra" / "vault"
        vault_dir.mkdir(parents=True, exist_ok=True)
        (vault_dir / f"{entity_id}.md").write_text(body_md, encoding="utf-8")

    def _build_connector_registry(self) -> ConnectorRegistry:
        registry = ConnectorRegistry()
        registry.register(LocalFolderConnector(self.translator_registry))
        return registry

    # --- Hierarchy helpers ---

    def _record_to_hierarchy_node(self, record: PageRecord) -> HierarchyNode:
        body = self._read_body(record.entity_id)
        return HierarchyNode(
            entity_id=record.entity_id,
            content_hash=record.content_hash,
            body_md=body,
            title=record.title or record.entity_id,
            description=record.description,
            tags=list(record.tags),
            level=record.level,
        )

    def _build_hierarchy_config(self) -> HierarchyConfig:
        h = self.config.hierarchy
        model = "default"
        hier_cfg = self.config.llm.hierarchy
        if hier_cfg is not None:
            model = hier_cfg.model
        return HierarchyConfig(
            mode=h.mode,
            min_cluster_size=h.min_cluster_size,
            home_threshold=h.home_threshold,
            probability_threshold=h.probability_threshold,
            model=model,
            domain="default",
        )

    def _build_incremental_config(self) -> IncrementalConfig:
        h = self.config.hierarchy
        judge_model = "default"
        judge_cfg = self.config.llm.judge
        if judge_cfg is not None:
            judge_model = judge_cfg.model
        return IncrementalConfig(
            materiality_threshold=h.materiality_threshold,
            drift_threshold_percent=h.drift_threshold_percent,
            judge_model=judge_model,
        )

    def _embed_nodes(
        self, nodes: list[HierarchyNode], cache: EmbeddingCache
    ) -> dict[str, list[float]]:
        texts = [n.body_md for n in nodes]
        hashes = [n.content_hash for n in nodes]
        vectors = cache.get_or_embed(texts, hashes, self.embedding_provider)
        return {n.entity_id: v for n, v in zip(nodes, vectors, strict=True)}

    def _diff_ids(
        self, nodes: list[HierarchyNode], prev: HierarchyStateRecord
    ) -> tuple[list[str], list[str], list[str]]:
        """Return (changed, added, removed) entity_ids vs prev snapshot."""
        prev_hashes = prev.page_content_hashes
        current_ids = {n.entity_id for n in nodes}
        prev_ids = set(prev_hashes.keys())
        added = sorted(current_ids - prev_ids)
        removed = sorted(prev_ids - current_ids)
        changed: list[str] = []
        for n in nodes:
            if n.entity_id in prev_hashes and prev_hashes[n.entity_id] != n.content_hash:
                changed.append(n.entity_id)
        return changed, added, removed

    def _apply_stability(
        self,
        result: HierarchyResult,
        prev: HierarchyStateRecord | None,
        threshold: float,
    ) -> tuple[HierarchyResult, dict[str, str]]:
        """Match new cluster/home pages against prev's; inherit entity_ids where Jaccard passes."""
        if prev is None:
            return result, {}

        prev_clusters = [
            OldCluster(entity_id=eid, children=list(children))
            for eid, children in self._prev_cluster_children(prev).items()
        ]
        new_clusters = [
            NewCluster(entity_id=p.entity_id, children=list(p.children))
            for p in result.pages
            if p.type in ("cluster", "home")
        ]
        if not prev_clusters or not new_clusters:
            return result, dict(prev.superseded_map)

        match_result = match_clusters(prev_clusters, new_clusters, threshold=threshold)
        rename: dict[str, str] = {}
        for m in match_result.matches:
            new_id = new_clusters[m.new_index].entity_id
            if m.inherited and new_id != m.new_entity_id:
                rename[new_id] = m.new_entity_id

        if not rename:
            return result, dict(match_result.superseded)

        new_pages: list[Page] = []
        new_bodies: dict[str, str] = {}
        for p in result.pages:
            renamed_children = [rename.get(c, c) for c in p.children]
            if p.entity_id in rename:
                new_eid = rename[p.entity_id]
                p_new = p.model_copy(update={"entity_id": new_eid, "children": renamed_children})
                new_pages.append(p_new)
                new_bodies[new_eid] = result.bodies.get(p.entity_id, "")
            else:
                p_new = p.model_copy(update={"children": renamed_children})
                new_pages.append(p_new)
                new_bodies[p.entity_id] = result.bodies.get(p.entity_id, "")

        rewritten = HierarchyResult(pages=new_pages, bodies=new_bodies, max_level=result.max_level)
        superseded = dict(match_result.superseded)
        return rewritten, superseded

    @staticmethod
    def _prev_cluster_children(prev: HierarchyStateRecord) -> dict[str, list[str]]:
        """Invert prev.cluster_membership → parent_id → [child_ids]."""
        out: dict[str, list[str]] = defaultdict(list)
        for child_id, parent_id in prev.cluster_membership.items():
            out[parent_id].append(child_id)
        return dict(out)

    def _persist_hierarchy(
        self,
        result: HierarchyResult,
        page_embeddings: dict[str, list[float]],
        concept_nodes: list[HierarchyNode],
        superseded_map: dict[str, str],
        run_id: str,
    ) -> None:
        """Persist cluster/home pages to state + vault; save HierarchyStateRecord."""
        import hashlib

        cluster_membership: dict[str, str] = {}
        cluster_summaries: dict[str, str] = {}

        for page in result.pages:
            body = result.bodies.get(page.entity_id, "")
            content_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
            self.state.put_page(
                PageRecord(
                    entity_id=page.entity_id,
                    source_ids=[],
                    level=page.level,
                    content_hash=content_hash,
                    title=page.title,
                    description=page.description,
                    tags=list(page.tags),
                ),
                run_id=run_id,
            )
            self._write_body(page.entity_id, body)
            for child_id in page.children:
                cluster_membership[child_id] = page.entity_id
            cluster_summaries[page.entity_id] = page.description

        page_content_hashes = {n.entity_id: n.content_hash for n in concept_nodes}
        record = HierarchyStateRecord(
            run_id=run_id,
            page_embeddings=page_embeddings,
            page_content_hashes=page_content_hashes,
            cluster_membership=cluster_membership,
            cluster_summaries=cluster_summaries,
            superseded_map=superseded_map,
        )
        self.state.put_hierarchy_state(record, run_id=run_id)

    def _package_incremental_result(
        self,
        prev: HierarchyStateRecord,
        inc_result: IncrementalResult,
        new_embeddings: dict[str, list[float]],
        nodes: list[HierarchyNode],
        run_id: str,
    ) -> HierarchyResult:
        """No structural change — refresh embeddings snapshot, return synthetic result."""
        page_content_hashes = {n.entity_id: n.content_hash for n in nodes}
        record = HierarchyStateRecord(
            run_id=run_id,
            page_embeddings=new_embeddings,
            page_content_hashes=page_content_hashes,
            cluster_membership=prev.cluster_membership,
            cluster_summaries=prev.cluster_summaries,
            superseded_map=prev.superseded_map,
        )
        self.state.put_hierarchy_state(record, run_id=run_id)

        pages: list[Page] = []
        bodies: dict[str, str] = {}
        for record_ in self.state.list_pages():
            if record_.level == 0:
                continue
            page = self._record_to_page(record_)
            if page is None:
                continue
            bodies[record_.entity_id] = self._read_body(record_.entity_id)
            pages.append(page)
        max_level = max((p.level for p in pages), default=0)
        return HierarchyResult(pages=pages, bodies=bodies, max_level=max_level)
