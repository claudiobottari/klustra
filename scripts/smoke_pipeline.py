"""Real-LLM smoke test: mini_corpus end-to-end through OpenRouter.

Gated by KLUSTRA_SMOKE=1 (per CLAUDE.md). Costs money. Do not run in CI.

    KLUSTRA_SMOKE=1 uv run python scripts/smoke_pipeline.py

Reports failures verbatim + total token cost.

Design notes:
- LLM: real OpenAICompatibleProvider against OpenRouter, model set below.
- Embeddings: repo has no concrete EmbeddingProvider (only ABC at
  klustra/hierarchy/embeddings.py:8). OpenRouter doesn't proxy embeddings.
  So we inline a deterministic hash-based embedder purely to unblock the
  pipeline. This isolates LLM-shape failures from embedding-quality issues.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import traceback
from pathlib import Path

# Load .env if present (repo convention; python-dotenv not a dep, do it manually).
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from klustra.api import Klustra  # noqa: E402
from klustra.hierarchy.embeddings import EmbeddingProvider  # noqa: E402
from klustra.llm import OpenAICompatibleProvider  # noqa: E402

MODEL = "deepseek/deepseek-v4-flash"
BASE_URL = "https://openrouter.ai/api/v1"


class _HashEmbedder(EmbeddingProvider):
    """Deterministic hash-based embedder — pipeline-unblocking only, NOT semantic.

    Uses sliding character n-grams hashed into fixed-dim vectors. Enough for
    HDBSCAN to run without crashing; clustering quality is not evaluated here.
    """

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def _vec(self, text: str) -> list[float]:
        buckets = [0.0] * self.dim
        norm = text.lower()
        for i in range(len(norm) - 3):
            ngram = norm[i : i + 4]
            h = int.from_bytes(hashlib.sha256(ngram.encode()).digest()[:4], "big")
            buckets[h % self.dim] += 1.0
        total = sum(x * x for x in buckets) ** 0.5 or 1.0
        return [x / total for x in buckets]


def _setup_project(root: Path, corpus_src: Path) -> Path:
    """Fresh temp project rooted at `root`, with mini_corpus copied in and klustra.toml."""
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    (root / "klustra.toml").write_text(
        "[llm.extraction]\n"
        f'provider = "openrouter"\nmodel = "{MODEL}"\n\n'
        "[llm.librarian]\n"
        f'provider = "openrouter"\nmodel = "{MODEL}"\n\n'
        "[llm.hierarchy]\n"
        f'provider = "openrouter"\nmodel = "{MODEL}"\n\n'
        "[llm.judge]\n"
        f'provider = "openrouter"\nmodel = "{MODEL}"\n\n'
        "[hierarchy]\n"
        "min_cluster_size = 2\n"
        "home_threshold = 2\n",
        encoding="utf-8",
    )
    corpus_dst = root / "corpus"
    shutil.copytree(corpus_src, corpus_dst)
    return corpus_dst


def _report_sink(nx: Klustra) -> tuple[int, int, dict[str, tuple[int, int, int]]]:
    """Return (total_in, total_out, per_role) from the accounting sink."""
    per_role: dict[str, tuple[int, int, int]] = {}  # role -> (calls, in, out)
    total_in = total_out = 0
    for e in nx._sink.entries:
        calls, ti, to_ = per_role.get(e.role, (0, 0, 0))
        per_role[e.role] = (calls + 1, ti + e.tokens_in, to_ + e.tokens_out)
        total_in += e.tokens_in
        total_out += e.tokens_out
    return total_in, total_out, per_role


def _step(label: str, fn):
    print(f"\n=== {label} ===", flush=True)
    try:
        result = fn()
        print(f"[OK] {label}", flush=True)
        return result, None
    except Exception as exc:
        print(f"[FAIL] {label}: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        return None, exc


def main() -> int:
    if os.environ.get("KLUSTRA_SMOKE") != "1":
        print("KLUSTRA_SMOKE!=1 — refusing to run (real API costs money).", file=sys.stderr)
        return 2

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY not set.", file=sys.stderr)
        return 2

    repo_root = Path(__file__).parent.parent
    corpus_src = repo_root / "tests" / "fixtures" / "mini_corpus"
    project_root = repo_root / ".smoke_project"
    corpus_dst = _setup_project(project_root, corpus_src)

    provider = OpenAICompatibleProvider(api_key=api_key, base_url=BASE_URL)
    nx = Klustra(root=project_root, provider=provider, embedding_provider=_HashEmbedder())

    print(f"model={MODEL}  base_url={BASE_URL}  corpus={corpus_dst}", flush=True)

    _, err_ingest = _step("ingest", lambda: nx.ingest_folder(corpus_dst))
    if err_ingest:
        return _finalize(nx, 1)

    _, err_compile = _step("compile", lambda: nx.compile())
    if err_compile:
        return _finalize(nx, 1)

    _, err_hier = _step("build_hierarchy(full=True)", lambda: nx.build_hierarchy(full=True))
    if err_hier:
        return _finalize(nx, 1)

    _, err_export = _step(
        "export(obsidian)",
        lambda: nx.export("obsidian", project_root / "vault_out"),
    )
    if err_export:
        return _finalize(nx, 1)

    return _finalize(nx, 0)


def _finalize(nx: Klustra, code: int) -> int:
    total_in, total_out, per_role = _report_sink(nx)
    print("\n=== token accounting ===", flush=True)
    print(f"total_in={total_in}  total_out={total_out}  calls={len(nx._sink.entries)}")
    for role, (calls, ti, to_) in sorted(per_role.items()):
        print(f"  {role:12s} calls={calls:3d}  in={ti:7d}  out={to_:7d}")
    print(f"\nexit={code}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
