# Architecture (as built)

Condensed, code-grounded companion to `SPEC.md` §2–§7. This describes what the modules actually do and how they call each other today; it does not restate the spec's rationale or data model at length — follow the `SPEC §x` references for that.

## Module map (real files)

```
klustra/core/         knowledge_unit.py, page.py, source_ref.py, changeset.py,
                       config.py, state_store.py (ABC), file_state_store.py, errors.py     SPEC §3
klustra/ingestion/     translator.py, translator_registry.py, source_manager.py,
                       connectors.py, domain_registry.py                                  SPEC §4.1, §4.3, §4.4
klustra/translators/   excel.py, markdown.py, text.py, registry.py                        SPEC §4.1, §4.2
klustra/engine/        extraction.py, chunking.py, librarian.py, models.py,
                       dependency.py, validate.py, lint.py                                SPEC §5, §5.1, §5.2
klustra/linking/       resolver.py, link_graph.py                                          SPEC §3.1 (wikilink rule), §5
klustra/hierarchy/     embeddings.py (ABC only), clustering.py, pages.py,
                       incremental.py, stability.py, context.py                           SPEC §6, §7
klustra/exporters/     exporter.py (ABC + registry), obsidian.py, okf_bundle.py            SPEC §11
klustra/llm/           provider.py (ABC), openai_provider.py, anthropic_provider.py,
                       mock_provider.py, retry.py, tokens.py, accounting.py,
                       prompts.py, prompts/<role>[.<kind>].md                             SPEC §8, §9, §10
klustra/api.py         class Klustra — the only public facade                             SPEC §4.3, §12
klustra/logging_setup.py  configure_logging (CLI verbosity) + log_op progress contract    SPEC §13.1
klustra/cli.py         typer app, thin wrapper over api.py                                SPEC §12
```

See `STATUS.md` for what in this map is implemented vs. still a gap (html exporter, Google provider, concrete embedding provider, etc.).

## Ingestion → translation

