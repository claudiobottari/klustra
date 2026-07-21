"""Integration test: full pipeline ingest → compile → export using MockProvider."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from klustra.api import Klustra
from klustra.llm.provider import LLMProvider, LLMRequest, LLMResponse


class _PipelineMockProvider(LLMProvider):
    """Mock provider that returns sensible extraction + librarian responses."""

    name = "pipeline_mock"

    def __init__(self) -> None:
        self._call_count = 0

    def call(self, request: LLMRequest) -> LLMResponse:
        self._call_count += 1
        system_content = request.messages[0].content if request.messages else ""

        if "concept candidates" in system_content.lower() or "extraction" in system_content.lower():
            return self._extraction_response(request)
        return self._librarian_response(request)

    def _extraction_response(self, request: LLMRequest) -> LLMResponse:
        content = json.dumps(
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
        return LLMResponse(
            content=content,
            parsed=json.loads(content),
            tokens_in=100,
            tokens_out=50,
            model=request.model,
        )

    def _librarian_response(self, request: LLMRequest) -> LLMResponse:
        content = json.dumps(
            {
                "title": "Test Material",
                "description": "A test material used in cables.",
                "body_md": "Test material is widely used. ^[src:doc:1]\n\nSee related processes.",
                "tags": ["material", "test"],
                "aliases": ["TM"],
                "confidence": 0.85,
            }
        )
        return LLMResponse(
            content=content,
            parsed=json.loads(content),
            tokens_in=200,
            tokens_out=100,
            model=request.model,
        )


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Set up a minimal klustra project with fixture files."""
    root = tmp_path / "project"
    root.mkdir()

    (root / "klustra.toml").write_text(
        '[llm.extraction]\nprovider = "mock"\nmodel = "test-model"\n\n'
        '[llm.librarian]\nprovider = "mock"\nmodel = "test-model"\n',
        encoding="utf-8",
    )

    data_dir = root / "data"
    data_dir.mkdir()

    (data_dir / "intro.md").write_text(
        "# Test Material\n\nTest material is widely used in cable insulation.\n",
        encoding="utf-8",
    )
    (data_dir / "details.md").write_text(
        "# Properties\n\nTest material has excellent dielectric properties.\n",
        encoding="utf-8",
    )

    return root


class TestFacadePipeline:
    def test_ingest_folder(self, project_dir: Path) -> None:
        nx = Klustra(root=project_dir, provider=_PipelineMockProvider())
        cs = nx.ingest_folder(project_dir / "data")

        assert len(cs.sources.added) == 2
        assert cs.sources.modified == []

    def test_ingest_then_compile(self, project_dir: Path) -> None:
        provider = _PipelineMockProvider()
        nx = Klustra(root=project_dir, provider=provider)

        cs = nx.ingest_folder(project_dir / "data")
        assert len(cs.sources.added) == 2

        results = nx.compile()
        assert len(results) >= 1
        assert results[0].page.entity_id == "mat.test-material"
        assert results[0].page.title == "Test Material"
        assert "^[" in results[0].body_md

    def test_full_pipeline_ingest_compile_export(self, project_dir: Path) -> None:
        provider = _PipelineMockProvider()
        nx = Klustra(root=project_dir, provider=provider)

        nx.ingest_folder(project_dir / "data")
        results = nx.compile()
        assert len(results) >= 1

        obsidian_dir = project_dir / "export_obsidian"
        nx.export("obsidian", obsidian_dir)
        assert obsidian_dir.exists()
        md_files = list(obsidian_dir.rglob("*.md"))
        assert len(md_files) >= 1

        okf_dir = project_dir / "export_okf"
        nx.export("okf_bundle", okf_dir)
        assert (okf_dir / "index.md").exists()
        assert (okf_dir / "log.md").exists()
        okf_page_files = [f for f in okf_dir.rglob("*.md") if f.name not in ("index.md", "log.md")]
        assert len(okf_page_files) >= 1

    def test_validate_after_compile(self, project_dir: Path) -> None:
        provider = _PipelineMockProvider()
        nx = Klustra(root=project_dir, provider=provider)

        nx.ingest_folder(project_dir / "data")
        nx.compile()

        findings = nx.validate()
        assert findings == []

    def test_accounting_records_calls(self, project_dir: Path) -> None:
        provider = _PipelineMockProvider()
        nx = Klustra(root=project_dir, provider=provider)

        nx.ingest_folder(project_dir / "data")
        nx.compile()

        assert len(nx._sink.entries) >= 2


class TestCliInit:
    def test_init_scaffolds_project(self, tmp_path: Path) -> None:
        from klustra.cli import app

        runner = CliRunner()
        target = tmp_path / "new_project"
        result = runner.invoke(app, ["init", str(target)])

        assert result.exit_code == 0
        assert (target / "klustra.toml").exists()
        assert (target / ".klustra" / "domains").is_dir()
        assert (target / ".klustra" / "instructions").is_dir()
        assert (target / ".klustra" / "vault").is_dir()
        assert (target / ".klustra" / "instructions" / "_template.md").exists()

    def test_init_idempotent(self, tmp_path: Path) -> None:
        from klustra.cli import app

        runner = CliRunner()
        target = tmp_path / "existing"
        target.mkdir()
        (target / "klustra.toml").write_text("# existing", encoding="utf-8")

        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code == 0
        assert (target / "klustra.toml").read_text(encoding="utf-8") == "# existing"


class TestCliIngest:
    def test_ingest_file_via_cli(self, project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from klustra.cli import app

        monkeypatch.chdir(project_dir)
        runner = CliRunner()
        result = runner.invoke(app, ["ingest", str(project_dir / "data" / "intro.md")])
        assert result.exit_code == 0
        assert "+1 source(s)" in result.output

    def test_ingest_folder_via_cli(
        self, project_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from klustra.cli import app

        monkeypatch.chdir(project_dir)
        runner = CliRunner()
        result = runner.invoke(app, ["ingest", str(project_dir / "data")])
        assert result.exit_code == 0
        assert "+2 source(s)" in result.output
