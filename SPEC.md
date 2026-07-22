# klustra — Project Specification

**Recursive knowledge abstraction engine.** From heterogeneous files to a hierarchical OKF wiki: concepts → clusters → home.
**Version:** 0.2-draft · **License:** to be decided before the first commit · **Runtime:** Python ≥ 3.11
**Name:** `klustra` (confirmed available on PyPI)
**Reference prior art:** Karpathy LLM Wiki (gist Apr-2026), OKF v0.1 (GoogleCloudPlatform/knowledge-catalog), RAPTOR (Sarthi et al., ICLR 2024), llm-wiki-compiler (atomicstrata), llm_wiki (nashsu), okf-gem/okflint (validator ecosystem).

---

## 1. Goal

Python library + CLI that:
1. Ingests heterogeneous sources (files, recursive folders, and in the future URL/SharePoint/blob) via **pluggable translators**
2. Compiles level-0 OKF pages (`concept`/`entity`) with exact provenance and wikilinks
3. **Recursively abstracts**: clusters the concepts, generates `cluster` pages of increasing level up to a `home` per domain (RAPTOR pattern applied to wiki pages instead of chunks)
4. Maintains the wiki incrementally (add/modify/delete of individual sources)
5. Exports to multiple targets (OKF/Obsidian filesystem, HTML, Delta)
6. Exposes a context API for agent retrieval (concept + cluster ancestors)

Non-goals for v1: UI, serving, a dedicated embedding server, SharePoint auth (arrives with the URL translator).

**Design risk note (from the literature):** a compiled wiki costs more tokens per query than flat RAG, and the advantage materializes on multi-source synthesis questions, not on pinpoint lookups (Cochran 2026, preregistered). Consequence: retrieval must activate the hierarchy only where it helps (§7.3), and the context API is parsimonious by default (§7.2).

---

## 2. Architecture — modules

```
klustra/
├── core/           # data models (pydantic), config, StateStore, ChangeSet
├── ingestion/      # source manager, translator registry, DomainRegistry + SourceConnector (§4.4)
├── translators/    # one module per format (excel.py, markdown.py, text.py, ...)
├── engine/         # two-phase compile + librarian + validate/lint
├── hierarchy/      # recursive clustering + cluster/home pages + judge
├── linking/        # wikilink resolver + link graph (deterministic)
├── exporters/      # okf_bundle, obsidian, html, delta
├── llm/            # provider abstraction + prompt registry + token budget
│   └── prompts/    # default prompts (Jinja2 .md)
├── cli.py          # CLI entrypoint (typer)
└── api.py          # library facade (class Klustra)
tests/              # pytest; fixtures: mini-corpus per domain + golden bundle
```

Dependencies: `pydantic>=2`, `typer`, `hdbscan`, `scikit-learn` (optional GMM), `umap-learn`, `numpy`, `openai`, `anthropic`, `pyyaml`, `jinja2`, `openpyxl`. Optional extras: `klustra[delta]` (databricks-sdk, delta), `klustra[pdf]` (docling).

---

## 3. Data model (core)

### 3.1 Page (OKF-P frontmatter)

```yaml
---
type: concept            # concept | entity | record-set | cluster | home | index
level: 0                 # 0 = atomic; cluster: 1..N; home: max level of the hierarchy
entity_id: prod.cable.p-laser-320kv
title: "..."
description: "..."
aliases: []
domain: engineering
tags: [domain/hvdc, standard/iec-62895, status/verified]
confidence: 0.92
sources:                 # level 0 ONLY. Exact path + locator
  - source_id: "sha256:9f2a..."
    source_path: "sharepoint://sites/RD/datasheets/PL320.pdf"
    locator: "page:4/table:2"
    translator: "pdf@1.0"
children: []             # level >= 1 ONLY: entity_id of the aggregated pages
memberships: []          # level 0 ONLY, if soft clustering is active: secondary clusters (§6.1)
cluster_meta:            # type: cluster|home ONLY
  algo: hdbscan          # or gmm
  run_id: "..."
  cohesion: 0.78
superseded_by: null      # entity_id of the successor cluster, if superseded (§6.4)
created_at: ...
updated_at: ...
schema_version: "1.0"
---
```

