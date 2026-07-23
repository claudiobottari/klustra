# CLAUDE.md — klustra

Recursive knowledge abstraction engine: heterogeneous files → OKF wiki → hierarchical cluster/home pages.
**This file is for agents. Keep it short. Non-obvious info only. If something is discoverable by reading code, don't write it here.**

## Context budget rule (read this first)

Do NOT preload the whole repo. Progressive disclosure:
1. This file (always in context)
2. `SPEC.md` — the authoritative spec. Architecture questions are answered THERE, not by exploring code. Read the relevant section only.
3. `docs/wiki/` — the repo's own OKF wiki (dogfooding: klustra documents itself with klustra). `docs/wiki/index.md` is the entry point. Prefer reading a wiki concept page over grepping the codebase for "why" questions.
4. Source code — only the module you're changing.

If SPEC.md and code disagree: the spec wins for intent, the code wins for current behavior. Flag the divergence in your response; never silently pick one.

## Commands (uv only — never pip, never python directly)

```bash
uv sync                        # install deps (creates .venv from uv.lock)
uv sync --extra delta --extra pdf   # with optional extras
uv run klustra --help           # run the CLI
uv run pytest                  # full test suite
uv run pytest tests/test_translators/ -x   # one area, fail fast
uv run pytest -k "excel" -x    # by keyword
uv run ruff check --fix . && uv run ruff format .   # lint + format (do this before claiming done)
uv run mypy klustra/            # type check (strict on core/, engine/, hierarchy/)
uv add <pkg>                   # add a dependency (updates pyproject + lock)
uv add --dev <pkg>             # dev dependency
```

Python ≥ 3.11. Version pinned in `.python-version`. Never edit `uv.lock` by hand.

## Definition of done (verification loop)

A change is done ONLY when all pass, in this order:
1. `uv run ruff check . && uv run ruff format --check .`
2. `uv run mypy klustra/`
3. `uv run pytest` — including the golden-bundle integration tests (`tests/test_integration/`)
4. If you touched translators, engine, or hierarchy: run the mini-corpus end-to-end and diff the golden bundle: `uv run pytest tests/test_integration/test_golden.py -x`
5. If you changed any public behavior: update SPEC.md section AND the matching `docs/wiki/` concept page in the same commit

Never claim success without running these. Paste the actual output, not "tests should pass".

## Architecture map (one line per module — details in SPEC.md)

```
klustra/core/         pydantic models, config, StateStore ABC, ChangeSet
klustra/ingestion/    source manager, TranslatorRegistry, DomainRegistry (.klustra/domains/*.toml) + SourceConnector registry
klustra/translators/  one file per format; deterministic, ZERO LLM calls here
klustra/engine/       two-phase compile (extract → librarian merge), validate, lint
klustra/hierarchy/    UMAP + HDBSCAN/GMM clustering, cluster/home pages, LLM judge, materiality filter
klustra/linking/      wikilink resolver + link graph — deterministic, ZERO LLM
klustra/exporters/    okf_bundle, obsidian, html, delta — Exporter ABC + registry
klustra/llm/          provider abstraction, prompt registry (Jinja2), token budget, accounting
klustra/api.py        Klustra facade — the ONLY public import surface
klustra/cli.py        typer CLI — thin wrapper over api.py, no logic here
```

## Hard rules (violations = rejected PR)

