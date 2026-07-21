from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from klustra.exporters.exporter import ExportContext, Exporter, ExportPage
from klustra.exporters.obsidian import _entity_id_to_path, _page_frontmatter

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _relative_link(source_path: PurePosixPath, target_path: PurePosixPath, title: str) -> str:
    """Compute a relative markdown link from source to target."""
    source_dir = source_path.parent
    rel = PurePosixPath(*_relpath_parts(target_path, source_dir))
    return f"[{title}]({rel})"


def _relpath_parts(target: PurePosixPath, source_dir: PurePosixPath) -> list[str]:
    """Compute relative path parts from source_dir to target using PurePosixPath."""
    target_parts = list(target.parts)
    source_parts = list(source_dir.parts)

    common = 0
    for a, b in zip(target_parts, source_parts, strict=False):
        if a == b:
            common += 1
        else:
            break

    ups = len(source_parts) - common
    remainder = target_parts[common:]
    parts: list[str] = [".."] * ups + remainder
    return parts if parts else [target_parts[-1]]


def _convert_wikilinks(
    body_md: str,
    source_entity_id: str,
    page_index: dict[str, tuple[str, PurePosixPath]],
) -> str:
    """Replace [[entity_id]] wikilinks with relative markdown links."""
    source_path = PurePosixPath(*_entity_id_to_path(source_entity_id).parts)

    def _replace(match: re.Match[str]) -> str:
        target_id = match.group(1)
        if target_id not in page_index:
            return target_id
        title, target_path = page_index[target_id]
        return _relative_link(source_path, target_path, title)

    return _WIKILINK_RE.sub(_replace, body_md)


def _render_okf_page(page: ExportPage, page_index: dict[str, tuple[str, PurePosixPath]]) -> str:
    """Render a page with relative markdown links instead of wikilinks."""
    fm = _page_frontmatter(page)
    fm_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    body = _convert_wikilinks(page.body_md, page.page.entity_id, page_index)
    return f"---\n{fm_str}---\n\n{body}\n"


def _render_index(pages: list[ExportPage]) -> str:
    """Render root index.md with okf_version and page listing."""
    fm: dict[str, Any] = {"okf_version": "0.1"}
    fm_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    lines = [f"---\n{fm_str}---\n"]
    lines.append("# Index\n")
    for page in sorted(pages, key=lambda p: p.page.entity_id):
        rel_path = PurePosixPath(*_entity_id_to_path(page.page.entity_id).parts)
        lines.append(f"- [{page.page.title}]({rel_path})")
    lines.append("")
    return "\n".join(lines)


class OkfBundleExporter(Exporter):
    """Exports OKF v0.1 conformant bundle with relative markdown links (SPEC §11)."""

    name = "okf_bundle"

    def export(self, pages: list[ExportPage], output_dir: Path, ctx: ExportContext) -> None:
        page_index: dict[str, tuple[str, PurePosixPath]] = {}
        for p in pages:
            rel = PurePosixPath(*_entity_id_to_path(p.page.entity_id).parts)
            page_index[p.page.entity_id] = (p.page.title, rel)

        for page in pages:
            rel_path = _entity_id_to_path(page.page.entity_id)
            file_path = output_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(_render_okf_page(page, page_index), encoding="utf-8")

        index_path = output_dir / "index.md"
        index_path.write_text(_render_index(pages), encoding="utf-8")

        log_path = output_dir / "log.md"
        log_path.write_text("", encoding="utf-8")
