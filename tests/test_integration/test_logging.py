"""Integration test: CLI/logging-layer progress + retry visibility (no api.py
return-value changes — see CLAUDE.md and klustra/logging_setup.py)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from klustra.api import Klustra
from klustra.llm.openai_provider import OpenAICompatibleProvider

EXTRACTION_JSON = json.dumps(
    {
        "candidates": [
            {
                "name": "Test Material",
                "entity_id_proposal": "mat.test-material",
                "summary": "A test material used in cables.",
                "is_new": True,
                "related_existing": [],
            }
        ]
    }
)

LIBRARIAN_JSON = json.dumps(
    {
        "title": "Test Material",
        "description": "A test material used in cables.",
        "body_md": "Test material is widely used. ^[src:doc:1]",
        "tags": ["material"],
        "aliases": ["TM"],
        "confidence": 0.85,
    }
)


def _mock_completion(content: str, prompt_tokens: int = 50, completion_tokens: int = 25):
    usage = MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    message = MagicMock(content=content)
    choice = MagicMock(message=message, finish_reason="stop")
    return MagicMock(choices=[choice], usage=usage)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "klustra.toml").write_text(
        '[llm.extraction]\nprovider = "openrouter"\nmodel = "test-model"\n\n'
        '[llm.librarian]\nprovider = "openrouter"\nmodel = "test-model"\n',
        encoding="utf-8",
    )
    data_dir = root / "data"
    data_dir.mkdir()
    (data_dir / "intro.md").write_text(
        "# Test Material\n\nTest material is widely used in cable insulation.\n",
        encoding="utf-8",
    )
    return root


def test_compile_emits_info_progress_and_warning_on_retry(
    project_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A mock compile run: INFO progress lines for source/entity position, and a
    WARNING line naming the retry when the librarian call returns bad JSON once."""
    provider = OpenAICompatibleProvider(api_key="test-key", base_url="http://fake")
    nx = Klustra(root=project_dir, provider=provider)
    nx.ingest_folder(project_dir / "data")

    good_extraction = _mock_completion(EXTRACTION_JSON)
    bad_librarian = _mock_completion("not valid json")
    good_librarian = _mock_completion(LIBRARIAN_JSON)

    with (
        patch.object(
            provider._client.chat.completions,
            "create",
            side_effect=[good_extraction, bad_librarian, good_librarian],
        ),
        caplog.at_level(logging.INFO, logger="klustra"),
    ):
        results = nx.compile()

    assert len(results) == 1

    info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("[compile] starting: 1 source" in m for m in info_messages)
    assert any("[compile] extracting concepts from source 1/1" in m for m in info_messages)
    assert any(
        "[compile] librarian synthesizing entity 'mat.test-material' (1/1)" in m
        for m in info_messages
    )
    assert any("[compile] done: 1 page" in m for m in info_messages)

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "retrying" in m and "invalid response" in m and "mat.test-material" in m
        for m in warning_messages
    )


