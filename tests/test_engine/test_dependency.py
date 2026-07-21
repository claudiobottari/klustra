from __future__ import annotations

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.core.state_store import PageRecord
from klustra.engine.dependency import (
    build_reverse_index,
    filter_units_for_sources,
    resolve_dependencies,
)


def test_build_reverse_index(sample_page_records: list[PageRecord]) -> None:
    index = build_reverse_index(sample_page_records)
    assert index["prod.cable.p-laser-320kv"] == {"src001", "src002"}
    assert index["mat.xlpe"] == {"src002", "src003"}
    assert index["proc.extrusion"] == {"src003"}


def test_resolve_dependencies_finds_shared_sources(
    sample_page_records: list[PageRecord],
) -> None:
    index = build_reverse_index(sample_page_records)
    additional = resolve_dependencies({"src001"}, index)
    assert "src002" in additional
    assert "src001" not in additional


def test_resolve_dependencies_transitive(
    sample_page_records: list[PageRecord],
) -> None:
    index = build_reverse_index(sample_page_records)
    additional = resolve_dependencies({"src002"}, index)
    assert "src001" in additional
    assert "src003" in additional


def test_resolve_dependencies_no_shared(
    sample_page_records: list[PageRecord],
) -> None:
    _ = build_reverse_index(sample_page_records)
    index_isolated = {"isolated.entity": {"src099"}}
    additional = resolve_dependencies({"src099"}, index_isolated)
    assert additional == set()


def test_resolve_dependencies_empty_index() -> None:
    additional = resolve_dependencies({"src001"}, {})
    assert additional == set()


def test_filter_units_for_sources() -> None:
    units = [
        KnowledgeUnit(unit_id="src001#1", kind="narrative", content_md="A", locator="a"),
        KnowledgeUnit(unit_id="src001#2", kind="narrative", content_md="B", locator="b"),
        KnowledgeUnit(unit_id="src002#1", kind="narrative", content_md="C", locator="c"),
        KnowledgeUnit(unit_id="src003#1", kind="narrative", content_md="D", locator="d"),
    ]
    filtered = filter_units_for_sources(units, {"src001", "src003"})
    assert len(filtered) == 3
    assert all(u.unit_id.startswith(("src001", "src003")) for u in filtered)
