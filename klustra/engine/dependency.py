from __future__ import annotations

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.state_store import PageRecord


def build_reverse_index(pages: list[PageRecord]) -> dict[str, set[str]]:
    """Build entity_id → set of source_ids mapping from page records."""
    index: dict[str, set[str]] = {}
    for page in pages:
        index[page.entity_id] = set(page.source_ids)
    return index


def resolve_dependencies(
    changed_source_ids: set[str],
    reverse_index: dict[str, set[str]],
) -> set[str]:
    """Find additional source_ids that share concepts with changed sources.

    Returns source_ids NOT in changed_source_ids that need re-extraction
    because they contribute to pages also contributed to by changed sources.
    """
    affected_entities: set[str] = set()
    for entity_id, source_ids in reverse_index.items():
        if source_ids & changed_source_ids:
            affected_entities.add(entity_id)

    additional_sources: set[str] = set()
    for entity_id in affected_entities:
        additional_sources.update(reverse_index[entity_id])

    return additional_sources - changed_source_ids


def filter_units_for_sources(
    units: list[KnowledgeUnit], source_ids: set[str]
) -> list[KnowledgeUnit]:
    """Filter units to only those belonging to the given source_ids."""
    return [u for u in units if _source_id_from_unit(u) in source_ids]


def _source_id_from_unit(unit: KnowledgeUnit) -> str:
    """Extract source_id from unit_id (format: {source_id}#{seq})."""
    return unit.unit_id.split("#")[0]
