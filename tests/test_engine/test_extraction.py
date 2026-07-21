from __future__ import annotations

import json

from klustra.core.knowledge_unit import KnowledgeUnit
from klustra.engine.extraction import extract_concepts
from klustra.llm import MockProvider
from klustra.llm.accounting import ListSink


def test_extract_concepts_returns_results(
    mock_provider: MockProvider, sample_units: list[KnowledgeUnit]
) -> None:
    sink = ListSink()
    results = extract_concepts(
        units=sample_units,
        source_id="src001",
        existing_index=["mat.xlpe"],
        provider=mock_provider,
        model="test-model",
        sink=sink,
    )
    assert len(results) == 2
    assert results[0].source_id == "src001"
    assert results[0].unit_id == "src001#1"
    assert results[1].unit_id == "src001#2"


def test_extract_concepts_records_tokens(
    mock_provider: MockProvider, sample_units: list[KnowledgeUnit]
) -> None:
    sink = ListSink()
    extract_concepts(
        units=sample_units,
        source_id="src001",
        existing_index=[],
        provider=mock_provider,
        model="test-model",
        sink=sink,
    )
    assert len(sink.entries) == 2
    assert all(e.role == "extraction" for e in sink.entries)
    assert all(e.model == "test-model" for e in sink.entries)


def test_extract_concepts_with_canned_response() -> None:
    import hashlib

    unit = KnowledgeUnit(
        unit_id="src001#1",
        kind="narrative",
        content_md="P-Laser cable info",
        locator="doc:1",
    )

    canned_output = json.dumps(
        {
            "candidates": [
                {
                    "name": "P-Laser 320kV",
                    "entity_id_proposal": "prod.cable.p-laser-320kv",
                    "summary": "A high-voltage cable.",
                    "is_new": True,
                    "related_existing": [],
                }
            ]
        }
    )

    system = (
        "You are an extraction engine. Given a knowledge unit, identify concept candidates.\n"
        "Return structured JSON with a list of candidates.\n"
        "Each candidate has: name, entity_id_proposal (dot-separated lowercase), "
        "summary, is_new (true if not in existing index), related_existing (entity_ids from index)."
    )
    user = (
        "## Existing entity index\n(empty)\n\n"
        "## Knowledge unit [narrative]\nLocator: doc:1\n\nP-Laser cable info"
    )
    content = system + user
    key = hashlib.sha256(content.encode()).hexdigest()[:16]

    provider = MockProvider(canned={key: canned_output})
    sink = ListSink()

    results = extract_concepts(
        units=[unit],
        source_id="src001",
        existing_index=[],
        provider=provider,
        model="test-model",
        sink=sink,
    )
    assert len(results) == 1
    assert len(results[0].candidates) == 1
    c = results[0].candidates[0]
    assert c.name == "P-Laser 320kV"
    assert c.entity_id_proposal == "prod.cable.p-laser-320kv"
    assert c.is_new is True


def test_extract_concepts_empty_units(mock_provider: MockProvider) -> None:
    sink = ListSink()
    results = extract_concepts(
        units=[],
        source_id="src001",
        existing_index=[],
        provider=mock_provider,
        model="test-model",
        sink=sink,
    )
    assert results == []
    assert len(sink.entries) == 0
