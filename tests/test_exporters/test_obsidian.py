from __future__ import annotations

from pathlib import Path

import yaml

from klustra.exporters.exporter import ExportContext, ExportPage
from klustra.exporters.obsidian import ObsidianExporter


class TestObsidianExporter:
    def test_creates_files_from_entity_id(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = ObsidianExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        assert (tmp_path / "mat" / "xlpe.md").exists()
        assert (tmp_path / "prod" / "cable" / "p-laser-320kv.md").exists()
        assert (tmp_path / "proc" / "extrusion.md").exists()

    def test_preserves_wikilinks(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = ObsidianExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "prod" / "cable" / "p-laser-320kv.md").read_text(encoding="utf-8")
        assert "[[mat.xlpe]]" in content
        assert "[[proc.extrusion]]" in content

    def test_frontmatter_contains_metadata(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = ObsidianExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "mat" / "xlpe.md").read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_end = content.index("---\n", 4) + 4
        fm_raw = content[4 : fm_end - 4]
        fm = yaml.safe_load(fm_raw)

        assert fm["type"] == "concept"
        assert fm["entity_id"] == "mat.xlpe"
        assert fm["title"] == "XLPE Insulation"
        assert fm["domain"] == "materials"
        assert fm["confidence"] == 0.95
        assert fm["schema_version"] == "1.0"
        assert "insulation" in fm["tags"]

    def test_body_after_frontmatter(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = ObsidianExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "proc" / "extrusion.md").read_text(encoding="utf-8")
        fm_end = content.index("---\n", 4) + 4
        body = content[fm_end:].strip()
        assert "Extrusion applies heat and pressure" in body
        assert "^[src003:doc:1]" in body

    def test_sources_in_frontmatter(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = ObsidianExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "prod" / "cable" / "p-laser-320kv.md").read_text(encoding="utf-8")
        fm_end = content.index("---\n", 4) + 4
        fm_raw = content[4 : fm_end - 4]
        fm = yaml.safe_load(fm_raw)

        assert len(fm["sources"]) == 2
        assert fm["sources"][0]["source_id"] == "src001"

    def test_name_attribute(self) -> None:
        exporter = ObsidianExporter()
        assert exporter.name == "obsidian"