1. **LLM calls live ONLY in `engine/`, `hierarchy/`, and `llm/`.** Translators, linking, exporters, validate/lint are deterministic. If you're tempted to add an LLM call elsewhere, stop and re-read SPEC §4.1.
2. **Wikilinks only to existing `entity_id`s from a closed list.** Never let a prompt invent link targets. The resolver in `linking/` is the only component that writes `[[...]]` into final output.
3. **Every LLM output crosses a pydantic model.** No raw-string parsing of model responses. Structured output via JSON schema; validation failure = retry with error feedback, then hard fail.
4. **Provenance is sacred.** Every KnowledgeUnit carries `source_id + locator`. Every factual claim in a generated page carries `^[source_id:locator]`. Code that drops provenance is a bug even if tests pass.
5. **State mutations only through StateStore.** No direct file writes to `.klustra/` or the vault from feature code.
6. **`validate` ≠ `lint`.** Conformance (OKF §9) never fails on broken links or missing optional fields. Quality gates live in lint config. Don't mix them.
7. **No bloat.** No speculative abstractions, no "manager" classes wrapping one function, no comments narrating obvious code. If a docstring restates the signature, delete it. Straight to the point — this is a project value, not a style preference.
8. **Token accounting is not optional.** Any new LLM call site must report {role, tokens_in, tokens_out} through `llm/accounting`. A call that doesn't show up in `klustra stats` is a leak.
9. **Input size is checked pre-call with a real token count** (`llm/tokens.py`) and chunked when over `extraction.max_input_tokens` (SPEC §5.2). Never blind-retry `LLMInputTooLargeError` — it is not an `LLMCallError` for exactly that reason.
10. **Compile must checkpoint per-file completion via `StateStore` and resume from the last incomplete file by default** (SPEC §5.3); a full rebuild requires explicit `--fresh`/`--no-resume`. Checkpoints key on `source_id` (not `entity_id` — that's a Phase 1 output), clear only on a fully successful run, and gate Phase 2 so the Librarian never merges a partial contribution set.
11. **No operation may run silently.** Every step >1-2s or involving an LLM call wraps in `log_op(phase, action, ...)` (`logging_setup.py`) — start/end with `status` and `elapsed_ms`, `heartbeat=True` for blocking calls. All LLM/embedding clients take an explicit client-side timeout and `max_retries=0` (tenacity is the one visible retry layer). See SPEC §13.1.
12. **OpenRouter third-party models treat `strict: true` as best-effort — always enforce bounds both in JSON schema AND in the system prompt; pydantic is the final gate, not the schema.**

## Conventions

- pydantic v2 everywhere; `model_config = ConfigDict(frozen=True)` for value objects
- Type hints mandatory; `mypy --strict` on core/, engine/, hierarchy/
- Errors: raise domain exceptions from `core/errors.py`; never bare `except:`
- Tests mirror source layout: `klustra/translators/excel.py` → `tests/test_translators/test_excel.py`
- New translator = subclass `Translator` + register + fixture file + golden expected units. Nothing else should change — if adding a format forces edits outside `translators/` and its tests, the design broke; stop and discuss.
- Same rule for sources: new `SourceConnector` (e.g. SharePoint, blob) = one class + a new `type` value in domain TOML. Never touch `DomainRegistry`, `engine/`, or `hierarchy/` to add a connector — v0.1 ships only `LocalFolderConnector`, but the seam must already be clean (SPEC §4.4).
- Prompts are Jinja2 `.md` files in `klustra/llm/prompts/`, never f-strings in code — `PromptRegistry.render(role, kind=...)` is the only source of prompt text. Naming: `<role>[.<kind>][.<version>].md` with fallback (SPEC §10). Templates use `StrictUndefined`, so a missing variable raises. Changing a prompt = changing behavior = update golden tests (`tests/fixtures/prompts/`).
- Provider routing (chat AND embeddings) resolves `base_url` through the single `OPENAI_COMPATIBLE_PROVIDERS` table in `llm/provider.py`. Adding a provider = one dict entry, never a new `elif` in a role-specific resolver (SPEC §8).
- Commits: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`). One logical change per commit.

## Working style (Karpathy mode)

- **Plan before code on anything non-trivial.** State the plan in 3-6 bullets, get the shape right, then implement. For multi-file changes, list the files you'll touch first.
- **Small diffs.** Prefer three reviewable commits over one heroic one. If a refactor and a feature are entangled, split them.
- **The wiki is the memory.** After completing a significant change, append what you learned (gotchas, decisions, dead ends) to the matching `docs/wiki/` page. Future agents read the wiki instead of re-deriving context — that's the whole point of this project; practice it on itself.
- **When stuck, reproduce first.** Write the failing test before the fix. A bug without a regression test isn't fixed.
- **Don't guess library APIs.** For hdbscan/umap/openai SDK specifics, check the installed version (`uv run python -c "import x; print(x.__version__)"`) and read the actual signature. Training-data memories of APIs are stale.

## What NOT to do

- Don't add dependencies without asking (each one is a supply-chain and lock-file decision)
- Don't touch `uv.lock`, `.klustra/` fixtures, or golden bundles to "make tests pass" — fix the code or explicitly regenerate goldens with `uv run pytest --update-goldens` and say so
- Don't write to `docs/wiki/` by hand-editing frontmatter — use the repo's own tooling where it exists
- Don't create README-style prose in code comments; link the SPEC section instead
- Don't run the real-LLM smoke tests (`KLUSTRA_SMOKE=1`) unless explicitly asked — they cost money

## Repo self-maintenance

This file is a living document. If an instruction here proved wrong or incomplete during your session, propose the edit to CLAUDE.md in the same PR — one-line diff, no rewrites. Keep it under 150 lines forever.
