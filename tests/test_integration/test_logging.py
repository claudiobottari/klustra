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
