from __future__ import annotations

from pathlib import Path

import yaml

from klustra.exporters.exporter import ExportContext, Exporter, ExportPage


def _entity_id_to_path(entity_id: str) -> Path:
    """Convert dotted entity_id to a file path: 'a.b.c' → 'a/b/c.md'."""
    parts = entity_id.split(".")
    return Path(*parts[:-1], f"{parts[-1]}.md") if len(parts) > 1 else Path(f"{parts[0]}.md")


def _page_frontmatter(page: ExportPage) -> dict[str, object]:
    """Build frontmatter dict from page metadata."""
    fm: dict[str, object] = {
        "type": page.page.type,
        "level": page.page.level,
        "entity_id": page.page.entity_id,
        "title": page.page.title,
        "domain": page.page.domain,
        "confidence": page.page.confidence,
        "schema_version": page.page.schema_version,
    }
    if page.page.description:
        fm["description"] = page.page.description
    if page.page.aliases:
        fm["aliases"] = page.page.aliases
    if page.page.tags:
        fm["tags"] = page.page.tags
    if page.page.sources:
        fm["sources"] = [
            {"source_id": s.source_id, "source_path": s.source_path} for s in page.page.sources
        ]
    if page.page.children:
        fm["children"] = page.page.children
    if page.page.memberships:
        fm["memberships"] = page.page.memberships
    if page.page.cluster_meta is not None:
        fm["cluster_meta"] = page.page.cluster_meta.model_dump()
    if page.page.superseded_by is not None:
        fm["superseded_by"] = page.page.superseded_by
    fm["created_at"] = page.page.created_at.isoformat()
    fm["updated_at"] = page.page.updated_at.isoformat()
    return fm


def _render_page(page: ExportPage) -> str:
    """Render a page as YAML frontmatter + body markdown."""
    fm = _page_frontmatter(page)
    fm_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{fm_str}---\n\n{page.body_md}\n"


class ObsidianExporter(Exporter):
    """Exports pages as [[wikilinks]] markdown files into a vault directory (SPEC §11)."""

    name = "obsidian"

    def export(self, pages: list[ExportPage], output_dir: Path, ctx: ExportContext) -> None:
        for page in pages:
            rel_path = _entity_id_to_path(page.page.entity_id)
            file_path = output_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(_render_page(page), encoding="utf-8")
