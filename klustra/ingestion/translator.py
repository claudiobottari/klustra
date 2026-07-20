from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.source_ref import SourceRef


class TranslateContext(BaseModel):
    """Execution context passed to every Translator.translate() call (SPEC §4.1)."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    extra: dict[str, Any] = {}


class TranslationResult(BaseModel):
    """Output of a single Translator.translate() call: N KnowledgeUnits (SPEC §4.1)."""

    model_config = ConfigDict(frozen=True)

    units: list[KnowledgeUnit]
    source_metadata: dict[str, Any] = {}
    warnings: list[str] = []


class Translator(ABC):
    """Strategy contract for format-specific translators (SPEC §4.1).

    Subclasses must set class-level ``name``, ``version``, ``extensions``.
    Translators are deterministic and ZERO-LLM — no model calls here.
    """

    name: str
    version: str
    extensions: set[str]
    schemes: set[str] = set()
    deterministic: bool = True

    @abstractmethod
    def translate(self, source: SourceRef, ctx: TranslateContext) -> TranslationResult: ...
