# STATUS

Real implementation state, not aspirational. Rebuilt from `SPEC.md`, `CLAUDE.md`, the actual `klustra/` tree, `git log`, and a full audit run (ruff/mypy/pytest + wiring read-through). If this file and `SPEC.md` disagree, trust this one for *what exists today*; trust `SPEC.md` for *intended design*.

**Current version:** `v0.2.0` (git tag, at commit `d0b8923`). Note: `pyproject.toml` still says `version = "0.1.0"` — the version string was not bumped when the tag was cut; cosmetic, but real.

## Verified working

Real-LLM smoke test (`scripts/smoke_pipeline.py`, gated by `KLUSTRA_SMOKE=1`, OpenRouter × `deepseek/deepseek-v4-flash`) passed **end-to-end**: ingest → compile → hierarchy → export, ~77 LLM calls, ~2.6¢ total cost.

Two real bugs were found this way and are fixed in code (verified, not just claimed):
- **Confidence schema had no numeric bounds** → model returned `9` on a 1–10 scale. Fixed in `klustra/engine/models.py`: `confidence: float = Field(ge=0.0, le=1.0)` plus matching `"minimum"/"maximum"` in the JSON schema sent to the model.
- **Empty completions from the model** → `LLMEmptyCompletionError` (`klustra/core/errors.py`) raised in `klustra/llm/openai_provider.py`, caught by the retry path.

Baseline verification (last full run):
```
ruff check .            -> All checks passed
ruff format --check .   -> 103 files already formatted
mypy klustra/           -> Success: no issues found in 52 source files
pytest -q               -> 379 passed
pytest test_golden.py   -> 1 passed (mini-corpus -> golden OKF bundle, end-to-end)
```

## Module status

| Module | Implemented | Tested | Wired into `api.py`/CLI |
|---|---|---|---|
| `core/` (models, config, StateStore, ChangeSet) | Yes | Yes | Yes |
| `ingestion/` (TranslatorRegistry, source manager, DomainRegistry, connectors) | Yes | Yes | Yes — `domain list/show`, `sync --domain/--all` |
| `translators/` (excel, markdown, text) | Yes (3 of eventual N; pdf/docx are v0.3) | Yes | Yes |
| `engine/` (extraction, librarian, validate, lint, dependency) | Yes | Yes | Yes — `compile`, `validate`, `lint` |
| `linking/` (resolver, link_graph) | Yes | Yes | Yes — invoked from `engine/librarian.py` post-generation |
| `hierarchy/` (clustering, pages, incremental, stability, context) | Yes | Yes | Yes — `build_hierarchy`, `context`/`navigate`/`search` |
| `hierarchy/embeddings.py` | **ABC only** — no concrete `EmbeddingProvider` implementation exists anywhere | N/A | **No** — CLI never constructs one from `llm.embeddings` in `klustra.toml`; must be passed manually to `Klustra(embedding_provider=...)` in library use |
| `exporters/` | `obsidian` + `okf_bundle` only | Yes (for those two) | Yes |
| `exporters/` — `html` | **Not implemented** (SPEC §15 lists it under v0.2) | — | — |
| `exporters/` — `delta` | Not implemented (v1.0 roadmap item, expected absent) | — | — |
| `llm/` providers | `OpenAICompatible` (OpenAI/OpenRouter/Databricks), `Anthropic`, `Mock` | Yes | Yes |
| `llm/` — Google provider | **Not implemented** (SPEC §8 lists it) | — | — |
| `llm/accounting.py` | `TokenRecord{role, model, tokens_in, tokens_out}` | Yes | Yes, but narrower than SPEC §9's `{run_id, role, model, tokens_in/out, cost_estimate}` — no `run_id`, no `cost_estimate` |
| `llm/retry.py` | Retry with exponential backoff, 3 attempts default | Yes | Yes, but `_after_failure` is a no-op — no attempt count recorded, no WARNING on N≥2, no retry rate in `klustra stats` |

## Known wiring nuance (not a bug given current config, but real)

`Klustra.provider` (`api.py`) resolves and caches **one** LLM client, built only from `llm.extraction.provider`/`.base_url`. The `librarian`, `hierarchy`, and `judge` role configs are read only for their `.model` string — their `.provider`/`.base_url` fields are declared but currently inert. Fine as long as all LLM roles share one provider (the common case); silently wrong if you configure a role on a different provider (e.g. `llm.hierarchy` on `anthropic` while `llm.extraction` is `openrouter` — the hierarchy call would still go through the OpenRouter client).

## Gap list (priority order)

1. **`docs/wiki/` not yet populated.** CLAUDE.md's own progressive-disclosure model and "wiki is the memory" convention depend on it dogfooding itself; it doesn't exist yet.
2. **Retry-attempt visibility.** `llm/retry.py`'s `_after_failure` is a no-op; `TokenRecord` has no `attempt` field; `klustra stats` has no retry-rate output.
3. **`html` exporter missing** (SPEC §15, listed under v0.2 alongside hierarchy engine + context API).
4. **`retry_attempts` config field is dead.** `LLMRoleConfig.retry_attempts` exists in `core/config.py` but nothing reads it; `@llm_retry()` always uses the hardcoded default of 3.
5. **`klustra prompts show/diff` CLI commands absent.** `PromptRegistry` supports `list_roles()`/`is_overridden()` internally; no CLI surface.
6. **Domain webhook stub absent.** SPEC §4.4 asks for a pass-through `klustra webhook serve` stub (contract only); not present.
7. **Accounting record narrower than SPEC §9** — missing `run_id` and `cost_estimate`, so per-run cost breakdowns aren't derivable from `klustra stats` yet.
8. **No Google LLM provider** (SPEC §8 lists OpenAICompatible/Anthropic/Google) — only OpenAI-compatible, Anthropic, and Mock exist.
9. **No concrete `EmbeddingProvider` implementation**, and the CLI doesn't wire `llm.embeddings` config into one even once it exists — currently a library-only concern (see module table above).
10. *(found while writing this doc)* **`engine/dependency.py` (SPEC §5 dependency resolution) is built and unit-tested but never called from `api.py::compile()`.** `compile()` re-translates and re-extracts every tracked source on every call — there is no reverse-index-based incremental re-extraction today, despite `ChangeSet` existing and the machinery for it being present.

Everything else audited against SPEC §4–§7 (translators, two-phase compile, hierarchy recursion/incrementality/stability, context API) is implemented and covered by tests, not just scaffolded.
