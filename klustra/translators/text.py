"""TextTranslator — one KnowledgeUnit per plain-text file (SPEC §4.1)."""

from pathlib import Path

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.source_ref import SourceRef
from klustra.ingestion.translator import TranslateContext, TranslationResult, Translator


class TextTranslator(Translator):
    """Deterministic plain-text → KnowledgeUnit translator (SPEC §4.1).

    One unit per file, kind="narrative", locator="file".
    Empty files (whitespace only) produce no units.
    """

    name = "text"
    version = "1.0"
    extensions = {".txt"}

    def translate(self, source: SourceRef, ctx: TranslateContext) -> TranslationResult:
        content = Path(source.source_path).read_text(encoding="utf-8")

        if not content.strip():
            return TranslationResult(
                units=[],
                source_metadata={"file_path": source.source_path},
            )

        return TranslationResult(
            units=[
                KnowledgeUnit(
                    unit_id=f"{source.source_id}#0",
                    kind="narrative",
                    content_md=content,
                    locator="file",
                    inherited_context={"file_path": source.source_path},
                )
            ],
            source_metadata={"file_path": source.source_path},
        )
