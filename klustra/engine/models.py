from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.page import Page


class ConceptCandidate(BaseModel):
    """Structured output from Phase 1 extraction (SPEC §5)."""

    model_config = ConfigDict(frozen=True)

    name: str
    entity_id_proposal: str
    summary: str
    is_new: bool
    related_existing: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Extraction output for one KnowledgeUnit."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    unit_id: str
    candidates: list[ConceptCandidate]


class SourceContribution(BaseModel):
    """One source's contributions to a concept — input to Librarian (SPEC §5 Phase 2)."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    source_path: str
    units: list[KnowledgeUnit]


class LibrarianOutput(BaseModel):
    """Structured LLM output from Librarian merge."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    body_md: str
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class LibrarianResult(BaseModel):
    """Full result of Librarian merge for one concept."""

    model_config = ConfigDict(frozen=True)

    page: Page
    body_md: str
    link_targets: list[str] = Field(default_factory=list)


CONCEPT_CANDIDATES_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "entity_id_proposal": {"type": "string"},
                    "summary": {"type": "string"},
                    "is_new": {"type": "boolean"},
                    "related_existing": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "name",
                    "entity_id_proposal",
                    "summary",
                    "is_new",
                    "related_existing",
                ],
            },
        },
    },
    "required": ["candidates"],
}

LIBRARIAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "body_md": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "aliases": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["title", "description", "body_md", "tags", "aliases", "confidence"],
}