`Klustra.ingest_file`/`ingest_folder`/`update_source`/`remove_source`/`sync_folder` (`api.py`) delegate directly to `ingestion/source_manager.py`, which hashes sources, tracks them via `FileStateStore`, and returns a `ChangeSet` (SPEC §3.3, §4.3). `TranslatorRegistry.get_for_path` (`ingestion/translator_registry.py`) picks the translator by extension; `translators/excel.py`, `markdown.py`, `text.py` implement the `Translator` ABC and are the only code paths that touch raw files — deterministic, zero LLM calls (CLAUDE.md hard rule #1). Each produces `KnowledgeUnit`s (SPEC §4.1) consumed by the engine.

Domains are config, not code: `.klustra/domains/<label>.toml` → `ingestion/domain_registry.py` (`DomainConfig`, `LocalFolderSourceConfig`) is the only component that reads that file (SPEC §4.4). `LocalFolderConnector` (`ingestion/connectors.py`) is the only `SourceConnector` in v0.1.

## Two-phase compile (`Klustra.compile`, `api.py`)

0. **Resume check** (SPEC §5.3): `compile()` reads `StateStore.get_checkpoints()` before Phase 1. Sources checkpointed `done` with a matching `sha256` replay their stored `entity_ids` instead of calling the LLM; everything else is reprocessed. Checkpoints clear only on a fully successful run, so a repeated `compile()` is unchanged. `--fresh`/`--no-resume` discards them.
1. **Translate**: every tracked source is re-translated into `KnowledgeUnit`s on every `compile()` call. SPEC §5's dependency-resolution step (reverse index concept→sources, re-extract sources that share concepts with changed ones) is implemented and unit-tested in `engine/dependency.py` (`build_reverse_index`, `resolve_dependencies`, `filter_units_for_sources`) but **not called from `api.py::compile()`** — today compile is all-sources-every-time, not incremental at the engine level.
2. **Phase 1 — Extraction** (`engine/extraction.py::extract_concepts`): per-source-unit LLM call, structured output → concept candidates, validated through pydantic (CLAUDE.md hard rule #3). Grows `existing_index` as new entity_ids are proposed, so later sources in the same compile see earlier ones. Input is token-counted before the call (`llm/tokens.py`) and, only above `extraction.max_input_tokens`, split by `engine/chunking.py` into several calls whose candidates are accumulated back onto the unit's single `ExtractionResult` (SPEC §5.2). Phase 2 has no equivalent bound yet — see the known gap in SPEC §5.2.
3. **Phase 2 — Librarian merge** (`engine/librarian.py::merge_and_generate`): one LLM call per `entity_id`, given all `SourceContribution`s that proposed it. Generates frontmatter + body with mandatory `^[source_id:locator]` citations (SPEC §5, provenance = CLAUDE.md hard rule #4). `resolve_links` (`linking/resolver.py`) then rewrites `[[...]]` targets against the closed `existing_index` list — this is the *only* place wikilinks are written (CLAUDE.md hard rule #2).
4. `persist_librarian_result` writes the `PageRecord` to `FileStateStore` and `Klustra._write_body` writes the markdown body to `.klustra/vault/<entity_id>.md`.

Both LLM calls in this flow go through the **same cached client** (`Klustra.provider`, resolved once from `llm.extraction.provider`) — see the wiring nuance in `STATUS.md`.

`validate()` (`engine/validate.py`) checks OKF conformance only (frontmatter parses, `type` set, path=identity) and never fails on broken links or missing optional fields (SPEC §5.1, hard rule #6). `lint()` (`engine/lint.py`) is the separate quality pass (orphans, staleness, provenance gaps, hygiene) — warnings by default, promotable to errors via `LintConfig.promote_to_error`.

## Hierarchy recursion (`Klustra.build_hierarchy`, SPEC §6)

Given all level-0 concept pages as `HierarchyNode`s:

- **Full path**: `hierarchy/pages.py::build_hierarchy_fn` — embed via `EmbeddingProvider` (cached per content-hash by `EmbeddingCache`), reduce with UMAP, cluster with HDBSCAN (hard mode, default) or GMM (soft mode) in `hierarchy/clustering.py`, generate cluster/home pages bottom-up until `home_threshold` top nodes remain, per SPEC §6.1.
- **Incremental path**: taken when a prior `HierarchyStateRecord` exists and `should_full_rebuild` (`hierarchy/incremental.py`) says drift is below `drift_threshold_percent`. Materiality pre-filter (cosine distance on embeddings vs. `materiality_threshold`) skips non-material deltas with zero LLM calls; material changes go through the LLM-judge (`fits`/`regenerate_page`/`recluster_subtree`) per SPEC §6.2.
- **Stability**: `Klustra._apply_stability` calls `hierarchy/stability.py::match_clusters` — new clusters inherit the old `entity_id` if member Jaccard ≥ `stability_threshold` (default 0.6, SPEC §6.3); non-matched old clusters are tracked in `superseded_map` for lint to flag as migrations.

Results and the embeddings/membership/summaries snapshot are persisted via `Klustra._persist_hierarchy` into a `HierarchyStateRecord`, which is what the next incremental run diffs against.

## Retrieval (`hierarchy/context.py`, SPEC §7)

`Klustra.context`/`navigate`/`search` build a `dict[entity_id, PageSummary]` from all stored pages and delegate to `context()`/`navigate()`/`search()` in `hierarchy/context.py`. `context()` defaults to ancestors-only (SPEC §7.2 parsimony); `search(mode="collapsed")` ranks concept/cluster/home pages together in one space (SPEC §7.3 anti-bypass strategy) — `mode="tree"` does explicit top-down traversal instead.

## Export (`Klustra.export`, SPEC §11)

`ExporterRegistry` (`exporters/__init__.py::build_default_registry`) currently registers `ObsidianExporter` and `OkfBundleExporter` only; both consume the same `list[ExportPage]` (page + rendered body) built from `FileStateStore` + vault contents. `html` and `delta` exporters are not implemented (see `STATUS.md`).
