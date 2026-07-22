"""Resumable compile (SPEC §5.3): interruption mid-Phase-1 must not restart from
the first file. Interruption is simulated by a provider that raises, so the
`in_progress` checkpoint is written by the real code path rather than seeded.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from klustra.api import Klustra
from klustra.core.errors import CompileIncompleteError
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse

_N_SOURCES = 4


class _CountingProvider(LLMProvider):
    """Records every extraction call by source, and can be told to fail on one.

    `fail_on_extraction_call` is 1-based: 3 means "the third extraction call of
    this run raises", i.e. two sources completed before the crash.
    """

    name = "counting_mock"

    def __init__(self, fail_on_extraction_call: int | None = None) -> None:
        self.fail_on_extraction_call = fail_on_extraction_call
        self.extraction_labels: list[str] = []
        self.librarian_calls = 0

    @property
    def extracted_source_ids(self) -> list[str]:
        return [label.split(":")[1] for label in self.extraction_labels]

    def call(self, request: LLMRequest) -> LLMResponse:
        system_content = request.messages[0].content if request.messages else ""

        if "extraction" in system_content.lower():
            self.extraction_labels.append(request.label or "")
            if len(self.extraction_labels) == self.fail_on_extraction_call:
                raise RuntimeError("simulated interruption mid-Phase-1")
            data: dict = {
                "candidates": [
                    {
                        "name": "Shared Concept",
                        "entity_id_proposal": "concept.shared",
                        "summary": "proposed by every source",
                        "is_new": True,
                        "related_existing": [],
                    }
                ]
            }
        else:
            self.librarian_calls += 1
            data = {
                "title": "Shared Concept",
                "description": "Merged from every source.",
                "body_md": "Body with a citation. ^[src:doc:1]",
                "tags": [],
                "aliases": [],
                "confidence": 0.9,
            }

        content = json.dumps(data)
        return LLMResponse(
            content=content,
            parsed=data,
            tokens_in=1,
            tokens_out=1,
            model=request.model,
        )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "klustra.toml").write_text(
        '[llm.extraction]\nprovider = "mock"\nmodel = "m"\n\n'
        '[llm.librarian]\nprovider = "mock"\nmodel = "m"\n',
        encoding="utf-8",
    )
    (root / ".klustra").mkdir()
    corpus = root / "corpus"
    corpus.mkdir()
    for i in range(_N_SOURCES):
        (corpus / f"doc{i}.md").write_text(f"# Doc {i}\n\nContent of document {i}.\n", "utf-8")
    return root


def _ingest(project: Path, provider: LLMProvider) -> Klustra:
    nx = Klustra(root=project, provider=provider)
    nx.ingest_folder(project / "corpus")
    return nx


def test_interrupted_compile_resumes_from_last_unprocessed_source(
    project: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    crashing = _CountingProvider(fail_on_extraction_call=3)
    nx = _ingest(project, crashing)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        nx.compile()

    # Two sources finished, the third died mid-call.
    done_before = crashing.extracted_source_ids[:2]
    assert len(done_before) == 2
    assert crashing.librarian_calls == 0, "Phase 2 must not have run"

    checkpoints = nx.state.get_checkpoints()
    assert {c.status for c in checkpoints.values() if c.source_id in done_before} == {"done"}

    # Resume with a fresh client and a fresh provider.
    resumed = _CountingProvider()
    nx2 = Klustra(root=project, provider=resumed)
    with caplog.at_level(logging.INFO, logger="klustra"):
        results = nx2.compile()

    # The crux: already-done sources are NOT re-sent to the LLM.
    for source_id in done_before:
        assert source_id not in resumed.extracted_source_ids
    assert len(resumed.extracted_source_ids) == _N_SOURCES - len(done_before)

    assert any("resuming" in r.message for r in caplog.records)

    # Phase 2 ran once over the complete contribution set.
    assert resumed.librarian_calls == 1
    assert len(results) == 1
    page = results[0].page
    assert page.entity_id == "concept.shared"

    # Provenance is identical to an uninterrupted run: every source contributed.
    assert len(page.sources) == _N_SOURCES
    tracked = {s.source_id for s in nx2.state.list_sources()}
    assert {s.source_id for s in page.sources} == tracked


def test_resumed_page_matches_uninterrupted_run(project: Path, tmp_path: Path) -> None:
    """A resumed compile produces the same page and provenance as a clean run."""
    clean = _CountingProvider()
    nx_clean = _ingest(project, clean)
    expected = nx_clean.compile()[0]

    # Second project, same corpus, interrupted then resumed.
    other = tmp_path / "project2"
    other.mkdir()
    (other / "klustra.toml").write_text(
        (project / "klustra.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (other / ".klustra").mkdir()
    corpus2 = other / "corpus"
    corpus2.mkdir()
    for f in (project / "corpus").iterdir():
        (corpus2 / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

    crashing = _CountingProvider(fail_on_extraction_call=2)
    nx_a = _ingest(other, crashing)
    with pytest.raises(RuntimeError):
        nx_a.compile()
    resumed = Klustra(root=other, provider=_CountingProvider()).compile()[0]

    assert resumed.page.entity_id == expected.page.entity_id
    assert resumed.body_md == expected.body_md
    assert len(resumed.page.sources) == len(expected.page.sources)


def test_successful_compile_clears_checkpoints(project: Path) -> None:
    """Checkpoints are a crash artifact, not permanent state: a clean run retires
    them, so the next compile behaves exactly as before this feature."""
    nx = _ingest(project, _CountingProvider())
    nx.compile()
    assert nx.state.get_checkpoints() == {}

    second = _CountingProvider()
    Klustra(root=project, provider=second).compile()
    assert len(second.extracted_source_ids) == _N_SOURCES, "no silent skipping on a clean rerun"


def test_fresh_flag_bypasses_checkpoints(project: Path) -> None:
    crashing = _CountingProvider(fail_on_extraction_call=3)
    nx = _ingest(project, crashing)
    with pytest.raises(RuntimeError):
        nx.compile()
    assert nx.state.get_checkpoints(), "checkpoints must survive the crash"

    rebuilt = _CountingProvider()
    Klustra(root=project, provider=rebuilt).compile(fresh=True)

    assert len(rebuilt.extracted_source_ids) == _N_SOURCES
    assert sorted(rebuilt.extracted_source_ids) == sorted(set(rebuilt.extracted_source_ids))


def test_in_progress_checkpoint_is_treated_as_pending(project: Path) -> None:
    """The source that was mid-extraction when the crash hit is reprocessed in
    full — a partial extraction is never trusted."""
    crashing = _CountingProvider(fail_on_extraction_call=2)
    nx = _ingest(project, crashing)
    with pytest.raises(RuntimeError):
        nx.compile()

    interrupted = crashing.extracted_source_ids[1]
    statuses = {c.source_id: c.status for c in nx.state.get_checkpoints().values()}
    assert statuses[interrupted] == "failed"

    resumed = _CountingProvider()
    Klustra(root=project, provider=resumed).compile()
    assert interrupted in resumed.extracted_source_ids


def test_stale_checkpoint_invalidated_when_source_removed(
    project: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    crashing = _CountingProvider(fail_on_extraction_call=4)
    nx = _ingest(project, crashing)
    with pytest.raises(RuntimeError):
        nx.compile()
    assert len(nx.state.get_checkpoints()) >= 3

    # Delete a source that had already completed, then re-sync.
    completed = crashing.extracted_source_ids[0]
    path = next(s.source_path for s in nx.state.list_sources() if s.source_id == completed)
    Path(path).unlink()

    resumed = _CountingProvider()
    nx2 = Klustra(root=project, provider=resumed)
    nx2.sync_folder(project / "corpus")
    with caplog.at_level(logging.INFO, logger="klustra"):
        nx2.compile()

    assert completed not in resumed.extracted_source_ids
    assert any("no longer tracked" in r.message for r in caplog.records)
    assert nx2.state.get_checkpoints() == {}


def test_edited_source_invalidates_its_own_checkpoint(project: Path) -> None:
    crashing = _CountingProvider(fail_on_extraction_call=4)
    nx = _ingest(project, crashing)
    with pytest.raises(RuntimeError):
        nx.compile()

    edited = crashing.extracted_source_ids[0]
    path = next(s.source_path for s in nx.state.list_sources() if s.source_id == edited)
    Path(path).write_text("# Doc 0\n\nCompletely rewritten content.\n", encoding="utf-8")

    resumed = _CountingProvider()
    nx2 = Klustra(root=project, provider=resumed)
    nx2.sync_folder(project / "corpus")
    nx2.compile()

    assert edited in resumed.extracted_source_ids, "changed content must be re-extracted"


def test_phase2_refused_on_incomplete_phase1(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard against a partial Librarian merge, which would drop provenance for
    sources whose extraction never ran."""
    nx = _ingest(project, _CountingProvider())

    real_get = nx.state.get_checkpoints

    def _drop_one() -> dict:
        found = real_get()
        if found:
            found.pop(next(iter(found)))
        return found

    monkeypatch.setattr(nx.state, "get_checkpoints", _drop_one)

    with pytest.raises(CompileIncompleteError, match="Phase 1 incomplete"):
        nx.compile()


def test_cli_exposes_fresh_and_no_resume_flags() -> None:
    """--fresh / --no-resume must be reachable from the CLI, not just the API."""
    import typer.main

    from klustra.cli import app

    command = typer.main.get_command(app).commands["compile"]  # type: ignore[attr-defined]
    opts = {opt for param in command.params for opt in param.opts}
    assert {"--fresh", "--no-resume"} <= opts


def test_cli_fresh_flag_reaches_the_api(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from klustra import cli

    _ingest(project, _CountingProvider())
    seen: list[bool] = []

    class _Spy(Klustra):
        def compile(self, *, fresh: bool = False) -> list:  # type: ignore[override]
            seen.append(fresh)
            return []

    monkeypatch.setattr(cli, "_get_klustra", lambda: _Spy(root=project))

    runner = CliRunner()
    assert runner.invoke(cli.app, ["compile"]).exit_code == 0
    assert runner.invoke(cli.app, ["compile", "--fresh"]).exit_code == 0
    assert runner.invoke(cli.app, ["compile", "--no-resume"]).exit_code == 0
    assert seen == [False, True, True]