Rules:
- `type: cluster` is a single type for all aggregated levels; the level lives ONLY in `level`. `home` = root of the domain (one per domain). Cross-domain meta page (`domain: _meta`) is debug-only, excluded from retrieval by default.
- `entity_id` = identity = path (`.` → `/`). Cluster: `cluster.<domain>.l<level>.<stable-slug>`.
- Wikilinks in the body ONLY to existing `entity_id`s: `[[prod.family.p-laser]]`. Never to titles, never invented.

### 3.2 StateStore (ABC)

Implementations: `FileStateStore` (v0.1: `.klustra/state.json` + filesystem vault — standalone CLI) and `DeltaStateStore` (v1.0: pages/records/links/sources tables per the separate OKF-P storage spec).
Tracks: sources (SHA-256, path, translator, status, timestamps), pages (entity_id → source_ids, level, content-hash, embedding-hash), link graph, run log. Every mutation carries a `run_id`.

### 3.3 ChangeSet

Output of every ingestion operation and input to the incremental compile:
`{sources: {added, modified, removed}, pages: {added, updated, removed, affected}}`.

---

## 4. Ingestion and Translators

### 4.1 Pattern: Strategy + Registry

```python
class Translator(ABC):
    name: str                    # "excel"
    version: str                 # "1.0" — used in provenance
    extensions: set[str]         # {".xlsx", ".xls", ".xlsm"}
    schemes: set[str] = set()    # future: {"sharepoint", "https"}
    deterministic: bool = True   # False for agentic translators (same output contract)

    @abstractmethod
    def translate(self, source: SourceRef, ctx: TranslateContext) -> TranslationResult: ...

class TranslationResult(BaseModel):
    units: list[KnowledgeUnit]   # 1 source → N units
    source_metadata: dict
    warnings: list[str]

class KnowledgeUnit(BaseModel):
    unit_id: str                 # {source_id}#{seq} — deterministic
    kind: str                    # narrative | table | record_batch | image_text
    content_md: str
    records: list[dict] | None   # tidy rows if kind=table/record_batch
    locator: str                 # "sheet:Params!A1:F120" | "page:4/table:2"
    inherited_context: dict      # inherited metadata (sheet, section, global units)
```

- `TranslatorRegistry.register(translator)`: extension/scheme → translator. Custom format = one class, zero changes elsewhere.
- Deterministic translators: **zero LLM** (unanimous ecosystem consensus: deterministic fetch/convert kept separate from LLM synthesis). Semantics are the engine's job.

### 4.2 ExcelTranslator (quality reference)

1 file → N units:
1. Table detection per sheet (structural anchors: empty rows/columns, type changes, merged headers); one sheet can produce multiple units.
2. Table → `KnowledgeUnit(kind="table")`: `content_md` = normalized markdown table (merged cells exploded), `records` = typed tidy rows, `locator` = `sheet:{name}!{range}`, `inherited_context` = {sheet_name, title_row, global_units, file_props}.
3. Text outside tables → `kind="narrative"` per sheet.
4. Formulas: `{"value": 42, "formula": "=B2*C2"}`.
5. No entity-vs-record semantic decision here: that's the engine's job.

### 4.3 Source manager

| Operation | Library | CLI |
|---|---|---|
| Ingest file | `nx.ingest_file(path, domain=...)` | `klustra ingest FILE -d DOMAIN` |
| Ingest folder recursively | `nx.ingest_folder(path, recursive=True, glob=...)` | `klustra ingest DIR -r` |
| Update file | `nx.update_source(path)` | `klustra update FILE` |
| Removal | `nx.remove_source(path)` | `klustra remove FILE` |
| Sync folder (diff) | `nx.sync_folder(path)` | `klustra sync DIR` |
| Compile | `nx.compile()` | `klustra compile` |
| Hierarchy | `nx.build_hierarchy()` | `klustra hierarchy` |
| Export | `nx.export(target, out)` | `klustra export obsidian -o DIR` |

