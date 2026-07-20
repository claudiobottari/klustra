"""MarkdownTranslator — splits on top-level ATX headings (SPEC §4.1)."""

from pathlib import Path

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.source_ref import SourceRef
from klustra.ingestion.translator import TranslateContext, TranslationResult, Translator


def _split_md_sections(text: str) -> list[tuple[str, str]]:
    """Return (heading_text, content_md) pairs for each top-level section.

    Splitting rule: ATX ``# Heading`` lines (no indentation) are boundaries.
    Content before the first heading is the preamble with heading_text="".
    content_md includes the heading line so each unit is self-contained.
    No fenced-code-block awareness — good enough for real-world docs.
    """
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        if line.startswith("# ") or line.rstrip("\r\n") == "#":
            body = "".join(current_lines).strip()
            if body or current_heading:
                sections.append((current_heading, body))
            current_heading = line[2:].rstrip("\r\n") if line.startswith("# ") else ""
            current_lines = [line]
        else:
            current_lines.append(line)

    body = "".join(current_lines).strip()
    if body or current_heading:
        sections.append((current_heading, body))

    return sections


class MarkdownTranslator(Translator):
    """Deterministic markdown → KnowledgeUnit translator (SPEC §4.1).

    One unit per top-level section (``# Heading``).
    Preamble content (before first heading) → locator="preamble".
    Single-section or heading-free files → locator="file".
    """

    name = "markdown"
    version = "1.0"
    extensions = {".md", ".markdown"}

    def translate(self, source: SourceRef, ctx: TranslateContext) -> TranslationResult:
        text = Path(source.source_path).read_text(encoding="utf-8")
        sections = _split_md_sections(text)

        if not sections:
            return TranslationResult(
                units=[],
                source_metadata={"file_path": source.source_path, "sections": 0},
            )

        has_named_sections = any(h for h, _ in sections)
        units: list[KnowledgeUnit] = []

        for seq, (heading, content_md) in enumerate(sections):
            if not has_named_sections:
                locator = "file"
            elif heading:
                locator = f"section:{heading}"
            else:
                locator = "preamble"

            units.append(
                KnowledgeUnit(
                    unit_id=f"{source.source_id}#{seq}",
                    kind="narrative",
                    content_md=content_md,
                    locator=locator,
                    inherited_context={
                        "file_path": source.source_path,
                        "heading": heading if heading else None,
                    },
                )
            )

        return TranslationResult(
            units=units,
            source_metadata={"file_path": source.source_path, "sections": len(units)},
        )
