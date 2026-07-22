# klustra

> ⚠️ **Work in progress.** Not production-ready. APIs and formats will change without notice. See [STATUS.md](STATUS.md) for current state.

Recursive knowledge abstraction engine: heterogeneous files → an [OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog)-style wiki of atomic concept pages → hierarchical cluster/home pages built by recursively clustering and summarizing those pages (RAPTOR pattern, applied to wiki pages instead of chunks). Point it at a folder of Excel sheets, Markdown, and text files; it ingests them deterministically, has an LLM extract and merge concepts with provenance, then recursively abstracts the result into a navigable domain wiki.

Status: **v0.2.0** — core pipeline + hierarchy engine built and tested; see [STATUS.md](STATUS.md) for exactly what's implemented vs. still open.

## Quickstart

```bash
uv sync --extra hierarchy        # install deps, incl. UMAP/HDBSCAN for the hierarchy engine
uv run klustra init               # scaffold klustra.toml + .klustra/{domains,instructions,vault}
```

Configure a domain in `.klustra/domains/<label>.toml` (source folders, glob patterns) and, optionally, `.klustra/instructions/<label>.md` (domain-specific guidance injected into every prompt). Then:

```bash
uv run klustra sync --domain <label>   # or: klustra ingest <path> -d <label>
uv run klustra compile                 # two-phase extraction + librarian merge -> concept pages
uv run klustra hierarchy                # recursive clustering -> cluster/home pages
uv run klustra export obsidian -o OUT   # or: okf_bundle
```

`klustra.toml` at the repo/project root configures the LLM roles (`extraction`, `librarian`, `hierarchy`, `judge`, `embeddings`) and hierarchy thresholds. API keys are read only from environment variables (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`), never from config files.

## Docs

- [SPEC.md](SPEC.md) — the authoritative design spec (architecture, data model, algorithms, roadmap)
- [CLAUDE.md](CLAUDE.md) — contributor/agent instructions (commands, verification loop, hard rules)
- [STATUS.md](STATUS.md) — real implementation state as of the last audit
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — condensed, code-grounded architecture walkthrough