class TestCliVerbosity:
    def test_quiet_suppresses_progress_output(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from klustra.cli import app

        monkeypatch.chdir(project_dir)
        runner = CliRunner()
        result = runner.invoke(app, ["-q", "ingest", str(project_dir / "data")])
        assert result.exit_code == 0
        assert "[ingest]" not in result.output

    def test_default_shows_progress_output(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from klustra.cli import app

        monkeypatch.chdir(project_dir)
        runner = CliRunner()
        result = runner.invoke(app, ["ingest", str(project_dir / "data")])
        assert result.exit_code == 0
        assert "[ingest]" in result.output

    def test_verbose_and_quiet_are_mutually_exclusive(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from klustra.cli import app

        monkeypatch.chdir(project_dir)
        runner = CliRunner()
        result = runner.invoke(app, ["-v", "-q", "ingest", str(project_dir / "data")])
        assert result.exit_code == 1


# --- progress contract end-to-end (SPEC §13.1) ---

_BIG_EXTRACTION_JSON = json.dumps(
    {
        "candidates": [
            {
                "name": "Big",
                "entity_id_proposal": "doc.big",
                "summary": "s",
                "is_new": True,
                "related_existing": [],
            }
        ]
    }
)

_BIG_LIBRARIAN_JSON = json.dumps(
    {
        "title": "Big",
        "description": "d",
        "body_md": "Body. ^[src:doc:1]",
        "tags": [],
        "aliases": [],
        "confidence": 0.9,
    }
)

_CHUNK_LIMIT = 3000


def _big_project(tmp_path: Path, sections: int = 30) -> Path:
    root = tmp_path / "bigproject"
    root.mkdir()
    (root / "klustra.toml").write_text(
        '[llm.extraction]\nprovider = "openrouter"\nmodel = "test-model"\n\n'
        '[llm.librarian]\nprovider = "openrouter"\nmodel = "test-model"\n\n'
        f"[extraction]\nmax_input_tokens = {_CHUNK_LIMIT}\n",
        encoding="utf-8",
    )
    corpus = root / "data"
    corpus.mkdir()
    body = "\n\n".join(
        f"## Section {i}\n\n" + " ".join(f"t{i}w{j}" for j in range(300)) for i in range(sections)
    )
    (corpus / "big.md").write_text(f"# Big\n\n{body}\n", encoding="utf-8")
    return root


def test_chunked_compile_with_retry_emits_the_full_progress_sequence(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Large file + one malformed response: the log must show chunking, every
    chunk's call bracketed, the retry, and the Phase 1 → Phase 2 transition."""
    root = _big_project(tmp_path)
    provider = OpenAICompatibleProvider(api_key="test-key", base_url="http://fake")
    nx = Klustra(root=root, provider=provider)
    nx.ingest_folder(root / "data")

    # Route by role rather than by call index — the chunk count is derived from
    # the token budget, so a fixed response list would drift with it.
    calls = {"n": 0}

    def _respond(**kwargs: object):  # noqa: ANN202
        messages = kwargs["messages"]
        assert isinstance(messages, list)
        system = str(messages[0]["content"]).lower()
        if "extraction engine" in system:
            calls["n"] += 1
            if calls["n"] == 1:
                return _mock_completion("not valid json")  # forces a corrective retry
            return _mock_completion(_BIG_EXTRACTION_JSON)
        return _mock_completion(_BIG_LIBRARIAN_JSON)

    with (
        patch.object(provider._client.chat.completions, "create", side_effect=_respond),
        caplog.at_level(logging.INFO, logger="klustra"),
    ):
        nx.compile()

    msgs = [r.message for r in caplog.records]

    def first_index(needle: str, *extra: str) -> int:
        return next(i for i, m in enumerate(msgs) if needle in m and all(e in m for e in extra))

    # Chunking brackets itself, and its start precedes the decision line.
    i_chunk_start = first_index("action=chunking", "status=start")
    i_chunk_done = first_index("action=chunking", "status=done")
    i_triggered = first_index("chunking triggered")
    assert i_chunk_start < i_chunk_done < i_triggered

    # Every extraction call is bracketed and carries chunk N/M + input size.
    starts = [m for m in msgs if "phase=extraction action=llm_call" in m and "status=start" in m]
    assert len(starts) > 1, "oversized input must fan out over several calls"
    assert all("chunk=" in m and "input_tokens=" in m and "model=" in m for m in starts)
    assert any(
        "phase=extraction action=llm_call" in m and "status=done" in m and "elapsed_ms=" in m
        for m in msgs
    )

    # The corrective retry is visible at WARNING.
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("retrying" in m and "invalid response" in m for m in warnings)

    # Phase 1 → Phase 2 transition, with Phase 2 bracketed too.
    i_merge_start = first_index("phase=librarian_merge action=llm_call", "status=start")
    assert i_merge_start > first_index("phase=extraction action=llm_call")
    assert any("phase=librarian_merge action=llm_call" in m and "status=done" in m for m in msgs)


def test_progress_lines_carry_no_prompt_or_response_content(
    project_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """CLAUDE.md rule 8: progress fields are ids, counts and timings — never the
    source text or the model's output, at any verbosity."""
    secret = "SUPERSECRETSOURCETEXT"
    (project_dir / "data" / "intro.md").write_text(
        f"# Test Material\n\n{secret} is used in cable insulation.\n", encoding="utf-8"
    )

    provider = OpenAICompatibleProvider(api_key="test-key", base_url="http://fake")
    nx = Klustra(root=project_dir, provider=provider)
    nx.ingest_folder(project_dir / "data")

    with (
        patch.object(
            provider._client.chat.completions,
            "create",
            side_effect=[_mock_completion(EXTRACTION_JSON), _mock_completion(LIBRARIAN_JSON)],
        ),
        caplog.at_level(logging.DEBUG, logger="klustra"),
    ):
        nx.compile()

    progress = [r.message for r in caplog.records if "phase=" in r.message]
    assert progress
    assert not any(secret in m for m in progress)