- `sync_folder` = diff listing ↔ state → generates add/update/remove. Building block for the future SharePoint scheduler (same diff, listing from a Graph API delta query).
- Delete: cascades with **shared entity preservation** — removes the source from `sources[]`; the page is regenerated from the remaining sources; zero sources → page removed, inbound links → lint.
- All operations return a `ChangeSet`.

### 4.4 Domain Registry

A dedicated component (`ingestion/domain_registry.py`) that exposes domain configuration to the rest of the system. **v0.1: reads from local files.** No other module touches the config file directly — if the source later becomes a Delta table or a service, only this component changes.

**Format:** one TOML file per domain in `.klustra/domains/<label>.toml` (consistent with the `noesis.toml`/`.klustra/instructions/` already in the spec — same style, same folder).

```toml
# .klustra/domains/engineering.toml
label = "engineering"
title = "Engineering — HVDC Cables"
description = "Technical documentation, datasheets, standards for the HVDC product line"

[[sources]]
type = "local_folder"       # only type supported in v0.1
path = "C:/data/engineering"
recursive = true
glob = ["*.xlsx", "*.pdf", "*.md"]

[[sources]]
type = "local_folder"
path = "C:/data/engineering-archive"
recursive = false
```

The **per-domain context/behavior prompt** is not duplicated here: it stays in `.klustra/instructions/<label>.md` (§10), linked by naming convention (the domain's `label` = the instructions filename). The domain file describes *where the data is*; the instructions describe *how to treat it*. If instructions don't exist for a given `label`, compile proceeds with default instructions only, plus a warning.

**Data model:**

```python
class SourceConfig(BaseModel):
    type: str              # "local_folder" today; "sharepoint"|"blob" in the future — same field, new values
    # type-specific fields, validated by a per-type schema

class DomainConfig(BaseModel):
    label: str              # primary key, matches instructions/<label>.md
    title: str
    description: str
    sources: list[SourceConfig]   # one or more sources per domain
```

**Connector pattern (parallel to Translator, same registry):**

```python
class SourceConnector(ABC):
    type: str                # "local_folder"
    @abstractmethod
    def sync(self, source: SourceConfig, state: StateStore) -> ChangeSet: ...
```

`LocalFolderConnector` is the only v0.1 implementation — it wraps `ingestion.sync_folder` (already in §4.3) behind this contract. Adding a `SharePointConnector`/`BlobConnector` in the future means: one new class + one new `type` in the TOML, **zero changes** to `DomainRegistry`, `engine/`, `hierarchy/` — the same extensibility guarantee as translators.

**Update triggers (v0.1, both manual/explicit — no automatic polling):**

| Mechanism | Command | Notes |
|---|---|---|
| Manual CLI | `klustra sync --domain engineering` | Invokes the connector for every source in the domain, produces a `ChangeSet`, passes it to compile. For all domains: `klustra sync --all` |
| Webhook (stub, endpoint ready but not wired to anything in v0.1) | `klustra webhook serve` | Exposes a minimal HTTP endpoint that accepts `{domain, source_index}` and invokes the same connector `sync()` — pass-through, zero provider-payload parsing logic. Real integration with Graph API change notifications / Event Grid is v1.x (§15); here only the contract is fixed: whichever provider notifies, the webhook always translates it into the same `connector.sync()` → `ChangeSet` → compile call |

**Additional CLI commands:**

| Command | Effect |
|---|---|
| `klustra domain list` | Lists domains from `.klustra/domains/*.toml` |
| `klustra domain show LABEL` | Resolved config + last-sync status + linked instructions (or a warning if missing) |
| `klustra sync --domain LABEL` / `--all` | Manual trigger, for all sources in the domain |

---

## 5. Engine — two-phase compile + Librarian

### Phase 1 — Extraction
For every new/changed unit: LLM structured-output → concept candidates `{name, entity_id_proposal, summary, is_new, related_existing[]}`. The prompt receives: the unit, the domain's current index filtered by relevance (§9), and domain instructions (§10).

### Dependency resolution
Reverse concept→sources index from state. Unchanged sources that share concepts with changed ones → re-extracted in the same batch (a single post-extraction pass; the full state is queryable).

### Phase 2 — Merge & generate (Librarian)
An LLM that generates/updates the page for a concept, receiving all contributions from the owning sources. Prompt responsibilities:
1. Coherent multi-contribution synthesis
2. **Obsolescence**: conflicting claims → the most recent timestamp wins; the discarded claim goes into `## History and revisions` with a reference, never silently dropped
3. **Mandatory citations**: every factual claim → `^[source_id:locator]`; a page with no citations = reject
4. **Wikilinks only from the closed list** of entity_ids provided in the prompt

Post-generation (deterministic): frontmatter validation (pydantic), wikilink resolver (rule-based on the alias map), link graph update, atomic write, index rebuild.

### 5.1 Validate vs Lint (separated, aligned with the OKF ecosystem)

| Command | Question | Policy |
|---|---|---|
| `klustra validate` | OKF §9 conformance: frontmatter parseable, `type` non-empty, path=identity, reserved files correct | Hard error, blocks the okf_bundle export. **Never** an error for a broken link or missing optional fields (per OKF spec these are "knowledge not yet written") |
| `klustra lint` | Quality: reachability (orphans, disconnected islands, not-in-index), completeness (stubs, missing fields), freshness (`--stale-after`), provenance (uncited claims, broken citations), hygiene (duplicate titles, self-links), broken wikilinks | Warning by default; each category can be promoted to an error in config → the run's quality gate |

Contradictions and *semantic* staleness are outside deterministic lint (they require understanding): the responsibility of the Librarian (§5) and of a schedulable LLM check (`klustra lint --semantic`, v0.3).

### 5.2 Input bounds and chunking (Phase 1)

Input size is checked **before** the call, never discovered from a provider error. `llm/tokens.py::count_tokens` counts with `cl100k_base` and inflates the result by `SAFETY_MARGIN` (1.20); when tiktoken cannot be loaded (offline machine, no cached vocab) it degrades to a deliberately pessimistic 3 chars/token heuristic rather than failing the compile. cl100k is a *proxy* — the target model's tokenizer is generally not available locally — so the margin, not tokenizer fidelity, is what makes the gate safe. For a threshold gate an overestimate is the benign direction: too high means chunking a little early, too low means the context overflow this guards against.

**Config: `extraction.max_input_tokens`, default 24 000.** Derivation, using the smallest context window we are willing to assume for a configured model (32 768):

| Term | Tokens |
|---|---|
| assumed context floor | 32 768 |
| reserved for completion (`llm.extraction.max_tokens`, typical) | −4 096 |
| prompt scaffolding: system prompt, JSON schema, entity index | −2 048 |
| remaining | 26 624 |
| −10 % headroom | ≈ 23 960 |

Rounded down to **24 000**. It is a floor-oriented default, not a model-specific one: no claim is made here about any particular provider's window. Large-context models should raise it in `klustra.toml`; too low only costs extra chunks. **A model with a window below 32 768 must lower it** — at the default, chunking would not trigger until 24 000 tokens and a 16 k-context model would overflow, i.e. the original bug re-armed.

The per-call budget for *content* is `max_input_tokens` minus the measured cost of the scaffolding, so a growing entity index shrinks the content budget instead of silently blowing the ceiling. If the scaffolding alone leaves less than 256 tokens, `LLMInputTooLargeError` is raised naming the index size.

**Chunking** (`engine/chunking.py`, deterministic, zero LLM) applies only above the threshold — content that fits is passed through byte-identical. Split ladder, each rung used only when the previous one is insufficient:

1. **blocks** — markdown headings start a block, otherwise blank-line paragraphs; blocks are packed greedily
2. **sentences** — only for a single block that overflows alone; logged at WARNING
3. **hard character slice** — only for a single sentence that overflows alone; logged at WARNING

The only context carried between chunks is the enclosing heading, repeated as `<heading> (continued)`; structured extraction does not need overlapping windows.

**Map-reduce.** Each chunk is one extraction call; the partial candidates are accumulated (deduped by `entity_id_proposal`) onto the unit's single `ExtractionResult`. `source_id`, `unit_id` and `locator` are identical across chunks, so provenance is unaffected. Consolidation is *not* re-implemented: candidates converge through `api.compile`'s per-entity grouping into the existing Phase 2 Librarian merge.

**`LLMInputTooLargeError` is not an `LLMCallError`** — `llm/retry.py::_is_retryable` must never see it. Retrying identical oversized input is guaranteed to fail; the correct response is chunking. It survives as the runtime bound that fires when even the finest split cannot fit.

**Known gap:** Phase 2 has no equivalent bound. `api.compile` builds every `SourceContribution` with all units of a source, so the Librarian call can still exceed a context window on a large corpus. Chunking there is not simply reusable — the Librarian's job is whole-entity synthesis — and is deferred.

### 5.3 Resumable compile

An interrupted compile resumes from the first unprocessed source instead of restarting. Progress is checkpointed through `StateStore` (`get_checkpoints` / `put_checkpoint` / `clear_checkpoints`), persisted in `.klustra/state.json`.

**Key = `source_id`, not `entity_id`.** `entity_id` is a Phase 1 *output* — LLM-proposed, discovered only after extraction runs, and many-to-many with files — so it cannot identify a file whose extraction has not happened yet. `source_id` (SHA-256 of the resolved absolute path) is the per-file identity that already exists in state.

A `CompileCheckpoint` carries `{source_id, status, sha256, entity_ids, updated_at}` with `status ∈ {pending, in_progress, done, failed}`. `entity_ids` is the checkpointed Phase 1 result: on resume it is replayed in place of the LLM call, which is what makes a resumed page's `sources[]` identical to an uninterrupted run. Units are re-derived by re-translating (deterministic, zero LLM), so nothing else needs persisting — `is_new` and `related_existing` are not consumed downstream.

**Resume rules.** Only `done` gates skipping; `pending`, `in_progress` and `failed` all mean reprocess. `in_progress` is never trusted — it is exactly what a crash mid-extraction leaves behind, and redo is always at whole-file granularity, never at chunk granularity (§5.2), to avoid a partial-unit merge.

**Invalidation.** A checkpoint whose `source_id` is no longer tracked is dropped and logged; a checkpoint whose `sha256` no longer matches the source is requeued. Neither triggers a silent full reprocess.

**Scoping.** Checkpoints live in the project's single `.klustra/state.json`, keyed by a path-derived `source_id`, so different source sets cannot cross-contaminate. Lookup is deliberately **run_id-independent**: a resuming compile mints a new `run_id` and must still see the prior run's progress. Note that `compile` has no notion of a domain today — it processes every source in `state.list_sources()` — so domain-level scoping does not apply.

**Lifecycle.** Checkpoints are a crash artifact, not permanent state: a fully successful compile clears them, so a repeated `compile()` behaves exactly as it did before this feature. Any raise leaves them intact.

**Phase 2 gate.** The Librarian merge runs only when every tracked source is `done`; otherwise `CompileIncompleteError` is raised. Merging a partial contribution set would silently drop the provenance of sources whose extraction never ran. A crash between Phase 1 and Phase 2 therefore resumes by replaying all checkpoints (zero extraction calls) and re-running Phase 2.

**Known gap:** Phase 2 itself is not checkpointed — an interruption during the Librarian merge re-runs every entity, though pages already written are simply overwritten with equivalent content.

**CLI:** resume is the default; `klustra compile --fresh` (alias `--no-resume`) discards checkpoints and recompiles everything.

---

## 6. Hierarchy engine (the heart of the system)

### 6.1 Recursive algorithm (RAPTOR-style on pages)

```
level = 0; pages = domain concepts
loop:
    embeddings = embed(pages)                     # body_md; cached by content-hash
    reduced = UMAP(embeddings)                    # n_neighbors scales with |pages|
    clusters, outliers = cluster(reduced)         # see below
    if n_top_nodes <= home_threshold (default 5) or len(clusters) <= 1:
        generate HOME (type: home, level=level+1); break
    for c in clusters:  generate cluster page (level=level+1, children=[...])
    outliers: pass through to the next level (no placeholder page)
    pages = cluster_pages + outliers; level += 1
```

**Clustering — hard vs soft decision (configurable per domain, default hard):**
- `mode: "hard"` (default): HDBSCAN. Every concept has a single parent cluster → a clean tree, `children` is a partition. `min_cluster_size` is configurable (default 4).
- `mode: "soft"`: GMM with a probability threshold (RAPTOR): a concept can belong to multiple clusters. The highest-probability cluster is the **primary parent** (for the navigation tree and the home); the others end up in the concept's `memberships` and as *secondary* children of the cluster (linked in the body, not in `children`). The hierarchy stays a tree for navigation, a DAG for context.
- Features: embedding (weight 1.0); tag-overlap and link-graph adjacency optional behind a flag (v0.2+).

**Cluster page:** LLM synthesis from the title+description+tags of the children (never the full bodies; for cluster children, also their synthesis). Output: a thematic title, a description, a body that explains the theme and links all members. **Home:** a dedicated prompt ("explain the domain to a new engineer, navigate by area").

### 6.2 Incrementality

Trigger: the compile's `ChangeSet`.
1. **Materiality pre-filter (deterministic, zero LLM):** for every modified concept, cosine distance between the old and new embedding; below the threshold (default 0.10, configurable) → the delta isn't material, only `updated_at` is refreshed, no judge, no propagation upward. (Materiality-scored principle from the streaming-compilation literature: not every delta deserves an LLM call.)
2. Material deltas and new/removed concepts → identify the affected L1 clusters (membership, or nearest centroid for new concepts).
3. **Reclustering LLM-judge** for every affected cluster: input {current synthesis, members, delta} → structured `fits | regenerate_page | recluster_subtree`:
   - `fits`: update only the cluster page
   - `regenerate_page`: regenerate the synthesis, propagate the judge to the parent
   - `recluster_subtree`: re-run clustering on the parent's subset, rebuild the branch
4. Upward propagation only on a structural change at the level below. Full re-hierarchy: `klustra hierarchy --full` or an accumulated-drift threshold (% of concepts changed since the last full run).

### 6.3 Cluster stability

- Matching across runs: a new cluster inherits the old one's `entity_id` if member Jaccard ≥ 0.6. Otherwise a new id; the old one → `status/superseded` + `superseded_by` in the frontmatter (redirect: inbound wikilinks stay resolvable, lint flags the migration).
- Cluster slug: thematic, LLM-generated at first creation, then **immutable** for as long as the cluster survives matching.

---

## 7. Retrieval and context API

### 7.1 API

```python
nx.context(entity_id, depth=1, include=("ancestors",)) -> ConceptContext
nx.navigate(from_entity_id=None) -> home / children       # guided descent
nx.search(query, level=None, mode="collapsed") -> ranked   # see 7.3
```

### 7.2 Parsimony by default

`nx.context` default: page + **only the ancestors chain as title+description** (one lookup, zero LLM, a few hundred tokens). Siblings, cluster bodies, records_ref: only on explicit request (`include=("ancestors","siblings","records")`, `depth=N`). Rationale: the wiki's query cost can exceed flat RAG on simple lookups; rich context should only be spent where the query justifies it.

### 7.3 Anti-bypass strategy (Progressive Disclosure lesson)

Empirical evidence: agents with generic search tools **don't load the index/hierarchy** — they infer the page path and read it directly, zeroing out the value of the synthesis levels. Design countermeasures:
1. **Collapsed-tree search** (`mode="collapsed"`, default): concept + cluster + home indexed **together** in the same vector space; ranking picks the right abstraction level for the query on its own (synthetic queries naturally match cluster pages). The hierarchy adds value even to an agent doing a single search, without requiring explicit traversal.
2. `mode: "tree"`: explicit top-down traversal with per-level pruning (for orchestrated agents that navigate).
3. In downstream integrations (MCP server, agent tooling): expose `context/navigate/search` as the **only tools for accessing the wiki** — don't put a generic file-read next to the vault, or agents will use it and bypass the hierarchy.

The ranking boost for cluster/home pages is not klustra's responsibility (it depends on the downstream stack); klustra guarantees `level` and the ancestors chain are always available at O(1) cost.

---

## 8. LLM layer

`LLMProvider` ABC + implementations: `OpenAICompatible` (OpenRouter/OpenAI/Databricks/gateway, configurable base_url), `Anthropic`, `Google`. Per-role config:

```toml
[llm.extraction]   provider="openrouter" model="deepseek/deepseek-v4-flash" max_tokens=4096
[llm.librarian]    provider="openrouter" model="deepseek/deepseek-v4-pro"
[llm.hierarchy]    provider="anthropic"  model="claude-sonnet-4-6"
[llm.judge]        provider="openrouter" model="deepseek/deepseek-v4-flash"
[llm.embeddings]   provider="openai"     model="text-embedding-3-small"
```

Retry with backoff (default 3), rate limiting, structured output via JSON schema (tool-use where supported, otherwise response_format).

## 9. Token sensitivity

- Per-call, per-role budget; every prompt builder declares components with priority and a reduction strategy: index → filtered by similarity to the unit, then truncated; merge contributions → summary-of-summaries past budget; cluster children → title+description only.
- Per-call accounting {run_id, role, model, tokens_in/out, cost_estimate} → `klustra stats`.
- Extraction+embedding cache keyed by content-hash; zero calls on unchanged content.

## 10. Prompt customization

- Defaults ship in the package (`klustra/llm/prompts/*.md`, Jinja2).
- Override: `.klustra/prompts/{role}.md` (full replacement) or `.klustra/instructions/{domain}.md` (**injected** into every prompt for that domain: company context, tag taxonomy, entity-vs-record rule, glossary). User-authored, never rewritten by the system.
- `klustra prompts show ROLE` / `klustra prompts diff` for transparency.

## 11. Exporters

`Exporter` ABC + registry: `okf_bundle` (relative markdown links; passes `klustra validate` + interoperable with okflint/okf-gem; reserved index/log with no frontmatter; root index with `okf_version: "0.1"`), `obsidian` ([[wikilinks]]), `html` (static, home→cluster→concept nav), `delta` (v1.0). Multiple exports per run.

## 12. CLI and config

`typer`; commands from §4.3 + `init` (scaffold: klustra.toml, instructions template, .klustra/), `validate`, `lint`, `stats`, `prompts`. Config in root `klustra.toml`; secrets ONLY from env (`OPENROUTER_API_KEY` etc.). `klustra` ≡ `python -m klustra`.

## 13. Traceability

Every run: `run_id`, command, parameters, ChangeSet, LLM accounting, quality-gate outcome → `.klustra/runs.jsonl` (or a run table on Delta). Page contents/prompts/LLM output are never logged (unless `--debug`). Per-domain OKF `log.md` generated deterministically from the runs.

### 13.1 Progress contract — nothing runs silently

Every operation expected to exceed 1-2s, and every LLM/embedding call, is wrapped in `logging_setup.log_op`. It emits one line per transition on the `klustra.progress` logger:

```
phase=extraction action=llm_call source_id=a227c4e2 unit_id=a227c4e2#0 chunk=9/17 input_tokens=2996 model=... status=start
phase=extraction action=llm_call ... status=running elapsed_ms=15002      # heartbeat
phase=extraction action=llm_call ... status=done elapsed_ms=18431
```

`phase ∈ {extraction, librarian_merge, hierarchy, export, llm}`, `action ∈ {chunking, llm_call, retry, embed, umap_reduce, cluster, ...}`, `status ∈ {start, running, done, failed}`. Failures log at ERROR with `error=<ExceptionType>` and re-raise. Fields are ids, counts and timings only — never prompt or response content, at any verbosity (rule 8); the sole exception is the bounded malformed-JSON snippet the corrective-retry loop already carries.

**Instrumented:** chunking (which re-tokenizes per block and can run tens of seconds on a very large unit), each per-chunk extraction call, the librarian merge and its citation retry, cluster/home page synthesis, the incremental judge, embedding batches, UMAP reduction and HDBSCAN/GMM clustering.

**Heartbeat.** A synchronous blocking call cannot log from the thread that is inside it, so `heartbeat=True` starts a daemon watchdog emitting `status=running elapsed_ms=…` every `HEARTBEAT_INTERVAL_SECONDS` (15s). This is what distinguishes long-but-healthy from hung. UMAP/HDBSCAN release the GIL, so it works for CPU work too.

**Verbosity.** Default INFO shows forward progress without any flag — silence at default level is itself the bug. `--verbose` adds DEBUG request/response shapes and token counts; `--quiet` drops to WARNING (retries, timeouts, errors only) and is an explicit opt-in.

**Flushing.** `logging.StreamHandler` flushes per record, verified by a subprocess test asserting the `status=start` line arrives before a 5s operation completes. No buffering layer may be introduced between the handler and stdout.

**Timeouts.** Every LLM and embedding client is constructed with an explicit `timeout_seconds` (`LLMRoleConfig.timeout_seconds`, default 120s) and `max_retries=0`. The SDK defaults — 600s read timeout with 2 silent internal retries — meant one unresponsive call could block ~30 minutes per attempt with no output and no hook to log from. A timeout raises `LLMTimeoutError` (distinct from `LLMCallError`, still retryable) and logs `status=timeout`. In both providers the `except APITimeoutError` branch **must precede** `except APIConnectionError`, which it subclasses.

## 14. Testing

- Unit: translators (real fixture files per format, including a messy multi-table Excel), wikilink resolver, cluster matching (Jaccard), materiality pre-filter.
- Integration: per-domain mini-corpus → OKF golden bundle diffed; incremental runs (add/modify/delete) with assertions on the ChangeSet and on cluster entity_id stability.
- LLM: deterministic mock provider for CI; optional smoke test with a real provider behind an env flag.

## 15. Roadmap

| Phase | Contents |
|---|---|
| v0.1 | core + FileStateStore, DomainRegistry (TOML, LocalFolderConnector), Excel/Markdown/Text translators, two-phase compile, validate+lint, obsidian+okf_bundle exporters, CLI (incl. `domain`/`sync`) |
| v0.2 | Hierarchy engine (UMAP+HDBSCAN/GMM, judge, materiality, stability), context API + collapsed search, html exporter |
| v0.3 | PdfTranslator (layout-aware), DocxTranslator, lint --semantic, full stats |
| v1.0 | DeltaStateStore + delta exporter, sync scheduler hooks, MCP server, hardening |
| v1.x | `SharePointConnector`/`BlobConnector` (new `type` values in DomainConfig, §4.4), real webhook (Graph API change notifications / Event Grid), URL/scrape translator, agentic translators |

## 16. Open decisions (blocking for v0.1)

1. ~~Name~~ — decided: `klustra`
2. License (internal Prysmian vs open source)
3. Default embedding (`text-embedding-3-small` vs local) — affects who can run the CLI without an OpenAI key
4. Language of generated pages: forced per domain or auto-detected (dominant language of the sources)
