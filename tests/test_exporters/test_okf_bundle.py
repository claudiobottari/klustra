from __future__ import annotations

from pathlib import Path

import yaml

from klustra.engine.validate import validate_all
from klustra.exporters.exporter import ExportContext, ExportPage
from klustra.exporters.okf_bundle import OkfBundleExporter


class TestOkfBundleExporter:
    def test_creates_files_from_entity_id(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        assert (tmp_path / "mat" / "xlpe.md").exists()
        assert (tmp_path / "prod" / "cable" / "p-laser-320kv.md").exists()
        assert (tmp_path / "proc" / "extrusion.md").exists()

    def test_creates_index_and_log(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        assert (tmp_path / "index.md").exists()
        assert (tmp_path / "log.md").exists()

    def test_index_has_okf_version(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "index.md").read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_end = content.index("---\n", 4) + 4
        fm_raw = content[4 : fm_end - 4]
        fm = yaml.safe_load(fm_raw)
        assert fm["okf_version"] == "0.1"

    def test_index_has_no_page_frontmatter(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "index.md").read_text(encoding="utf-8")
        fm_end = content.index("---\n", 4) + 4
        fm_raw = content[4 : fm_end - 4]
        fm = yaml.safe_load(fm_raw)
        assert "entity_id" not in fm
        assert "type" not in fm

    def test_log_is_empty(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "log.md").read_text(encoding="utf-8")
        assert content == ""

    def test_wikilinks_replaced_with_relative_links(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "prod" / "cable" / "p-laser-320kv.md").read_text(encoding="utf-8")
        assert "[[" not in content
        assert "[XLPE Insulation](../../mat/xlpe.md)" in content
        assert "[Extrusion Process](../../proc/extrusion.md)" in content

    def test_no_wikilinks_in_output(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        for md_file in tmp_path.rglob("*.md"):
            if md_file.name in ("index.md", "log.md"):
                continue
            content = md_file.read_text(encoding="utf-8")
            assert "[[" not in content, f"Wikilink found in {md_file}"

    def test_relative_links_differ_by_depth(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        # mat/xlpe.md links to prod/cable/p-laser-320kv.md (peer dir)
        content = (tmp_path / "mat" / "xlpe.md").read_text(encoding="utf-8")
        assert "[P-Laser 320kV](../prod/cable/p-laser-320kv.md)" in content

    def test_pages_pass_validate(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        """OKF bundle pages must pass klustra validate."""
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        pages = [ep.page for ep in sample_pages]
        findings = validate_all(pages)
        assert findings == []

    def test_index_lists_all_pages(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        exporter = OkfBundleExporter()
        exporter.export(sample_pages, tmp_path, export_ctx)

        content = (tmp_path / "index.md").read_text(encoding="utf-8")
        assert "XLPE Insulation" in content
        assert "P-Laser 320kV" in content
        assert "Extrusion Process" in content

    def test_name_attribute(self) -> None:
        exporter = OkfBundleExporter()
        assert exporter.name == "okf_bundle"


class TestExporterLinkFormatDifference:
    """Verify the two exporters produce different link formats for the same input."""

    def test_obsidian_vs_okf_link_format(
        self, sample_pages: list[ExportPage], export_ctx: ExportContext, tmp_path: Path
    ) -> None:
        from klustra.exporters.obsidian import ObsidianExporter

        obsidian_dir = tmp_path / "obsidian"
        okf_dir = tmp_path / "okf"

        ObsidianExporter().export(sample_pages, obsidian_dir, export_ctx)
        OkfBundleExporter().export(sample_pages, okf_dir, export_ctx)

        # Same page, different link format
        obsidian_content = (obsidian_dir / "prod" / "cable" / "p-laser-320kv.md").read_text(
            encoding="utf-8"
        )
        okf_content = (okf_dir / "prod" / "cable" / "p-laser-320kv.md").read_text(encoding="utf-8")

        # Obsidian keeps wikilinks
        assert "[[mat.xlpe]]" in obsidian_content
        assert "[[proc.extrusion]]" in obsidian_content

        # OKF uses relative markdown links
        assert "[[" not in okf_content
        assert "[XLPE Insulation](" in okf_content
        assert "[Extrusion Process](" in okf_content
