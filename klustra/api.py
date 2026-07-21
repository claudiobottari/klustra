"""Klustra facade — the ONLY public import surface (SPEC §4.3, §12)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from pathlib import Path

from klustra.core.changeset import ChangeSet
from klustra.core.config import KlustraConfig, load_config
from klustra.core.file_state_store import FileStateStore
from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.page import Page
from klustra.core.source_ref import SourceRef
from klustra.core.state_store import PageRecord
from klustra.engine.extraction import extract_concepts
from klustra.engine.librarian import merge_and_generate, persist_librarian_result
from klustra.engine.lint import LintConfig, LintFinding, lint_pages
from klustra.engine.models import LibrarianResult, SourceContribution
from klustra.engine.validate import ValidationFinding, validate_all
from klustra.exporters import ExportContext, ExporterRegistry, ExportPage, build_default_registry
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
from klustra.llm import AccountingSink, ListSink, LLMProvider, resolve_provider
from klustra.translators.registry import build_default_registry as build_translator_registry


class Klustra:
    """Public facade for all klustra operations (SPEC §4.3)."""

    def __init__(
        self,
        root: Path | str = Path("."),
        *,
        provider: LLMProvider | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.config: KlustraConfig = load_config(self.root / "klustra.toml")
        self.state = FileStateStore(self.root)
        self.translator_registry: TranslatorRegistry = build_translator_registry()
        self.exporter_registry: ExporterRegistry = build_default_registry()
        self._provider = provider
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

    # --- Hierarchy (stub) ---

    def build_hierarchy(self) -> None:
        raise NotImplementedError("hierarchy/ not yet implemented")

    # --- Accounting ---

    @property
    def accounting(self) -> AccountingSink:
        return self._sink

    # --- Private helpers ---

    def _load_pages(self) -> list[Page]:
        pages: list[Page] = []
        for record in self.state.list_pages():
            page = self._record_to_page(record)
            if page:
                pages.append(page)
        return pages

    def _record_to_page(self, record: PageRecord) -> Page | None:
        """Reconstruct a Page from PageRecord. In v0.1, pages are re-derived from state."""
        from datetime import UTC, datetime

        sources = []
        for sid in record.source_ids:
            sr = self.state.get_source(sid)
            if sr:
                sources.append(SourceRef(source_id=sid, source_path=sr.source_path))

        now = datetime.now(UTC)
        return Page(
            type="concept",
            level=record.level,
            entity_id=record.entity_id,
            title=record.entity_id,
            domain="default",
            confidence=0.5,
            sources=sources,
            created_at=now,
            updated_at=now,
        )

    def _read_body(self, entity_id: str) -> str:
        """Read body markdown from vault. Returns empty string if not found."""
        vault_path = self.root / ".klustra" / "vault" / f"{entity_id}.md"
        if vault_path.exists():
            return vault_path.read_text(encoding="utf-8")
        return ""

    def _build_connector_registry(self) -> ConnectorRegistry:
        registry = ConnectorRegistry()
        registry.register(LocalFolderConnector(self.translator_registry))
        return registry
